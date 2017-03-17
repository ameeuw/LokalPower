import glob
import os
import pickle

from LokalPower_Backend.LokalPower import LokalPower


def creatUserDicts(start=0, end=35136):
    lp = LokalPower()
    userFiles = glob.glob('../Daten/users/*.csv')
    userLocations = pickle.load(open('../Daten/users/locations.pickle', "rb"))

    print(userFiles)

    producerColumns = [12, 13, 14, 15, 16]
    producerIds = ['Hydro1', 'Hydro2', 'Biogas', 'PV1', 'PV2']

    numProducers = len(producerColumns)
    numUsers = len(userFiles)

    print("Number of Locations: {}".format(len(userLocations)))
    print("Number of users: {}".format(numUsers))
    print("Number of producers: {}".format(numProducers))

    for i in range(len(userFiles)):
        userFile = userFiles[i]
        userId = os.path.basename(userFile).split('.')[0]
        lp.addConsumer(userFile, userLocations[userId], userId)

    producerFile = '../LastgangdatenRePower/Lastgangdaten_slim.csv'

    for i in range(numProducers):
        userId = producerIds[i]
        lp.addProducer(producerFile, userLocations[userId], userId, producerColumns[i])

    consumerDicts = lp.getConsumerDicts(start, end)

    lp.saveDictsToFile(consumerDicts, '../Daten/dicts/consumerDicts.pickle')

    for i in range(len(userFiles)):
        userFile = userFiles[i]
        userId = os.path.basename(userFile).split('.')[0]
        userDict = lp.getUserDicts(consumerDicts, userId)
        lp.saveDictsToFile(userDict, '../Daten/dicts/{}.pickle'.format(userId))

creatUserDicts()