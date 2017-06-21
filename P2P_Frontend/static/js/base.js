$("#btn_previous").click(function() { post_form("/move", {direction: 'previous'}); });
$("#btn_next").click(    function() { post_form("/move", {direction: 'next'}); });
$("#period_name").click( function() { post_form("/move", {direction: 'up'}); });

$("#btn_day").click( function() { get_form("/setResolution/minimal"); });
$("#btn_month").click( function() { get_form("/setResolution/daily"); });
$("#btn_year").click( function() { get_form("/setResolution/monthly"); });


function numberWithCommas(x) {
    return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, "'");
}

function reload_ui_elements(period_json)
{
    $('#sum_consumption').text(numberWithCommas(period_json.sum_consumption.toFixed(0)));
    $('#sum_production').text(numberWithCommas(period_json.sum_production.toFixed(0)));
    $('#self_consumption').text(numberWithCommas(period_json.kpi_self_consumption.toFixed(1)));
    $('#mean_distance').text(numberWithCommas(period_json.kpi_mean_distance.toFixed(1)));

    $('#period_name').text(period_json.name);

    if (period_json.resolution == 'minimal')
        $("#btn_day").addClass("active");
    else
        $("#btn_day").removeClass("active");

    if (period_json.resolution == 'daily')
        $("#btn_month").addClass("active");
    else
        $("#btn_month").removeClass("active");

    if (period_json.resolution == 'monthly')
        $("#btn_year").addClass("active");
    else
        $("#btn_year").removeClass("active");


    if (origin == 'dashboard.html')
        $('#link_dashboard').addClass('active');
    else
        $('#link_dashboard').removeClass('active');

    if ( (origin == 'maps.html') && (type == 'sources') )
        $('#link_maps_consumption').addClass('active');
    else
        $('#link_maps_consumption').removeClass('active');

    if ( (origin == 'details.html') && (type == 'sources') )
        $('#link_details_consumption').addClass('active');
    else
        $('#link_details_consumption').removeClass('active');

    if ( (origin == 'maps.html') && (type == 'sinks') )
        $('#link_maps_production').addClass('active');
    else
        $('#link_maps_production').removeClass('active');

    if ( (origin == 'details.html') && (type == 'sinks') )
        $('#link_details_production').addClass('active');
    else
        $('#link_details_production').removeClass('active');

    if (origin == 'batterySim.html')
        $('#link_battery_simulator').addClass('active');
    else
        $('#link_battery_simulator').removeClass('active');
}

function get_form(url)
{
    $.get(url, function(data)
    {
        period_json = JSON.parse(data);
        update_ui(period_json);
    });
}

function post_form(url, payload)
{
    $.post(url, payload, function(data)
    {
        period_json = JSON.parse(data);
        update_ui(period_json);
    });
}

function update_ui(period_json)
{
    console.log("UI Update");

    reload_ui_elements(period_json);

    if (typeof reload_pie_charts === "function")
    {
        init_pie_charts();
        reload_pie_charts(period_json);
    }


    if (typeof reload_overview_chart === "function")
    {
        init_overview_chart(period_json);
        reload_overview_chart(period_json);
    }


    if (typeof reload_accordion_list === "function")
    {
        reload_accordion_list(period_json);
    }


    if (typeof reload_details_chart === "function")
    {
        init_details_chart();
        reload_details_chart(period_json);
    }



    if (typeof init_map === "function")
    {
        deinit_map();
        $.getJSON( "/map_json/"+type, function( map_json ) {
            build_map(map_json);
        });
    }
}