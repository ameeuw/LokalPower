import glob

import numpy as np
from flask import Flask, render_template, url_for
from flask_googlemaps import Map, GoogleMaps
from geopy.distance import vincenty
import pickle

import Algos as ag

# load consumption file

locations = pickle.load(open('../Daten/users/locations.pickle', "rb"))
descriptions = pickle.load(open('../Daten/users/descriptions.pickle', "rb"))

userId = locations.keys()[13]

user = ag.User('../Daten/users/{}.csv'.format(userId), locations[userId], userId)
user.setUserDict('../Daten/dicts/{}.pickle'.format(userId))

user.setAggregatedConnections()

user.setProducerDict('../Daten/dicts/prod_{}.pickle'.format(userId))
user.setAggregatedDeliveries()

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
                iconFile = 'static/img/solar.png'

                if (supplierId == 'Hydro1') or (supplierId == 'Hydro2'):
                    iconFile = 'static/img/hydro.png'

                if (supplierId == 'Biogas'):
                    iconFile = 'static/img/biomass.png'

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

@app.route("/")
def home():
    supplierIdsOrdered, kWhSharesBySourceOrdered, dFromUserordered = getOrderedItems(getDFromUser(), user.getKWhBySource())
    return render_template('dashboard.html', user=user, producerNames=supplierIdsOrdered, kWh_SharesBySource=kWhSharesBySourceOrdered.tolist(), descriptions=descriptions)


@app.route("/maps")
def maps():
    markerList, paths = getMarkerList(user.aggregatedConnections)
    sndmap = Map(
        identifier="sndmap",
        lat=user.location[0],
        lng=user.location[1],
        style="height:750px;width:1500px;margin:0;",
        markers = markerList,
        polylines = paths
    )
    return render_template('maps.html', sndmap=sndmap)

@app.route("/sinks")
def sinks():
    markerList, paths = getMarkerList(user.aggregatedDeliveries)
    sndmap = Map(
        identifier="sndmap",
        lat=user.location[0],
        lng=user.location[1],
        style="height:750px;width:1500px;margin:0;",
        markers = markerList,
        polylines = paths,
        cluster = True
    )
    return render_template('maps.html', sndmap=sndmap)

@app.route("/community")
def community():
    supplierIdsOrdered, kWhSharesBySourceOrdered, dFromUserordered = getOrderedItems(getDFromUser(), user.getKWhBySource())
    return render_template('community.html', user=user, kWh_SharesBySource=kWhSharesBySourceOrdered.tolist(),
                           dFromUser=dFromUserordered, d=np.dot(kWhSharesBySourceOrdered, dFromUserordered), producerNames=supplierIdsOrdered, descriptions=descriptions)


@app.route("/getAggregatedConnections/<int:start>/<int:end>/")
def getAggregatedConnections(start=0, end=36136):
    print("Getting aggregated connections from {} to {}".format(start, end))
    user.setAggregatedConnections(start=start, end=end)
    return render_template('dashboard.html', user=user)

if __name__ == "__main__":
    app.run()
