#!/bin/bash
current_pwd=`pwd`
gs=' -gs '
gs=''
# symbols=(XRPUSDT MATICUSDT DOGEUSDT )
# symbols=(AVAXUSDT DOGEUSDT )
symbols=(ADAUSDT )
for i in "${symbols[@]}"
do
    :
    echo "Running screen on $i"
    screen -S "bybit_tedy_$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot.py $gs bybit_tedy $i  configs/live/a_adausdt_97472.json "
done

symbols=(XRPUSDT )
for i in "${symbols[@]}"
do
    :
    echo "Running screen on $i"
    screen -S "bybit_tedy_$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot.py $gs bybit_tedy $i  configs/live/a_af59b_only_long.json "
done

symbols=(MATICUSDT )
for i in "${symbols[@]}"
do
    :
    echo "Running screen on $i"
    screen -S "bybit_tedy_$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot.py $gs bybit_tedy $i  configs/live/a_matic_MDCL.json "
done
