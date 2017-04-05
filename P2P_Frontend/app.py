import glob

import numpy as np
from flask import Flask, render_template, url_for, request
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


def getMarkerList(aggregatedConnections):
    kWhBySource = user.getKWhBySource()
    autarky, selfConsumption = user.getAutarkySelfConsumption()

    # Only print values on map with more than 1 % share.
    filterValue = 0.01

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
                   "Autarkie: {:.2f} %".format(descriptions[user.index],
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
                                   "Anteil: {:.1f} %".format(descriptions[supplierId],
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

app.before_first_request(setup_data)

@app.route("/")
def home():
    supplierIdsOrdered, kWhSharesBySourceOrdered, dFromUserordered = getOrderedItems(getDFromUser(), user.getKWhBySource())
    return render_template('dashboard.html', user=user, producerNames=supplierIdsOrdered, kWh_SharesBySource=kWhSharesBySourceOrdered.tolist(), descriptions=descriptions)


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
    return render_template('maps.html', sndmap=sndmap, user=user, producerNames=supplierIdsOrdered, kWh_SharesBySource=kWhSharesBySourceOrdered.tolist(), descriptions=descriptions)

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

    if resolution == 'monthly':
        user.aggregatedConnections = user.aggregateDailyConnections(user.dailyAggregatedConnections)

    user.resolution = resolution
    print('Setting user resolution to {}'.format(resolution))
    supplierIdsOrdered, kWhSharesBySourceOrdered, dFromUserordered = getOrderedItems(getDFromUser(),
                                                                                     user.getKWhBySource())
    return render_template('dashboard.html', user=user, producerNames=supplierIdsOrdered,
                           kWh_SharesBySource=kWhSharesBySourceOrdered.tolist(), descriptions=descriptions)

@app.route("/getMonthlyGraph/<string:month>/")
def getMonthlyGraph(month='Jan'):
    user.resolution = 'daily'
    user.month = month

    monthNumbers = {'Jan':1, 'Feb':2, 'Mar':3, 'Apr':4, 'May':5, 'Jun':6, 'Jul':7, 'Aug':8, 'Sep':9, 'Oct':10, 'Nov':11, 'Dec':12}
    monthNames =  {'Jan':'Januar', 'Feb':'Februar', 'Mar':'Maerz', 'Apr':'April', 'May':'Mai', 'Jun':'Juni',
                   'Jul':'Juli', 'Aug':'August', 'Sep':'September', 'Oct':'Oktober', 'Nov':'November', 'Dec':'Dezember'}
    MONTHVEC = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    DELTAT = 0.25  # hours

    start = sum(MONTHVEC[0:monthNumbers[month]])
    stop = sum(MONTHVEC[0:monthNumbers[month]+1])

    print('Getting monthly data for {} (days: {} - {})'.format(month, start, stop))

    user.period = {}
    user.period['name'] = "{} 2016".format(monthNames[month])
    user.period['categories'] = range(1,MONTHVEC[monthNumbers[month]]+1)
    user.period['demand'] = user.demandByDay[start:stop]
    user.period['production'] = user.productionByDay[start:stop]
    user.period['aggregatedConnections'] = user.dailyAggregatedConnections[start:stop]

    selfConsumption = []
    for dayConnections in user.dailyAggregatedConnections[start:stop]:
        found = False
        for supplierId, connection in dayConnections.iteritems():
            if connection['location'] == user.location:
                selfConsumption.append(connection['energy'] / 1000.)
                found = True
        if not found:
            selfConsumption.append(0)
    user.period['selfConsumption'] = selfConsumption

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
                           kWh_SharesBySource=kWhSharesBySourceOrdered.tolist(), descriptions=descriptions)



@app.route("/batterySim", methods=["GET","POST"])
def batterySim():
    
    EbatR=0.0
    if request.method=='POST':
        EbatR=float(request.form['BatteryCapacity'])
    

    
    
    user.prosumerSim(EbatR=EbatR)


    return render_template('batterySim.html', user=user, BatterySize=EbatR)

if __name__ == "__main__":
    app.run()
