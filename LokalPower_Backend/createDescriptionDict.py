import pickle
import pandas as pd
import ast

descriptions_df = pd.read_excel('../Daten/users/descriptions.xlsx')
descriptions_df = descriptions_df.set_index('ID')

descriptions = {}
for user_index in descriptions_df.index:
    description_dict = descriptions_df.loc[user_index].to_dict()
    description_dict['LOCATION'] = ast.literal_eval(description_dict['LOCATION'])
    descriptions[user_index] = description_dict

pickle.dump( descriptions, open( '../Daten/users/descriptions.pickle', "wb" ) )