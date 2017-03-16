import glob
import os

from LokalPower_Backend.LokalPower import LokalPower

prosumerLocations = [(46.961748, 9.559035),
                     (46.961142, 9.559173),
                     (46.960805, 9.559783),
                     (46.935596, 9.563438),
                     (46.935089, 9.561513),
                     (46.940076, 9.569257),
                     (46.942914, 9.571266),
                     (46.947246, 9.576537),
                     (46.949040, 9.577870),
                     (46.948910, 9.574680)]

print('len(prosumerLocations) = {}'.format(len(prosumerLocations)))

consumerLocations = [(46.968064, 9.558147),
                     (46.968499, 9.557931),
                     (46.966635, 9.560233),
                     (46.966561, 9.559968),
                     (46.966561, 9.559968),
                     (46.966909, 9.560144),
                     (46.967238, 9.560221),
                     (46.967145, 9.559788),
                     (46.949361, 9.573609),
                     (46.949393, 9.573156),
                     (46.949369, 9.572858),
                     (46.949381, 9.572602),
                     (46.949389, 9.572334),
                     (46.948658, 9.572136),
                     (46.948586, 9.571902),
                     (46.948485, 9.571746),
                     (46.948352, 9.571391),
                     (46.948235, 9.571135),
                     (46.948307, 9.570566),
                     (46.948516, 9.570393)]

print('len(consumerLocations) = {}'.format(len(consumerLocations)))

producerLocations = [(47.045076, 9.53354),  # hydro
                     (46.927656, 9.583668),  # hydro
                     (47.001958, 9.554126),  # biogas
                     (46.965493, 9.531499),  # solar
                     (46.999632, 9.537646)]  # solar

print('len(producerLocations) = {}'.format(len(producerLocations)))


def creatUserDict(start, end):
    lp = LokalPower()
    consumerFiles = glob.glob('../Daten/consumers/*.csv')
    prosumerFiles = glob.glob('../Daten/prosumers/*.csv')

    print(consumerFiles)
    print(prosumerFiles)

    producerColumns = [12, 13, 14, 15, 16]
    producerIds = ['Hydro 1', 'Hydro 2', 'Biogas', 'PV 1', 'PV 2']
    numConsumers = len(consumerFiles)
    numProsumers = len(prosumerFiles)
    numProducers = len(producerColumns)

    print("Number of Locations: {}".format(len(consumerLocations) + len(prosumerLocations) + len(producerLocations)))
    print("Number of consumers: {}".format(numConsumers))
    print("Number of prosumers: {}".format(numProsumers))
    print("Number of producers: {}".format(numProducers))

    locationdict = {}

    for i in range(len(consumerFiles)):
        userFile = consumerFiles[i]
        lp.addConsumer(userFile, consumerLocations[i], os.path.basename(userFile).split()[0])
        locationdict[os.path.basename(consumerFiles[i]).split()[0]] = consumerLocations[i]

    for i in range(len(prosumerFiles)):
        userFile = prosumerFiles[i]
        lp.addConsumer(userFile, prosumerLocations[i], os.path.basename(userFile).split()[0])
        locationdict[os.path.basename(prosumerFiles[i]).split()[0]] = prosumerLocations[i]

    producerFile = '../LastgangdatenRePower/Lastgangdaten_slim.csv'

    for i in range(numProducers):
        lp.addProducer(producerFile, producerLocations[i], producerIds[i], producerColumns[i])
        locationdict[producerIds[i]] = producerLocations[i]

    lp.saveDictsToFile(locationdict, '../Daten/dicts/locations.pickle')

    consumerDicts = lp.getConsumerDicts(start, end)

    lp.saveDictsToFile(consumerDicts, '../Daten/dicts/consumerDicts.pickle')

    for i in range(len(consumerFiles)):
        consumerId = os.path.basename(consumerFiles[i]).split()[0]
        lp = LokalPower()
        userdict = lp.getUserDicts(consumerDicts, consumerId)
        lp.saveDictsToFile(userdict, '../Daten/dicts/{}.pickle'.format(consumerId))

    for i in range(len(prosumerFiles)):
        consumerId = os.path.basename(prosumerFiles[i]).split()[0]
        lp = LokalPower()
        userdict = lp.getUserDicts(consumerDicts, consumerId)
        lp.saveDictsToFile(userdict, '../Daten/dicts/{}.pickle'.format(consumerId))

creatUserDict(0, 35136)