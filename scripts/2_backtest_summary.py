
import glob
import os
import subprocess
import json
import pandas as pd
from tabulate import tabulate
import argparse
import os
import hjson

# normal usage : python3 2_backtest_summary.py 3 ../configs/live/a_tedy.json ../configs/backtest/default.hjson 
###
# PBOS usage : 
# python3 2_backtest_summary.py 3 ../configs/live/a_tedy.json ../configs/backtest/default.hjson \
# -o-csv ../configs/live/PBSO/bt_2021-01-01_2022-07-23_1000_1_XRPUSDT_LTCUSDT_ADAUSDT_DOTUSDT_UNIUSDT_DOGEUSDT_MATICUSDT_BNBUSDT_SOLUSDT_TRXUSDT_AVAXUSDT_USDCUSDT.csv \
# -bd ../configs/live/PBSO/BT_UNIFORMISED/bt_2021-01-01_2022-07-23_1000_1_XRPUSDT_LTCUSDT_ADAUSDT_DOTUSDT_UNIUSDT_DOGEUSDT_MATICUSDT_BNBUSDT_SOLUSDT_TRXUSDT_AVAXUSDT_USDCUSDT/
###

import sys

class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open("tmp/" + __file__ +".log", "a")
   
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)  

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # you might want to specify some extra behavior here.
        pass    

sys.stdout = Logger()

def arguments_management():
    ### Parameters management
    parser = argparse.ArgumentParser( description="This script will read all the 'plots' folders from backtests and create a summary sorted by adg",
    epilog="",
    usage="python3 " + __file__ + " 11 ../configs/live/a_tedy.json -max-stuck-avg 7 -max-stuck 200  -min-gain 10"
    )
    
    parser.add_argument("nb_best_coins", type=int, help="Number of coin wanted")
    parser.add_argument("live_config_filepath", type=str, help="file path to live config")
    parser.add_argument("backtest_config_filepath", type=str, help="file path to backtest")

    parser.add_argument("-min-bkr","--min-closest-bkr",
                        type=float,required=False,dest="min_closest_bkr",default=-99999999,
                        help="Show only result upper than min_closest_bkr",
    )

    parser.add_argument("-max-stuck-avg","--max-hrs-stuck-avg-long",
                        type=float,required=False,dest="max_stuck_avg",default=999999,
                        help="Show only result lower than max_stuck_avg",
    )

    parser.add_argument("-max-stuck","--max-hrs-stuck-long",
                        type=float,required=False,dest="max_stuck",default=999999,
                        help="Show only result lower than max_stuck",
    )

    parser.add_argument("-min-gain","--min-gain",
                        type=float,required=False,dest="min_gain",default=-99999999,
                        help="Show only result upper than gain_dollard",
    )

    parser.add_argument("-min-days","--min-days",
                        type=float,required=False,dest="min_days",default=0,
                        help="Show only result upper than min-days",
    )

    parser.add_argument("-bd-dir","--bd-dir",
                        type=str,required=False,dest="bd_dir",default="",
                        help="Parse all this directory to find backtest",
    )

    parser.add_argument("-o-csv","--o-csv",
                        type=str,required=False,dest="o_csv",default="",
                        help="Ouput to CSV file",
    )



    args = parser.parse_args()

    args.live_config_filepath       = os.path.realpath(args.live_config_filepath)


    if not os.path.exists(args.live_config_filepath) :
        print("live_config_path doesn't exist")
        exit()

    live_config = hjson.load(open(args.live_config_filepath, encoding="utf-8"))
    args.wallet_exposure_limit = live_config['long']['wallet_exposure_limit']

    args.backtest_config_filepath   = os.path.realpath(args.backtest_config_filepath)

    if not os.path.exists(args.backtest_config_filepath) :
        print("backtest_config_path doesn't exist")
        exit()

    backtest_config = hjson.load(open(args.backtest_config_filepath, encoding="utf-8"))

    args.starting_balance = backtest_config['starting_balance']

    return args

args = arguments_management()
number_coin_wanted = args.nb_best_coins

print('python3 ' + __file__ + " " + (" ").join(sys.argv[1:]))

if (args.bd_dir == ""):
    # Grab all files availables
    files = glob.glob('backtests/**/plots/*/result.json', recursive=True)

    # to avoid using a bad directory, and just the latest directory :
    latest_file = max(files, key=os.path.getctime)
    latest_file = os.path.realpath(latest_file)
    dir_to_read = os.path.realpath(os.path.dirname(latest_file) + "/../../../../")
    print("Workgin in directory : " + dir_to_read)

    files = glob.glob(dir_to_read + '/*/*/plots/*/result.json')
else:
    files = glob.glob(args.bd_dir + '/**/plots/*/result.json', recursive=True)
    dir_to_read = os.path.realpath(args.bd_dir)


print('Reading ', len(files), ' backtests')

datas_list = []
for file in files:
    # print(file)
    f = open(file)
    bt = json.load(f)
    f.close()

    symbol              = bt['result']['symbol']
    n_days              = bt['result']['n_days']
    hrs_stuck_avg_long  = bt['result']['hrs_stuck_avg_long']
    hrs_stuck_max_long  = bt['result']['hrs_stuck_max_long']
    hrs_stuck_avg_short  = bt['result']['hrs_stuck_avg_short']
    hrs_stuck_max_short  = bt['result']['hrs_stuck_max_short']
    # n_entries_long      = bt['result']['n_entries_long']
    # n_unstuck_entries_long  = bt['result']['n_unstuck_entries_long']
    # n_unstuck_closes_long  = bt['result']['n_unstuck_closes_long']
    # loss_sum_long  = bt['result']['loss_sum_long']
    # starting_balance    = bt['result']['starting_balance']

    adg_perct           = bt['result']['adg_long']*100
    adg_perct           += bt['result']['adg_short']*100
    
    gain_pct            = bt['result']['gain_long']*100 
    gain_pct            += bt['result']['gain_short']*100 

    gain_dollard        = bt['result']['final_balance_long'] -  bt['result']['starting_balance']
    gain_dollard        += bt['result']['final_balance_short'] -  bt['result']['starting_balance']

    closest_bkr_long    = bt['result']['closest_bkr_long']
    closest_bkr_short    = bt['result']['closest_bkr_short']

    if (closest_bkr_long < args.min_closest_bkr) :
        continue
    if (closest_bkr_short < args.min_closest_bkr) :
        continue
    
    # if (hrs_stuck_avg_long > args.max_stuck_avg) :
    #     continue
    
    # if (hrs_stuck_max_long > args.max_stuck) :
    #     continue
    
    if (gain_pct < args.min_gain) :
        continue

    parent_dir = os.path.realpath(file).replace(dir_to_read, '').strip("/").split("/")[0]

    datas = {}
    if not (args.bd_dir == ""):
        datas['uid']                 = parent_dir.replace('strat_', '')
    datas['symbol']                 = symbol
    datas['n_days']                 = n_days
    datas['h_stuck_avg_l']     = hrs_stuck_avg_long
    datas['h_stuck_max_l']     = hrs_stuck_max_long
    datas['h_stuck_avg_s']     = hrs_stuck_avg_short
    datas['h_stuck_max_s']     = hrs_stuck_max_short
    # datas['n_entries_long']     = n_entries_long
    # datas['n_unstuck_entries_long']     = n_unstuck_entries_long
    # datas['n_unstuck_closes_long']     = n_unstuck_closes_long
    # datas['loss_sum_long']     = loss_sum_long
    datas['l_adg %'] = bt['result']['adg_long']*100
    datas['s_adg %'] = bt['result']['adg_short']*100
    datas['total adg %']                  = adg_perct
    datas['total gain %']                 = gain_pct
    datas['total gain $']                 = gain_dollard
    # datas['starting balance']       = starting_balance
    datas['bkr Long']            = closest_bkr_long
    datas['bkr_Short']            = closest_bkr_short
    
    

    # print(datas)
    datas_list.append(datas)

if len(datas_list) == 0:
    print("No results finded")
    exit()
else:
    print(len(datas_list), " coins after filtering")

df = pd.DataFrame(datas_list)
# df.sort_values(by=['marketcapPosition', 'adg %', 'gain %'], ascending=[True, False, False], inplace=True)
df.sort_values(by=[ 'total adg %', 'total gain %'], ascending=[ False, False], inplace=True)
best_coin = df['symbol'].values[0:number_coin_wanted].tolist()
total_wallet_exposure = args.wallet_exposure_limit * len(best_coin)
print(tabulate(df, headers='keys', tablefmt='psql', showindex=False))

if not args.o_csv == "":
    df.to_csv(args.o_csv) 

print('')
print('')
print("--------------------------------------------------------------")
print("Limited to the first ", number_coin_wanted, " coins found : ")

print("- Total wallet_exposure_limit (1 Side) : ", total_wallet_exposure)
print("- Total wallet_exposure_limit (Long & Short) : ", total_wallet_exposure * 2)

print("- coin list : ", best_coin)

# adg_pct                 = (df['adg %'].values[0:number_coin_wanted].mean() * total_wallet_exposure)
adg_pct                 = (df['total adg %'].values[0:number_coin_wanted].sum())
print("- global adg % : ", (adg_pct), "%")

adg_dollard             = adg_pct * args.starting_balance / 100
print("- global adg $ : ", (adg_dollard), "$" )

print("- global adg 1 month (30 days) : ", int(adg_dollard * 30) , "$" )

# global_gain_pct         = (df['gain %'].values[0:number_coin_wanted].mean() * total_wallet_exposure)
gain_realized_dollards =  df['total gain $'].values[0:number_coin_wanted].sum() # already substracted => - (number_coin_wanted * args.starting_balance)


print("- global gain % : ", int(100 * gain_realized_dollards / args.starting_balance), "%")
print("- global gain $ : ", int(gain_realized_dollards), "$")

print("- Starting balance $ : ", int(args.starting_balance) , "$")
print("- Final amount $ : ", (int(args.starting_balance) + int(gain_realized_dollards)), "$")

print("--------------------------------------------------------------")
saving_data = "./tmp/best_coins.json"
print ("Saving the coin list to ", saving_data)
with open(saving_data, 'w') as outfile:
    json.dump(best_coin, outfile)


print('python3 ' + __file__ + " " + (" ").join(sys.argv[1:]))
