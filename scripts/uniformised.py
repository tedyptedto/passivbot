import os
import glob
import hashlib
import hjson
import re
import subprocess
import shutil


# @DONE : auto générer le summary à la fin

# @TODO : attendre la fin des backest...
# @TODO : relancer le uniformised.py pour créer les fichiers qui vont bien de provenance de la strat
# @TODO : relancer le uniformised.py pour vérifier que le summary fonctionne + génération du csv
# @TODO : modifier le csv pour indiquer la provenance de la strategie à la fin 


# @TODO : rendre paramétrable ce script

# @TODO : Big => check the grid OK before backtesting ? => not possible it will change the nb coins => at the start see all the coins possible for all the strats

# the goal is to uniformise the backtest of many strategies
# after we can read the results with :
###
# PBOS usage : 
# python3 2_backtest_summary.py 3 ../configs/live/a_tedy.json ../configs/backtest/default.hjson \
# -o-csv ../configs/live/PBSO/bt_2021-01-01_2022-07-23_1000_1_XRPUSDT_LTCUSDT_ADAUSDT_DOTUSDT_UNIUSDT_DOGEUSDT_MATICUSDT_BNBUSDT_SOLUSDT_TRXUSDT_AVAXUSDT_USDCUSDT.csv \
# -bd ../configs/live/PBSO/BT_UNIFORMISED/bt_2021-01-01_2022-07-23_1000_1_XRPUSDT_LTCUSDT_ADAUSDT_DOTUSDT_UNIUSDT_DOGEUSDT_MATICUSDT_BNBUSDT_SOLUSDT_TRXUSDT_AVAXUSDT_USDCUSDT/
###

we = 1
coin_list = ["XRPUSDT", "LTCUSDT", "ADAUSDT", "DOTUSDT", "UNIUSDT", "DOGEUSDT", "MATICUSDT", "BNBUSDT", "SOLUSDT", "TRXUSDT", "AVAXUSDT"]
start_date = "2021-01-01"
end_date = "2022-07-23"
starting_balance = "1000"


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


coin_file = "./tmp/grid_ok_coins.json"
if os.path.exists(coin_file):
    print ('AUTO LOADED config from ', coin_file)
    coin_list = hjson.load(open(coin_file, encoding="utf-8"))

tmp_dir = os.path.realpath("./tmp/")
if not os.path.exists(tmp_dir):
    os.makedirs(tmp_dir)
PBSO_dir = os.path.realpath("./../configs/live/PBSO/")

uid_bt = start_date + "_" + end_date + "_" + starting_balance + "_" + str(we) + '_' +  "_".join(coin_list)

PBSO_uniformed_directory = os.path.realpath("./../configs/live/PBSO/BT_UNIFORMISED/" + '/bt_'+ uid_bt + '/') 
if not os.path.exists(PBSO_uniformed_directory):
     os.makedirs(PBSO_uniformed_directory)



# 1/ find all the strategies
a_config = glob.glob(PBSO_dir+"/**/*.json", recursive=True)
nb_config = len(a_config)
i = 1
a_md5 = []
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
        avoid_already_done_bt = True

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

    if avoid_already_done_bt:
        print("Avoid to replay the BackTest")
        os.unlink(final_config)
        continue


    shutil.copy(config, backtest_directory + '/_original_config.json')

    for coin in coin_list:
        #Backtest [-h] [--nojit] [-b BACKTEST_CONFIG_PATH] [-s SYMBOL] [-u USER] [-sd START_DATE] [-ed END_DATE] [-sb STARTING_BALANCE] [-m MARKET_TYPE] [-bd BASE_DIR] [-lw LONG_WALLET_EXPOSURE_LIMIT]
        # [-sw SHORT_WALLET_EXPOSURE_LIMIT] [-le LONG_ENABLED] [-se SHORT_ENABLED] [-np N_PARTS] [-oh]
        print(i , "/", nb_config, " => ", config)
        command_line = [
                                    "python3", "backtest.py", 
                                    "-s", coin,
                                    "-sd", start_date,
                                    "-ed", end_date,
                                    "-sb", starting_balance,
                                    "-bd", backtest_directory,
                                    "-np", "0",
                                    "-oh",
                                    final_config
                                    ]

        try:
            print(' '.join(command_line))
            subprocess.run(command_line, cwd="..")
        except subprocess.TimeoutExpired:
            print('Timeout Reached  seconds)')

        #cleaning
        to_delete = glob.glob(backtest_directory+"/**/caches", recursive=True)
        if os.path.exists(to_delete[0]):
            shutil.rmtree(to_delete[0])
        to_delete = glob.glob(backtest_directory+"/**/optimize", recursive=True)
        if os.path.exists(to_delete[0]):
            shutil.rmtree(to_delete[0])

    print('Delete temporary strategy')
    os.unlink(final_config)
    
    print('Backtest ended')

#auto generate the CSV file


#python3 2_backtest_summary.py 3 ../configs/live/a_tedy.json 
# ../configs/backtest/default.hjson 
# -o-csv ../configs/live/PBSO/bt_2021-01-01_2022-07-23_1000_1_XRPUSDT_LTCUSDT_ADAUSDT_DOTUSDT_UNIUSDT_DOGEUSDT_MATICUSDT_BNBUSDT_SOLUSDT_TRXUSDT_AVAXUSDT_USDCUSDT.csv 
# -bd ../configs/live/PBSO/BT_UNIFORMISED/bt_2021-01-01_2022-07-23_1000_1_XRPUSDT_LTCUSDT_ADAUSDT_DOTUSDT_UNIUSDT_DOGEUSDT_MATICUSDT_BNBUSDT_SOLUSDT_TRXUSDT_AVAXUSDT_USDCUSDT/

command_line = [
                        "python3", "2_backtest_summary.py", 
                        "3", config
                        "../configs/backtest/default.hjson", 
                        "-o-csv", "../configs/live/PBSO/" + uid_bt + ".csv" 
                        "-bd", PBSO_uniformed_directory
                        ]
try:
    print(' '.join(command_line))
    subprocess.run(command_line)
except subprocess.TimeoutExpired:
    print('Timeout Reached  seconds)')