
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
        self.log = open("tmp/" + os.path.basename(__file__) +".log", "a")
   
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
    usage="python3 " + os.path.basename(__file__) + " 11 ../configs/live/a_tedy.json -max-stuck-avg 7 -max-stuck 200  -min-gain 10"
    )
    
    parser.add_argument("nb_best_coins", type=int, help="Number of coin wanted")
    parser.add_argument("live_config_filepath", type=str, help="file path to live config")
    parser.add_argument("backtest_config_filepath", type=str, help="file path to backtest")

    parser.add_argument("-min-bkr","--min-closest-bkr",
                        type=float,required=False,dest="min_closest_bkr",default=-99999999,
                        help="Show only result upper than min_closest_bkr",
    )

    parser.add_argument("-max-stuck-avg","--max-hrs-stuck-avg-long",
                        type=float,required=False,dest="max_stuck_avg",default=99999999,
                        help="Show only result lower than max_stuck_avg",
    )

    parser.add_argument("-max-stuck","--max-hrs-stuck-long",
                        type=float,required=False,dest="max_stuck",default=99999999,
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

    parser.add_argument("-min-gridspan","--min-gridspan",
                        type=float,required=False,dest="min_gridspan",default=0,
                        help="Minimum grid span",
    )

    parser.add_argument("-min-eqbal_ratio_min_long","--min-eqbal_ratio_min_long",
                        type=float,required=False,dest="min_eqbal_ratio_min_long",default=-99999999,
                        help="Minimum eqbal_ratio_min_long",
    )

    parser.add_argument("-max-pa_distance_mean_long","--max-pa_distance_mean_long",
                        type=float,required=False,dest="max_pa_distance_mean_long",default=99999999999,
                        help="max pa_distance_mean_long",
    )

    parser.add_argument("-max-loss_sum_long","-max-loss_sum_long",
                        type=float,required=False,dest="max_loss_sum_long",default=9999999999999,
                        help="max_loss_sum_long",
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
    args.wallet_exposure_limit = 1
    if ('long' in live_config):
        if ('wallet_exposure_limit' in live_config['long']):
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

    current_config_file = os.path.dirname(file) + "/live_config.json"
    current_config = live_config = hjson.load(open(current_config_file, encoding="utf-8"))


    l_grid_span = 0
    if "grid_span" in current_config['long']:
        l_grid_span = current_config['long']["grid_span"] * 100

    s_grid_span = 0
    if "grid_span" in current_config['short']:
        s_grid_span = current_config['short']["grid_span"] * 100


    if l_grid_span < args.min_gridspan:
        continue

    if s_grid_span < args.min_gridspan:
        continue


    symbol              = bt['result']['symbol']
    n_days              = bt['result']['n_days']
    hrs_stuck_avg_long  = bt['result']['hrs_stuck_avg_long']
    hrs_stuck_max_long  = bt['result']['hrs_stuck_max_long']
    # hrs_stuck_avg_short  = bt['result']['hrs_stuck_avg_short']
    # hrs_stuck_max_short  = bt['result']['hrs_stuck_max_short']
    # n_entries_long      = bt['result']['n_entries_long']
    # n_unstuck_entries_long  = bt['result']['n_unstuck_entries_long']
    # n_unstuck_closes_long  = bt['result']['n_unstuck_closes_long']
    # loss_sum_long  = bt['result']['loss_sum_long']
    # starting_balance    = bt['result']['starting_balance']

    adg_perct           = bt['result']['adg_long']*100
    # adg_perct           += bt['result']['adg_short']*100

    
    gain_pct            = bt['result']['gain_long']*100 
    # gain_pct            += bt['result']['gain_short']*100 

    gain_dollard        = bt['result']['final_balance_long'] -  bt['result']['starting_balance']
    # gain_dollard        += bt['result']['final_balance_short'] -  bt['result']['starting_balance']

    closest_bkr_long    = bt['result']['closest_bkr_long']
    closest_bkr_short    = bt['result']['closest_bkr_short']

    eqbal_ratio_min_long    = bt['result']['eqbal_ratio_min_long']
    pa_distance_mean_long    = bt['result']['pa_distance_mean_long']

    if (closest_bkr_long < args.min_closest_bkr) :
        continue
    # if (closest_bkr_short < args.min_closest_bkr) :
    #     continue
    
    if (hrs_stuck_avg_long > args.max_stuck_avg) :
        continue
    
    if (hrs_stuck_max_long > args.max_stuck) :
        continue
    
    # if (hrs_stuck_avg_short > args.max_stuck_avg) :
    #     continue
    
    # if (hrs_stuck_max_short > args.max_stuck) :
    #     continue
    
    if (eqbal_ratio_min_long < args.min_eqbal_ratio_min_long) :
        continue
    
    loss_sum = bt['result']['loss_sum_long']

    if abs(args.max_loss_sum_long) > 0:
        # if loss_sum == 0.0:
        #     continue

        if loss_sum < -abs(args.max_loss_sum_long):
            continue


    if (gain_pct < args.min_gain) :
        continue

    if pa_distance_mean_long > args.max_pa_distance_mean_long: 
        continue

    parent_dir = os.path.realpath(file).replace(dir_to_read, '').strip("/").split("/")[0]

    father_full_dirname = dir_to_read + '/' + parent_dir + '/'
    # print(father_full_dirname)
    from_strat_data = father_full_dirname + '/unif_info.json'
    if (os.path.exists(from_strat_data)):
        from_strat_data = hjson.load(open(from_strat_data, encoding="utf-8"))
    else:
        from_strat_data = {}

    datas = {}
    if not (args.bd_dir == ""):
        datas['uid']                 = parent_dir.replace('strat_', '')
    if 'orig_strategy' in from_strat_data:
        datas['strat'] = from_strat_data['orig_strategy']

    datas['symbol']                 = symbol
    datas['n_days']                 = n_days
    datas['h_stuck_avg_l']     = hrs_stuck_avg_long
    datas['h_stuck_max_l']     = hrs_stuck_max_long
    # datas['h_stuck_avg_s']     = hrs_stuck_avg_short
    # datas['h_stuck_max_s']     = hrs_stuck_max_short

    datas['pa_distance_mean_long']     = pa_distance_mean_long
    datas['l_gridspan']     = l_grid_span
    # datas['s_gridspan']     = s_grid_span

    datas['l_eqbal_ratio_min_long']     = eqbal_ratio_min_long
    

    datas['profit_sum_long']     = bt['result']['profit_sum_long']
    datas['loss_sum_long']     = loss_sum
    datas['l_ratio_loss_profit']     = bt['result']['loss_sum_long'] / bt['result']['profit_sum_long'] if bt['result']['profit_sum_long'] > 0 else 0

    # datas['profit_sum_short']     = bt['result']['profit_sum_short']
    # datas['loss_sum_short']     = bt['result']['loss_sum_short']
    # datas['s_ratio_loss_profit']     = bt['result']['loss_sum_short'] / bt['result']['profit_sum_short'] if bt['result']['profit_sum_short'] > 0 else 0




    # datas['n_entries_long']     = n_entries_long
    # datas['n_unstuck_entries_long']     = n_unstuck_entries_long
    # datas['n_unstuck_closes_long']     = n_unstuck_closes_long
    # datas['loss_sum_long']     = loss_sum_long
    datas['l_adg %'] = bt['result']['adg_long']*100
    # datas['s_adg %'] = bt['result']['adg_short']*100
    datas['total adg %']                  = adg_perct
    datas['total gain %']                 = gain_pct
    datas['total gain $']                 = gain_dollard
    # datas['starting balance']       = starting_balance
    datas['bkr Long']            = closest_bkr_long
    # datas['bkr_Short']            = closest_bkr_short
    
    

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
