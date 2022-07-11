# sample run : 
# python3 start_opti_mono_coin.py  ../configs/optimize/harmony_search.hjson --coin_list=XRPUSDT --nb_days=900 --iters=100 --n_cpus=6 --grid_span=[0.05,0.20] --min_markup=[0.05,0.05] --markup_range=[0.0,0.01] -oh
# coin by coin
#       will create a fake configuration in : ../configs/optimize/_*.hjson
#       will run the harmony optimisation
#       will use choose the good config with inspect_opt_results.py (PAD 0.02)
#       then backtest the config
#       After, save the config in configs/live/PBSO/COIN_DIRECTORY/config.json (the best config)
#       After, save the backtest result in configs/live/PBSO/COIN_DIRECTORY/result.txt (the Backtest of best config)

# @TODO : in high level folder, add the difference between, recursive or static grid (or neat)
# @TODO : Where to add the PNL 

import argparse
from hashlib import md5
import os
from pickle import FALSE, TRUE
from textwrap import indent
import hjson
import subprocess
import glob
import shutil
import re
import time
import datetime
from datetime import timedelta
import glob
import hashlib



# ------------------------------------------------------------
#             CREATE THE configs/live/PBSO/ directory  
# ------------------------------------------------------------
pbso_dir  = os.path.realpath("./../configs/live/PBSO/")
if not os.path.exists(pbso_dir):
     os.makedirs(pbso_dir)

# ------------------------------------------------------------
#             Manage command line parameters  
# ------------------------------------------------------------
parser = argparse.ArgumentParser( description="This script will loop on coins to optimize and backtest",
epilog="",
usage="python3 " + __file__ + " ./bulk_optimisation.hjson "
)

parser.add_argument("bo_config", type=str, help="file path to the bulk optimize config (hjson)")
args = parser.parse_args()
if not os.path.exists(args.bo_config) :
    print("bo_config doesn't exist")
    exit()

# ------------------------------------------------------------
#             Load  Bulk config  
# ------------------------------------------------------------
bo_config = hjson.load(open(args.bo_config, encoding="utf-8"))
# check exist configs
harmony_config_file = ""
if not os.path.exists(bo_config['harmony_config_file']):
    exit("ERROR : harmony_config_file doesn't exist")
else:
    harmony_config_file = bo_config['harmony_config_file'] = os.path.realpath(bo_config['harmony_config_file'])

backtest_config_file = ""
if not os.path.exists(bo_config['backtest_config_file']):
    exit("ERROR : backtest_config_file doesn't exist")
else:
    backtest_config_file = bo_config['backtest_config_file'] = os.path.realpath(bo_config['backtest_config_file'])


# -----------------------------------------------------------
#              Generate the name of the harmony config name (only name)
# -----------------------------------------------------------
md5_name = hashlib.md5(hjson.dumps(bo_config).encode('utf-8')).hexdigest()
harmony_config = os.path.dirname(bo_config['harmony_config_file']) + '/_harmony_' + md5_name + ".hjson"
print("We will use this auto generated and OVERIDED config : ", harmony_config)

# -----------------------------------------------------------
#              Generate the name of the backtest_config config name (only name)
# -----------------------------------------------------------
backtest_config = os.path.dirname(bo_config['backtest_config_file']) + '/_backtest_' + md5_name + ".hjson"
print("We will use this auto generated and OVERIDED config : ", backtest_config)

# -----------------------------------------------------------
#              Generate start_date & end_date 
# -----------------------------------------------------------
if ('nb_days' in bo_config['override_bt_and_opti']):
    today = datetime.date.today()
    bo_config['override_bt_and_opti']['start_date'] = str(today - timedelta(days=bo_config['override_bt_and_opti']['nb_days']))
    bo_config['override_bt_and_opti']['end_date'] = str(today)

print('Period :', bo_config['override_bt_and_opti']['start_date'], ' to ', bo_config['override_bt_and_opti']['end_date'])


# -----------------------------------------------------------
#              Generate the new backtest config OVERRIDE IT
# -----------------------------------------------------------
new_config_hjson = hjson.load(open(bo_config['backtest_config_file'], encoding="utf-8"))

# override from "override_bt_and_opti"
for key in bo_config['override_bt_and_opti']:
    if (key in new_config_hjson):
        new_config_hjson[key]  = bo_config['override_bt_and_opti'][key]

with open(backtest_config, 'w') as outfile:
    hjson.dumpJSON(new_config_hjson, outfile, indent=True)

# -----------------------------------------------------------
#              Generate the new harmony config OVERRIDE IT
# -----------------------------------------------------------
new_config_hjson = hjson.load(open(bo_config['harmony_config_file'], encoding="utf-8"))
new_config_hjson['symbols'] = ['NOTSET']

# override from "override_bt_and_opti"
for key in bo_config['override_bt_and_opti']:
    if (key in new_config_hjson):
        new_config_hjson[key]  = bo_config['override_bt_and_opti'][key]

# override basic setting in "override_harmony_config"
for key in bo_config['override_harmony_config']:
    if (key == "strategies_long_and_short"):
        continue
    if (key in new_config_hjson):
        new_config_hjson[key]  = bo_config['override_harmony_config'][key]

# override section "strategies_long_and_short"
for key in bo_config['override_harmony_config']['strategies_long_and_short']:
    value = bo_config['override_harmony_config']['strategies_long_and_short'][key]
    if (key in new_config_hjson):
        new_config_hjson[key]  = value

    if ('bounds_static_grid' in new_config_hjson):
        new_config_hjson['bounds_static_grid']['long'][key] = value
        new_config_hjson['bounds_static_grid']['short'][key] = value

    if ('bounds_recursive_grid' in new_config_hjson):
        new_config_hjson['bounds_recursive_grid']['long'][key] = value
        new_config_hjson['bounds_recursive_grid']['short'][key] = value

    if ('bounds_neat_grid' in new_config_hjson):
        new_config_hjson['bounds_neat_grid']['long'][key] = value
        new_config_hjson['bounds_neat_grid']['short'][key] = value



with open(harmony_config, 'w') as outfile:
    hjson.dumpJSON(new_config_hjson, outfile, indent=True)




# -----------------------------------------------------------
#              Load coin List
# -----------------------------------------------------------
print("Coin List :")
coin_list = bo_config['coin_list']
for a_coin in coin_list:
    print(a_coin['coin'] + " / Harmony start config : " +  
            (a_coin['harmony_starting_config'] if 'harmony_starting_config' in a_coin else "None")
        )

if len(coin_list) == 0 :
    exit('ERROR : No coin finded with the program arguments.')



# -----------------------------------------------------------
#              Loop on coin 
# -----------------------------------------------------------
for coin in coin_list:
    print('Start Optimize loop', coin['coin'])

    #python3 harmony_search.py -o config --oh -sd startdat -ed enddate -s SYMBOL
    command_line = [
                            "python3", "harmony_search.py", 
                            "-o", harmony_config,
                            "-s", coin['coin'],
                            "-b", backtest_config
                            ]
    if ('harmony_starting_config' in coin):
        command_line.append("-t")
        command_line.append(os.path.realpath(coin['harmony_starting_config']).replace('%COIN%', coin['coin']))    

    if bo_config['override_bt_and_opti']['ohlc']:
        command_line.append("-oh") 

    print(' '.join(command_line))
    
    try:
        subprocess.run(command_line, cwd="..")
        # print("othing")
    except subprocess.TimeoutExpired:
        print('Timeout Reached  seconds)')



    # find the last file all_results.txt (must be the new one created)
    list_of_files = glob.glob("./../results_harmony_*/*/all_results.txt", recursive=True)
    latest_file = max(list_of_files, key=os.path.getctime)
    latest_file = os.path.realpath(latest_file)

    print("Last result file is : ", latest_file)

    #         Findd the best strategy with inspect_opt_results.py
    #                     -p 0.02
    #                             [PAD around 0.02]

    #python3 inspect_opt_results.py results_harmony_search_recursive_grid/2022-07-10T18-32-36_XRPUSDT/all_results.txt -p 0.02 -d
    command_line = [
                            "python3", "inspect_opt_results.py", 
                             latest_file,
                            "-p", "0.02",  
                            "-d"
                            ]
    try:
        print(' '.join(command_line))
        subprocess.run(command_line, cwd="..")
    except subprocess.TimeoutExpired:
        print('Timeout Reached  seconds)')

    dir_to_save = pbso_dir + "/" + coin['coin'] + "_" + md5_name + "/"
    if not os.path.exists(dir_to_save):
        os.makedirs(dir_to_save)

    best_config_dest = dir_to_save + "/config.json"
    shutil.copy(os.path.dirname(latest_file) + "/all_results_best_config.json", best_config_dest)

    command_line = [
                                "python3", "backtest.py", 
                                "-s", coin['coin'],
                                "-b", backtest_config
                                ]

    if bo_config['override_bt_and_opti']['ohlc']:
        command_line.append("-oh") 
    
    command_line.append(best_config_dest) 


    try:
        print(' '.join(command_line))
        subprocess.run(command_line, cwd="..")
    except subprocess.TimeoutExpired:
        print('Timeout Reached  seconds)')


    #         Copy the backtest configuration
    #             change the config 
    #                 start_date: => now lower than 900 days [nb_days]
    #                   end_date: => now 
    #         run the backtest with this configs
    #         Copy the strategy in 
    #             /configs/live/PBSO/900d_1000i_0.02,0.4gs_0.02,0.4mm_0.02,0.4mr/config.json
    #         Copy the backtest result in 
    #             /configs/live/PBSO/900d_1000i_0.02,0.4gs_0.02,0.4mm_0.02,0.4mr/result.txt

    # find the last file  (must be the new one created)
    list_of_files = glob.glob("./../backtests/*/*/*/*/backtest_result.txt", recursive=True)
    latest_result = max(list_of_files, key=os.path.getctime)
    latest_result = os.path.realpath(latest_result)

    shutil.copy(latest_result, dir_to_save + '/result.txt')


    other_files_to_copy = [
                        'balance_and_equity_sampled_long.png',
                        'balance_and_equity_sampled_short.png',
                        'whole_backtest_long.png',
                        'whole_backtest_short.png',
    ]

    for src in other_files_to_copy:
        src_file = os.path.dirname(latest_result) + '/' + src
        if os.path.exists(src_file):
            shutil.copy(src_file, dir_to_save + '/' + src)
    
    shutil.copy(harmony_config, dir_to_save + '/')
    shutil.copy(backtest_config, dir_to_save + '/')
    shutil.copy(args.bo_config, dir_to_save + '/')



os.unlink(harmony_config)
os.unlink(backtest_config)

print('All Results files are stored in this directory : ', pbso_dir)


