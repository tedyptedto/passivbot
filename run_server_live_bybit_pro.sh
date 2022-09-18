#!/bin/bash
current_pwd=`pwd`
gs=' -gs '
gs=''
symbols=(MATICUSDT DOGEUSDT AVAXUSDT SOLUSDT DOTUSDT UNIUSDT XRPUSDT ADAUSDT TRXUSDT LTCUSDT )
for i in "${symbols[@]}"
do
    :
    echo "Running screen on $i"
    # screen -S "bybit_pro_$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot.py $gs bybit_pro $i  configs/live/a_pro.json "
    # screen -S "bybit_pro_$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot.py $gs bybit_pro $i  configs/live/eb1ed_long_only_pro.json "
    screen -S "bybit_pro_$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot.py $gs bybit_pro $i  configs/live/a_57123_long_we_1.json "
done

