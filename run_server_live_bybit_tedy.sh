#!/bin/bash
current_pwd=`pwd`
gs=' -gs '
gs=''
symbols=(XRPUSDT MATICUSDT DOGEUSDT )
for i in "${symbols[@]}"
do
    :
    echo "Running screen on $i"
    screen -S "bybit_tedy_$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot.py $gs bybit_tedy $i  configs/live/a_b4483_only_long_we_1.json "
done

