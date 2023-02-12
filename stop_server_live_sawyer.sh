#!/bin/bash
symbols=(CHZUSDT ATOMUSDT MATICUSDT CRVUSDT ETHUSDT )
for i in "${symbols[@]}"
do
    :
    echo "Kill screen for $i"
    screen -S "sawyer_$i" -X quit
done

