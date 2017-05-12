import glob
import folium
import os.path
import pandas as pd
import ast
import math
from operator import itemgetter

import numpy as np
from flask import Flask, render_template, url_for, request, send_file
from flask_script import Manager
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
    # STEERCO: 5
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
        user.setUserDict('../Daten/dicts/{}.pickle'.format(user_index))

        #print('aggregated connections.')
        #user.setAggregatedConnections()

        print('producer data.')
        user.setProducerDict('../Daten/dicts/prod_{}.pickle'.format(user_index))

        # print('aggregated deliveries.')
        # user.setAggregatedDeliveries()

        print('daily aggregated connections.')
        user.setDailyAggregatedConnections()
        print('monthly aggregated connections')
        user.setMonthlyAggregatedConnections()
        print('aggregate connections.')
        user.aggregatedConnections = user.aggregateDailyConnections(user.dailyAggregatedConnections)

        print('daily aggregated deliveries.')
        user.setDailyAggregatedDeliveries()
        print('monthly aggregated deliveries')
        user.setMonthlyAggregatedDeliveries()
        print('aggregate deliveries.')
        user.aggregatedDeliveries = user.aggregateDailyConnections(user.dailyAggregatedDeliveries)

        print('battery simulation size: S')
        user.prosumerSim(EbatR=4.0)

        print('saving user_data')
        pickle.dump(user, open('../Daten/user_data/user_{}.pickle'.format(user_index), "wb"))

    print('Done.')

    #init_period()
    get_period()


def get_period(resolution='monthly', month=None, day=None):
    DELTAT = 0.25
    monthNumbers = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'Mai': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Okt': 10,
                    'Nov': 11, 'Dez': 12}

    monthNames =  {'Jan':'Januar', 'Feb':'Februar', 'Mar':'Maerz', 'Apr':'April', 'Mai':'Mai', 'Jun':'Juni',
                   'Jul':'Juli', 'Aug':'August', 'Sep':'September', 'Okt':'Oktober', 'Nov':'November', 'Dez':'Dezember'}

    monthNameArray = ['Januar', 'Februar', 'Maerz', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober',
                  'November', 'Dezember']

    MONTHVEC = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

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

        demand = user.demandByDay[start:stop]
        production = user.productionByDay[start:stop]
        timely_aggregated_connections = user.dailyAggregatedConnections[start:stop]
        aggregated_connections = user.aggregateDailyConnections(user.dailyAggregatedConnections[start:stop])

        timely_aggregated_deliveries = user.dailyAggregatedDeliveries[start:stop]
        battery_simulation['battery_to_load'] = user.daily_b2l[start:stop]

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

        for timeSlice in range(start, stop):
            aggregatedConnections = {}
            if timeSlice in user.connections.keys():
                timeSliceConnections = user.connections[timeSlice]
                for connection in timeSliceConnections:
                    fromId = connection['fromId']
                    if fromId not in aggregatedConnections.keys():
                        aggregatedConnections[fromId] = {}
                        aggregatedConnections[fromId]['energy'] = connection['energy'] * DELTAT
                        aggregatedConnections[fromId]['location'] = connection['from']
                    else:
                        aggregatedConnections[fromId]['energy'] += connection['energy'] * DELTAT

            timely_aggregated_connections.append(aggregatedConnections)


        aggregated_connections = user.getAggregatedConnections(start, stop)



        for timeSlice in range(start, stop):
            aggregatedDeliveries = {}
            if timeSlice in user.deliveries.keys():
                timeSliceDeliveries = user.deliveries[timeSlice]
                for delivery in timeSliceDeliveries:
                    toId = delivery['toId']
                    if toId not in aggregatedDeliveries.keys():
                        aggregatedDeliveries[toId] = {}
                        aggregatedDeliveries[toId]['energy'] = delivery['energy'] * DELTAT
                        aggregatedDeliveries[toId]['location'] = delivery['to']
                    else:
                        aggregatedDeliveries[toId]['energy'] += delivery['energy'] * DELTAT

            timely_aggregated_deliveries.append(aggregatedDeliveries)

        aggregated_deliveries = user.getAggregatedDeliveries(start, stop)

        battery_simulation['battery_to_load'] = (np.multiply(user.B2L[start:stop], DELTAT)).tolist()

    else:
        # Default to full year, data by month
        start = 0
        stop = 35136
        resolution = 'monthly'
        name = 'Jahr 2016'
        categories = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
        demand = user.demandByMonth
        production = user.productionByMonth
        timely_aggregated_connections = user.monthlyAggregatedConnections
        aggregated_connections = user.aggregateDailyConnections(user.dailyAggregatedConnections)

        timely_aggregated_deliveries = user.monthlyAggregatedDeliveries
        aggregated_deliveries = user.aggregateDailyDeliveries(user.dailyAggregatedDeliveries)

        battery_simulation['battery_to_load'] = user.monthly_b2l



    # print('sum(demandByMonth: {} {}'.format(sum(demand), demand))
    # print('sum(productionByMonth: {} {}'.format(sum(production), production))


    # Fill detail_connections
    for connections in timely_aggregated_connections:
        for supplier_id in connections.keys():
            if supplier_id not in detail_connections.keys():
                detail_connections[supplier_id] = []

    for connections in timely_aggregated_connections:
        for supplier_id, connection in connections.iteritems():
            detail_connections[supplier_id].append(connection['energy'] / 1000)

        for supplier_id in detail_connections.keys():
            if supplier_id not in connections.keys():
                detail_connections[supplier_id].append(0)


    # Fill detail deliveries
    for deliveries in timely_aggregated_deliveries:
        for sink_id in deliveries.keys():
            if sink_id not in detail_deliveries.keys():
                detail_deliveries[sink_id] = []

    for deliveries in timely_aggregated_deliveries:
        for sink_id, delivery in deliveries.iteritems():
            detail_deliveries[sink_id].append(delivery['energy'] / 1000)

        for sink_id in detail_deliveries.keys():
            if sink_id not in deliveries.keys():
                detail_deliveries[sink_id].append(0)


    categorized_connections = {'self': {'sum': 0, 'list': [], 'time_series': np.zeros(len(categories)).tolist()},
                               'local': {'sum': 0, 'list': [], 'time_series': np.zeros(len(categories)).tolist()},
                               'grisons': {'sum': 0, 'list': [], 'time_series': np.zeros(len(categories)).tolist()},
                               'other': {'sum': 0, 'list': [], 'time_series': np.zeros(len(categories)).tolist()}}

    # Fill categorized_connections
    for supplier_id, connections in detail_connections.iteritems():
        supplier_distance = round(vincenty(user.location, locations[supplier_id]).km, 2)
        list_entry = {}

        list_entry['supplier_id'] = supplier_id
        list_entry['distance'] = supplier_distance
        list_entry['energy'] = sum(connections)

        supplier_category = 'other'
        if (supplier_id == user.index):
            supplier_category = 'self'
        elif supplier_distance < 10:
            supplier_category = 'local'
        elif (supplier_distance > 10) and (supplier_distance < 30) and (supplier_id != 'GRID'):
            supplier_category = 'grisons'
        elif (supplier_distance > 30) or (supplier_id == 'GRID'):
            supplier_category = 'other'

        #print('LEN(CONNECTIONS: {}'.format(len(connections)))

        categorized_connections[supplier_category]['sum'] += sum(connections)
        categorized_connections[supplier_category]['list'].append(list_entry)
        categorized_connections[supplier_category]['time_series'] = np.add(categorized_connections[supplier_category]['time_series'], connections).tolist()



    # sort lists by energy
    categorized_connections['local']['list'] = sorted(categorized_connections['local']['list'], key=itemgetter('energy'), reverse=True)
    categorized_connections['grisons']['list'] = sorted(categorized_connections['grisons']['list'], key=itemgetter('energy'), reverse=True)
    categorized_connections['other']['list'] = sorted(categorized_connections['other']['list'], key=itemgetter('energy'), reverse=True)

    categorized_deliveries = {'self': {'sum': 0, 'list': [], 'time_series': np.zeros(len(categories)).tolist()},
                               'local': {'sum': 0, 'list': [], 'time_series': np.zeros(len(categories)).tolist()},
                               'grisons': {'sum': 0, 'list': [], 'time_series': np.zeros(len(categories)).tolist()},
                               'other': {'sum': 0, 'list': [], 'time_series': np.zeros(len(categories)).tolist()}}

    # Fill categorized_deliveries
    for sink_id, deliveries in detail_deliveries.iteritems():
        sink_distance = round(vincenty(user.location, locations[sink_id]).km, 2)

        list_entry = {}
        list_entry['sink_id'] = sink_id
        list_entry['distance'] = sink_distance
        list_entry['energy'] = sum(deliveries)

        sink_category = 'other'
        if (sink_id == user.index):
            sink_category = 'self'
        elif sink_distance < 10:
            sink_category = 'local'
        elif (sink_distance > 10) and (sink_distance < 30) and (sink_id != 'GRID'):
            sink_category = 'grisons'
        elif (sink_distance > 30) or (sink_id == 'GRID'):
            sink_category = 'other'

        categorized_deliveries[sink_category]['sum'] += sum(deliveries)
        categorized_deliveries[sink_category]['list'].append(list_entry)
        categorized_deliveries[sink_category]['time_series'] = np.add(categorized_deliveries[supplier_category]['time_series'], deliveries).tolist()

    # print('CAT_CONNECTIONS: {}'.format(categorized_deliveries['local']['time_series']))
    # print('CAT_CONNECTIONS: {}'.format(categorized_deliveries['other']['time_series']))
    # print('CAT_DELIVERIES: {}'.format(categorized_deliveries))

    # sort lists by energy
    categorized_deliveries['local']['list'] = sorted(categorized_deliveries['local']['list'], key=itemgetter('energy'), reverse=True)
    categorized_deliveries['grisons']['list'] = sorted(categorized_deliveries['grisons']['list'], key=itemgetter('energy'), reverse=True)
    categorized_deliveries['other']['list'] = sorted(categorized_deliveries['other']['list'], key=itemgetter('energy'), reverse=True)

    # print('\ncategorized_deliveries\n{}'.format(categorized_deliveries))

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

    user.period['resolution'] = resolution
    user.period['start'] = start
    user.period['stop'] = stop
    user.period['name'] = name
    user.period['categories'] = categories
    user.period['demand'] = demand
    user.period['production'] = production
    user.period['aggregated_connections'] = aggregated_connections
    user.period['timely_aggregated_connections'] = timely_aggregated_connections
    user.period['detail_connections'] = detail_connections
    user.period['categorized_connections'] = categorized_connections
    user.period['aggregated_deliveries'] = aggregated_deliveries
    user.period['timely_aggregated_deliveries'] = timely_aggregated_deliveries
    user.period['detail_deliveries'] = detail_deliveries
    user.period['categorized_deliveries'] = categorized_deliveries
    user.period['self_consumption'] = self_consumption
    user.period['sum_consumption'] = sum_consumption
    user.period['sum_production'] = sum_production
    user.period['sum_self_consumption'] = sum_self_consumption
    user.period['kpi_self_consumption'] = kpi_self_consumption
    user.period['kpi_autarky'] = kpi_autarky
    user.period['battery_simulation'] = battery_simulation

    print('Getting {} data ({} - {})'.format(resolution, start, stop))
    generateMap(user.period['aggregated_connections'], 'sources_map.html')
    #print('\n\nGENERATING SOURCES MAP USING:\n\n{}\n\n'.format(user.period['aggregated_connections']))
    generateMap(user.period['aggregated_deliveries'], 'sinks_map.html')
    #print('\n\nGENERATING SINKS MAP USING:\n\n{}\n\n'.format(user.period['aggregated_deliveries']))

# google Maps Object

def generateMap(aggregatedConnections, file_name='sources_map.html'):
    photo_dict = {'Hydro1' : 'hydro_klosters.jpeg', 'Hydro2' : 'hydro_kueblis.jpeg', 'Biogas' : 'biomass_raps.jpeg',
                  'PV1': 'solar_bauernhof.jpeg', 'PV2' : 'solar_molkerei.jpeg'}
    description_texts = {'Hydro1' : 'hydro_klosters.jpeg', 'Hydro2' : 'hydro_kueblis.jpeg', 'Biogas' : 'biomass_raps.jpeg',
                  'PV1': 'solar_bauernhof.jpeg', 'PV2' : 'solar_molkerei.jpeg'}
    print("generating osmap")

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


    for supplierId, supplyDict in aggregatedConnections.iteritems():
        if supplierId != 'GRID':
            if (locations[supplierId] != user.location):
                icon = folium.features.CustomIcon('static/img/markers/{}.png'.format(descriptions[supplierId]['TYPE']),
                                                  icon_size=icon_size)

                if (descriptions[supplierId]['KIND'] == 'plant'):
                    print('img: {} {}'.format(supplierId, photo_dict[supplierId]))
                    html = """
                        <img src="http://127.0.0.1:5000/static/img/photos/{photo}" style="width: 136px; height: 69px">
                        <h4>{name}</h4><br>
                        
                        <p>
                        </p>
                        """.format(name=descriptions[supplierId]['NAME'], photo=photo_dict[supplierId])

                    iframe = folium.IFrame(html=render_template('tooltip.html', photo=photo_dict[supplierId],
                                                                name=descriptions[supplierId]['NAME'],
                                                                supplierId=supplierId),
                                           width=360, height=250)
                else:
                    html = """
                        <h3>{name}</h3><br>
                        Einfacher Text mit Zusammenfassssung und Bild
                        <p>
                        </p>
                        """.format(name=descriptions[supplierId]['NAME'])
                    iframe = folium.IFrame(html=html, width=200, height=150)


                popup = folium.Popup(iframe, max_width=2650)

                folium.Marker(locations[supplierId], popup=popup, icon=icon).add_to(osmap)

                folium.PolyLine([user.location, locations[supplierId]], color="red", weight=2.5, opacity=.6).add_to(osmap)

    osmap.save(file_name)

    return 0


def getMarkerList(aggregatedConnections):
    kWhBySource = user.getKWhBySource()
    autarky, selfConsumption = user.getAutarkySelfConsumption()

    # Only print values on map with more than 1 % share.
    filterValue = 0.005

    markerList = []
    paths = []

    markerList.append({
        'icon': 'static/img/house.png',
        'lat': user.location[0],
        'lng': user.location[1],
        'infobox': "<b>Das sind Sie, {}</b><br>"
                   "Jahresverbrauch: {:.2f} kWh<br>"
                   "Jahreserzeugung: {:.2f}<br>"
                   "Periodenverbrauch: {:.2f}<br>"
                   "Eigenverbrauch: {:.2f} %<br>"
                   "Autarkie: {:.2f} %".format(descriptions[user.index]['NAME'],
                                               user.annualDemand,
                                               user.annualProduction,
                                               np.sum(kWhBySource) / 1000,
                                               selfConsumption * 100,
                                               autarky * 100)
    })

    for supplierId, supplyDict in aggregatedConnections.iteritems():
        if supplierId != 'GRID':
            if (locations[supplierId] != user.location):
                iconFile = 'static/img/solar_small.png'

                if (supplierId == 'Hydro1') or (supplierId == 'Hydro2'):
                    iconFile = 'static/img/hydro_small.png'

                if (supplierId == 'Biogas'):
                    iconFile = 'static/img/biomass_small.png'

                if (supplierId == 'Wind'):
                    iconFile = 'static/img/wind_small.png'

                supplierShare = (supplyDict['energy'] / 1000.) / (np.sum(kWhBySource) / 1000)
                suppliedEnergy = supplyDict['energy'] / 1000

                if supplierShare > filterValue:
                    markerList.append({
                        'icon': iconFile,
                        'lat': locations[supplierId][0],
                        'lng': locations[supplierId][1],
                        'infobox': "<b>Supplier</b><br>"
                                   "{}<br>"
                                   "Bezogen: {:.2f} kWh<br>"
                                   "Anteil: {:.1f} %".format(descriptions[supplierId]['NAME'],
                                                             suppliedEnergy,
                                                             supplierShare * 100)
                        })
                    paths.append([user.location, locations[supplierId]])
    return markerList, paths

# TODO: welchen kpi brauchst du? Autarkie oder Eigenverbrauch
app = Flask(__name__)

@app.before_first_request
def startup():
    setup_data()
    print("database tables created")

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

@app.route("/maps")
def maps():
    supplierIdsOrdered, kWhSharesBySourceOrdered, dFromUserordered = getOrderedItems(getDFromUser(), user.getKWhBySource())
    markerList, paths = getMarkerList(user.aggregatedConnections)
    sndmap = Map(
        identifier="sndmap",
        lat=user.location[0],
        lng=user.location[1],
        style="",
        markers = markerList,
        polylines = paths
    )
    return render_template('maps.html', sndmap=sndmap, user=user, producerNames=supplierIdsOrdered, kWh_SharesBySource=kWhSharesBySourceOrdered.tolist(), dFromUserordered=dFromUserordered, descriptions=descriptions)

@app.route("/osmaps/<string:type>/")
def osmaps(type='sources'):
    #generateMap(user.period['aggregated_connections'])
    return render_template('maps.html', user=user, descriptions=descriptions, type=type, origin='maps.html')


@app.route("/sinks")
def sinks():
    markerList, paths = getMarkerList(user.aggregatedDeliveries)
    sndmap = Map(
        identifier="sndmap",
        lat=user.location[0],
        lng=user.location[1],
        style="",
        markers = markerList,
        polylines = paths,
        cluster = True
    )
    return render_template('maps.html', sndmap=sndmap, user=user, origin='maps.html')


@app.route("/details/osmaps/<string:type>/")
def details(type='sources'):

    return render_template('details.html', user=user, descriptions=descriptions, type=type, origin='details.html')


@app.route("/setResolution/<string:resolution>/")
def setResolution(resolution='monthly'):
    get_period(resolution = resolution)

    print('Setting user resolution to {}'.format(resolution))

    return render_template('dashboard.html', user=user, descriptions=descriptions, origin='dashboard.html')

@app.route("/getLast24hours/<int:month>/<int:day>")
def getLast24hours(month=244, day=10):
    get_period('minimal', month=month, day=day)

    return render_template('dashboard.html', user=user, descriptions=descriptions, origin='dashboard.html')


@app.route("/getMonthlyGraph/<string:month>/")
def getMonthlyGraph(month='Jan'):
    get_period('daily', month=month)

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

    get_period('daily', month=month_name)


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
