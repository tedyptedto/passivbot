#!/bin/bash
symbols=(AVAXUSDT ADAUSDT )
for i in "${symbols[@]}"
do
    :
    echo "Kill screen for $i"
    screen -S "bybit_tedySUB3_$i" -X quit
done

