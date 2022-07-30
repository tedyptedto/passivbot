import os
import glob
import hashlib
import hjson
import re
import subprocess
import shutil


# the goal is to uniformise the backtest of many strategies

we = 1
coin_list = ["XRPUSDT", "LTCUSDT", "ADAUSDT", "DOTUSDT", "UNIUSDT", "DOGEUSDT", "MATICUSDT", "BNBUSDT", "SOLUSDT", "TRXUSDT", "AVAXUSDT", "USDCUSDT"]
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
    print ('AUTO LOADED coni from ', coin_file)
    coin_list = hjson.load(open(coin_file, encoding="utf-8"))

tmp_dir = os.path.realpath("./tmp/")
if not os.path.exists(tmp_dir):
    os.makedirs(tmp_dir)
PBSO_dir = os.path.realpath("./../configs/live/PBSO/")
PBSO_uniformed_directory = os.path.realpath("./../configs/live/PBSO/BT_UNIFORMISED/")
if not os.path.exists(PBSO_uniformed_directory):
     os.makedirs(PBSO_uniformed_directory)


# 1/ find all the strategies
a_config = glob.glob(PBSO_dir+"/**/config.json", recursive=True)
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

    if md5 in a_md5:
        print('Avoid already BACKTESTED strategy')
        continue
    a_md5.append(md5)
    print("backtesting : " , config)

    # 2/ update the wallet exposure of the strategy

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

    backtest_directory = PBSO_uniformed_directory + '/strat_' + md5 + '/'
    if os.path.exists(backtest_directory):
        shutil.rmtree(backtest_directory)
        
    if not os.path.exists(backtest_directory):
        os.makedirs(backtest_directory)
    
    shutil.copy(config, backtest_directory + '/_original_config.json')

    for coin in coin_list:
        #Backtest [-h] [--nojit] [-b BACKTEST_CONFIG_PATH] [-s SYMBOL] [-u USER] [-sd START_DATE] [-ed END_DATE] [-sb STARTING_BALANCE] [-m MARKET_TYPE] [-bd BASE_DIR] [-lw LONG_WALLET_EXPOSURE_LIMIT]
        # [-sw SHORT_WALLET_EXPOSURE_LIMIT] [-le LONG_ENABLED] [-se SHORT_ENABLED] [-np N_PARTS] [-oh]
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


    os.unlink(final_config)
    

