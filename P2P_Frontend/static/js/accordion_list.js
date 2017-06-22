function reload_accordion_list(period_json)
{
    $.getJSON( "/descriptions_json", function( descriptions_json ) {
        if (type == 'sinks')
        {
            $('#list_title').text('Produktion (' + numberWithCommas(period_json.sum_production.toFixed(1)) + ' kWh)');

            $('#self_title').text('Eigenverbrauch');
            $('#self_header_table td').remove();
            $('#self_header_table').append( $('<td style="padding-right:5px;"></td>').html(period_json.sum_self_consumption.toFixed(1) + ' kWh') );
            $('#self_header_table').append( $('<td></td>').html('(' + period_json.kpi_self_consumption.toFixed(1) + ' %)') );

            $('#local_title').text('Einspeisung Lokal (<10km)');
            $('#local_header_table td').remove();
            $('#local_header_table').append( $('<td style="padding-right:5px;"></td>').html(period_json.categorized_deliveries.local.sum.toFixed(1) + ' kWh') );
            $('#local_header_table').append( $('<td></td>').html('(' + (period_json.categorized_deliveries.local.sum / period_json.sum_production * 100).toFixed(1) + ' %)') );
            $('#local_s_title').text('Bezüger');

            $('#grisons_title').text('Einspeisung Graubünden');
            $('#grisons_header_table td').remove();
            $('#grisons_header_table').append( $('<td style="padding-right:5px;"></td>').html(period_json.categorized_deliveries.grisons.sum.toFixed(1) + ' kWh') );
            $('#grisons_header_table').append( $('<td></td>').html('(' + (period_json.categorized_deliveries.grisons.sum / period_json.sum_production * 100).toFixed(1) + ' %)') );
            $('#grisons_s_title').text('Bezüger');

            $('#other_title').text('Einspeisung Schweiz');
            $('#other_header_table td').remove();
            $('#other_header_table').append( $('<td style="padding-right:5px;"></td>').html(period_json.categorized_deliveries.other.sum.toFixed(1) + ' kWh') );
            $('#other_header_table').append( $('<td></td>').html('(' + (period_json.categorized_deliveries.other.sum / period_json.sum_production * 100).toFixed(1) + ' %)') );

            var grisons_list = period_json.categorized_deliveries.grisons.list;
            var local_list = period_json.categorized_deliveries.local.list;
        }
        else
        {
            $('#list_title').text('Verbrauch (' + numberWithCommas(period_json.sum_consumption.toFixed(1)) + ' kWh)');

            $('#self_title').text('Selbstversorgung');
            $('#self_header_table td').remove();
            $('#self_header_table').append( $('<td style="padding-right:5px;"></td>').html(period_json.sum_self_consumption.toFixed(1) + ' kWh') );
            $('#self_header_table').append( $('<td></td>').html('(' + period_json.kpi_autarky.toFixed(1) + ' %)') );

            $('#local_title').text('Bezug Lokal (<10km)');
            $('#local_header_table td').remove();
            $('#local_header_table').append( $('<td style="padding-right:5px;"></td>').html(period_json.categorized_connections.local.sum.toFixed(1) + ' kWh') );
            $('#local_header_table').append( $('<td></td>').html('(' + (period_json.categorized_connections.local.sum / period_json.sum_consumption * 100).toFixed(1) + ' %)') );
            $('#local_s_title').text('Quelle');

            $('#grisons_title').text('Bezug Graubünden');
            $('#grisons_header_table td').remove();
            $('#grisons_header_table').append( $('<td style="padding-right:5px;"></td>').html(period_json.categorized_connections.grisons.sum.toFixed(1) + ' kWh') );
            $('#grisons_header_table').append( $('<td></td>').html('(' + (period_json.categorized_connections.grisons.sum / period_json.sum_consumption * 100).toFixed(1) + ' %)') );
            $('#grisons_s_title').text('Quelle');

            $('#other_title').text('Bezug Schweiz');
            $('#other_header_table td').remove();
            $('#other_header_table').append( $('<td style="padding-right:5px;"></td>').html(period_json.categorized_connections.other.sum.toFixed(1) + ' kWh') );
            $('#other_header_table').append( $('<td></td>').html('(' + (period_json.categorized_connections.other.sum / period_json.sum_consumption * 100).toFixed(1) + ' %)') );


            if ( (period_json.categorized_connections.local.sum == 0) && (period_json.categorized_connections.local.sum == 0) )
            {
                $("#collapse1").removeClass("in");
                $("#collapse2").addClass("in");
            }
            else
            {
                $("#collapse2").removeClass("in");
                $("#collapse1").addClass("in");
            }

            var grisons_list = period_json.categorized_connections.grisons.list;
            var local_list = period_json.categorized_connections.local.list;
        }

        $('#local_table tbody').remove();
        $('#local_table').append(build_table(local_list, period_json, descriptions_json));


        $('#grisons_table tbody').remove();
        $('#grisons_table').append(build_table(grisons_list, period_json, descriptions_json));

    });
}

function build_table(list, period_json, descriptions_json)
{
    var body = $('<tbody></tbody>');

    for (var key in list)
    {
        var s_json = list[key];

        var row = $('<tr></tr>');

        if (type == 'sinks')
            row.append( $('<td></td>').html(descriptions_json[s_json.s_id].name) );
        else
            row.append( $('<td></td>').html('<img src="/static/img/markers/' + descriptions_json[s_json.s_id].type + '.png" style="height: 20px; width: 20px;"> ' + descriptions_json[s_json.s_id].name) );

        row.append( $('<td></td>').html(s_json.distance + ' km') );

        if (type == 'sinks')
            if ( (s_json.energy / period_json.sum_production) < 0.01 )
                row.append( $('<td></td>').html(' < 1 %') );
            else
                row.append( $('<td></td>').html( (s_json.energy / period_json.sum_production * 100).toFixed(1) + ' %') );
        else
            if ( (s_json.energy / period_json.sum_consumption) < 0.01 )
                row.append( $('<td></td>').html(' < 1 %') );
            else
                row.append( $('<td></td>').html( (s_json.energy / period_json.sum_consumption * 100).toFixed(1) + ' %') );

        body.append(row);
    }
    return body;
}