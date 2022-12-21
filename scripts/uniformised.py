import os
import glob
import hashlib
import time
import hjson
import re
import subprocess
import shutil
import argparse


number_of_thread = 11

# To be the best more realistic
# @TODO : check the grid OK before backtesting ? 

### Parameters management
parser = argparse.ArgumentParser( description="This script will create a multi backtest on many strategies on PBSO",
epilog="",
usage="python3 " + __file__ + " "
)

parser.add_argument("-sd",
                    type=str,required=False,dest="start_date",default="2020-01-01",
                    help="Backtest start date",
)
parser.add_argument("-ed",
                    type=str,required=False,dest="end_date",default="2022-12-21",
                    help="Backtest end date",
)
parser.add_argument("-we",
                    type=float,required=False,dest="we",default=1,
                    help="Total WE of the strategy in backtest",
)
parser.add_argument("-balance",
                    type=int,required=False,dest="starting_balance",default=1000,
                    help="Starting balance",
)
parser.add_argument("-cl","--coin_list",
                        type=str,required=False,dest="coin_list",default="XRPUSDT,LTCUSDT,ADAUSDT,DOTUSDT,UNIUSDT,DOGEUSDT,MATICUSDT,BNBUSDT,SOLUSDT,TRXUSDT,AVAXUSDT",
                        # type=str,required=False,dest="coin_list",default="XRPUSDT",
                        help="A list of coin separated by coma. Ex : 'ONEUSDT,XLMUSDT'",
)
args = parser.parse_args()



start_date = args.start_date
end_date = args.end_date
we = args.we
starting_balance = str(args.starting_balance)
coin_list = args.coin_list.split(',')

number_of_thread = min(len(coin_list), number_of_thread)


def convertHJsonToHumanReadable(filename):
    # Read in the file
    with open(filename, 'r') as file :
        filedata = file.read()

    # Replace the target string
    filedata = re.sub('\[\r?\n[ ]*', '[', filedata ) 
    filedata = re.sub('[ ]*\r?\n[ ]*\]', ']', filedata ) 
    filedata = re.sub('([0-9]+),\r?\n[ ]*([0-9]+)', r'\1,\2', filedata ) 

    # Write the file out again
    with open(filename, 'w') as file:
        file.write(filedata)

def cleanningBigFiles(PBSO_uniformed_directory):
    #second cleaning action
    to_delete = glob.glob(PBSO_uniformed_directory+"/**/caches", recursive=True)
    to_delete = to_delete + glob.glob(PBSO_uniformed_directory+"/**/optimize", recursive=True)
    to_delete = to_delete + glob.glob(PBSO_uniformed_directory+"/**/fills_long.csv", recursive=True)
    to_delete = to_delete + glob.glob(PBSO_uniformed_directory+"/**/fills_short.csv", recursive=True)
    to_delete = to_delete + glob.glob(PBSO_uniformed_directory+"/**/stats.csv", recursive=True)
    to_delete = to_delete + glob.glob(PBSO_uniformed_directory+"/**/psizes_plot.png", recursive=True)
    to_delete = to_delete + glob.glob(PBSO_uniformed_directory+"/**/auto_unstuck_bands_long.png", recursive=True)
    to_delete = to_delete + glob.glob(PBSO_uniformed_directory+"/**/auto_unstuck_bands_short.png", recursive=True)
    to_delete = to_delete + glob.glob(PBSO_uniformed_directory+"/**/initial_entry_band_long.png", recursive=True)
    to_delete = to_delete + glob.glob(PBSO_uniformed_directory+"/**/initial_entry_band_short.png", recursive=True)
    for delete in to_delete:
        if os.path.exists(delete):
            print("Cleaning : ", delete)
            if os.path.isdir(delete):
                shutil.rmtree(delete)
            elif os.path.isfile(delete):
                os.unlink(delete)


# coin_file = "./tmp/grid_ok_coins.json"
# if os.path.exists(coin_file):
#     print ('AUTO LOADED config from ', coin_file)
#     coin_list = hjson.load(open(coin_file, encoding="utf-8"))

tmp_dir = os.path.realpath("./tmp/")
if not os.path.exists(tmp_dir):
    os.makedirs(tmp_dir)
PBSO_dir = os.path.realpath("./../configs/live/PBSO/")

uid_bt = start_date + "_" + end_date + "_" + starting_balance + "_" + str(we) + '_' +  "_".join(coin_list)

PBSO_uniformed_directory = os.path.realpath("./../configs/live/PBSO/BT_UNIFORMISED/" + '/bt_'+ uid_bt + '/') + '/'
if not os.path.exists(PBSO_uniformed_directory):
     os.makedirs(PBSO_uniformed_directory)



# 1/ find all the strategies
a_config = glob.glob(PBSO_dir+"/**/*.json", recursive=True)
nb_config = len(a_config)
i = 1
a_md5 = []
backtest_directory_previous = ''

nb_new_config = 0

for config in a_config:

    print(i , "/", nb_config)
    i = i + 1

    parent_dir = config.replace(PBSO_dir, '').strip("/").split("/")[0]
    # avoid trash directory
    if parent_dir == "xx_trash":
        print("Avoid Trash Directory")
        continue
    # avoid BT_UNIFORMISED
    if parent_dir == "BT_UNIFORMISED":
        print("Avoid BT_UNIFORMISED Directory")
        continue


    o_config = hjson.load(open(config, encoding="utf-8"))
    md5 = hashlib.md5(hjson.dumps(o_config).encode('utf-8')).hexdigest()[0:5]

    # check if it is a strategy
    if not 'config_name' in o_config:
        print("Not a config")
        continue
    if not 'long' in o_config:
        print("Not a config")
        continue

    # memory check to avoid playing twice the same strategy
    if md5 in a_md5:
        print('Avoid already BACKTESTED strategy')
        continue
    a_md5.append(md5)
    print("backtesting : " , config)
    
    # 2/ update the wallet exposure of the strategy

    if not 'wallet_exposure_limit' in o_config['long']:
        print('to Old configuration, continue')
        continue

    print('Original WE Long : ', o_config['long']['enabled'], o_config['long']['wallet_exposure_limit'])
    print('Original WE Short : ', o_config['short']['enabled'], o_config['short']['wallet_exposure_limit'])

    if o_config['long']['enabled'] and o_config['short']['enabled']:
        ratio = we / (o_config['long']['wallet_exposure_limit'] + o_config['short']['wallet_exposure_limit'])
        o_config['long']['wallet_exposure_limit'] = o_config['long']['wallet_exposure_limit'] * ratio
        o_config['short']['wallet_exposure_limit'] = o_config['short']['wallet_exposure_limit'] * ratio
    elif o_config['long']['enabled']:
        ratio = we / (o_config['long']['wallet_exposure_limit'])
        o_config['long']['wallet_exposure_limit'] = o_config['long']['wallet_exposure_limit'] * ratio
    elif o_config['short']['enabled']:
        ratio = we / (o_config['short']['wallet_exposure_limit'])
        o_config['short']['wallet_exposure_limit'] = o_config['short']['wallet_exposure_limit'] * ratio

    print('Final WE Long : ', o_config['long']['enabled'], o_config['long']['wallet_exposure_limit'])
    print('Final WE Short : ', o_config['short']['enabled'], o_config['short']['wallet_exposure_limit'])

    final_config = tmp_dir + '/' + md5 + '.json'

    with open(final_config, 'w') as outfile:
        hjson.dumpJSON(o_config, outfile, indent=True)

    convertHJsonToHumanReadable(final_config)

    # 3/ run the backtest in a organised directory /uid/
    


    backtest_directory = PBSO_uniformed_directory  + 'strat_' + md5 + '/'
    
    avoid_already_done_bt = False
    if os.path.exists(backtest_directory):
        if os.path.exists(backtest_directory + "/_original_config.json"):
            avoid_already_done_bt = True


    if avoid_already_done_bt:
        print("Avoid to replay the BackTest")
        os.unlink(final_config)
        continue

    print("new config finded : ", config)
    nb_new_config = nb_new_config + 1
    # time.sleep(2.4)
    # continue

    if not os.path.exists(backtest_directory):
        os.makedirs(backtest_directory)

    unif_info_json = {
                        'orig_strategy' : config.replace(PBSO_dir, ''),
    }

    # save some information in JSON format
    with open(backtest_directory + "/unif_info.json", 'w') as the_file:
        hjson.dumpJSON(unif_info_json, the_file, indent=True)

    # push a readme to know where come from the strategy
    with open(backtest_directory + "/README.md", 'w') as the_file:
        the_file.write("Strategy come from : " + config.replace(PBSO_dir, ''))




    shutil.copy(config, backtest_directory + '/_original_config.json')


    #cleaning
    if not backtest_directory_previous== "":
        # copy the cache files
        # trouver les cache file du previous
        cache_to_copy = glob.glob(backtest_directory_previous+"/**/caches/*", recursive=True)

        # les copier dans le nouveau
        for cache_file in cache_to_copy:
            src_cache  = os.path.realpath(cache_file)
            dest_cache = src_cache.replace(backtest_directory_previous, backtest_directory)

            dir_cache = os.path.dirname(dest_cache)
            if not os.path.exists(dir_cache):
                os.makedirs(dir_cache)

            shutil.copy(src_cache, dest_cache)

        # nettoyer le previous
        cleanningBigFiles(backtest_directory_previous)


    list_backtest_directories = []
    threads = []

    for coin in coin_list:
        #Backtest [-h] [--nojit] [-b BACKTEST_CONFIG_PATH] [-s SYMBOL] [-u USER] [-sd START_DATE] [-ed END_DATE] [-sb STARTING_BALANCE] [-m MARKET_TYPE] [-bd BASE_DIR] [-lw LONG_WALLET_EXPOSURE_LIMIT]
        # [-sw SHORT_WALLET_EXPOSURE_LIMIT] [-le LONG_ENABLED] [-se SHORT_ENABLED] [-np N_PARTS] [-oh]

        #attente des backtest lancé en // 
        print('Waiting process to end')
        if len(threads) == number_of_thread:
            for p in threads:
                p.wait()
            threads = []  # clear the threads

        print(i , "/", nb_config, " => ", config)
        command_line = [
                                    "python3", "backtest.py", 
                                    "-s", coin,
                                    "-sd", start_date,
                                    "-ed", end_date,
                                    "-sb", starting_balance,
                                    "-bd", backtest_directory,
                                    "-np", "0",
                                    # "-oh",
                                    final_config
                                    ]
        list_backtest_directories.append(backtest_directory)

        try:
            print(' '.join(command_line))
            process = subprocess.Popen(command_line, cwd="..")
            threads.append(process)
        except subprocess.TimeoutExpired:
            print('Timeout Reached  seconds)')

    #attente des backtest lancé en // au cas ou il en reste
    print('After loop, another waiting process to end')
    for p in threads:
        p.wait()

    # nettoyage des fichiers de cache sauf le dernier dont on va avoir besoin
    for bt_dir in list_backtest_directories:
        if (bt_dir != backtest_directory):
            cleanningBigFiles(bt_dir)

    backtest_directory_previous = backtest_directory

    print('Delete temporary strategy')
    os.unlink(final_config)
    
    print('Backtest ended')

#auto generate the CSV file

#second cleaning action
cleanningBigFiles(PBSO_uniformed_directory)

print("New strategies backtested : ", nb_new_config)

#python3 2_backtest_summary.py 3 ../configs/live/a_tedy.json 
# ../configs/backtest/default.hjson 
# -o-csv ../configs/live/PBSO/bt_2021-01-01_2022-07-23_1000_1_XRPUSDT_LTCUSDT_ADAUSDT_DOTUSDT_UNIUSDT_DOGEUSDT_MATICUSDT_BNBUSDT_SOLUSDT_TRXUSDT_AVAXUSDT_USDCUSDT.csv 
# -bd ../configs/live/PBSO/BT_UNIFORMISED/bt_2021-01-01_2022-07-23_1000_1_XRPUSDT_LTCUSDT_ADAUSDT_DOTUSDT_UNIUSDT_DOGEUSDT_MATICUSDT_BNBUSDT_SOLUSDT_TRXUSDT_AVAXUSDT_USDCUSDT/

command_line = [
                        "python3", "2_backtest_summary.py", 
                        "3", config,
                        "../configs/backtest/default.hjson", 
                        "-o-csv", "../configs/live/PBSO/bt_" + uid_bt + ".csv" ,
                        "-bd", PBSO_uniformed_directory,
                        ]
try:
    print(' '.join(command_line))
    subprocess.run(command_line)
except subprocess.TimeoutExpired:
    print('Timeout Reached  seconds)')



command_line = [
                        "python3", "github_upload.py"
                        ]
try:
    print(' '.join(command_line))
    subprocess.run(command_line)
except subprocess.TimeoutExpired:
    print('Timeout Reached  seconds)')


# python3 2_backtest_summary.py 3 ../configs/live/a_tedy.json 
# ../configs/backtest/default.hjson 
# -o-csv ../configs/live/PBSO/bt_2021-01-01_2022-07-23_1000_1_XRPUSDT_LTCUSDT_ADAUSDT_DOTUSDT_UNIUSDT_DOGEUSDT_MATICUSDT_BNBUSDT_SOLUSDT_TRXUSDT_AVAXUSDT_USDCUSDT.csv 
# -bd ../configs/live/PBSO/BT_UNIFORMISED/bt_2021-01-01_2022-07-23_1000_1_XRPUSDT_LTCUSDT_ADAUSDT_DOTUSDT_UNIUSDT_DOGEUSDT_MATICUSDT_BNBUSDT_SOLUSDT_TRXUSDT_AVAXUSDT_USDCUSDT/ 
# -min-bkr 1 -min-gain 100 -min-days 365 -max-stuck 500

# command_line = [
#                         "python3", "2_backtest_summary.py", 
#                         "3", config,
#                         "../configs/backtest/default.hjson", 
#                         "-o-csv", "../configs/live/PBSO/best_bt_" + uid_bt + ".csv" ,
#                         "-bd", PBSO_uniformed_directory,
#                         # "-min-gridspan","19","-min-bkr","1","-max-stuck-avg","5"

#                         "-min-eqbal_ratio_min_long", "0.8", "-max-stuck-avg", "2", "-min-gridspan", "19", 
#                         "-min-gain", "100", "-max-pa_distance_mean_long", "0.02"
#                         , "-max-loss_sum_long","500"



#                         # , "-min-gain","200"
#                         # -min-gridspan 19  -min-bkr 1 -max-stuck-avg 5
#                         # "-min-bkr","1","-min-gain","100","-min-days","365","-max-stuck","140",
#                         # "-max-stuck-avg", "2"
#                         ]

# try:
#     print(' '.join(command_line))
#     subprocess.run(command_line)
# except subprocess.TimeoutExpired:
#     print('Timeout Reached  seconds)')
