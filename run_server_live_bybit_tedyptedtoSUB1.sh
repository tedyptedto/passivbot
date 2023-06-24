#!/bin/bash
current_pwd=`pwd`
gs=' -gs '
gs=''
symbols=(XRPUSDT MATICUSDT DOGEUSDT )
for i in "${symbols[@]}"
do
    :
    echo "Running screen on $i"
    screen -S "bybit_tedySUB1_$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot.py $gs bybit_tedySUB1 $i  configs/live/a_tedyptedtoSUB1.json "
done

