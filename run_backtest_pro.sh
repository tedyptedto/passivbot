#!/bin/bash
current_pwd=`pwd`
symbols="MATICUSDT,DOGEUSDT,AVAXUSDT,SOLUSDT,DOTUSDT,UNIUSDT,XRPUSDT,ADAUSDT,TRXUSDT,LTCUSDT"
config="configs/live/_running/pro/a_57123_long_we_pro.json"
i="bybit_pro_multi"
twe_long="2"
bbuser="bybit_pro"

cd ${current_pwd}/;
# not allowed : -dcp ${config} <= must change in multi.hjson

python3 backtest_multi.py -le y -se n -tl ${twe_long} -u binance_01 -s ${symbols}  -bc configs/backtest/_running/multi.hjson 
