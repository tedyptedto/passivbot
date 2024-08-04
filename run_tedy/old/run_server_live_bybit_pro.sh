#!/bin/bash
current_pwd=`pwd`
symbols="MATICUSDT,DOGEUSDT,AVAXUSDT,SOLUSDT,DOTUSDT,UNIUSDT,XRPUSDT,ADAUSDT,TRXUSDT,LTCUSDT"
config="configs/live/_running/pro/a_57123_long_we_pro.json"
i="bybit_pro_multi"
twe_long="2"
bbuser="bybit_pro"

echo "Running screen $i"
screen -S "$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot_multi.py -le y -se n -tl ${twe_long} -u ${bbuser} -s ${symbols} -dcp ${config} configs/live/_running/config.hjson "
