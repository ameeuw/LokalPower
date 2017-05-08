import glob
import os
import pickle
import pandas as pd
import ast

descriptions_df = pd.read_excel('../Daten/users/descriptions.xlsx')
descriptions_df = descriptions_df.set_index('ID')
user_locations = {}
for user_index in descriptions_df.index:
    user_location = ast.literal_eval(descriptions_df.loc[user_index]['LOCATION'])
    user_locations[user_index] = user_location

locationdict = user_locations

pickle.dump( locationdict, open( '../Daten/users/locations.pickle', "wb" ) )

print("Created location dictionary:")
for key, value in locationdict.iteritems():
    print('{} : {}'.format(key, value))