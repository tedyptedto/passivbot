#!/bin/bash
current_pwd=`pwd`
gs=' -gs '
gs=''
symbols=(CHZUSDT ALICEUSDT MATICUSDT CRVUSDT )
for i in "${symbols[@]}"
do
    :
    echo "Running screen on $i"
    screen -S "bybit_sawyer_$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot.py $gs sawyer $i  configs/live/a_sawyer.json "
    sleep 20
done

