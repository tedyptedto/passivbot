#!/bin/bash
current_pwd=`pwd`
gs=' -gs '
gs=''
symbols=(ADAUSDT SOLUSDT DOGEUSDT )
for i in "${symbols[@]}"
do
    :
    echo "Running screen on $i"
    screen -S "bybit_tedySUB2_$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot.py $gs bybit_tedySUB2 $i  configs/live/a_tedy_be550.json "
done

