import glob
import folium
import os.path


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

    userId = locations.keys()[13]

    print('user data.')
    if os.path.isfile('../Daten/user_data/user_{}.pickle'.format(userId)):
        print('loading from pickle')
        user = pickle.load(open('../Daten/user_data/user_{}.pickle'.format(userId), 'rb'))
    else:
        print('generating from sources...')
        user = ag.User('../Daten/users/{}.csv'.format(userId), locations[userId], userId)
        user.setUserDict('../Daten/dicts/{}.pickle'.format(userId))

        #print('aggregated connections.')
        #user.setAggregatedConnections()

        print('producer data.')
        user.setProducerDict('../Daten/dicts/prod_{}.pickle'.format(userId))

        # print('aggregated deliveries.')
        # user.setAggregatedDeliveries()

        print('daily aggregated connections.')
        user.setDailyAggregatedConnections()
        print('aggregate connections.')
        user.aggregatedConnections = user.aggregateDailyConnections(user.dailyAggregatedConnections)

        print('daily aggregated deliveries.')
        user.setDailyAggregatedDeliveries()
        print('aggregate deliveries.')
        user.aggregatedDeliveries = user.aggregateDailyConnections(user.dailyAggregatedDeliveries)
        print('saving user_data')

        pickle.dump(user, open('../Daten/user_data/user_{}.pickle'.format(userId), "wb"))
    print('Done.')




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
    osmap = folium.Map(location=user.location, tiles='Stamen Terrain', zoom_start=11)
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
                icon = folium.features.CustomIcon('static/img/markers/{}.png'.format(descriptions[supplierId]['type']),
                                                  icon_size=icon_size)

                supplierShare = (supplyDict['energy'] / 1000.) / (np.sum(kWhBySource) / 1000)
                suppliedEnergy = supplyDict['energy'] / 1000

                if (supplierShare > filterValue):

                    if (descriptions[supplierId]['kind'] == 'plant'):
                        print('img: {} {}'.format(supplierId, photo_dict[supplierId]))
                        html = """
                            <img src="http://127.0.0.1:5000/static/img/photos/{photo}" style="width: 136px; height: 69px">
                            <h4>{name}</h4><br>
                            
                            <p>
                            </p>
                            """.format(name=descriptions[supplierId]['name'], photo=photo_dict[supplierId])

                        iframe = folium.IFrame(html=render_template('tooltip.html', photo=photo_dict[supplierId],
                                                                    name=descriptions[supplierId]['name'],
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
                            """.format(name=descriptions[supplierId]['name'])
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
                   "Autarkie: {:.2f} %".format(descriptions[user.index]['name'],
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
                                   "Anteil: {:.1f} %".format(descriptions[supplierId]['name'],
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
    if hasattr(user, 'period'):
        if user.period['resolution'] == 'monthly':
            user.aggregatedConnections = user.aggregateDailyConnections(user.dailyAggregatedConnections)

        user.period['resolution'] = resolution
        print('Setting user.period[resolution] to {}'.format(resolution))

    if resolution == 'monthly':
        user.aggregatedConnections = user.aggregateDailyConnections(user.dailyAggregatedConnections)

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

@app.route("/getLast24hours/<int:now>")
def getLast24hours(now = 17000):
    DELTAT = 0.25  # hours

    start = now - (24 * 4)
    stop = now

    user.period = {}
    user.period['resolution'] = 'minimal'
    user.period['name'] = 'Letzte 24 Stunden'
    user.period['categories'] = range( 1, (24*4) )
    user.period['demand'] = user.demand[start:stop]
    user.period['production'] = user.production[start:stop]

    user.period['aggregatedConnections'] = []
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

        user.period['aggregatedConnections'].append(aggregatedConnections)

    print('aggregatedConnections: {}'.format(user.period['aggregatedConnections']))

    detailConnections = {}
    for dayConnections in user.period['aggregatedConnections']:
        for supplierId, connection in dayConnections.iteritems():
            if supplierId not in detailConnections.keys():
                detailConnections[supplierId] = []
            detailConnections[supplierId].append(connection['energy'] / 1000.)

        for supplierId in detailConnections.keys():
            if supplierId not in dayConnections.keys():
                detailConnections[supplierId].append(0)

    user.period['detailConnections'] = detailConnections
    print('detailConnections: {}'.format(user.period['detailConnections']))

    if user.index in user.period['detailConnections']:
        user.period['selfConsumption'] = user.period['detailConnections'][user.index]
    else:
        user.period['selfConsumption'] = [0]
    print('selfConsumption: {}'.format(user.period['selfConsumption']))

    user.period['outsource'] = np.subtract(user.period['demand'], user.period['selfConsumption']).tolist()
    print('outsource: {}'.format(user.period['outsource']))

    user.period['contribution'] = np.subtract(user.period['production'], user.period['selfConsumption']).tolist()
    print('contribution: {}'.format(user.period['contribution']))

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


    user.aggregatedConnections = user.period['aggregatedConnections']

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

    monthNumbers = {'Jan':1, 'Feb':2, 'Mar':3, 'Apr':4, 'May':5, 'Jun':6, 'Jul':7, 'Aug':8, 'Sep':9, 'Oct':10, 'Nov':11, 'Dec':12}
    monthNames =  {'Jan':'Januar', 'Feb':'Februar', 'Mar':'Maerz', 'Apr':'April', 'May':'Mai', 'Jun':'Juni',
                   'Jul':'Juli', 'Aug':'August', 'Sep':'September', 'Oct':'Oktober', 'Nov':'November', 'Dec':'Dezember'}
    MONTHVEC = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    DELTAT = 0.25  # hours

    start = sum(MONTHVEC[0:monthNumbers[month]])
    stop = sum(MONTHVEC[0:monthNumbers[month]+1])

    print('Getting monthly data for {} (days: {} - {})'.format(month, start, stop))

    user.period['name'] = "{} 2016".format(monthNames[month])
    user.period['categories'] = range(1, MONTHVEC[monthNumbers[month]]+1)
    user.period['demand'] = user.demandByDay[start:stop]
    user.period['production'] = user.productionByDay[start:stop]
    user.period['aggregatedConnections'] = user.dailyAggregatedConnections[start:stop]

    detailConnections = {}
    for dayConnections in user.period['aggregatedConnections']:
        for supplierId in detailConnections.keys():
            if supplierId not in dayConnections.keys():
                detailConnections[supplierId].append(0)

        for supplierId, connection in dayConnections.iteritems():
            if supplierId not in detailConnections.keys():
                detailConnections[supplierId] = []
            detailConnections[supplierId].append(connection['energy'] / 1000.)

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


    user.aggregatedConnections = user.aggregateDailyConnections(user.period['aggregatedConnections'])

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
