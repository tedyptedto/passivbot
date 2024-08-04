#!/bin/bash

# Changed "i" 
# Changed "${current_pwd}" to "${current_pwd}/../"
# Changed "bbuser" 

#   Tedy1
current_pwd=`pwd`
symbols="XRPUSDT,MATICUSDT,DOGEUSDT"
config="configs/live/_running/tedy/a_57123_long_we_1.json"
i="HL_tedy_57123"
twe_long="2.5"
bbuser="hyperliquid_main"

echo "Running screen $i"
screen -S "$i" -dm bash -c "cd ${current_pwd}/../;python3 passivbot_multi.py -le y -se n -tl ${twe_long} -u ${bbuser} -s ${symbols} -dcp ${config} configs/live/_running/config.hjson "


#   Tedy2
# current_pwd=`pwd`
# symbols="ADAUSDT,SOLUSDT,DOGEUSDT"
# config="configs/live/_running/tedySUB2/a_tedy_be550.json"
# i="HL_tedy_be550"
# twe_long="3"
# bbuser="bybit_tedySUB2"

# echo "Running screen $i"
# screen -S "$i" -dm bash -c "cd ${current_pwd}/../;python3 passivbot_multi.py -le y -se n -tl ${twe_long} -u ${bbuser} -s ${symbols} -dcp ${config} configs/live/_running/config.hjson "
