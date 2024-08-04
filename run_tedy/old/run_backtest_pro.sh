#!/bin/bash
current_pwd=`pwd`
symbols="MATICUSDT,DOGEUSDT,AVAXUSDT,SOLUSDT,DOTUSDT,UNIUSDT,XRPUSDT,ADAUSDT,TRXUSDT,LTCUSDT"
i="bybit_pro_multi"
twe_long="2"
bbuser="bybit_pro"
file="configs/backtest/_running/multi.hjson"

cd ${current_pwd}/;
# not allowed : -dcp ${config} <= must change in multi.hjson

config="configs/live/_running/pro/a_57123_long_we_pro.json"
sed "s#PATH_TO_REPLACE#${config}#" "${file}" > "${file}.replaced.hjson"
python3 backtest_multi.py -le y -se n -tl ${twe_long} -u binance_01 -s ${symbols}  -bc $file.replaced.hjson 

config="configs/live/_running/tedySUB1/a_tedyptedtoSUB1.json"
sed "s#PATH_TO_REPLACE#${config}#" "${file}" > "${file}.replaced.hjson"
python3 backtest_multi.py -le y -se n -tl ${twe_long} -u binance_01 -s ${symbols}  -bc $file.replaced.hjson

config="configs/live/_running/tedySUB2/a_tedy_be550.json"
sed "s#PATH_TO_REPLACE#${config}#" "${file}" > "${file}.replaced.hjson"
python3 backtest_multi.py -le y -se n -tl ${twe_long} -u binance_01 -s ${symbols}  -bc $file.replaced.hjson

config="configs/live/_running/tedySUB3/a_tedy3_ada.json"
sed "s#PATH_TO_REPLACE#${config}#" "${file}" > "${file}.replaced.hjson"
python3 backtest_multi.py -le y -se n -tl ${twe_long} -u binance_01 -s ${symbols}  -bc $file.replaced.hjson

config="configs/live/_running/tedySUB3/a_tedy3_avax.json"
sed "s#PATH_TO_REPLACE#${config}#" "${file}" > "${file}.replaced.hjson"
python3 backtest_multi.py -le y -se n -tl ${twe_long} -u binance_01 -s ${symbols}  -bc $file.replaced.hjson
