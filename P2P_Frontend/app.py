import glob

import numpy as np
from flask import Flask, render_template
from flask_googlemaps import Map, GoogleMaps
from geopy.distance import vincenty
import pickle

import Algos as ag

# load consumption file

locations = pickle.load(open('../Daten/dicts/locations.pickle', "rb"))
producerIds = ['Hydro 1', 'Hydro 2', 'Biogas', 'PV 1', 'PV 2']

#userId = 'CH1099601234500000000000000111040'
#userId = 'CH1012101234500000000000000113115'
#userId = 'CH1012301234500000000000000027700'
userId = 'CH1012101234500000000000000110486'

user0 = ag.User('../Daten/users/{}.csv'.format(userId), locations[userId], userId)
user0.SetConnectionList('../Daten/dicts/{}.pickle'.format(userId))

#aggregatedConnections = user0.getAggregatedConnections(start=0,end=8783)
#aggregatedConnections = user0.getAggregatedConnections(start=8784,end=17567)
#aggregatedConnections = user0.getAggregatedConnections(start=17568,end=26351)
#aggregatedConnections = user0.getAggregatedConnections(start=26352,end=35136)
aggregatedConnections = user0.getAggregatedConnections()
print(aggregatedConnections)
paths = user0.getAggregatedPaths(aggregatedConnections)

dFromUser0 = []
_kWh_SharesBySource = np.array([])
for supplierLocation, supplyValue in aggregatedConnections.iteritems():
    dFromUser0.append(round(vincenty(user0.Location, supplierLocation).km, 2))
    _kWh_SharesBySource = np.append(_kWh_SharesBySource, supplyValue)

## Sort suppliers
order = np.argsort(_kWh_SharesBySource)[::-1]
dFromUser0ordered = []
_kWh_SharesBySource_ordered = []
for idx in order:
    dFromUser0ordered.append(dFromUser0[idx])
    _kWh_SharesBySource_ordered.append(_kWh_SharesBySource[idx])
dFromUser0 = dFromUser0ordered
_kWh_SharesBySource = _kWh_SharesBySource_ordered

kWh_SharesBySource = np.around(_kWh_SharesBySource / np.sum(_kWh_SharesBySource), 3)

# google Maps Object
markerList = []

markerList.append({
    'icon': 'static/img/house.png',
    'lat': user0.Location[0],
    'lng': user0.Location[1],
    'infobox': "<b>Das sind Sie!</b><br>Jahresverbrauch: {:.2f} kWh".format(user0.AnnualDemand)
})
# for _k in range(len(locations)):
for supplierLocation, supplyValue in aggregatedConnections.iteritems():
    markerList.append({
        'icon': 'http://maps.google.com/mapfiles/ms/icons/green-dot.png',
        'lat': supplierLocation[0],
        'lng': supplierLocation[1],
        'infobox': "<b>Supplier</b><br>Bezogen: {:.2f} kWh<br>Anteil: {:.1f} %".format(supplyValue / 1000, 100 * (supplyValue / 1000.) / user0.AnnualDemand)
    })

app = Flask(__name__)
app.config['DEBUG'] = True

app.config['GOOGLEMAPS_KEY'] = "8JZ7i18MjFuM35dJHq70n3Hx4"

# Initialize the extension
GoogleMaps(app)


@app.route("/")
def home():
    return render_template('dashboard.html', user=user0)


@app.route("/maps")
def maps():
    mymap = Map(
        identifier="view-side",
        lat=37.4419,
        lng=-122.1419,
        markers=[(37.4419, -122.1419)],
        # style="height:300px;width:1000px;margin:0;",
    )
    sndmap = Map(
        identifier="sndmap",
        lat=user0.Location[0],
        lng=user0.Location[1],
        style="height:750px;width:1500px;margin:0;",
        markers=markerList,
        polylines=paths
    )
    return render_template('maps.html', mymap=mymap, sndmap=sndmap)


@app.route("/community")
def community():
    return render_template('community.html', user=user0, kWh_SharesBySource=kWh_SharesBySource.tolist(),
                           dFromUser0=dFromUser0, d=np.dot(kWh_SharesBySource, dFromUser0), producerNames=producerIds)


if __name__ == "__main__":
    app.run()
