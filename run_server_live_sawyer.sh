#!/bin/bash
current_pwd=`pwd`
gs=' -gs '
gs=''
symbols=(CHZUSDT MATICUSDT CRVUSDT )
for i in "${symbols[@]}"
do
    :
    echo "Running screen on $i"
    screen -S "sawyer_$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot.py $gs bybit_sawyer $i  configs/live/a_sawyer.json "
    sleep 1
done

# current_pwd=`pwd`
gs=' -gs '
# gs=''
symbols=( ALICEUSDT   )
for i in "${symbols[@]}"
do
    :
    echo "Running screen on $i"
    screen -S "sawyer_$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot.py $gs bybit_sawyer $i  configs/live/a_sawyer.json "
    sleep 1
done
