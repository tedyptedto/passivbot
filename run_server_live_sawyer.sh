#!/bin/bash
current_pwd=`pwd`
gs=' -gs '
gs=''
symbols=(CHZUSDT ATOMUSDT MATICUSDT CRVUSDT XRPUSDT DOGEUSDT )
for i in "${symbols[@]}"
do
    :
    echo "Running screen on $i"
    screen -S "sawyer_$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot.py $gs bybit_sawyer $i  configs/live/_running/sawyer/a_sawyer.json "
    sleep 1
done


