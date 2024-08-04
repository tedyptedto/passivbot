#!/bin/bash
current_pwd=`pwd`
symbols="CHZUSDT,ATOMUSDT,MATICUSDT,CRVUSDT,XRPUSDT,DOGEUSDT"
config="configs/live/_running/sawyer/a_sawyer.json"
i="bybit_sawyer_multi"
twe_long="2.25"
bbuser="bybit_sawyer"

echo "Running screen $i"
screen -S "$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot_multi.py -le y -se n -tl ${twe_long} -u ${bbuser} -s ${symbols} -dcp ${config} configs/live/_running/config.hjson "
