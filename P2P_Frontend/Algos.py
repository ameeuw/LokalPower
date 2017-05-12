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
    def __init__(self, fileName, location, idx):
        self.fileName = fileName
        self.index = idx
        self.period = {}
        self.period['resolution'] = 'monthly'
        self.period['month'] = 'Jan'
        self.location = location
        self.setLoadProfile()
        self.demByMonth()
        self.demByDay()
        self.prodByMonth()
        self.prodByDay()
        self.setAnnualDemand()
        self.setAnnualProduction()
        self.price = 0.15  # Fr/kWh
        self.priceGrid = 0
        self.setCost()
        #self.prosumerSim()


    def setLoadProfile(self):
        demand, production = LoadConsumerData(self.fileName)
        setattr(self, 'demand', demand)
        setattr(self, 'production', production)

    def demByMonth(self):  # demand by month
        valsPerMonth = []
        for _k in range(len(cMonthVec) - 1):
            Pmonth = self.demand[cMonthVec[_k]:cMonthVec[_k + 1]]
            valsPerMonth.append(round(np.sum(Pmonth * DELTAT), 2))

        setattr(self, 'demandByMonth', valsPerMonth)

    def demByDay(self): # demand by day
        valsPerDay = []
        for day in range(NDAYS):
            demDay = self.demand[(day * 24*4):((day+1) * 24*4)]
            valsPerDay.append(round(np.sum(demDay * DELTAT), 2))
        setattr(self, 'demandByDay', valsPerDay)


    def prodByMonth(self):  # demand by month
        valsPerMonth = []
        for _k in range(len(cMonthVec) - 1):
            Pmonth = self.production[cMonthVec[_k]:cMonthVec[_k + 1]]
            valsPerMonth.append(round(np.sum(Pmonth * DELTAT), 2))
        setattr(self, 'productionByMonth', valsPerMonth)


    def prodByDay(self):
        valsPerDay = []
        for day in range(NDAYS):
            prodDay = self.production[(day * 24*4):((day+1) * 24*4)]
            valsPerDay.append(round(np.sum(prodDay * DELTAT), 2))
        setattr(self, 'productionByDay', valsPerDay)

    def setAnnualDemand(self):
        setattr(self, 'annualDemand', np.round(np.sum(self.demand * DELTAT), 2))

    def setAnnualProduction(self):
        if len(self.production) > 0:
            annualProduction = np.round(np.sum(self.production * DELTAT), 2)
        else:
            annualProduction = 0
        setattr(self, 'annualProduction', annualProduction)

    def setPeakDemandPerMonth(self):
        setattr(self, 'peakDemandPerMonth', np.max(self.demandByMonth * DELTAT))

    def setPeakProductionPerMonth(self):
        setattr(self, 'peakProductionPerMonth', np.max(self.productionByMonth * DELTAT))

    def setCost(self):
        setattr(self, 'totalCost', round(self.annualDemand * self.price, 2))

    def setUserDict(self, filename):
        setattr(self, 'connections', pickle.load(open(filename, "rb")))
        pass

    def setProducerDict(self, filename):
        setattr(self, 'deliveries', pickle.load(open(filename, "rb")))

    def getAggregatedConnections(self, start=0, end=35136):
        aggregatedConnections = {}
        if hasattr(self, 'connections'):
            # for timeSlice in self.Connections.keys():
            for timeSlice in range(start, end):
                if timeSlice in self.connections.keys():
                    timeSliceConnections = self.connections[timeSlice]
                    for connection in timeSliceConnections:
                        fromId = connection['fromId']
                        if fromId not in aggregatedConnections.keys():
                            aggregatedConnections[fromId] = {}
                            aggregatedConnections[fromId]['energy'] = connection['energy'] * DELTAT
                            aggregatedConnections[fromId]['location'] = connection['from']
                        else:
                            aggregatedConnections[fromId]['energy'] += connection['energy'] * DELTAT
        return aggregatedConnections


    def getAggregatedDeliveries(self, start=0, end=35136):
        aggregatedDeliveries = {}
        if hasattr(self, 'deliveries'):
            # for timeSlice in self.Connections.keys():
            for timeSlice in range(start, end):
                if timeSlice in self.deliveries.keys():
                    timeSliceConnections = self.deliveries[timeSlice]
                    for delivery in timeSliceConnections:
                        toId = delivery['toId']
                        if toId not in aggregatedDeliveries.keys():
                            aggregatedDeliveries[toId] = {}
                            aggregatedDeliveries[toId]['energy'] = delivery['energy'] * DELTAT
                            aggregatedDeliveries[toId]['location'] = delivery['to']
                        else:
                            aggregatedDeliveries[toId]['energy'] += delivery['energy'] * DELTAT
        return aggregatedDeliveries

    def setDailyAggregatedConnections(self):
        dailyAggregatedConnections = []
        if hasattr(self, 'connections'):
            for day in range(sum(MONTHVEC)):
                dailyAggregatedConnections.append(self.getAggregatedConnections(day * 24*4, (day+1) * 24*4))
        # print(len(dailyAggregatedConnections))
        # print(dailyAggregatedConnections)
        setattr(self, 'dailyAggregatedConnections', dailyAggregatedConnections)


    def setDailyAggregatedDeliveries(self):
        dailyAggregatedDeliveries = []
        if hasattr(self, 'deliveries'):
            for day in range(sum(MONTHVEC)):
                dailyAggregatedDeliveries.append(self.getAggregatedDeliveries(day * 24*4, (day+1) * 24*4))
        # print(len(dailyAggregatedDeliveries))
        # print(dailyAggregatedDeliveries)
        setattr(self, 'dailyAggregatedDeliveries', dailyAggregatedDeliveries)


    def setMonthlyAggregatedConnections(self):
        monthlyAggregatedConnections = []
        if hasattr(self, 'connections'):
            for month in range(12):
                start = sum(MONTHVEC[0:month + 1])
                stop = sum(MONTHVEC[0:month + 2])
                monthlyAggregatedConnections.append(self.aggregateDailyConnections(self.dailyAggregatedConnections[start:stop]))
        setattr(self, 'monthlyAggregatedConnections', monthlyAggregatedConnections)


    def setMonthlyAggregatedDeliveries(self):
        monthlyAggregatedDeliveries = []
        if hasattr(self, 'deliveries'):
            for month in range(12):
                start = sum(MONTHVEC[0:month + 1])
                stop = sum(MONTHVEC[0:month + 2])
                monthlyAggregatedDeliveries.append(self.aggregateDailyDeliveries(self.dailyAggregatedDeliveries[start:stop]))
        setattr(self, 'monthlyAggregatedDeliveries', monthlyAggregatedDeliveries)


    def aggregateDailyConnections(self, dailyConnections):
        aggregatedConnections = {}
        for timeSliceConnections in dailyConnections:
            for fromId, connection in timeSliceConnections.iteritems():
                if fromId not in aggregatedConnections.keys():
                    aggregatedConnections[fromId] = {}
                    aggregatedConnections[fromId]['energy'] = connection['energy']
                    aggregatedConnections[fromId]['location'] = connection['location']
                else:
                    aggregatedConnections[fromId]['energy'] += connection['energy']
        return aggregatedConnections


    def aggregateDailyDeliveries(self, dailyDeliveries):
        aggregatedDeliveries = {}
        for timeSliceDeliveries in dailyDeliveries:
            for toId, delivery in timeSliceDeliveries.iteritems():
                if toId not in aggregatedDeliveries.keys():
                    aggregatedDeliveries[toId] = {}
                    aggregatedDeliveries[toId]['energy'] = delivery['energy']
                    aggregatedDeliveries[toId]['location'] = delivery['location']
                else:
                    aggregatedDeliveries[toId]['energy'] += delivery['energy']
        return aggregatedDeliveries


    def setAggregatedConnections(self, start=0, end=35136):
        setattr(self, 'aggregatedConnections', self.getAggregatedConnections(start=start, end=end))


    def setAggregatedDeliveries(self, start=0, end=35136):
        setattr(self, 'aggregatedDeliveries', self.getAggregatedDeliveries(start=start, end=end))


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


        g2l_daily = []
        pv2g_daily = []
        b2l_daily = []
        pv2l_daily = []
        pv2b_daily = []
        pv_daily = []
        for day in range(NDAYS):
            g2l = self.G2L[(day * 24*4):((day+1) * 24*4)]
            pv2g = self.PV2G[(day * 24*4):((day+1) * 24*4)]

            b2l = self.B2L[(day * 24*4):((day+1) * 24*4)]
            pv2l = self.PV2L[(day * 24*4):((day+1) * 24*4)]
            pv2b = self.PV2B[(day * 24*4):((day+1) * 24*4)]
            pv = self.PV[(day * 24*4):((day+1) * 24*4)]

            g2l_daily.append(round(np.sum(g2l * DELTAT), 2))
            pv2g_daily.append(round(np.sum(pv2g * DELTAT), 2))

            b2l_daily.append(round(np.sum(b2l * DELTAT), 2))
            pv2l_daily.append(round(np.sum(pv2l * DELTAT), 2))
            pv2b_daily.append(round(np.sum(pv2b * DELTAT), 2))
            pv_daily.append(round(np.sum(pv * DELTAT), 2))
        setattr(self, 'daily_g2l', g2l_daily)
        setattr(self, 'daily_pv2l', pv2l_daily)
        setattr(self, 'daily_b2l', b2l_daily)
        setattr(self, 'daily_pv', pv_daily)


        monthly_g2l = []
        monthly_pv2l = []
        monthly_b2l = []
        monthly_pv = []
        for _k in range(len(cMonthVec) - 1):
            g2l = self.G2L[cMonthVec[_k]:cMonthVec[_k + 1]]
            pv2l = self.PV2L[cMonthVec[_k]:cMonthVec[_k + 1]]
            b2l = self.B2L[cMonthVec[_k]:cMonthVec[_k + 1]]
            pv = self.PV[cMonthVec[_k]:cMonthVec[_k + 1]]

            monthly_g2l.append(round(np.sum(g2l * DELTAT), 2))
            monthly_pv2l.append(round(np.sum(pv2l * DELTAT), 2))
            monthly_b2l.append(round(np.sum(b2l * DELTAT), 2))
            monthly_pv.append(round(np.sum(pv * DELTAT), 2))
        setattr(self, 'monthly_g2l', monthly_g2l)
        setattr(self, 'monthly_pv2l', monthly_pv2l)
        setattr(self, 'monthly_b2l', monthly_b2l)
        setattr(self, 'monthly_pv', monthly_pv)

        print('\n\ndaily_b2l = {}\n\n'.format(self.daily_b2l))
        print('\n\ndaily_pv = {}\n\n'.format(self.daily_pv))

        for _k in keyList:
            setattr(self, 'annual_'+_k, np.sum( getattr(self, _k) * Inputs['dt'] ).astype(int) )
