#!/bin/bash
symbols=(ADAUSDT SOLUSDT DOGEUSDT )
for i in "${symbols[@]}"
do
    :
    echo "Kill screen for $i"
    screen -S "bybit_tedySUB1_$i" -X quit
done

