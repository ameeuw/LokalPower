function init_pie_charts()
{
	pie_chart_connections_options =
	{
		chart: {
			backgroundColor: 'var(--chart-bg-color)',
			plotBackgroundColor: null,
			plotBorderWidth: null,
			plotShadow: false,
			type: 'pie'
		},
		title: {
			text: 'Verbrauch',
			align: 'left'
		},
		tooltip: {
			formatter: function() {
				return '<b><span style="font-size: 130%">' + this.point.name + '</b></span><br>Anteil: ' + this.y.toFixed(1) + ' kWh (' + this.percentage.toFixed(1) + ' %)';
			},
		},
		plotOptions: {
			pie: {
				allowPointSelect: true,
				cursor: 'pointer',
				align: 'left',
				dataLabels: {
					enabled: false,
					name: 'Anteile',
					format: '<b>{point.name}</b>: {point.percentage:.1f} %',
					style: {
						color: (Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black'
					}
				},
			showInLegend: true,
			point: {
				events: {
					legendItemClick: function() {
					return false;
						}
					}
				},
			}
		},
		series: [{
			name: 'Anteil',
			colorByPoint: true,
			size: '100%',
			innerSize: '60%',
			data: []
		}],
		legend: {
			itemStyle: {
				fontSize:'13px'
			},
			layout: 'vertical',
			align: 'right',
			verticalAlign: 'middle',
			itemMarginTop: 8,
			useHTML: true,
			labelFormatter: function() {
				if (this.name == 'Selbstversorgung')
					var info_icon = '<i class="glyphicon glyphicon-info-sign" style=""></i>';
				else
					info_icon = '';
				return this.name + " (" + this.percentage.toFixed(1) + " %) " + info_icon;
			}
		}
	};

	pie_chart_deliveries_options =
	{
		chart: {
			backgroundColor: 'var(--chart-bg-color)',
			plotBackgroundColor: null,
			plotBorderWidth: null,
			plotShadow: false,
			type: 'pie'
		},
		title: {
			text: 'Produktion',
			align: 'left'
		},
		tooltip: {
			formatter: function() {
				return '<b><span style="font-size: 130%">' + this.point.name + '</b></span><br>Anteil: ' + this.y.toFixed(1) + ' kWh (' + this.percentage.toFixed(1) + ' %)';
			},
		},
		plotOptions: {
			pie: {
				allowPointSelect: true,
				cursor: 'pointer',
				align: 'left',
				dataLabels: {
					enabled: false,
					name: 'Anteile',
					format: '<b>{point.name}</b>: {point.percentage:.1f} %',
					style: {
						color: (Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black'
					}
				},

			showInLegend: true,
			point: {
				events: {
					legendItemClick: function() {
					return false;
						}
					}
				},

			},

		},
		series: [{
			name: 'Anteil',
			colorByPoint: true,
			size: '100%',
			innerSize: '60%',
			data: []
		}],
		legend: {
			itemStyle: {
				fontSize:'13px'
			},
			layout: 'vertical',
			align: 'right',
			verticalAlign: 'middle',
			itemMarginTop: 8,
			useHTML: true,
			labelFormatter: function() {
				if (this.name == 'Eigenverbrauch')
					var info_icon = '<i class="glyphicon glyphicon-info-sign" style=""></i>';
				else
					info_icon = '';
				return this.name + " (" + this.percentage.toFixed(1) + " %) " + info_icon;
			}
		}
	};
}

var text_self_consumption = 'Es handelt sich um den Anteil Ihres Verbrauchs, den Sie gerade dann verbrauchen, wenn Ihre Photovoltaik-Anlage produziert.<br>Der Grad des Eigenverbrauchs kann erhöht werden, wenn Verbraucher (z.B. Warmwasser-Boiler) dann eingeschalten werden, wenn die Sonne scheint.</div>';
var text_autarky = 'Es handelt sich um den Anteil Ihres Jahresverbrauchs, den Sie mit dem Eigenverbrauch abdecken können.<br>Der Selbstversorgungsgrad kann entweder erhöht werden, wenn die Photovoltaik-Anlage vergrössert wird oder wenn der Eigenverbrauchsgrad erhöht wird (siehe Eigenverbrauch).<br>Ein Selbstversorgungsgrad von 100 % ist ökonomisch praktisch nicht zu erreichen, da die Photovoltaik-Anlage in den Wintermonaten viel weniger produziert als im Sommer.';

function build_tooltip(legend, keyword, text)
{
	for (var i = 0, len = legend.allItems.length; i < len; i++) {
		if (legend.allItems[i].name == keyword)
		{
			(function(i) {
				var t=legend.allItems[i],
				//content= '<b>'+ t.name +'</b>: '+ Math.round(t.percentage*100)/100 + ' %';
				tooltip_title = '<b><h4>' + t.name + '</h4></b><div style="text-align: justify;">' + text + '</div>';
				jQuery($(t.legendItem.element)).tooltip({title:tooltip_title, html:true, container: 'body'});
			})(i);
		}
	}
}

function reload_pie_charts()
{
	var data = []
	for (var key in period.categorized_connections)
	{
		var data_json = {};
		var category_json = period.categorized_connections[key];
		data_json.name = key.replace("self", "Selbstversorgung").replace("local","Bezug Lokal (<10km)").replace("grisons","Bezug Graubünden").replace("other","Bezug Schweiz");
		data_json.y = category_json.sum;
		data_json.color = key.replace("self","var(--self-color)").replace("local","var(--local-color)").replace("grisons","var(--grisons-color)").replace("other","var(--other-color)");
		data_json.legendIndex = key.replace("self","0").replace("local","1").replace("grisons","2").replace("other","3");
		data.push(data_json);
	}
	pie_chart_connections_options.series[0].data = data;
	pie_chart_connections_options.title.text = 'Verbrauch (' + numberWithCommas(period.sum_consumption.toFixed(1)) + ' kWh)';
	pie_chart_connections = Highcharts.chart('pie_chart_connections', pie_chart_connections_options);

    build_tooltip(pie_chart_connections.legend, 'Selbstversorgung', text_self_consumption);


	var data = []
	for (var key in period.categorized_deliveries)
	{
		var data_json = {};
		var category_json = period.categorized_deliveries[key];
		data_json.name = key.replace("self", "Eigenverbrauch").replace("local","Einspeisung Lokal (<10km)").replace("grisons","Einspeisung Graubünden").replace("other","Einspeisung Schweiz");
		data_json.y = category_json.sum;
		data_json.color = key.replace("self","var(--self-color)").replace("local","var(--local-color)").replace("grisons","var(--grisons-color)").replace("other","var(--other-color)");
		data_json.legendIndex = key.replace("self","0").replace("local","1").replace("grisons","2").replace("other","3");
		data.push(data_json);
	}
	pie_chart_deliveries_options.series[0].data = data;
	pie_chart_deliveries_options.title.text = 'Produktion (' + numberWithCommas(period.sum_production.toFixed(1)) + ' kWh)';
	pie_chart_deliveries = Highcharts.chart('pie_chart_deliveries', pie_chart_deliveries_options);

	build_tooltip(pie_chart_deliveries.legend, 'Eigenverbrauch', text_autarky);

	// $('#pie_chart_connections').highcharts(pie_chart_connections.options);
}