var stamen_tiles = 'https://stamen-tiles-{s}.a.ssl.fastly.net/terrain/{z}/{x}/{y}.jpg';
var mapbox_tiles = 'https://api.mapbox.com/styles/v1/tscheng805/cj2a7l00s004j2sn0f4a938in/tiles/256/{z}/{x}/{y}?access_token=pk.eyJ1IjoidHNjaGVuZzgwNSIsImEiOiJjajJhNzJ1cGIwMDBkMzNvNXdtbDJ5OHhyIn0.veVS3rSwK4U0NoHEWxXK1g';
var user_location = [46.940076, 9.569257];


function init_map() {
    if (type=="sinks")
        var start_zoom = 15;
    else
        var start_zoom = 11;

    lokalpower_map = L.map('map_div').setView(user_location, start_zoom);
    L.tileLayer(stamen_tiles, {
        attribution: '',
        maxZoom: 18,
        minZoom: 10,
        id: 'lokalpower.sources.map',
        accessToken: 'your.mapbox.public.access.token'
    }).addTo(lokalpower_map);
}


function get_icon(icon) {
    return L.icon({
        iconUrl: 'http://127.0.0.1:5000/static/img/markers/' + icon,
        iconSize: [30, 30],
        iconAnchor: [16, 16],
        popupAnchor: [0, -16],
        shadowUrl: null,
        shadowSize: null,
        shadowAnchor: null
    });
}


function build_map(map_json)
{
    var popups = [];
    var markers = [];
    var paths = []

    for (var i = 0; i < map_json.markers.length; i++) {
        // console.log(map_json.markers[i]);
        current_marker = map_json.markers[i];

        markers.push(L.marker(current_marker.location, {icon: get_icon(current_marker.icon)}).addTo(lokalpower_map));
        popups.push(L.popup({className: 'map_popup', minWidth: '360'}));
        //var iframe = $('<iframe src="data:text/html;charset=utf-8;base64,' + current_marker.iframe_b64 + '" width="360" style="border:none !important;" height="250"></iframe>')[0];
        //console.log(iframe);
        popups[i].setContent('<iframe src="data:text/html;charset=utf-8;base64,' + current_marker.iframe_b64 + '" width="360" style="border:none !important;" height="250"></iframe>');
        //popups[i].setContent(iframe);
        markers[i].bindPopup(popups[i]);
    }

    for (var i = 0; i < map_json.paths.length; i++) {
        // console.log(map_json.paths[i]);
        // paths.push(L.polyline(map_json.paths[i], {className: 'map_polyline'}).addTo(lokalpower_map));
        // paths.push(L.polyline(map_json.paths[i], {className: 'map_polyline', vertices: 200}).addTo(lokalpower_map));

        if (type=="sinks"){
            var direction = 'normal';
            var factor = 15;
        }
        else
        {
            var direction = 'reverse';
            var factor = 1;
        }

        speed = factor * lokalpower_map.distance(map_json.paths[i][0], map_json.paths[i][1]);
        console.log("Speed: "+ speed)
        paths.push(L.curve(['M',map_json.paths[i][0],
                            'L',map_json.paths[i][1]], {className: 'map_polyline', dashArray: 1, animate: {duration: speed, iterations: Infinity, direction: direction}}).addTo(lokalpower_map));
    }
}
// console.log(map_json);
// console.log(markers);
// console.log(popups);