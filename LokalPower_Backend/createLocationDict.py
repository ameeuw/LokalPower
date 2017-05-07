import glob
import os
import pickle

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

producerLocations = [(46.912633, 9.779556),  # hydro 1: klosters
                     (46.8851, 9.878602),  # hydro 2: kueblis
                     (46.835896, 9.487296),  # biomasse
                     (47.149092,9.7571782),  # solar: Wehinger Josef
                     (46.8491408,9.5402532)]  # solar: Pixelmolkerei

print('len(producerLocations) = {}'.format(len(producerLocations)))

consumerFiles = glob.glob('../Daten/consumers/*.csv')
prosumerFiles = glob.glob('../Daten/prosumers/*.csv')
producerFile = '../LastgangdatenRePower/Lastgangdaten_slim.csv'

print(consumerFiles)
print(prosumerFiles)

producerColumns = [12, 13, 14, 15, 16]
producerIds = ['Hydro1', 'Hydro2', 'Biogas', 'PV1', 'PV2']
numConsumers = len(consumerFiles)
numProsumers = len(prosumerFiles)
numProducers = len(producerColumns)

print("Number of Locations: {}".format(len(consumerLocations) + len(prosumerLocations) + len(producerLocations)))
print("Number of consumers: {}".format(numConsumers))
print("Number of prosumers: {}".format(numProsumers))
print("Number of producers: {}".format(numProducers))

locationdict = {}

for i in range(len(consumerFiles)):
    locationdict[os.path.basename(consumerFiles[i]).split()[0]] = consumerLocations[i]

for i in range(len(prosumerFiles)):
    locationdict[os.path.basename(prosumerFiles[i]).split()[0]] = prosumerLocations[i]

for i in range(numProducers):
    locationdict[producerIds[i]] = producerLocations[i]

pickle.dump( locationdict, open( '../Daten/users/locations.pickle', "wb" ) )

print("Created location dictionary:")
for key, value in locationdict.iteritems():
    print('{} : {}'.format(key, value))