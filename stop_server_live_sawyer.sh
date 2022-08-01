#!/bin/bash
symbols=(CHZUSDT ALICEUSDT MATICUSDT CRVUSDT )
for i in "${symbols[@]}"
do
    :
    echo "Kill screen for $i"
    screen -S "sawyer_$i" -X quit
done

