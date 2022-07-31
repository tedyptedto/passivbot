#!/bin/bash
current_pwd=`pwd`
gs=' -gs '
gs=''
# symbols=(XRPUSDT MATICUSDT DOGEUSDT )
# symbols=(AVAXUSDT DOGEUSDT )
symbols=(AVAXUSDT MATICUSDT DOTUSDT )
for i in "${symbols[@]}"
do
    :
    echo "Running screen on $i"
    screen -S "bybit_tedy_$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot.py $gs bybit_tedy $i  configs/live/eb1ed_long_only.json "
done

