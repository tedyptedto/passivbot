#!/bin/bash
current_pwd=`pwd`
gs=' -gs '
gs=''
symbols=(AVAXUSDT )
for i in "${symbols[@]}"
do
    :
    echo "Running screen on $i"
    screen -S "bybit_tedySUB3_$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot.py $gs bybit_tedySUB3 $i  configs/live/a_tedy3_avax.json "
done

symbols=(ADAUSDT )
for i in "${symbols[@]}"
do
    :
    echo "Running screen on $i"
    screen -S "bybit_tedySUB3_$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot.py $gs bybit_tedySUB3 $i  configs/live/a_tedy3_ada.json "
done
