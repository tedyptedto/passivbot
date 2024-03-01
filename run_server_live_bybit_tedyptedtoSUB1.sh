#!/bin/bash
current_pwd=`pwd`
symbols="XRPUSDT,MATICUSDT,DOGEUSDT"
config="configs/live/_running/tedySUB1/a_tedyptedtoSUB1.json"
i="bybit_tedySUB1_multi"
twe_long="2"

echo "Running screen $i"
screen -S "$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot_multi.py -le y -se n -tl ${twe_long} -u bybit_tedy -s ${symbols} -dcp ${config} configs/live/_running/config.hjson "
