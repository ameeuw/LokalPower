import pandas as pd
import numpy as np
import pickle

NDAYS = 366  # number of days in 2016
DELTAT = 0.25  # hours
MONTHVEC = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
cMonthVec = np.cumsum(MONTHVEC) * 24 * 4


class Producer(object):
    def __init__(self, FileName, location, id, column):
        self.FileName = FileName
        self.Location = location
        self.Id = id
        self.setLoadProfile(column)

    def loadProducerData(self, fname, column):
        dat = pd.read_csv(fname, header=0, skiprows=[0], usecols=np.arange(20))
        dat = dat[dat.columns[column]].values * (-1000)
        return dat

    def setLoadProfile(self, column):
        setattr(self, 'demand', self.loadProducerData(self.FileName, column))


class User(object):
    def __init__(self, FileName, location, id):
        self.FileName = FileName
        self.Location = location
        self.Id = id
        self.SetLoadProfile()
        self.DemByMonth()
        self.SetAnnualDemand()
        self.Price = 0.15  # Fr/kWh
        self.PriceGrid = 0
        self.SetCost()

    def LoadConsumerData(self, fname):
        _dat = pd.read_csv(fname, header=None, delimiter=';')
        production = _dat[_dat[_dat.columns[1]].values == 'Wirkenergie A- 15']
        demand = _dat[_dat[_dat.columns[1]].values == 'Wirkenergie A+ 15']

        Pprod = production[production.columns[4]].values / 0.25  # W
        Pdem = demand[demand.columns[4]].values / 0.25  # W

        Pprod = np.nan_to_num(Pprod)
        Pdem = np.nan_to_num(Pdem)

        return Pdem, Pprod

    def SetLoadProfile(self):
        demand, production = self.LoadConsumerData(self.FileName)
        setattr(self, 'demand', demand)
        setattr(self, 'production', production)

    def DemByMonth(self):  # demand by month
        valsPerMonth = []
        for _k in range(len(cMonthVec) - 1):
            Pmonth = self.demand[cMonthVec[_k]:cMonthVec[_k + 1]]
            valsPerMonth.append(round(np.sum(Pmonth * DELTAT)))

        setattr(self, 'DemandByMonth', valsPerMonth)

    def SetAnnualDemand(self):
        setattr(self, 'AnnualDemand', np.round(np.sum(self.demand * DELTAT) / 1000).astype(int)) # kWh

    def SetPeakDemandPerMonth(self):
        setattr(self, 'PeakDemandPerMonth', np.max(self.demand * DELTAT))

    def SetCost(self):
        setattr(self, 'TotalCost', round(self.AnnualDemand * self.Price, 2))

    def SetConsumerDict(self, filename):
        setattr(self, 'userDict', pickle.load(open(filename, "rb")))
        pass
