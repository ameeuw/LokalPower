import pickle
producerDict = pickle.load(open('../Daten/dicts/prod_CH1012301234500000000000000112183.pickle', "rb"))


for key, value in producerDict.iteritems():
    print(key, value)