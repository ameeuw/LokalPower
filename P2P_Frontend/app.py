# -*- coding: utf-8 -*-

import glob
import os.path
import pandas as pd
import ast
import math
from operator import itemgetter
import numpy as np
from flask import Flask, render_template, url_for, request, send_file
from geopy.distance import vincenty
import pickle
from datetime import datetime
from datetime import timedelta
import calendar
import locale
import base64
import json

locale.setlocale(locale.LC_ALL, 'de_CH')

import Algos as ag


def setup_data():
    # define global variables
    global locations
    global descriptions
    global descriptions_df
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
    #prosumer = 15
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

    year = 2016
    periods = {}

    print('Building monthly period')
    periods['monthly'] = get_period()

    print('Building daily periods')
    periods['daily'] = {}
    for month_index in range(0, 12):
        # print('Building {}'.format(month))
        periods['daily'][month_index] = get_period(resolution='daily', month_index=month_index)

    print('Building minimal periods')
    periods['minimal'] = {}
    for month_index in range(0, 12):
        last_day_in_month = calendar.monthrange(year, month_index+1)[1]
        for day_index in range(0, last_day_in_month):
            date = datetime.strptime('{} {} {}'.format(day_index+1, month_index+1, year), '%d %m %Y')
            day_index = date.timetuple().tm_yday-1
            print("day_index = {}".format(day_index))
            periods['minimal'][day_index] = get_period(resolution='minimal', day_index=day_index)

    user.periods = periods

    #print('user.periods.keys() = {}'.format(user.periods.keys()))
    #print('user.periods["daily"].keys() = {}'.format(user.periods['daily'].keys()))


def set_period(resolution='monthly', month_index=None, day_index=None):

    if resolution == 'daily':
        if month_index is None:
            month_index = 6
        if hasattr(user, 'periods') :
            if resolution in user.periods.keys():
                if month_index in user.periods[resolution].keys():
                    user.period = user.periods[resolution][month_index]
            else:
                user.period = get_period(resolution, month_index=month_index)

    elif resolution == 'minimal':
        if day_index is None:
            day_index=150
        if hasattr(user, 'periods'):
            if resolution in user.periods.keys():
                if day_index in user.periods[resolution].keys():
                    user.period = user.periods[resolution][day_index]
            else:
                user.period = get_period(resolution, day_index=day_index)

    else:
        if hasattr(user, 'periods'):
            if 'monthly' in user.periods.keys():
                user.period = user.periods[resolution]
            else:
                user.period = get_period(resolution, month_index=month_index, day_index=day_index)


def get_period(resolution='monthly', month_index=None, day_index=None):
    DELTAT = 0.25

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
        if month_index is None:
            month_index = 0

        year = 2017
        day_index = 0
        month = month_index + 1
        last_day_in_month = calendar.monthrange(year, month)[1]

        start_date = datetime.strptime('{} {}'.format(month, year), '%m %Y')
        stop_date = datetime.strptime('{} {} {}'.format(last_day_in_month, month, year), '%d %m %Y')

        start = start_date.timetuple().tm_yday - 1
        stop = stop_date.timetuple().tm_yday

        # print("start = {} ; stop = {}".format(start, stop))

        name = datetime.strftime(start_date, '%B %Y')
        # print(name)

        categories = []
        for day in range(0, last_day_in_month):
            current_date = start_date + timedelta(days=day)
            categories.append(datetime.strftime(current_date, '%a, %d.%m.'))

        # categories = range(1, last_day_in_month+1)

        demand = user.demand_by_day[start:stop]
        production = user.production_by_day[start:stop]
        timely_aggregated_connections = user.daily_aggregated_connections[start:stop]
        aggregated_connections = user.aggregate_daily_connections(user.daily_aggregated_connections[start:stop])
        aggregated_deliveries = user.aggregate_daily_deliveries(user.daily_aggregated_deliveries[start:stop])
        timely_aggregated_deliveries = user.daily_aggregated_deliveries[start:stop]
        battery_simulation['battery_to_load'] = user.battery_simulation['daily_b2l'][start:stop]

    elif resolution == 'minimal':
        # View 24 hours with data by 15 minutes

        DELTAT = 0.25

        if day_index is None:
            day_index = 244

        day_in_year = day_index + 1
        year = 2017


        start_date = datetime.strptime('{} {}'.format(day_in_year, year), '%j %Y')
        month_index = start_date.timetuple().tm_mon - 1

        if (day_in_year == 365) or (day_in_year == 366):
            stop = int(day_in_year * 24 / DELTAT)
        else:
            stop_date = datetime.strptime('{} {}'.format(day_in_year + 1, year), '%j %Y')
            stop = int((stop_date.timetuple().tm_yday - 1) * 24 / DELTAT)

        start = int((start_date.timetuple().tm_yday - 1) * 24 / DELTAT)

        name = datetime.strftime(start_date, '%A %-d. %B %Y')
        #print(name)

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
        month_index = 0
        day_index = 0
        start = 0
        stop = 35136
        resolution = 'monthly'
        name = 'Jahr 2017'
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
            elif (s_distance > 10) and (s_distance < 60) and (s_id != 'GRID'):
                s_category = 'grisons'
            elif (s_distance > 60) or (s_id == 'GRID'):
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


    distance_energy_sum = 0
    for s_id, connections in detail_connections.iteritems():
        s_distance = round(vincenty(user.location, locations[s_id]).km, 2)
        energy_sum = sum(connections)
        distance_energy_sum += s_distance * energy_sum

    kpi_autarky = 0
    kpi_mean_distance = 0
    if sum_consumption > 0:
        kpi_autarky = round(sum_self_consumption / sum_consumption * 100, 2)
        kpi_mean_distance = round(distance_energy_sum / sum_consumption, 2)


    period['resolution'] = resolution
    period['month_index'] = month_index
    period['day_index'] = day_index
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
    period['kpi_mean_distance'] = kpi_mean_distance
    period['battery_simulation'] = battery_simulation

    return period

def generate_map_json(aggregated, type='sources', root='http://127.0.0.1:5000/'):
    map_dictionary = {'markers':[],'paths':[]}

    for s_id, supplyDict in aggregated.iteritems():
        if s_id != 'GRID':
            if (locations[s_id] != user.location):

                if type == "sinks":
                    share = aggregated[s_id]['energy'] / user.period['sum_production'] / 10
                else:
                    share = aggregated[s_id]['energy'] / user.period['sum_consumption'] / 10

                if (descriptions[s_id]['KIND'] == 'plant'):
                    iframe = render_template('tooltip.html', photo=descriptions_df.loc[s_id]['PHOTO'],
                                             name=descriptions[s_id]['NAME'], share=share,
                                             supplierId=s_id, kind='plant', root=root)
                else:
                    if descriptions[s_id]['ANONYMITY'] == True:
                        name = 'Nachbar'
                    else:
                        name = descriptions[s_id]['NAME']

                    iframe = render_template('tooltip.html', photo=descriptions_df.loc[s_id]['PHOTO'],
                                             name=name, share=share,
                                             supplierId=s_id, kind=descriptions_df.loc[s_id]['KIND'], root=root)

                marker_dictionary = {}
                marker_dictionary['icon'] = '{}.png'.format(descriptions[s_id]['TYPE'])
                marker_dictionary['location'] = locations[s_id]
                marker_dictionary['iframe_b64'] = base64.b64encode(iframe.encode('utf-8'))
                map_dictionary['markers'].append(marker_dictionary)
                map_dictionary['paths'].append([user.location, locations[s_id]])


    if user.period['sum_production'] > 0:

        if type=="sinks":
            share = aggregated[user.index]['energy'] / user.period['sum_production'] / 10
        else:
            share = aggregated[user.index]['energy'] / user.period['sum_consumption'] / 10
    else:
        share = 0

    iframe = render_template('tooltip.html', photo=descriptions_df.loc[user.index]['PHOTO'],
                             name=descriptions[user.index]['NAME'], share=share,
                             supplierId=user.index, kind='self', root=root)

    marker_dictionary = {}
    marker_dictionary['icon'] = 'house.png'
    marker_dictionary['location'] = user.location
    marker_dictionary['iframe_b64'] = base64.b64encode(iframe)
    map_dictionary['markers'].append(marker_dictionary)

    return json.dumps(map_dictionary)


app = Flask(__name__)


@app.before_first_request
def startup():
    setup_data()

app.config['DEBUG'] = True


@app.after_request
def add_header(response):
    response.cache_control.max_age = 0
    response.headers['Access-Control-Allow-Origin'] = "null"
    return response


@app.route("/")
def home():
    return render_template('dashboard.html', user=user, descriptions=descriptions, type='sources', origin='dashboard.html')

@app.route("/mbs1")
def mbs1():
    return render_template('mbs1.html', user=user, descriptions=descriptions, type='sources', origin='dashboard.html')
@app.route("/mbs2")
def mbs2():
    return render_template('mbs2.html', user=user, descriptions=descriptions, type='sources', origin='dashboard.html')



@app.route("/osmaps/<string:type>/")
def osmaps(type='sources'):
    return render_template('maps.html', user=user, descriptions=descriptions, type=type, origin='maps.html', root=request.url_root)


@app.route("/details/<string:type>/")
def details(type='sources'):
    return render_template('details.html', user=user, descriptions=descriptions, type=type, origin='details.html', root=request.url_root)


@app.route("/battery", methods=["GET","POST"])
def battery():
    set_period()
    EbatR=4.0
    if request.method=='POST':
        EbatR=float(request.form['BatteryCapacity'])

    user.prosumerSim(EbatR=EbatR)

    return render_template('batterySim.html', user=user, BatterySize=EbatR, origin='batterySim.html', type='sources')


@app.route('/descriptions_json/')
def descriptions_json():
    desc = {}
    for s_id, description in descriptions.iteritems():
        desc[s_id] = {}
        desc[s_id]['name'] = description['NAME']
        desc[s_id]['type'] = description['TYPE']
    return json.dumps(desc)


@app.route('/period_json/')
def period_json():
    return json.dumps(user.period)


@app.route('/map_json/<string:type>/')
def maps_json(type='sources'):
    if type=="sinks":
        maps_json = generate_map_json(user.period['aggregated_deliveries'], type, request.url_root)
    else:
        maps_json = generate_map_json(user.period['aggregated_connections'], 'sources', request.url_root)

    return maps_json


@app.route("/setResolution/<string:resolution>/")
def setResolution(resolution='monthly'):
    set_period(resolution=resolution)
    print('Setting user resolution to {}'.format(resolution))
    return json.dumps(user.period)

@app.route("/setMinimalPeriod/<int:day>/")
def setMinimalPeriod(day=10):
    set_period('minimal', month_index=None, day_index=day)
    return json.dumps(user.period)

@app.route("/setDailyPeriod/<int:month>/")
def setDailyPeriod(month=0):
    set_period('daily', month_index=month)
    return json.dumps(user.period)

@app.route("/move", methods=['GET','POST'])
def move():
    direction = 'next'
    if request.method=='POST':
        direction = request.form['direction']

    if direction == 'up':
        if user.period['resolution'] == 'minimal':
            set_period('daily', month_index=user.period['month_index'])
        else:
            set_period('monthly')
    else:

        if user.period['resolution'] == 'daily':
            if direction == 'next':
                month_index = user.period['month_index'] + 1
            elif direction == 'previous':
                month_index = user.period['month_index'] - 1

            limit_value = 11
            month_index = min(limit_value, month_index)
            set_period('daily', month_index=month_index)

        elif user.period['resolution'] == 'minimal':
            if direction == 'next':
                day_index = user.period['day_index'] + 1
            elif direction == 'previous':
                day_index = user.period['day_index'] - 1

            limit_value = 365
            day_index = min(limit_value, day_index)
            set_period('minimal', day_index=day_index)

    return json.dumps(user.period)

if __name__ == "__main__":
    #setup_data()
    app.run(threaded=True, host='0.0.0.0')
