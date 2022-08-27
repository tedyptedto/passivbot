
import glob
import os
import subprocess
import json
import pandas as pd
from tabulate import tabulate
import argparse
import os
import hjson

# loop on all strategy

base_dir = os.path.realpath("../configs/live/PBSO/BT_UNIFORMISED/bt_2020-01-01_2022-07-23_1000_1_XRPUSDT_LTCUSDT_ADAUSDT_DOTUSDT_UNIUSDT_DOGEUSDT_MATICUSDT_BNBUSDT_SOLUSDT_TRXUSDT_AVAXUSDT_USDCUSDT/")
# find all strategies

if not os.path.exists(base_dir) :
    print('Dir not exist')
    exit()

strats_dirs = glob.glob(base_dir + '/strat_*')

array_info = []

def addTo(object, key, value):
    if key in object:
        object[key] += value
    else:
        object[key] = value
    return object

for strat_dir in strats_dirs:
    # find all backtests 
    results_file = glob.glob(strat_dir + '/**/result.json', recursive=True)

    object={}
    strat_name = os.path.realpath(strat_dir).replace(base_dir, '').strip("/").split("/")[0]



    is_first = True
    for result_file in results_file:
        data = hjson.load(open(result_file, encoding="utf-8"))

        we_ratio = 1 / data['long']['wallet_exposure_limit']

        if is_first:
                addTo(object, 'strat_name', strat_name)
                addTo(object, 'au', (not (data['result']['n_unstuck_closes_long'] == 0)))
                is_first = False

        addTo(object, 'sum_final_equity_long', (data['result']['final_equity_long'] -  data['result']['starting_balance']) * we_ratio )
        addTo(object, 'sum_gain', (data['result']['final_balance_long'] -  data['result']['starting_balance']) * we_ratio)
        addTo(object, 'sum_loss', data['result']['loss_sum_long'] * we_ratio)
        addTo(object, 'Lowest equity/balance ratio', data['result']['eqbal_ratio_min_long'])
        addTo(object, 'pa_distance_mean_long', data['result']['pa_distance_mean_long'])
        addTo(object, 'long_we', data['long']['wallet_exposure_limit'])


    array_info.append(object)

df = pd.DataFrame(array_info)

df['ratio_loss']     = abs(df['sum_loss']) / df['sum_final_equity_long']       
df['ratio_distance'] = df['sum_final_equity_long'] / df['sum_gain']       

df['valid_for_me'] = (
                        (df['ratio_loss'] < 0.20) 
                        & 
                        (df['ratio_distance'] < 0.70) 
                        & 
                        (df['Lowest equity/balance ratio'] > 4)
                        &
                        (df['sum_final_equity_long'] > 0)
                        &
                        (df['sum_final_equity_long'] > 20000)
                        &
                        (df['pa_distance_mean_long'] < 5)
                        &
                        (df['au'] == True)
                        )
#(df['Lowest equity/balance ratio'] > 6) #& (df['pa_distance_mean_long'] < 1)
# df['valid_for_me'] = True

df = df[df.valid_for_me == True]

df.sort_values(by=[ 'valid_for_me', 'sum_final_equity_long'], ascending=[False, False], inplace=True)
print(tabulate(df, headers='keys', tablefmt='psql', showindex=False))

