import folium
import pickle
#osmap = folium.Map(location=[46.967238, 9.560221], zoom_start=12,tiles='Stamen Terrain')


#osmap = folium.Map(location=[46.967238, 9.560221], tiles='Stamen Terrain', zoom_start=13)

osmap = folium.Map(location=[46.967238, 9.560221], tiles='Mapbox Control Room', zoom_start=10, API_key='pk.eyJ1IjoidHNjaGVuZzgwNSIsImEiOiJjajJhNzJ1cGIwMDBkMzNvNXdtbDJ5OHhyIn0.veVS3rSwK4U0NoHEWxXK1g')

#tileset = r'http://{s}.tiles.mapbox.com/v4/wtgeographer.2fb7fc73/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoidHNjaGVuZzgwNSIsImEiOiJjajJhNzJ1cGIwMDBkMzNvNXdtbDJ5OHhyIn0.veVS3rSwK4U0NoHEWxXK1g'

#osmap = folium.Map(location=[46.967238, 9.560221],
#       zoom_start=12,
#       tiles='http://{s}.tiles.mapbox.com/v4/wtgeographer.2fb7fc73/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoidHNjaGVuZzgwNSIsImEiOiJjajJhN2dhN2kwMDAyMzNwanU3cnY3bXRnIn0.oYedEQQuwiDv0KCo6zqMDw',
#       attr='XXX Mapbox Attribution')



#location = (46.940076, 9.569257)

locations = pickle.load(open('../Daten/users/locations.pickle', "rb"))
descriptions = pickle.load(open('../Daten/users/descriptions.pickle', "rb"))

for user, location in locations.iteritems():
    #print('Adding {} : {}'.format(user, location))
    html="""
        <h1> This is a big popup</h1><br>
        With a few lines of code...
        <p>
        </p>
        """
    iframe = folium.IFrame(html=html, width=250, height=200)
    popup = folium.Popup(iframe, max_width=2650)

    icon = folium.features.CustomIcon('static/img/markers/{}.png'.format(descriptions[user]['type']), icon_size=(40, 40))
    folium.Marker(location, popup=popup, icon=icon).add_to(osmap)

folium.PolyLine([(46.967238, 9.560221), (46.947246, 9.576537)]).add_to(osmap)


#folium.Marker((46.947246, 9.576537), icon=icon).add_to(osmap)


folium.Marker((46.9128, 9.9), icon=folium.Icon(icon='home', color='green')).add_to(osmap)

osmap.save('osmaps.html')

folium.Icon()