import glob
import folium
import os.path
import pandas as pd
import ast
import math
from operator import itemgetter
import time

import numpy as np
from flask import Flask, render_template, url_for, request, send_file
from flask_googlemaps import Map, GoogleMaps
from geopy.distance import vincenty
import pickle

import Algos as ag


def setup_data():
    # define global variables
    global locations
    global descriptions
    global user

    # load consumption file
    print('Loading data...')
    print('locations.')
    locations = pickle.load(open('../Daten/users/locations.pickle', "rb"))
    print('descriptions.')
    descriptions = pickle.load(open('../Daten/users/descriptions.pickle', "rb"))
    descriptions_df = pd.read_excel('../Daten/users/descriptions.xlsx')
    descriptions_df = descriptions_df.set_index('ID')

    prosumer = 5
    #userId = locations.keys()[prosumer]
    user_index = descriptions_df.index[prosumer]
    user_location = ast.literal_eval(descriptions_df.loc[user_index]['LOCATION'])
    print(descriptions_df.loc[user_index]['NAME'])
    print(user_index)
    print('user data.')
    if os.path.isfile('../Daten/user_data/user_{}.pickle'.format(user_index)):
        print('loading from pickle')
        user = pickle.load(open('../Daten/user_data/user_{}.pickle'.format(user_index), 'rb'))
    else:
        print('generating from sources...')
        user = ag.User('../Daten/users/{}.csv'.format(user_index), user_location, user_index)
        user.set_user_dict('../Daten/dicts/{}.pickle'.format(user_index))

        print('producer data.')
        user.set_producer_dict('../Daten/dicts/prod_{}.pickle'.format(user_index))

        print('daily aggregated connections.')
        user.set_daily_aggregated_connections()
        print('monthly aggregated connections')
        user.set_monthly_aggregated_connections()
        print('aggregate connections.')
        user.aggregated_connections = user.aggregate_daily_connections(user.daily_aggregated_connections)

        print('daily aggregated deliveries.')
        user.set_daily_aggregated_deliveries()
        print('monthly aggregated deliveries')
        user.set_monthly_aggregated_deliveries()
        print('aggregate deliveries.')
        user.aggregated_deliveries = user.aggregate_daily_deliveries(user.daily_aggregated_deliveries)

        print('battery simulation size: S')
        user.prosumerSim(EbatR=4.0)

        print('building periods')
        build_periods()

        print('saving user_data')
        pickle.dump(user, open('../Daten/user_data/user_{}.pickle'.format(user_index), "wb"))

    print('Done.')

    set_period()


def build_periods():
    periods = {}
    monthNumbers = {'Jan': 0, 'Feb': 1, 'Mar': 3, 'Apr': 4, 'Mai': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9,
                    'Okt': 10,
                    'Nov': 11, 'Dez': 12}

    MONTHVEC = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    print('Building monthly period')
    periods['monthly'] = get_period()

    print('Building daily periods')
    periods['daily'] = {}
    for month in monthNumbers.keys():
        # print('Building {}'.format(month))
        periods['daily'][month] = get_period(resolution='daily', month=month)

    print('Building minimal periods')
    periods['minimal'] = {}
    month = 0
    for i in range(len(MONTHVEC)-1):
        days_in_month = MONTHVEC[i]
        month += days_in_month
        periods['minimal'][month] = {}
        # print('month = {}'.format(month))

        for day in range(MONTHVEC[i+1]):
            #print('day = {}'.format(day+1))
            periods['minimal'][month][day+1] = get_period(resolution='minimal', month=month, day=day+1)
    user.periods = periods

    # print('user.periods.keys() = {}'.format(user.periods.keys()))
    # print('user.periods["daily"].keys() = {}'.format(user.periods['daily'].keys()))


def set_period(resolution='monthly', month=None, day=None):

    if resolution == 'daily':
        if hasattr(user, 'periods'):
            if resolution in user.periods.keys():
                print(month)

                if month in user.periods[resolution].keys():
                    user.period = user.periods[resolution][month]
                else:
                    user.period = get_period(resolution, month, day)

    elif resolution == 'minimal':
        if hasattr(user, 'periods'):
            if resolution in user.periods.keys():
                if month in user.periods[resolution].keys():
                    if day in user.periods[resolution][month].keys():
                        user.period = user.periods[resolution][month][day]
                    else:
                        user.period = get_period(resolution, month, day)

    else:
        if hasattr(user, 'periods'):
            if 'monthly' in user.periods.keys():
                user.period = user.periods[resolution]
            else:
                user.period = get_period(resolution, month, day)


def get_period(resolution='monthly', month=None, day=None):
    DELTAT = 0.25
    monthNumbers = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'Mai': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Okt': 10,
                    'Nov': 11, 'Dez': 12}

    monthNames =  {'Jan':'Januar', 'Feb':'Februar', 'Mar':'Maerz', 'Apr':'April', 'Mai':'Mai', 'Jun':'Juni',
                   'Jul':'Juli', 'Aug':'August', 'Sep':'September', 'Okt':'Oktober', 'Nov':'November', 'Dez':'Dezember'}

    monthNameArray = ['Januar', 'Februar', 'Maerz', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober',
                  'November', 'Dezember']

    MONTHVEC = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    period = {}
    start = 0
    stop = 0
    name = ''
    categories = []
    demand = []
    production = []
    timely_aggregated_connections = []
    aggregated_connections = {}
    detail_connections = {}

    timely_aggregated_deliveries = []
    aggregated_deliveries = {}
    detail_deliveries = {}

    battery_simulation = {}

    if resolution == 'daily':
        # View month with data by day
        if (month is not None) and (month in monthNames.keys()):
            start = sum(MONTHVEC[0:monthNumbers[month]])
            stop = sum(MONTHVEC[0:monthNumbers[month]+1])
        else:
            # Default to January if month is not set
            start = 0
            stop = sum(MONTHVEC[0:2])
            month = 'Jan'

        name = '{} 2016'.format(monthNames[month])
        categories = range(1, MONTHVEC[monthNumbers[month]]+1)

        demand = user.demand_by_day[start:stop]
        production = user.production_by_day[start:stop]
        timely_aggregated_connections = user.daily_aggregated_connections[start:stop]
        aggregated_connections = user.aggregate_daily_connections(user.daily_aggregated_connections[start:stop])
        aggregated_deliveries = user.aggregate_daily_deliveries(user.daily_aggregated_deliveries[start:stop])
        timely_aggregated_deliveries = user.daily_aggregated_deliveries[start:stop]
        battery_simulation['battery_to_load'] = user.battery_simulation['daily_b2l'][start:stop]

    elif resolution == 'minimal':
        # View 24 hours with data by 15 minutes
        if (day is not None) and (month is not None):
            now = int( (month+day) *  24 / DELTAT)
            start = now - int(24 / DELTAT)
            stop = now
        else:
            # Default to specific day
            month = 244
            day = 6
            now = int((month + day) * 24 / DELTAT)
            start = now - int(24 / DELTAT)
            stop = now

        month_index = 0
        for days_in_month in MONTHVEC:
            month = month - days_in_month
            if month == 0:
                break
            month_index += 1
        month_name = monthNameArray[month_index]
        name = '{}. {} 2016'.format(day, month_name)

        categories = []
        for time_slice in range(start, stop):
            t = 15 * (time_slice - start)
            h = math.floor(t / 60) % 24
            m = (t % 60)
            time_string = '{:0>2}:{:0>2} Uhr'.format(int(h), m)
            categories.append(time_string)

        demand = np.multiply( user.demand[start:stop], DELTAT ).tolist()
        production = np.multiply( user.production[start:stop], DELTAT ).tolist()

        for time_slice in range(start, stop):
            timely_aggregated_connections.append(user.get_aggregated_connections(start=time_slice, stop=time_slice+1))
            timely_aggregated_deliveries.append(user.get_aggregated_deliveries(start=time_slice, stop=time_slice+1))

        aggregated_connections = user.get_aggregated_connections(start, stop)
        aggregated_deliveries = user.get_aggregated_deliveries(start, stop)

        battery_simulation['battery_to_load'] = (np.multiply(user.battery_simulation['B2L'][start:stop], DELTAT)).tolist()

    else:
        # Default to full year, data by month
        start = 0
        stop = 35136
        resolution = 'monthly'
        name = 'Jahr 2016'
        categories = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
        demand = user.demand_by_month
        production = user.production_by_month
        timely_aggregated_connections = user.monthly_aggregated_connections
        aggregated_connections = user.aggregate_daily_connections(user.daily_aggregated_connections)

        timely_aggregated_deliveries = user.monthly_aggregated_deliveries
        aggregated_deliveries = user.aggregate_daily_deliveries(user.daily_aggregated_deliveries)

        battery_simulation['battery_to_load'] = user.battery_simulation['monthly_b2l']



    # print('sum(demandByMonth: {} {}'.format(sum(demand), demand))
    # print('sum(productionByMonth: {} {}'.format(sum(production), production))


    # Fill details
    def get_details(timely_aggregated):
        details = {}
        for connections in timely_aggregated:
            for s_id in connections.keys():
                if s_id not in details.keys():
                    details[s_id] = []

        for connections in timely_aggregated:
            for s_id, connection in connections.iteritems():
                details[s_id].append(connection['energy'] / 1000)

            for s_id in details.keys():
                if s_id not in connections.keys():
                    details[s_id].append(0)
        return details

    def get_categorized(details):
        categorized = {'self': {'sum': 0, 'list': [], 'time_series': np.zeros(len(categories)).tolist()},
                       'local': {'sum': 0, 'list': [], 'time_series': np.zeros(len(categories)).tolist()},
                       'grisons': {'sum': 0, 'list': [], 'time_series': np.zeros(len(categories)).tolist()},
                       'other': {'sum': 0, 'list': [], 'time_series': np.zeros(len(categories)).tolist()}}

        for s_id, connections in details.iteritems():
            s_distance = round(vincenty(user.location, locations[s_id]).km, 2)
            list_entry = {}

            list_entry['s_id'] = s_id
            list_entry['distance'] = s_distance
            list_entry['energy'] = sum(connections)

            s_category = 'other'
            if (s_id == user.index):
                s_category = 'self'
            elif s_distance < 10:
                s_category = 'local'
            elif (s_distance > 10) and (s_distance < 30) and (s_id != 'GRID'):
                s_category = 'grisons'
            elif (s_distance > 30) or (s_id == 'GRID'):
                s_category = 'other'

            categorized[s_category]['sum'] += sum(connections)
            categorized[s_category]['list'].append(list_entry)
            categorized[s_category]['time_series'] = np.add(categorized[s_category]['time_series'], connections).tolist()

        # sort lists by energy
        categorized['local']['list'] = sorted(categorized['local']['list'], key=itemgetter('energy'), reverse=True)
        categorized['grisons']['list'] = sorted(categorized['grisons']['list'], key=itemgetter('energy'), reverse=True)
        categorized['other']['list'] = sorted(categorized['other']['list'], key=itemgetter('energy'), reverse=True)

        return categorized

    detail_connections = get_details(timely_aggregated_connections)
    detail_deliveries = get_details(timely_aggregated_deliveries)

    categorized_connections = get_categorized(detail_connections)
    categorized_deliveries = get_categorized(detail_deliveries)

    self_consumption = [0]
    if user.index in detail_connections:
        self_consumption = detail_connections[user.index]

    sum_consumption = round(sum(demand), 2)
    sum_production = round(sum(production), 2)
    sum_self_consumption = round(sum(self_consumption), 2)

    kpi_self_consumption = 0
    if sum_production > 0:
        kpi_self_consumption = round(sum_self_consumption / sum_production * 100, 2)

    kpi_autarky = 0
    if sum_consumption > 0:
        kpi_autarky = round(sum_self_consumption / sum_consumption * 100, 2)

    period['resolution'] = resolution
    period['start'] = start
    period['stop'] = stop
    period['name'] = name
    period['categories'] = categories
    period['demand'] = demand
    period['production'] = production
    period['aggregated_connections'] = aggregated_connections
    period['timely_aggregated_connections'] = timely_aggregated_connections
    period['detail_connections'] = detail_connections
    period['categorized_connections'] = categorized_connections
    period['aggregated_deliveries'] = aggregated_deliveries
    period['timely_aggregated_deliveries'] = timely_aggregated_deliveries
    period['detail_deliveries'] = detail_deliveries
    period['categorized_deliveries'] = categorized_deliveries
    period['self_consumption'] = self_consumption
    period['sum_consumption'] = sum_consumption
    period['sum_production'] = sum_production
    period['sum_self_consumption'] = sum_self_consumption
    period['kpi_self_consumption'] = kpi_self_consumption
    period['kpi_autarky'] = kpi_autarky
    period['battery_simulation'] = battery_simulation

    return period

# google Maps Object

def generate_map(aggregated_connections, file_name='sources_map.html'):
    photo_dict = {'Hydro1' : 'hydro_klosters.jpeg', 'Hydro2' : 'hydro_kueblis.jpeg', 'Biogas' : 'biomass_raps.jpeg',
                  'PV1': 'solar_bauernhof.jpeg', 'PV2' : 'solar_molkerei.jpeg'}
    description_texts = {'Hydro1' : 'hydro_klosters.jpeg', 'Hydro2' : 'hydro_kueblis.jpeg', 'Biogas' : 'biomass_raps.jpeg',
                  'PV1': 'solar_bauernhof.jpeg', 'PV2' : 'solar_molkerei.jpeg'}
    # print("generating osmap")

    osmap = folium.Map(location=user.location, tiles='Stamen Terrain', zoom_start=11, min_zoom=10)

    #osmap = folium.Map(location=user.location, zoom_start=11, min_zoom=10,
    #                   tiles = 'https://api.mapbox.com/styles/v1/tscheng805/cj2a7l00s004j2sn0f4a938in/tiles/256/{z}/{x}/{y}?access_token=pk.eyJ1IjoidHNjaGVuZzgwNSIsImEiOiJjajJhNzJ1cGIwMDBkMzNvNXdtbDJ5OHhyIn0.veVS3rSwK4U0NoHEWxXK1g',
    #                   attr = 'XXX Mapbox Attribution')

    # Only print values on map with more than 1 % share.
    filterValue = 0.005
    icon_size = (25, 25)
    html = """
        <h3>Das sind Sie!</h3><b>
        Einfacher Text mit Zusammenfassung und Bild
        <p>
        </p>
        """
    iframe = folium.IFrame(html=html, width=250, height=200)
    popup = folium.Popup(iframe, max_width=2650)
    icon = folium.Icon(icon='home', color='green')
    folium.Marker(user.location, popup=popup, icon=icon).add_to(osmap)


    for supplierId, supplyDict in aggregated_connections.iteritems():
        if supplierId != 'GRID':
            if (locations[supplierId] != user.location):
                icon = folium.features.CustomIcon('static/img/markers/{}.png'.format(descriptions[supplierId]['TYPE']),
                                                  icon_size=icon_size)

                if (descriptions[supplierId]['KIND'] == 'plant'):
                    iframe = folium.IFrame(html=render_template('tooltip.html', photo=photo_dict[supplierId],
                                                                name=descriptions[supplierId]['NAME'],
                                                                supplierId=supplierId),
                                           width=360, height=250)
                else:
                    if descriptions[supplierId]['ANONYMITY'] == True:
                        name = 'Nachbar'
                    else:
                        name = descriptions[supplierId]['NAME']
                    html = """
                        <h3>{name}</h3><br>
                        Einfacher Text mit Zusammenfassssung und Bild
                        <p>
                        </p>
                        """.format(name=name)
                    iframe = folium.IFrame(html=html, width=200, height=150)


                popup = folium.Popup(iframe, max_width=2650)

                folium.Marker(locations[supplierId], popup=popup, icon=icon).add_to(osmap)

                folium.PolyLine([user.location, locations[supplierId]], color="red", weight=2.5, opacity=.6).add_to(osmap)

    osmap.save(file_name)

    return 0


app = Flask(__name__)

@app.before_first_request
def startup():
    setup_data()

app.config['DEBUG'] = True

app.config['GOOGLEMAPS_KEY'] = "8JZ7i18MjFuM35dJHq70n3Hx4"

# Initialize the extension
GoogleMaps(app)

# app.before_first_request(setup_data)

@app.route("/")
def home():
    return render_template('dashboard.html', user=user, descriptions=descriptions, origin='dashboard.html')

@app.after_request
def add_header(response):
    response.cache_control.max_age = 30
    return response

@app.route('/os_maps')
def os_maps():
    return send_file('osmaps.html')


@app.route('/sources_maps')
def sources_maps():
    return send_file('sources_map.html')


@app.route('/sinks_maps')
def sinks_maps():
    return send_file('sinks_map.html')


@app.route("/osmaps/<string:type>/")
def osmaps(type='sources'):

    generate_map(user.period['aggregated_connections'], 'sources_map.html')
    #print('\n\nGENERATING SOURCES MAP USING:\n\n{}\n\n'.format(user.period['aggregated_connections']))
    generate_map(user.period['aggregated_deliveries'], 'sinks_map.html')
    #print('\n\nGENERATING SINKS MAP USING:\n\n{}\n\n'.format(user.period['aggregated_deliveries']))

    #generateMap(user.period['aggregated_connections'])
    return render_template('maps.html', user=user, descriptions=descriptions, type=type, origin='maps.html')


@app.route("/details/<string:type>/")
def details(type='sources'):

    return render_template('details.html', user=user, descriptions=descriptions, type=type, origin='details.html')


@app.route("/setResolution/<string:resolution>/")
def setResolution(resolution='monthly'):
    set_period(resolution = resolution)

    print('Setting user resolution to {}'.format(resolution))

    return render_template('dashboard.html', user=user, descriptions=descriptions, origin='dashboard.html')

@app.route("/getLast24hours/<int:month>/<int:day>")
def getLast24hours(month=244, day=10):
    set_period('minimal', month=month, day=day)

    return render_template('dashboard.html', user=user, descriptions=descriptions, origin='dashboard.html')


@app.route("/getMonthlyGraph/<string:month>/")
def getMonthlyGraph(month='Jan'):
    set_period('daily', month=month)

    return render_template('dashboard.html', user=user, descriptions=descriptions, origin='dashboard.html')


@app.route("/move", methods=['GET','POST'])
def move():
    origin = 'dashboard.html'
    start = 0
    direction = 'next'
    if request.method=='POST':
        origin = request.form['origin']
        start = int(request.form['start'])
        direction = request.form['direction']


    monthNameArray = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']

    MONTHVEC = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    month = start
    month_index = 0
    for days_in_month in MONTHVEC:
        month = month - days_in_month
        if month == 0:
            break
        month_index += 1

    limit_value = 0
    if user.period['resolution'] == 'daily':
        limit_value = 12 - 1
    else:
        limit_value = 366 - 1

    if direction == 'next':
        month_name = monthNameArray[min(limit_value, month_index+1)]
    else:
        month_name = monthNameArray[max(0, month_index-1)]


    print('\n\n')
    print("origin = {}".format(origin))
    print("start = {}".format(start))
    print("direction = {}".format(direction))
    print("month_name = {}".format(month_name))
    print('\n\n')

    set_period('daily', month=month_name)


    return render_template(origin, user=user, descriptions=descriptions, origin=origin)

@app.route("/batterySim", methods=["GET","POST"])
def batterySim():

    EbatR=0.0
    if request.method=='POST':
        EbatR=float(request.form['BatteryCapacity'])

    user.prosumerSim(EbatR=EbatR)

    return render_template('batterySim.html', user=user, BatterySize=EbatR, origin='batterySim.html')

if __name__ == "__main__":
    #setup_data()
    app.run(threaded=True)
