import glob
import pickle

import numpy as np
import pandas as pd

NDAYS = 366  # number of days in 2016
DELTAT = 0.25  # hours
MONTHVEC = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
cMonthVec = np.cumsum(MONTHVEC) * 24 * 4



def neg2Zero(x):
    x[x<0]=0
    return x

def pos2Zero(x):
    x[x>=0]=0
    return x


## -------------------------------------
## battery simulation functions
## -------------------------------------


Inputs={
    'EtaInv': 0.95, # solar string inverter efficiency
    'EbatR' : 10.0, # rated battery capacity
    'EtaCh' : 0.95, # Charging efficiency of battery+charger
    'EtaDCh': 0.95, # discharging efficiency of battery+charger
    'SigmaCL': 0.9, # degradation factor
    'dt' : DELTAT, # dt in hour
    'DoD' : 0.8 # battery depth of discharge
}


def BatteryCalc2(Pload,Pdc,Inputs):
    # Pload, Pdc in kW within dt
    # EbatR, rated energy capacity in kWh
    n=len(Pload)

    EbatMax=Inputs['EbatR']*(1-(1-Inputs['DoD'])/2.)*Inputs['SigmaCL']
    EbatMin=Inputs['EbatR']*(1-Inputs['DoD'])/2.*Inputs['SigmaCL']

    Ebat=np.zeros(n)
    Ebat[0]=EbatMin

    AnnualBalance={
    'W_PV2B' : np.zeros(n),
    'W_PV2G' : np.zeros(n),
    'W_B2L' :  np.zeros(n),
    'W_PV2L' : np.zeros(n),
    'W_G2L' : np.zeros(n)
    }

    dt=Inputs['dt']

    dP=Pdc-Pload/Inputs['EtaInv']


    for k in range(n)[:-1]:
        if dP[k]>=0.0:
            Ebat[k+1]=min(Ebat[k]+dP[k]*dt*Inputs['EtaCh'], EbatMax)

        else: #dP[k]<0.0:

            Ebat[k+1]=max(Ebat[k]+dP[k]*dt/Inputs['EtaDCh'], EbatMin)


        AnnualBalance['W_PV2B'][k] = max( Ebat[k+1] - Ebat[k] , 0)
        AnnualBalance['W_PV2G'][k] = max( dP[k]*dt*Inputs['EtaInv']-AnnualBalance['W_PV2B'][k]*Inputs['EtaInv']/Inputs['EtaCh'],0)
        AnnualBalance['W_B2L'][k] = max( -(Ebat[k+1] - Ebat[k]) * (Inputs['EtaInv']*Inputs['EtaDCh']) , 0)
        AnnualBalance['W_PV2L'][k] = Pload[k]*dt+min(dP[k]*dt,0)*Inputs['EtaInv']
        AnnualBalance['W_G2L'][k] = Pload[k]*dt-AnnualBalance['W_B2L'][k]-AnnualBalance['W_PV2L'][k]

    AnnualBalance['Ebat'] = Ebat
    AnnualBalance['W_PV'] = Pdc*dt
    AnnualBalance['W_L'] = Pload*dt

    return AnnualBalance



def LoadConsumerData(fname):
    _dat = pd.read_csv(fname, header=None, delimiter=';')
    production = _dat[_dat[_dat.columns[1]].values == 'Wirkenergie A- 15']
    demand = _dat[_dat[_dat.columns[1]].values == 'Wirkenergie A+ 15']

    Pprod = production[production.columns[4]].values / 0.25 / 1000 # kW
    Pdem = demand[demand.columns[4]].values / 0.25 / 1000 # kW

    Pprod = np.nan_to_num(Pprod)
    Pdem = np.nan_to_num(Pdem)

    return Pdem, Pprod


class User:
    def __init__(self, file_name, location, idx):
        self.file_name = file_name
        self.index = idx
        self.period = {}
        self.period['resolution'] = 'monthly'
        self.period['month'] = 'Jan'
        self.location = location
        self.set_load_profile()
        self.set_demand_by_month()
        self.set_demand_by_day()
        self.set_production_by_month()
        self.set_production_by_day()
        self.set_annual_demand()
        self.set_annual_production()
        self.price = 0.15  # Fr/kWh
        self.grid_price = 0
        self.set_cost()
        #self.prosumerSim()


    def set_load_profile(self):
        demand, production = LoadConsumerData(self.file_name)
        setattr(self, 'demand', demand)
        setattr(self, 'production', production)

    def set_demand_by_month(self):  # demand by month
        valsPerMonth = []
        for _k in range(len(cMonthVec) - 1):
            Pmonth = self.demand[cMonthVec[_k]:cMonthVec[_k + 1]]
            valsPerMonth.append(round(np.sum(Pmonth * DELTAT), 2))
        setattr(self, 'demand_by_month', valsPerMonth)

    def set_demand_by_day(self): # demand by day
        valsPerDay = []
        for day in range(NDAYS):
            demDay = self.demand[(day * 24*4):((day+1) * 24*4)]
            valsPerDay.append(round(np.sum(demDay * DELTAT), 2))
        setattr(self, 'demand_by_day', valsPerDay)


    def set_production_by_month(self):  # demand by month
        valsPerMonth = []
        for _k in range(len(cMonthVec) - 1):
            Pmonth = self.production[cMonthVec[_k]:cMonthVec[_k + 1]]
            valsPerMonth.append(round(np.sum(Pmonth * DELTAT), 2))
        setattr(self, 'production_by_month', valsPerMonth)


    def set_production_by_day(self):
        valsPerDay = []
        for day in range(NDAYS):
            prodDay = self.production[(day * 24*4):((day+1) * 24*4)]
            valsPerDay.append(round(np.sum(prodDay * DELTAT), 2))
        setattr(self, 'production_by_day', valsPerDay)

    def set_annual_demand(self):
        setattr(self, 'annual_demand', np.round(np.sum(self.demand * DELTAT), 2))

    def set_annual_production(self):
        if len(self.production) > 0:
            annual_production = np.round(np.sum(self.production * DELTAT), 2)
        else:
            annual_production = 0
        setattr(self, 'annual_production', annual_production)

    def set_peak_demand_per_month(self):
        setattr(self, 'peak_demand_per_month', np.max(self.demandByMonth * DELTAT))

    def set_peak_production_per_month(self):
        setattr(self, 'peak_production_per_month', np.max(self.productionByMonth * DELTAT))

    def set_cost(self):
        setattr(self, 'total_cost', round(self.annual_demand * self.price, 2))

    def set_user_dict(self, filename):
        setattr(self, 'connections', pickle.load(open(filename, "rb")))

    def set_producer_dict(self, filename):
        setattr(self, 'deliveries', pickle.load(open(filename, "rb")))

    def get_aggregated_connections(self, start=0, stop=35136):
        aggregated_connections = {}
        if hasattr(self, 'connections'):
            for time_slice in range(start, stop):
                if time_slice in self.connections.keys():
                    time_slice_connections = self.connections[time_slice]
                    for connection in time_slice_connections:
                        from_id = connection['fromId']
                        if from_id not in aggregated_connections.keys():
                            aggregated_connections[from_id] = {}
                            aggregated_connections[from_id]['energy'] = connection['energy'] * DELTAT
                            aggregated_connections[from_id]['location'] = connection['from']
                        else:
                            aggregated_connections[from_id]['energy'] += connection['energy'] * DELTAT
        return aggregated_connections


    def get_aggregated_deliveries(self, start=0, stop=35136):
        aggregated_deliveries = {}
        if hasattr(self, 'deliveries'):
            for time_slice in range(start, stop):
                if time_slice in self.deliveries.keys():
                    time_slice_connections = self.deliveries[time_slice]
                    for delivery in time_slice_connections:
                        to_id = delivery['toId']
                        if to_id not in aggregated_deliveries.keys():
                            aggregated_deliveries[to_id] = {}
                            aggregated_deliveries[to_id]['energy'] = delivery['energy'] * DELTAT
                            aggregated_deliveries[to_id]['location'] = delivery['to']
                        else:
                            aggregated_deliveries[to_id]['energy'] += delivery['energy'] * DELTAT
        return aggregated_deliveries

    def set_daily_aggregated_connections(self):
        daily_aggregated_connections = []
        if hasattr(self, 'connections'):
            for day in range(sum(MONTHVEC)):
                daily_aggregated_connections.append(self.get_aggregated_connections(day * 24*4, (day+1) * 24*4))
        setattr(self, 'daily_aggregated_connections', daily_aggregated_connections)

    def set_daily_aggregated_deliveries(self):
        daily_aggregated_deliveries = []
        if hasattr(self, 'deliveries'):
            for day in range(sum(MONTHVEC)):
                daily_aggregated_deliveries.append(self.get_aggregated_deliveries(day * 24*4, (day+1) * 24*4))
        setattr(self, 'daily_aggregated_deliveries', daily_aggregated_deliveries)

    def set_monthly_aggregated_connections(self):
        monthly_aggregated_connections = []
        if hasattr(self, 'connections'):
            for month in range(12):
                start = sum(MONTHVEC[0:month + 1])
                stop = sum(MONTHVEC[0:month + 2])
                monthly_aggregated_connections.append(self.aggregate_daily_connections(self.daily_aggregated_connections[start:stop]))
        setattr(self, 'monthly_aggregated_connections', monthly_aggregated_connections)


    def set_monthly_aggregated_deliveries(self):
        monthly_aggregated_deliveries = []
        if hasattr(self, 'deliveries'):
            for month in range(12):
                start = sum(MONTHVEC[0:month + 1])
                stop = sum(MONTHVEC[0:month + 2])
                monthly_aggregated_deliveries.append(self.aggregate_daily_deliveries(self.daily_aggregated_deliveries[start:stop]))
        setattr(self, 'monthly_aggregated_deliveries', monthly_aggregated_deliveries)


    def aggregate_daily_connections(self, daily_connections):
        aggregated_connections = {}
        for time_slice_connections in daily_connections:
            for from_id, connection in time_slice_connections.iteritems():
                if from_id not in aggregated_connections.keys():
                    aggregated_connections[from_id] = {}
                    aggregated_connections[from_id]['energy'] = connection['energy']
                    aggregated_connections[from_id]['location'] = connection['location']
                else:
                    aggregated_connections[from_id]['energy'] += connection['energy']
        return aggregated_connections


    def aggregate_daily_deliveries(self, daily_deliveries):
        aggregated_deliveries = {}
        for time_slice_deliveries in daily_deliveries:
            for to_id, delivery in time_slice_deliveries.iteritems():
                if to_id not in aggregated_deliveries.keys():
                    aggregated_deliveries[to_id] = {}
                    aggregated_deliveries[to_id]['energy'] = delivery['energy']
                    aggregated_deliveries[to_id]['location'] = delivery['location']
                else:
                    aggregated_deliveries[to_id]['energy'] += delivery['energy']
        return aggregated_deliveries

    def prosumerSim(self, EbatR=0):
        dLoad = self.demand - self.production

        if EbatR == 0:
            Inputs['EbatR'] = 0.001 # computation crashes if EbatR = 0 (div 0)
        else:
            Inputs['EbatR'] = EbatR

        # batterySim Runs always
        Inputs['EbatR'] = EbatR
        Ab = BatteryCalc2(self.demand, self.production / Inputs['EtaInv'], Inputs)

        autarky = np.sum( Ab['W_PV2L'] + Ab['W_B2L'] ) / np.sum(Ab['W_L'])
        selfconsumption = np.sum( Ab['W_PV2L'] + Ab['W_B2L'] ) / np.sum(Ab['W_PV'])

        battery_simulation = {}

        battery_simulation['EbatR'] = EbatR
        battery_simulation['G2L'] = Ab['W_G2L'] / Inputs['dt']
        battery_simulation['PV2G'] = Ab['W_PV2G'] / Inputs['dt']
        battery_simulation['B2L'] = Ab['W_B2L'] / Inputs['dt']
        battery_simulation['PV2L'] = Ab['W_PV2L'] / Inputs['dt']
        battery_simulation['PV2B'] = Ab['W_PV2B'] / Inputs['dt']
        battery_simulation['PV'] = Ab['W_PV'] / Inputs['dt']
        battery_simulation['autarky'] = autarky
        battery_simulation['selfconsumption'] = selfconsumption

        # DELETE
        setattr(self, 'EbatR', EbatR)
        setattr(self, 'G2L', Ab['W_G2L'] / Inputs['dt'] ) # all in kW
        setattr(self, 'PV2G', Ab['W_PV2G'] / Inputs['dt'] )
        setattr(self, 'B2L', Ab['W_B2L'] / Inputs['dt'] )
        setattr(self, 'PV2L', Ab['W_PV2L'] / Inputs['dt'] )
        setattr(self, 'PV2B', Ab['W_PV2B'] / Inputs['dt'] )
        setattr(self, 'PV', Ab['W_PV'] / Inputs['dt'] )

        setattr( self, 'autarky', autarky )
        setattr( self, 'selfconsumption', selfconsumption )

        keyList=['G2L', 'PV2G', 'B2L', 'PV2L', 'PV2B', 'PV']

        for _k in keyList:
            setattr(self, 'annual_'+_k, np.sum( getattr(self, _k) * Inputs['dt'] ).astype(int) ) # DELETE
            battery_simulation['annual_'+_k] = np.sum(battery_simulation[_k] * Inputs['dt']).astype(int)


        g2l_daily = []
        pv2g_daily = []
        b2l_daily = []
        pv2l_daily = []
        pv2b_daily = []
        pv_daily = []
        for day in range(NDAYS):
            g2l = battery_simulation['G2L'][(day * 24*4):((day+1) * 24*4)]
            pv2g = battery_simulation['PV2G'][(day * 24*4):((day+1) * 24*4)]

            b2l = battery_simulation['B2L'][(day * 24*4):((day+1) * 24*4)]
            pv2l = battery_simulation['PV2L'][(day * 24*4):((day+1) * 24*4)]
            pv2b = battery_simulation['PV2B'][(day * 24*4):((day+1) * 24*4)]
            pv = battery_simulation['PV'][(day * 24*4):((day+1) * 24*4)]

            g2l_daily.append(round(np.sum(g2l * DELTAT), 2))
            pv2g_daily.append(round(np.sum(pv2g * DELTAT), 2))

            b2l_daily.append(round(np.sum(b2l * DELTAT), 2))
            pv2l_daily.append(round(np.sum(pv2l * DELTAT), 2))
            pv2b_daily.append(round(np.sum(pv2b * DELTAT), 2))
            pv_daily.append(round(np.sum(pv * DELTAT), 2))

        battery_simulation['daily_g2l'] = g2l_daily
        battery_simulation['daily_pv2l'] = pv2l_daily
        battery_simulation['daily_b2l'] = b2l_daily
        battery_simulation['daily_pv'] = pv_daily


        monthly_g2l = []
        monthly_pv2l = []
        monthly_b2l = []
        monthly_pv = []
        for _k in range(len(cMonthVec) - 1):
            g2l = battery_simulation['G2L'][cMonthVec[_k]:cMonthVec[_k + 1]]
            pv2l = battery_simulation['PV2L'][cMonthVec[_k]:cMonthVec[_k + 1]]
            b2l = battery_simulation['B2L'][cMonthVec[_k]:cMonthVec[_k + 1]]
            pv = battery_simulation['PV'][cMonthVec[_k]:cMonthVec[_k + 1]]

            monthly_g2l.append(round(np.sum(g2l * DELTAT), 2))
            monthly_pv2l.append(round(np.sum(pv2l * DELTAT), 2))
            monthly_b2l.append(round(np.sum(b2l * DELTAT), 2))
            monthly_pv.append(round(np.sum(pv * DELTAT), 2))

        battery_simulation['monthly_g2l'] = monthly_g2l
        battery_simulation['monthly_pv2l'] = monthly_pv2l
        battery_simulation['monthly_b2l'] = monthly_b2l
        battery_simulation['monthly_pv'] = monthly_pv

        setattr(self, 'battery_simulation', battery_simulation)
