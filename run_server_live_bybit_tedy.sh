#!/bin/bash
current_pwd=`pwd`
symbols="XRPUSDT,MATICUSDT,DOGEUSDT"
config="configs/live/_running/tedy/a_57123_long_we_1.json"
i="bybit_tedy_multi"

echo "Running screen $i"
screen -S "$i" -dm bash -c "cd ${current_pwd}/;python3 passivbot_multi.py -u bybit_tedy -s ${symbols} -dcp ${config} configs/live/_running/config.hjson "
