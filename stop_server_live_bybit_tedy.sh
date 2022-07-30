#!/bin/bash
# symbols=(XRPUSDT MATICUSDT DOGEUSDT )
# symbols=(MATICUSDT DOGEUSDT AVAXUSDT )
symbols=(XRPUSDT MATICUSDT ADAUSDT )
for i in "${symbols[@]}"
do
    :
    echo "Kill screen for $i"
    screen -S "bybit_tedy_$i" -X quit
done

