import glob
import folium
import os.path
import pandas as pd
import ast
import math

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
        print('aggregate deliveries.')
        user.aggregatedDeliveries = user.aggregateDailyConnections(user.dailyAggregatedDeliveries)


        print('saving user_data')
        pickle.dump(user, open('../Daten/user_data/user_{}.pickle'.format(user_index), "wb"))

    print('Done.')

    init_period()


def get_period(resolution='monthly', month=None, day=None):
    DELTAT = 0.25
    monthNumbers = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'Mai': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Okt': 10,
                    'Nov': 11, 'Dez': 12}

    monthNames =  {'Jan':'Januar', 'Feb':'Februar', 'Mar':'Maerz', 'Apr':'April', 'May':'Mai', 'Jun':'Juni',
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
    aggregated_connections = []
    detail_connections = {}
    categorized_connections = {'self': 0, 'local': 0, 'grisons': 0, 'other': 0}


    if resolution == 'daily':
        # View month with data by day
        if month is not None:
            start = sum(MONTHVEC[0:monthNumbers[month]])
            stop = sum(MONTHVEC[0:monthNumbers[month]+1])
        else:
            # Default to January if month is not set
            start = 0
            stop = sum(MONTHVEC[0:2])
        name = '{} 2016'.format(monthNames[month])

        categories = range(1, MONTHVEC[monthNumbers[month]]+1)

        demand = user.demandByDay[start:stop]
        production = user.productionByDay[start:stop]
        timely_aggregated_connections = user.dailyAggegatedConnections[start:stop]

    elif resolution == 'minimal':
        # View 24 hours with data by 15 minutes
        if (day is not None) and (month is not None):
            now = int( (month+day) *  24 / DELTAT)
            start = now - int(24 / DELTAT)
            stop = now
        else:
            # Default to specific day
            now = int( (244 + 6) * 24 / DELTAT)
            start = now - int(24 / DELTAT)
            stop = now

        month_index = 0
        for days_in_month in MONTHVEC:
            month = month - days_in_month
            if month == 0:
                break
            month_index += 1
        month_name = monthNames[month_index]
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

    else:
        # Default to full year, data by month
        start = 0
        stop = 35136
        name = 'Jahr 2016'
        categories = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
        demand = user.demandByMonth
        production = user.productionByMonth
        timely_aggregated_connections = user.monthlyAggregatedConnections
        aggregated_connections = user.aggregateDailyConnections(user.dailyAggregatedConnections)


    # Fill detail_connections
    for connections in timely_aggregated_connections:
        for supplier_id in connections.keys():
            if supplier_id not in detail_connections.keys():
                detail_connections['supplier_id'] = []

    for connections in timely_aggregated_connections:
        for supplier_id, connection in connections.iteritems():
            detail_connections['supplier_id'].append(connection['energy'] / 1000)

        for supplier_id in detail_connections.keys():
            if supplier_id not in connections.keys():
                detail_connections['supplier_id'].append(0)

    # Fill categorized_connections
    for supplier_id, connections in detail_connections.iteritems():
        supplier_distance = round(vincenty(user.location), locations[supplier_id].km, 2)

        if (supplier_id == user.index):
            categorized_connections['self'] += sum(connections)
        elif supplier_distance < 10:
            categorized_connections['local'] += sum(connections)
        elif (supplier_distance > 10) and (supplier_distance < 30):
            categorized_connections['grisons'] += sum(connections)
        elif (supplier_distance > 30) or (supplierId == 'GRID'):
            categorized_connections['other'] += sum(connections)


    self_consumption = 0
    if user.index in detail_connections.keys():
        self_consumption = detail_connections[user.index]

    sum_consumption = round(sum(demand), 2)
    sum_production = round(sum(production), 2)
    sum_self_consumption = round(sum(self_consumption), 2)

    kpi_self_consumption = 0
    if sum_production > 0:
        kpi_self_consumption = sum_self_consumption / sum_production

    kpi_autarky = 0
    if sum_consumption > 0:
        kpi_autarky = sum_self_consumption / sum_consumption


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
    user.period['self_consumption'] = self_consumption
    user.period['sum_consumption'] = sum_consumption
    user.period['sum_production'] = sum_production
    user.period['sum_self_consumption'] = sum_self_consumption
    user.period['kpi_self_consumption'] = kpi_self_consumption
    user.period['kpi_autarky'] = kpi_autarky


    print('Getting {} data ({} - {})'.format(resolution, start, stop))


def init_period():
    DELTAT = 0.25
    start = 0
    stop = 35136
    user.period['start'] = start
    user.period['stop'] = stop

    user.period['name'] = 'Jahr 2016'
    user.period['categories'] = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
    user.period['demand'] = user.demandByMonth
    user.period['production'] = user.productionByMonth
    user.period['daily_aggregated_connections'] = user.dailyAggregatedConnections
    user.period['aggregated_connections'] = user.aggregateDailyConnections(user.dailyAggregatedConnections)
    user.period['start'] = 0
    user.period['stop'] = 35136


    detailConnections = {}
    for monthConnections in user.monthlyAggregatedConnections:
        for supplierId in detailConnections.keys():
            if supplierId not in monthConnections.keys():
                detailConnections[supplierId].append(0)

        for supplierId, connection in monthConnections.iteritems():
            if supplierId not in detailConnections.keys():
                detailConnections[supplierId] = []
            detailConnections[supplierId].append(connection['energy'] / 1000. / DELTAT)


    categorized_connections = {'self': 0, 'local': 0, 'grisons': 0, 'other': 0}
    for supplierId, connections in detailConnections.iteritems():
        supplier_distance = round(vincenty(user.location, locations[supplierId]).km, 2)
        if (supplierId == user.index):
            categorized_connections['self'] += sum(connections)
        elif supplier_distance < 10:
            categorized_connections['local'] += sum(connections)
        elif (supplier_distance > 10) and (supplier_distance < 30):
            categorized_connections['grisons'] += sum(connections)
        elif (supplier_distance > 30) or (supplierId == 'GRID'):
            categorized_connections['other'] += sum(connections)

    user.period['categorized_connections'] = categorized_connections
    user.period['detailConnections'] = detailConnections
    print(categorized_connections)
    print("Sum: {}".format(sum(categorized_connections.values())))

    if user.index in user.period['detailConnections']:
        user.period['selfConsumption'] = user.period['detailConnections'][user.index]
    else:
        user.period['selfConsumption'] = [0]

    #user.period['outsource'] = np.subtract(user.period['demand'], user.period['selfConsumption']).tolist()

    #user.period['contribution'] = np.subtract(user.period['production'], user.period['selfConsumption']).tolist()


    user.period['kpiConsumption'] = round( sum(user.period['demand']) , 2)
    print('kpiConsumption : {}'.format(user.period['kpiConsumption']))

    #user.period['kpiOutsource'] = round( sum(user.period['outsource']) / sum(user.period['demand']) * 100, 2)
    #print('kpiOutsource : {}'.format(user.period['kpiOutsource']))

    user.period['kpiAutarky'] = round( sum(user.period['selfConsumption']) / sum(user.period['demand']) * 100, 2)
    print('kpiAutarky : {}'.format(user.period['kpiAutarky']))

    user.period['kpiProduction'] = round( sum(user.period['production']), 2)
    print('kpiProduction : {}'.format(user.period['kpiProduction']))

    if (sum(user.period['production']) > 0):
        user.period['kpiSelfConsumption'] = round( sum(user.period['selfConsumption']) / sum(user.period['production']) * 100, 2)
    else:
        user.period['kpiSelfConsumption'] = 0
    print('kpiSelfConsumption : {}'.format(user.period['kpiSelfConsumption']))

    if (sum(user.period['production']) > 0):
        # user.period['kpiContribution'] = round( sum(user.period['contribution']) / sum(user.period['production']) * 100, 2)
        user.period['kpiContribution'] = 0
    else:
        user.period['kpiContribution'] = 0
    print('kpiContribution : {}'.format(user.period['kpiContribution']))



def getDFromUser():
    dFromUser = []
    for supplierId, supplyDict in user.aggregatedConnections.iteritems():
        dFromUser.append(round(vincenty(user.location, locations[supplierId]).km, 2))
    return dFromUser

def getOrderedItems(dFromUser, kWhBySource):
    order = np.argsort(kWhBySource)[::-1]
    dFromUserordered = []
    kWhBySourceOrdered = []
    supplierIdsOrdered = []

    for idx in order:
        dFromUserordered.append(dFromUser[idx])
        supplierIdsOrdered.append(user.aggregatedConnections.keys()[idx])
        kWhBySourceOrdered.append(kWhBySource[idx])

    kWhSharesBySourceOrdered = np.around(kWhBySourceOrdered / np.sum(kWhBySourceOrdered), 3)

    return supplierIdsOrdered, kWhSharesBySourceOrdered, dFromUserordered

# google Maps Object

def generateMap(aggregatedConnections):
    photo_dict = {'Hydro1' : 'hydro_klosters.jpeg', 'Hydro2' : 'hydro_kueblis.jpeg', 'Biogas' : 'biomass_raps.jpeg',
                  'PV1': 'solar_bauernhof.jpeg', 'PV2' : 'solar_molkerei.jpeg'}
    description_texts = {'Hydro1' : 'hydro_klosters.jpeg', 'Hydro2' : 'hydro_kueblis.jpeg', 'Biogas' : 'biomass_raps.jpeg',
                  'PV1': 'solar_bauernhof.jpeg', 'PV2' : 'solar_molkerei.jpeg'}
    print("generating osmap")

    osmap = folium.Map(location=user.location, tiles='Stamen Terrain', zoom_start=11, min_zoom=10)

    #osmap = folium.Map(location=user.location, zoom_start=11, min_zoom=10,
    #                   tiles = 'https://api.mapbox.com/styles/v1/tscheng805/cj2a7l00s004j2sn0f4a938in/tiles/256/{z}/{x}/{y}?access_token=pk.eyJ1IjoidHNjaGVuZzgwNSIsImEiOiJjajJhNzJ1cGIwMDBkMzNvNXdtbDJ5OHhyIn0.veVS3rSwK4U0NoHEWxXK1g',
    #                   attr = 'XXX Mapbox Attribution')

    kWhBySource = user.getKWhBySource()
    autarky, selfConsumption = user.getAutarkySelfConsumption()

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

                supplierShare = (supplyDict['energy'] / 1000.) / (np.sum(kWhBySource) / 1000)
                suppliedEnergy = supplyDict['energy'] / 1000

                if (supplierShare > filterValue):

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
                                                                    supplierId=supplierId,
                                                                    supplierShare=supplierShare,
                                                                    suppliedEnergy=suppliedEnergy),
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

    osmap.save('osmaps.html')

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
app.config['DEBUG'] = True

app.config['GOOGLEMAPS_KEY'] = "8JZ7i18MjFuM35dJHq70n3Hx4"

# Initialize the extension
GoogleMaps(app)

# app.before_first_request(setup_data)

@app.route("/")
def home():
    supplierIdsOrdered, kWhSharesBySourceOrdered, dFromUserordered = getOrderedItems(getDFromUser(), user.getKWhBySource())
    return render_template('dashboard.html', user=user, producerNames=supplierIdsOrdered, kWh_SharesBySource=kWhSharesBySourceOrdered.tolist(), descriptions=descriptions)

@app.after_request
def add_header(response):
    response.cache_control.max_age = 30
    return response

@app.route('/os_maps')
def os_maps():
    return send_file('osmaps.html')

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

@app.route("/osmaps")
def osmaps():
    supplierIdsOrdered, kWhSharesBySourceOrdered, dFromUserordered = getOrderedItems(getDFromUser(), user.getKWhBySource())
    generateMap(user.aggregatedConnections)
    return render_template('maps.html', user=user, producerNames=supplierIdsOrdered, kWh_SharesBySource=kWhSharesBySourceOrdered.tolist(), dFromUserordered=dFromUserordered, descriptions=descriptions)


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
    return render_template('maps.html', sndmap=sndmap, user=user)

@app.route("/community")
def community():
    supplierIdsOrdered, kWhSharesBySourceOrdered, dFromUserordered = getOrderedItems(getDFromUser(), user.getKWhBySource())
    return render_template('community.html', user=user, kWh_SharesBySource=kWhSharesBySourceOrdered.tolist(),
                           dFromUser=dFromUserordered, d=np.dot(kWhSharesBySourceOrdered, dFromUserordered), producerNames=supplierIdsOrdered, descriptions=descriptions)


@app.route("/details")
def details():
    supplierIdsOrdered, kWhSharesBySourceOrdered, dFromUserordered = getOrderedItems(getDFromUser(), user.getKWhBySource())

    return render_template('details.html', user=user, producerNames=supplierIdsOrdered,
                           kWh_SharesBySource=kWhSharesBySourceOrdered.tolist(), descriptions=descriptions)

@app.route("/setAggregatedConnections/<int:start>/<int:end>/")
def setAggregatedConnections(start=0, end=36136, ref='dashboard'):
    print("Getting aggregated connections from {} to {} for {}".format(start, end, ref))
    print(request.path)
    user.setAggregatedConnections(start=start, end=end)
    supplierIdsOrdered, kWhSharesBySourceOrdered, dFromUserordered = getOrderedItems(getDFromUser(), user.getKWhBySource())

    if ref=='dashboard':
        return render_template('dashboard.html', user=user, producerNames=supplierIdsOrdered,
                               kWh_SharesBySource=kWhSharesBySourceOrdered.tolist(), descriptions=descriptions)

    if ref=='maps':
        markerList, paths = getMarkerList(user.aggregatedConnections)
        sndmap = Map(
            identifier="sndmap",
            lat=user.location[0],
            lng=user.location[1],
            style="",
            markers=markerList,
            polylines=paths
        )
        return render_template('maps.html', sndmap=sndmap, user=user, producerNames=supplierIdsOrdered,
                               kWh_SharesBySource=kWhSharesBySourceOrdered.tolist(), descriptions=descriptions)

@app.route("/setResolution/<string:resolution>/")
def setResolution(resolution='monthly'):

    if resolution=='monthly':
        init_period()

    if resolution=='daily':
        getMonthlyGraph(month='Jan')

    if hasattr(user, 'period'):
        if user.period['resolution'] == 'monthly':
            user.aggregatedConnections = user.aggregateDailyConnections(user.dailyAggregatedConnections)

        user.period['resolution'] = resolution
        print('Setting user.period[resolution] to {}'.format(resolution))

    #if resolution == 'monthly':
    #    user.aggregatedConnections = user.aggregateDailyConnections(user.dailyAggregatedConnections)

    user.resolution = resolution
    print('Setting user resolution to {}'.format(resolution))


    supplierIdsOrdered, kWhSharesBySourceOrdered, dFromUserordered = getOrderedItems(getDFromUser(),
                                                                                     user.getKWhBySource())
    return render_template('dashboard.html', user=user, producerNames=supplierIdsOrdered,
                           kWh_SharesBySource=kWhSharesBySourceOrdered.tolist(), descriptions=descriptions)

@app.route("/setPeriod/<int:start>/<int:stop>/<int:resolution>")
def setPeriod(start, stop, resolution):
    if (resolution == 15):
        user.period["resolution"] = 'minimal'
        user.period["name"] = "Letzte 24 Stunden"
    elif ( resolution == 1440):
        user.period["resolution"] = 'daily'
    elif (resolution == 10080):
        user.period["resolution"] = 'weekly'
    else:
        user.period["resolution"] = 'monthly'

@app.route("/getLast24hours/<int:month>/<int:day>")
def getLast24hours(month=244, day=10):
    DELTAT = 0.25  # hours
    now = int((month + day) * 24 / DELTAT)

    start = now - int((24 / DELTAT))
    stop = now
    user.period['start'] = start
    user.period['stop'] = stop

    print('\n\n!!!')
    print(start)
    print(stop)

    print(user.connections[start])
    print('!!!\n\n')

    user.period = {}
    user.period['resolution'] = 'minimal'

    MONTHVEC = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    monthNames = ['Januar', 'Februar', 'Maerz', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober',
                  'November', 'Dezember']
    month_index = 0
    for days_in_month in MONTHVEC:
        month = month - days_in_month
        if month == 0:
            break
        month_index += 1
    month_name = monthNames[month_index]
    user.period['name'] = '{}. {} 2016'.format(day, month_name)
    #user.period['name'] = '24 Stunden'

    categories = []
    for time_slice in range(start, stop):
        t = 15 * (time_slice - start)
        h = math.floor(t / 60) % 24
        m = (t % 60)
        time_string = '{:0>2}:{:0>2} Uhr'.format(int(h), m)
        categories.append(time_string)

    user.period['categories'] = categories
    print("categories: {}".format(user.period['categories']))
    user.period['demand'] = (np.multiply(user.demand[start:stop], DELTAT)).tolist()
    print("demand: {}".format(user.period['demand']))
    user.period['production'] = (np.multiply(user.production[start:stop], DELTAT)).tolist()
    print("production: {}, sum: {}".format(user.period['production'], sum(user.period['production'])))
    print("sum: {}".format(sum(user.period['production'])))

    user.period['aggregated_connections'] = user.getAggregatedConnections(start, stop)
    user.period['quarterhourly_aggregated_connections'] = []

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

        user.period['quarterhourly_aggregated_connections'].append(aggregatedConnections)

    print('quarterhourly_aggregated_connections: {}'.format(user.period['quarterhourly_aggregated_connections']))


    categorized_connections = {'self': 0, 'local': 0, 'grisons': 0, 'other': 0}
    detailConnections = {}

    for connections in user.period['quarterhourly_aggregated_connections']:
        for supplierId in connections.keys():
            if supplierId not in detailConnections.keys():
                detailConnections[supplierId] = []

    print(detailConnections)

    for connections in user.period['quarterhourly_aggregated_connections']:

        for supplierId, connection in connections.iteritems():
            detailConnections[supplierId].append(connection['energy'] / 1000.)

        for supplierId in detailConnections.keys():
            if supplierId not in connections.keys():
                detailConnections[supplierId].append(0)


    categorized_connections = {'self': 0, 'local': 0, 'grisons': 0, 'other': 0}
    for supplierId, connections in detailConnections.iteritems():
        supplier_distance = round(vincenty(user.location, locations[supplierId]).km, 2)
        if (supplierId == user.index):
            categorized_connections['self'] += sum(connections)
        elif supplier_distance < 10:
            categorized_connections['local'] += sum(connections)
        elif (supplier_distance > 10) and (supplier_distance < 30):
            categorized_connections['grisons'] += sum(connections)
        elif (supplier_distance > 30) or (supplierId == 'GRID'):
            categorized_connections['other'] += sum(connections)

    user.period['categorized_connections'] = categorized_connections

    user.period['detailConnections'] = detailConnections
    print('detailConnections: {}'.format(user.period['detailConnections']))
    print('categorized_connections: {}'.format(categorized_connections))

    if user.index in user.period['detailConnections']:
        user.period['selfConsumption'] = user.period['detailConnections'][user.index]
    else:
        user.period['selfConsumption'] = [0]
    print('selfConsumption: {}'.format(user.period['selfConsumption']))

    #user.period['outsource'] = np.subtract(user.period['demand'], user.period['selfConsumption']).tolist()
    #print('outsource: {}'.format(user.period['outsource']))

    #user.period['contribution'] = np.subtract(user.period['production'], user.period['selfConsumption']).tolist()
    #print('contribution: {}'.format(user.period['contribution']))

    user.period['kpiConsumption'] = round( sum(user.period['demand']) , 2)
    print('kpiConsumption : {}'.format(user.period['kpiConsumption']))

    #user.period['kpiOutsource'] = round( sum(user.period['outsource']) / sum(user.period['demand']) * 100, 2)
    #print('kpiOutsource : {}'.format(user.period['kpiOutsource']))

    user.period['kpiAutarky'] = round( sum(user.period['selfConsumption']) / sum(user.period['demand']) * 100, 2)
    print('kpiAutarky : {}'.format(user.period['kpiAutarky']))

    user.period['kpiProduction'] = round( sum(user.period['production']), 2)
    print('kpiProduction : {}'.format(user.period['kpiProduction']))

    if (sum(user.period['production']) > 0):
        user.period['kpiSelfConsumption'] = round( sum(user.period['selfConsumption']) / sum(user.period['production']) * 100, 2)
    else:
        user.period['kpiSelfConsumption'] = 0
    print('kpiSelfConsumption : {}'.format(user.period['kpiSelfConsumption']))

    if (sum(user.period['production']) > 0):
        #user.period['kpiContribution'] = round( sum(user.period['contribution']) / sum(user.period['production']) * 100, 2)
        user.period['kpiContribution'] = 0
    else:
        user.period['kpiContribution'] = 0
    print('kpiContribution : {}'.format(user.period['kpiContribution']))


    user.aggregatedConnections = user.period['aggregated_connections']

    supplierIdsOrdered, kWhSharesBySourceOrdered, dFromUserordered = getOrderedItems(getDFromUser(),
                                                                                     user.getKWhBySource())
    return render_template('dashboard.html', user=user, producerNames=supplierIdsOrdered,
                           kWh_SharesBySource=kWhSharesBySourceOrdered.tolist(), descriptions=descriptions)


@app.route("/getMonthlyGraph/<string:month>/")
def getMonthlyGraph(month='Jan'):
    user.resolution = 'daily'
    user.month = month

    user.period = {}
    user.period['resolution'] = 'daily'
    user.period['month'] = month

    monthNumbers = {'Jan':1, 'Feb':2, 'Mar':3, 'Apr':4, 'Mai':5, 'Jun':6, 'Jul':7, 'Aug':8, 'Sep':9, 'Okt':10, 'Nov':11, 'Dez':12}
    monthNames =  {'Jan':'Januar', 'Feb':'Februar', 'Mar':'Maerz', 'Apr':'April', 'May':'Mai', 'Jun':'Juni',
                   'Jul':'Juli', 'Aug':'August', 'Sep':'September', 'Okt':'Oktober', 'Nov':'November', 'Dez':'Dezember'}
    MONTHVEC = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    DELTAT = 0.25  # hours

    start = sum(MONTHVEC[0:monthNumbers[month]])
    stop = sum(MONTHVEC[0:monthNumbers[month]+1])
    user.period['start'] = start
    user.period['stop'] = stop

    print('Getting monthly data for {} (days: {} - {})'.format(month, start, stop))

    user.period['name'] = "{} 2016".format(monthNames[month])
    user.period['categories'] = range(1, MONTHVEC[monthNumbers[month]]+1)
    user.period['demand'] = user.demandByDay[start:stop]
    user.period['production'] = user.productionByDay[start:stop]
    user.period['daily_aggregated_connections'] = user.dailyAggregatedConnections[start:stop]
    user.period['aggregated_connections'] = user.aggregateDailyConnections(user.period['daily_aggregated_connections'])

    user.aggregatedConnections = user.period['aggregated_connections']

    print('\n\n!!!!')
    print(sum(user.demandByDay))
    print(sum(user.demandByMonth))
    print(sum(user.demand))
    print('!!!!\n')
    categorized_connections = {'self': 0, 'local': 0, 'grisons': 0, 'other': 0}

    detailConnections = {}
    for dayConnections in user.dailyAggregatedConnections[start:stop]:
        for supplierId in detailConnections.keys():
            if supplierId not in dayConnections.keys():
                detailConnections[supplierId].append(0)

        for supplierId, connection in dayConnections.iteritems():
            if supplierId not in detailConnections.keys():
                detailConnections[supplierId] = []
            detailConnections[supplierId].append(connection['energy'] / 1000.)


    categorized_connections = {'self': 0, 'local': 0, 'grisons': 0, 'other': 0}
    for supplierId, connections in detailConnections.iteritems():
        supplier_distance = round(vincenty(user.location, locations[supplierId]).km, 2)
        if (supplierId == user.index):
            categorized_connections['self'] += sum(connections)
        elif supplier_distance < 10:
            categorized_connections['local'] += sum(connections)
        elif (supplier_distance > 10) and (supplier_distance < 30):
            categorized_connections['grisons'] += sum(connections)
        elif (supplier_distance > 30) or (supplierId == 'GRID'):
            categorized_connections['other'] += sum(connections)

    print(categorized_connections)
    print("Sum: {}".format(sum(categorized_connections.values())))
    user.period['categorized_connections'] = categorized_connections
    user.period['detailConnections'] = detailConnections


    if user.index in user.period['detailConnections']:
        user.period['selfConsumption'] = user.period['detailConnections'][user.index]
    else:
        user.period['selfConsumption'] = [0]

    user.period['outsource'] = np.subtract(user.period['demand'], user.period['selfConsumption']).tolist()

    user.period['contribution'] = np.subtract(user.period['production'], user.period['selfConsumption']).tolist()


    user.period['kpiConsumption'] = round( sum(user.period['demand']) , 2)
    print('kpiConsumption : {}'.format(user.period['kpiConsumption']))

    user.period['kpiOutsource'] = round( sum(user.period['outsource']) / sum(user.period['demand']) * 100, 2)
    print('kpiOutsource : {}'.format(user.period['kpiOutsource']))

    user.period['kpiAutarky'] = round( sum(user.period['selfConsumption']) / sum(user.period['demand']) * 100, 2)
    print('kpiAutarky : {}'.format(user.period['kpiAutarky']))

    user.period['kpiProduction'] = round( sum(user.period['production']), 2)
    print('kpiProduction : {}'.format(user.period['kpiProduction']))

    if (sum(user.period['production']) > 0):
        user.period['kpiSelfConsumption'] = round( sum(user.period['selfConsumption']) / sum(user.period['production']) * 100, 2)
    else:
        user.period['kpiSelfConsumption'] = 0
    print('kpiSelfConsumption : {}'.format(user.period['kpiSelfConsumption']))

    if (sum(user.period['production']) > 0):
        user.period['kpiContribution'] = round( sum(user.period['contribution']) / sum(user.period['production']) * 100, 2)
    else:
        user.period['kpiContribution'] = 0
    print('kpiContribution : {}'.format(user.period['kpiContribution']))


    supplierIdsOrdered, kWhSharesBySourceOrdered, dFromUserordered = getOrderedItems(getDFromUser(),
                                                                                     user.getKWhBySource())
    return render_template('dashboard.html', user=user, producerNames=supplierIdsOrdered,
                           kWh_SharesBySource=kWhSharesBySourceOrdered.tolist(), descriptions=descriptions, dFromUserordered=dFromUserordered)


@app.route("/batterySim", methods=["GET","POST"])
def batterySim():

    EbatR=0.0
    if request.method=='POST':
        EbatR=float(request.form['BatteryCapacity'])

    user.prosumerSim(EbatR=EbatR)

    return render_template('batterySim.html', user=user, BatterySize=EbatR)

if __name__ == "__main__":
    setup_data()
    app.run(threaded=True)
