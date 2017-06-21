function init_details_chart()
{
	details_chart_options =
	{
		chart: {
			backgroundColor: 'var(--chart-bg-color)',
		},

		title: {
				text: 'Verbrauch',
		},

		plotOptions: {
			series: {
				cursor: 'pointer',
				point: {
					events: {
					}
				}
			}
		},

		yAxis: {
			title: {
				text: 'kWh',
				style: {
				    fontSize: '16px'
				}
			},
			labels: {
			    style: {
			        fontSize: '16px'
			    }
			}
		},

		xAxis: {
			categories: [],
			crosshair: true,
			labels: {
			    style: {
			        fontSize: '16px'
			    }
			}
		},

		tooltip: {
			headerFormat: '<span style="font-size:14px">Monat : {point.key}</span><br><table>',
			pointFormat: '<tr><td style="color:{series.color};padding:0">{series.name}: </td>' +
				'<td style="padding:5"><b>{point.y:.1f}</b></td><td style="padding-left:3px">kWh</td></tr>',
			footerFormat: '</table>',
			shared: true,
			useHTML: true
		},

		series: []
	};
}


function reload_details_chart(period_json)
{
    if (type == 'sinks')
        details_chart_options.title.text = 'Produktion';
    else
        details_chart_options.title.text = 'Verbrauch';

    details_chart_options.xAxis.categories = period_json.categories;
    details_chart_options.tooltip.headerFormat = '<span style="font-size:14px">' + period_json.resolution.replace("daily", "Tag").replace("monthly", "Monat").replace("minimal", "Uhrzeit") + ' : {point.key}</span><br><table>';


    if (period_json.resolution == 'monthly')
    {
        details_chart_options.plotOptions.series.point.events.click = function() {
                                                                            // location.href='/setDailyPeriod/' + this.index + '/' + origin + '/' + 'all';
                                                                            get_form('/setDailyPeriod/' + this.index + '/');
                                                                            };
    }
    else if (period_json.resolution == 'daily')
    {

        details_chart_options.plotOptions.series.point.events.click = function() {
                                                                            // add up start of period and clicked day in month
                                                                            day = period_json.start + this.index;
                                                                            // location.href='/setMinimalPeriod/' + day + '/' + origin + '/' + 'all';
                                                                            get_form('/setMinimalPeriod/' + day + '/');
                                                                            };
    }
    else if (period_json.resolution == 'minimal')
    {
        details_chart_options.xAxis.labels = {step: 4, rotation: 45};
    }


    if (type == 'sinks')
        var categorized = period_json.categorized_deliveries;
    else
        var categorized = period_json.categorized_connections;

	var series = []
	for (var key in categorized)
	{
		var series_json = {};
		var category_json = categorized[key];

		series_json.type = 'column';
		series_json.stacking = true;

		if (type == 'sinks')
			series_json.name = key.replace("self", "Eigenverbrauch").replace("local","Einspeisung Lokal (<10km)").replace("grisons","Einspeisung Graubünden").replace("other","Einspeisung Schweiz");
		else
		    series_json.name = key.replace("self", "Selbstversorgung").replace("local","Bezug Lokal (<10km)").replace("grisons","Bezug Graubünden").replace("other","Bezug Schweiz");
		series_json.data = category_json.time_series;
		series_json.color = key.replace("self","var(--self-color)").replace("local","var(--local-color)").replace("grisons","var(--grisons-color)").replace("other","var(--other-color)");
		series_json.legendIndex = key.replace("self","0").replace("local","1").replace("grisons","2").replace("other","3");
		series_json.showInLegend = true;
		series_json.colorByPoint = false;
		series.push(series_json);
	}
	details_chart_options.series = series;

    details_chart = Highcharts.chart('details_chart', details_chart_options);
}