import glob
import os
import pickle

from LokalPower_Backend.LokalPower import LokalPower
import pandas as pd
import ast

def creatUserDicts(start=0, stop=35136):
    lp = LokalPower()
    userFiles = glob.glob('../Daten/users/*.csv')
    # userLocations = pickle.load(open('../Daten/users/locations.pickle', "rb"))
    descriptions_df = pd.read_excel('../Daten/users/descriptions.xlsx')
    descriptions_df = descriptions_df.set_index('ID')

    user_locations = {}
    for user_index in descriptions_df.index:
        user_location = ast.literal_eval(descriptions_df.loc[user_index]['LOCATION'])
        user_locations[user_index] = user_location

    userLocations = user_locations

    print(userFiles)

    producerColumns = [12, 13, 170, 15, 16, 195]
    producerIds = ['Hydro1', 'Hydro2', 'Biogas', 'PV1', 'PV2', 'Wind1']

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

    # consumerDicts = lp.getConsumerDicts(start, stop)
    consumerDicts, producerDicts = lp.getDicts(start, stop)

    lp.saveDictsToFile(consumerDicts, '../Daten/dicts/consumerDicts.pickle')
    lp.saveDictsToFile(producerDicts, '../Daten/dicts/producerDicts.pickle')

    print("Saving consumer_dicts")
    for i in range(len(userFiles)):
        print('{} / {} = {:.2f} %'.format(i, len(userFiles), (float(i) / len(userFiles)) * 100))
        userFile = userFiles[i]
        userId = os.path.basename(userFile).split('.')[0]
        userDict = lp.getUserDicts(consumerDicts, userId)
        lp.saveDictsToFile(userDict, '../Daten/dicts/{}.pickle'.format(userId))

    print("Saving producer_dicts")
    for i in range(len(userFiles)):
        print('{} / {} = {:.2f} %'.format(i, len(userFiles), (float(i) / len(userFiles)) * 100))
        userFile = userFiles[i]
        producerId = os.path.basename(userFile).split('.')[0]
        producerDict = lp.getUserDicts(producerDicts, producerId)
        lp.saveDictsToFile(producerDict, '../Daten/dicts/prod_{}.pickle'.format(producerId))

    print("Saving plant producer_dicts")
    for i in range(len(producerIds)):
        print('{} / {} = {:.2f} %'.format(i, len(producerIds), (float(i) / len(producerIds)) * 100))
        producerId = producerIds[i]
        producerDict = lp.getUserDicts(producerDicts, producerId)
        lp.saveDictsToFile(producerDict, '../Daten/dicts/prod_{}.pickle'.format(producerId))

creatUserDicts()