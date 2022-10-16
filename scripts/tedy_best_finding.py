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


# ../configs/live/PBSO/BT_UNIFORMISED/bt_2020-01-01_2022-10-13_1000_1_XRPUSDT_LTCUSDT_ADAUSDT_DOTUSDT_UNIUSDT_DOGEUSDT_MATICUSDT_BNBUSDT_SOLUSDT_TRXUSDT_AVAXUSDT_USDCUSDT/

dir_name = 'bt_2020-01-01_2022-10-13_1000_1_XRPUSDT_LTCUSDT_ADAUSDT_DOTUSDT_UNIUSDT_DOGEUSDT_MATICUSDT_BNBUSDT_SOLUSDT_TRXUSDT_AVAXUSDT_USDCUSDT'

dir_base = "../configs/live/PBSO/"

base_dir = os.path.realpath(dir_base + "BT_UNIFORMISED/" + dir_name + "/")
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

    nb_coins = len(results_file)

    is_first = True
    for result_file in results_file:
        data = hjson.load(open(result_file, encoding="utf-8"))

        we_ratio = 1 / data['long']['wallet_exposure_limit']

        if is_first:
            addTo(object, 'strat_name', strat_name.replace('strat_',''))
            addTo(object, 'au', (not (data['result']['n_unstuck_closes_long'] == 0)))
            is_first = False
            if 'grid_span' in data['long']:
                addTo(object, 'gs', int(data['long']['grid_span'] * 100))
            else:
                addTo(object, 'gs', -1)

        addTo(object, 's_k',   data['starting_balance'])
        addTo(object, 's_f_equ_long', ((data['result']['final_equity_long'] * we_ratio) -  data['result']['starting_balance'])  )
        addTo(object, 's_gain', ((data['result']['final_balance_long'] * we_ratio) -  data['result']['starting_balance']) )
        addTo(object, 's_loss', data['result']['loss_sum_long'] * we_ratio)
        addTo(object, 'low_equ_bal', data['result']['eqbal_ratio_min_long'])
        addTo(object, 'pa_dist_mean_long', data['result']['pa_distance_mean_long'])
        addTo(object, 'l_we', data['long']['wallet_exposure_limit'])
        addTo(object, 'we_ratio', we_ratio)
        addTo(object, 'adg_exposure', data['result']['adg_per_exposure_long'] * 100)
        addTo(object, 'n_days', data['n_days'])

    
    if nb_coins > 0:
        object['pa_dist_mean_long']   = object['pa_dist_mean_long'] / nb_coins
        object['low_equ_bal'] = object['low_equ_bal'] / nb_coins
        object['adg_exposure'] = object['adg_exposure'] / nb_coins
        object['n_days'] = object['n_days'] / nb_coins
        object['l_we'] = object['l_we'] / nb_coins

    array_info.append(object)

df = pd.DataFrame(array_info)

# df['s_loss']     = int(df['s_loss'])       
df['ratio_loss']     = abs(df['s_loss']) / df['s_f_equ_long']       
df['ratio_dist'] = df['s_f_equ_long'] / df['s_gain']       
df['krishn_ratio'] = df['s_f_equ_long'] * df['low_equ_bal']       

df['valid_for_me'] = (  True
                        # (df['ratio_loss'] < 0.20) 
                        # & 
                        # (df['ratio_dist'] < 0.70) 
                        # & 
                        # (df['low_equ_bal'] > 4)
                        # &
                        # (df['low_equ_bal'] > 6)
                        # &
                        # (df['sum_final_equity_long'] > 0)
                        # &
                        # (df['gridspan'] >= 20)
                        # &
                        # # &
                        # # (df['sum_final_equity_long'] > 20000)
                        # &
                        # (df['pa_distance_mean_long'] < 5)
                        # &
                        # (df['pa_distance_mean_long'] < 0.20)
                        # &
                        # (df['au'] == True)
                        )
#(df['Lowest equity/balance ratio'] > 6) #& (df['pa_distance_mean_long'] < 1)
# df['valid_for_me'] = True

df = df[df.valid_for_me == True]

df.drop(columns=['valid_for_me', 'au', 'we_ratio'], inplace=True)

df.sort_values(by=[ 'adg_exposure'], ascending=[False], inplace=True)
# df.sort_values(by=[ 'sum_final_equity_long'], ascending=[False], inplace=True)
print(tabulate(df, headers='keys', tablefmt='psql', showindex=False))

df.to_csv(dir_base + 'tedy_best_finding_' + dir_name + '.csv') 