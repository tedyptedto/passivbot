# sample run : python3 start_opti_mono_coin.py  ../configs/optimize/harmony_search.hjson --coin_list=XRPUSDT,BATUSDT --nb_days=30 --iters=50 --n_cpus=2 --grid_span=[0.05,0.20] --min_markup=[0.05,0.05] --markup_range=[0.0,0.01] -oh
# coin by coin
#       will create a fake configuration in : ../configs/optimize/_*.hjson
#       will run the harmony optimisation
#       will use choose the good config with inspect_opt_results.py (PAD 0.02)
#       then backtest the config
#       After, save the config in configs/live/PBSO/COIN_DIRECTORY/config.json (the best config)
#       After, save the backtest result in configs/live/PBSO/COIN_DIRECTORY/result.txt (the best config)


import argparse
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


config_overriding = ['iters', 'n_cpus', 'grid_span', 'min_markup', 'markup_range']
config_overriding_sub = ['grid_span', 'min_markup', 'markup_range']

# optimize_directory  = os.path.realpath("./harmony/")
# if not os.path.exists(optimize_directory):
#     os.makedirs(optimize_directory)

pbso_dir  = os.path.realpath("./../configs/live/PBSO/")
if not os.path.exists(pbso_dir):
     os.makedirs(pbso_dir)


def arguments_management():
    # Parameters :
    #     chemin_config_optimisation.json                   #config file
    #     - coin_list=XRPUSDT,MATICUSDT                     #coins list
    #     - nb_days=900                                     #how many days
    #     - iters=1000                              #number of iterations
    #     - n_cpus=2                                        #nb_cpu
    #     - oh                                              #activate OH 
    #     - grid_span=[0.02,0.4]                            #grid span
    #     - min_markup=[0.02,0.4]                           #min markup
    #     - markup_range=[0.02,0.4]                         #markup range 

    ### Parameters management
    parser = argparse.ArgumentParser( description="This script will loop on coins to optimize and backtest",
    epilog="",
    usage="python3 " + __file__ + " ../configs/optimize/harmony_search.hson "
    )

    parser.add_argument("optimize_config_filepath", type=str, help="file path to the base optimize config")

    parser.add_argument("--coin_list",
                        type=str, required=True, dest="coin_list",default="",
                        help="A list of coin separated by coma, ex : 'ONEUSDT,XLMUSDT'",
    )

    parser.add_argument("--nb_days",
                        type=int, required=True, dest="nb_days", default="300",
                        help="Nb Days from now to optimize",
    )

    parser.add_argument('-oh', "--ohlcv",
                        dest="ohlc",
                        help="use 1m ohlcv instead of 1s ticks",
                        action="store_true"
    )

    for field in config_overriding:
        parser.add_argument("--"+field,
                            type=str, required=True, dest=field, default="",
                            help="Override "+field+" in optimize config",
        )

 
    args = parser.parse_args()

    if not os.path.exists(args.optimize_config_filepath) :
        print("optimize_config_filepath doesn't exist")
        exit()


    args.optimize_config_filepath   = os.path.realpath(args.optimize_config_filepath)

    if not os.path.exists(args.optimize_config_filepath) :
        print("optimize_config_filepath doesn't exist")
        exit()


    if (len(args.coin_list.strip().split(',')) > 0) :
       args.coin_list = args.coin_list.strip().split(',')
       if args.coin_list[0] == '' :
           args.coin_list.pop(0)

    if len(args.coin_list) == 0 :
        print('No coin finded with the program arguments.')
        exit()

    return args




args = arguments_management()


#         Copy harmony_search.json into harmony_search_XRPUSDT.json
# creation et copie du nouveau fichier de configuration
new_opti_config_name = ""
array_args = vars(args)
not_needed = ['coin_list', 'ohlc', 'n_cpus', 'optimize_config_filepath']
for key in array_args:
    if (key in not_needed):
        continue

    new_opti_config_name += key + str(re.sub(r'[^a-z0-9,.]','', str(array_args[key]), flags=re.IGNORECASE)) + "_"
orig_opti_config_name = new_opti_config_name
new_opti_config_name = os.path.dirname(args.optimize_config_filepath) + '/_' + new_opti_config_name + ".hjson"

print("Create config for each coin : ")
#         Change values like this :
#             symbols => XRPUSDT          [coin by coin of coin_list]
#             n_cpus => 2                 [nb_cpu]
#             iters  => 1000              [nb_iterations]
#             grid_span => [0.02,0.4]     [grid_span]
#             min_markup => [0.02,0.4]    [min_markup]
#             markup_range => [0.02,0.4]  [markup_range]
new_config_hjson = hjson.load(open(args.optimize_config_filepath, encoding="utf-8"))

new_config_hjson['symbols'] = ['NOTSET']
new_config_hjson['n_cpus'] = int(args.n_cpus)
new_config_hjson['iters'] = int(args.iters)

for key in config_overriding_sub:
    new_config_hjson['bounds_static_grid']['long'][key] = hjson.loads(array_args[key])
    new_config_hjson['bounds_static_grid']['short'][key] = hjson.loads(array_args[key])
    new_config_hjson['bounds_recursive_grid']['long'][key] = hjson.loads(array_args[key])
    new_config_hjson['bounds_recursive_grid']['short'][key] = hjson.loads(array_args[key])



with open(new_opti_config_name, 'w') as outfile:
    # hjson.dump(new_config_hjson, outfile)
    hjson.dumpJSON(new_config_hjson, outfile, indent=True)

# Actions :
#     Loop on coins to optimise (for sample XRPUSDT) :

#         run the omptimisation for XRPUSDT
#     end loop
#new_opti_config_name
#   start_date: 2021-01-01
#   end_date: 2022-06-23
today = datetime.date.today()
start_date = str(today - timedelta(days=args.nb_days))
end_date = str(today)


for coin in args.coin_list:
    print('Optimize ', coin)
    #python3 harmony_search.py -o config --oh -sd startdat -ed enddate -s SYMBOL





    command_line = [
                            "python3", "harmony_search.py", 
                            "-o", new_opti_config_name,
                            "-sd", start_date,  
                            "-ed", end_date,
                            "-s", coin
                            # ,
                            # "-bd", optimize_directory 
                            ]
    if args.ohlc:
        command_line.append("-oh") 

    print(' '.join(command_line))
    # time.sleep(1)

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

    dir_to_save = pbso_dir + "/" + coin + "_" + orig_opti_config_name + "/"
    if not os.path.exists(dir_to_save):
        os.makedirs(dir_to_save)

    best_config_dest = dir_to_save + "/config.json"
    shutil.copy(os.path.dirname(latest_file) + "/all_results_best_config.json", best_config_dest)

    command_line = [
                                "python3", "backtest.py", 
                                "-s", coin,
                                "-sd", start_date,  
                                "-ed", end_date,
                                best_config_dest]

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







