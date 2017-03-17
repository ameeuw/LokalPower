import glob
import pickle

import numpy as np
import pandas as pd

from LokalPower_Backend.LokalPower import LokalPower

NDAYS = 366  # number of days in 2016
DELTAT = 0.25  # hours
MONTHVEC = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
cMonthVec = np.cumsum(MONTHVEC) * 24 * 4


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
    def __init__(self, FileName, Location, Idx):
        self.FileName = FileName
        self.Index = Idx
        self.Location = Location
        self.SetLoadProfile()
        self.DemByMonth()
        self.SetAnnualDemand()
        self.Price = 0.15  # Fr/kWh
        self.PriceGrid = 0
        self.SetCost()

    def SetLoadProfile(self):
        demand, production = LoadConsumerData(self.FileName)
        setattr(self, 'Demand', demand)
        setattr(self, 'Production', production)

    def DemByMonth(self):  # demand by month
        valsPerMonth = []
        for _k in range(len(cMonthVec) - 1):
            Pmonth = self.Demand[cMonthVec[_k]:cMonthVec[_k + 1]]
            valsPerMonth.append(round(np.sum(Pmonth * DELTAT)))

        setattr(self, 'DemandByMonth', valsPerMonth)

    def SetAnnualDemand(self):
        setattr(self, 'AnnualDemand', np.round(np.sum(self.Demand * DELTAT)).astype(int))

    def SetPeakDemandPerMonth(self):
        setattr(self, 'PeakDemandPerMonth', np.max(self.DemandByMonth * DELTAT))

    def SetCost(self):
        setattr(self, 'TotalCost', round(self.AnnualDemand * self.Price, 2))

    def setUserDict(self, filename):
        setattr(self, 'Connections', pickle.load(open(filename, "rb")))
        pass

    def getAggregatedConnections(self, start=0, end=35136):
        aggregatedConnections = {}
        if hasattr(self, 'Connections'):
            # for timeSlice in self.Connections.keys():
            for timeSlice in range(start, end):
                if timeSlice in self.Connections.keys():
                    timeSliceConnections = self.Connections[timeSlice]
                    for connection in timeSliceConnections:
                        fromId = connection['fromId']
                        if fromId not in aggregatedConnections.keys():
                            aggregatedConnections[fromId] = {}
                            aggregatedConnections[fromId]['energy'] = connection['energy'] * DELTAT
                            aggregatedConnections[fromId]['location'] = connection['from']
                        else:
                            aggregatedConnections[fromId]['energy'] += connection['energy'] * DELTAT
        return aggregatedConnections

    def getAggregatedPaths(self, aggregatedConnections=None):
        paths = []
        if aggregatedConnections is None:
            aggregatedConnections = self.getAggregatedConnections()
        for supplierId, supplyDict in aggregatedConnections.iteritems():
            path = []
            path.append(supplyDict['location'])
            path.append(self.Location)
            paths.append(path)
        return paths

    def getPaths(self):
        paths = []
        if hasattr(self, 'Connections'):
            for timeSlice in range(len(self.Connections)):
                for connection in range(len(self.Connections[timeSlice])):
                    path = []
                    path.append(self.Connections[timeSlice][connection]['from'])
                    path.append(self.Connections[timeSlice][connection]['to'])
                paths.append(path)
        return paths

    def creatUserDict(self, start, end):
        lp = LokalPower()
        demandFiles = glob.glob('../Daten/*.csv')
        print(demandFiles)
        producerColumns = [1, 2, 3, 12, 13, 14, 15]
        numConsumers = len(demandFiles)
        numProducers = 7
        locations = [(46.968064, 9.558147), (46.968499, 9.557931), (46.966635, 9.560233), (46.966561, 9.559968),
                     (46.966909, 9.560144), (46.967238, 9.560221), (46.967145, 9.559788), (46.967145, 9.559788),
                     (46.966262, 9.559003), (46.965699, 9.559023), (47.002399, 9.570044), (46.965493, 9.531499),
                     (46.927656, 9.583668), (47.045076, 9.53354)]
        print("Number of Locations: {}".format(len(locations)))
        print("Number of consumers: {}".format(numConsumers))
        print("Number of producers: {}".format(numProducers))

        for i in range(len(demandFiles)):
            userFile = demandFiles[i]
            lp.addConsumer(userFile, locations[i][0], locations[i][1])

        producerFile = '../LastgangdatenRePower/Lastgangdaten_slim.csv'

        for i in range(numProducers):
            lp.addProducer(producerFile, locations[numConsumers + i][0], locations[numConsumers + i][1])
            lp.users[numConsumers + i].SetLoadProfile(producerColumns[i])

        consumerDicts = lp.getConsumerDicts(start, end)
        userDicts = lp.getUserDicts(consumerDicts, self.Index)
        lp.saveDictsToFile(userDicts, 'user{}.pickle'.format(self.Index))
