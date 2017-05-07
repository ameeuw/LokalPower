import pickle

import networkx as nx
from geopy.distance import vincenty
from numpy import *

import LokalPower_Backend.User


class LokalPower(object):
    def __init__(self):
        self.users = []

    def addProducer(self, fname, location, id, column):
        self.users.append(LokalPower_Backend.User.Producer(fname, location, id, column))

    def addConsumer(self, fname, location, id):
        self.users.append(LokalPower_Backend.User.User(fname, location, id))

    def getGeoDistance(self, start, end, locations):
        dFloat = (vincenty(locations[start], locations[end]).kilometers)
        dInt = int(dFloat*1000)
        return dInt

    def generateGraph(self, demands, locations, ids):
        G = nx.DiGraph()
        n = len(demands)
        start_nodes = []
        end_nodes = []
        for i in range(n):
            for j in delete(range(n),i):
                # only production can give energy away
                if (demands[i] < 0) and (demands[j] > 0):
                    # print(demands[i], '>>', demands[j])
                    start_nodes.append(i)
                    end_nodes.append(int(j))

        for i in range(n):
            G.add_node(i, demand = demands[i], location = locations[i], id = ids[i])

        for i in range(len(start_nodes)):
            _start = start_nodes[i]
            _end = end_nodes[i]
            _weight = (self.getGeoDistance(_start, _end, locations))
            _capacity = -G.node[_start]['demand']
            #print(_capacity)
            G.add_edge(_start, _end, weight = _weight, capacity = _capacity, distance = self.getGeoDistance(_start, _end, locations))
        return G

    def flowToConsumerDict(self, flowDict, G):
        consumerDict = {}
        n = len(G.nodes())
        for fromIndex in range(n):
            for toIndex in flowDict[fromIndex]:
                if flowDict[fromIndex][toIndex] > 0:
                    energy = flowDict[fromIndex][toIndex]
                    distance = G.edge[fromIndex][toIndex]['distance']
                    fromId = G.node[fromIndex]['id']
                    toId = G.node[toIndex]['id']

                    if toId not in consumerDict.keys():
                        consumerDict[toId] = []
                    consumerDict[toId].append({'from' : fromIndex, 'to' : toIndex, 'distance' : distance, 'energy' : energy})
        return consumerDict

    def flowToProducerDict(self, flowDict, G):
        producerDict = {}
        n = len(G.nodes())
        for fromIndex in range(n):
            for toIndex in flowDict[fromIndex]:
                if flowDict[fromIndex][toIndex] > 0:
                    energy = flowDict[fromIndex][toIndex]
                    distance = G.edge[fromIndex][toIndex]['distance']
                    fromId = G.node[fromIndex]['id']
                    toId = G.node[toIndex]['id']

                    if fromId not in producerDict.keys():
                        producerDict[fromId] = []
                        producerDict[fromId].append({'from' : fromIndex, 'to': toIndex, 'distance': distance, 'energy' : energy})
        return producerDict

    def getConsumerDicts(self, start, stop):
        consumerDicts = []

        for currentSlice in range(start, stop):
            _demands, _locations, _ids = self.getTimeSliceData(currentSlice)
            G = self.generateGraph(_demands, _locations, _ids)
            _flowDict = nx.min_cost_flow(G)
            _consumerDict = self.flowToConsumerDict(_flowDict, G)
            _consumerDict['graph'] = G
            _consumerDict['flowDict'] = _flowDict
            consumerDicts.append(_consumerDict)
        return consumerDicts

    def getDicts(self, start, stop):
        consumerDicts = []
        producerDicts = []
        print('Getting dicts from {} to {}'.format(start, stop))
        for currentSlice in range(start, stop):
            if (currentSlice % 500 == 0):
                print('{} / {} = {} %'.format(currentSlice, stop, (float(currentSlice)/stop)*100))

            _demands, _locations, _ids = self.getTimeSliceData(currentSlice)
            G = self.generateGraph(_demands, _locations, _ids)
            _flowDict = nx.min_cost_flow(G)

            _consumerDict = self.flowToConsumerDict(_flowDict, G)
            _consumerDict['graph'] = G
            _consumerDict['flowDict'] = _flowDict
            consumerDicts.append(_consumerDict)

            _producerDict = self.flowToProducerDict(_flowDict, G)
            _producerDict['graph'] = G
            _producerDict['flowDict'] = _flowDict
            producerDicts.append(_producerDict)

        return consumerDicts, producerDicts

    # TODO: check for correctness of timeslices
    def getUserDicts(self, consumerDicts, consumer):
        userDicts = {}
        for timeSlice in range(len(consumerDicts)):
            connections = []
            G = consumerDicts[timeSlice]['graph']
            if consumer in consumerDicts[timeSlice].keys():
                for connection in consumerDicts[timeSlice][consumer]:
                    connectionDict = {}
                    connectionDict['fromId'] = (G.node[connection['from']]['id'])
                    connectionDict['toId'] = (G.node[connection['to']]['id'])
                    connectionDict['from'] = (G.node[connection['from']]['location'])
                    connectionDict['to'] = (G.node[connection['to']]['location'])
                    connectionDict['energy'] = connection['energy']
                    connections.append(connectionDict)
                userDicts[timeSlice] = connections
        return userDicts

    def getTimeSliceData(self, timeSlice):
        demands = []
        locations = []
        ids = []

        for i in range(len(self.users)):
            demand = int(self.users[i].demand[timeSlice])
            # print('USER: {} - DEMAND: {}'.format(self.users[i].Id, demand))
            try:
                production = int(self.users[i].production[timeSlice])

                if ( production > 0 ):
                    demands.append(-production)
                    locations.append(self.users[i].Location)
                    ids.append(self.users[i].Id)
            except:
                #print('No production...')
                pass

            demands.append(demand)
            locations.append(self.users[i].Location)
            ids.append(self.users[i].Id)


        # Add grid as load / supply for balance issues
        #self.addBalanceUser(-sum(demands), 46.966638, 9.555431)

        demands.append(-sum(demands))
        locations.append((46.746655, 9.841554))
        ids.append('GRID')

        return demands, locations, ids

    def saveDictsToFile(self, dicts, fileName):
        pickle.dump( dicts, open( fileName, "wb" ) )
