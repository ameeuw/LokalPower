function init_overview_chart(period_json)
{
	overview_chart_options =
	{
		chart: {
			backgroundColor: 'var(--chart-bg-color)'
		},

		title: {
				text: 'Verbrauch'
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
			categories: period_json.categories,
			crosshair: true,
			labels: {
			    style: {
			        fontSize: '16px'
			    }
			}
		},

		tooltip: {
			shared: true,
			useHTML: true,
			borderColor: '#000000',

			formatter: function() {
			   var s = '<span style="font-size:14px">' + period_json.resolution.replace("daily", "Tag").replace("monthly", "Monat").replace("minimal", "Uhrzeit") + ' : ' + this.x +'</span><br><table>';

			   var sortedPoints = this.points.sort(function(a, b){
					 return ((a.series.options.legendIndex < b.series.options.legendIndex) ? -1 : ((a.series.options.legendIndex > b.series.options.legendIndex) ? 1 : 0));
				 });

			   $.each(sortedPoints , function(i, point) {
			   s += '<tr><td style="color:' + point.series.options.color + '; padding:0">' + point.series.name + ': </td>' +
				'<td style="padding-right:5px;"><b> '+ point.y.toFixed(1) +'</b></td><td style="padding-left:3px">kWh</td></tr>'
			   });
			   s += '</table>';

			   return s;},
		},

		series: [

		{
			type: 'spline',
			stacking: false,
			name: 'Verbrauch',
			colorByPoint: false,
			color: 'var(--consumption-color)',
			data: period_json.demand,
			showInLegend: true,
			legendIndex: 0,
			index: 3,
            marker: {
                enabled: true
            },
		},

		{
			type: 'spline',
			name: 'Produktion',
			colorByPoint: false,
			color: 'var(--production-color)',
			data: period_json.production,
			showInLegend: true,
			legendIndex: 1,
			index: 2,
            marker: {
                enabled: true
            },
		},

		/*{
			type: 'areaspline',
			fillOpacity: 0.5,
			stacking: true,
			name: 'Batterie S (4 kWh)',
			colorByPoint: false,
			color: 'var(--battery-color)',
			fillColor: 'var(--battery-fill-color)',
			data: period_json.battery_simulation.battery_to_load,
			showInLegend: true,
			visible: false,
			legendIndex: 3,
			index: 0
		},*/

		{
			type: 'areaspline',
			stacking: true,
			name: 'Eigenverbrauch',
			colorByPoint: false,
			color: 'var(--self-consumption-color)',
			fillColor: 'var(--self-consumption-fill-color)',
			data: period_json.self_consumption,
			showInLegend: true,
			legendIndex: 2,
			index: 1,
            marker: {
                enabled: true
            },
		},

		]


	};
}

function reload_overview_chart_data(period_json)
{
    overview_chart.series[0].setData(period_json.demand);
    overview_chart.series[1].setData(period_json.production);
    overview_chart.series[2].setData(period_json.self_consumption);
}


function reload_overview_chart(period_json)
{
    if (period_json.sum_production > 0)
        overview_chart_options.title.text = 'Verbrauch und Produktion';
    else
        overview_chart_options.title.text = 'Verbrauch';

    if (period_json.resolution == 'monthly')
    {
        overview_chart_options.plotOptions.series.point.events.click = function() {
                                                                            // location.href='/setDailyPeriod/' + this.index + '/' + origin + '/' + 'all';
                                                                            get_form('/setDailyPeriod/' + this.index + '/');
                                                                            };
    }
    else if (period_json.resolution == 'daily')
    {
        overview_chart_options.plotOptions.series.point.events.click = function() {
                                                                            // add up start of period and clicked day in month
                                                                            day = period_json.start + this.index;
                                                                            // location.href='/setMinimalPeriod/' + day + '/' + origin + '/' + 'all';
                                                                            get_form('/setMinimalPeriod/' + day + '/');
                                                                            };
    }
    else if (period_json.resolution == 'minimal')
    {
        overview_chart_options.xAxis.labels = {step: 4, rotation: 45};
        overview_chart_options.series[0].marker.enabled = false;
        overview_chart_options.series[1].marker.enabled = false;
        overview_chart_options.series[2].marker.enabled = false;
    }

    overview_chart = Highcharts.chart('overview_chart', overview_chart_options);
}