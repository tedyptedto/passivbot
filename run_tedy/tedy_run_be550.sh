#!/bin/bash

cd ~/Documents/passivbot5.4.2tedy

# Get script from 'old' and after 
# Changed "i" to better name
# Changed "bbuser" to use HL account


#   Tedy2
current_pwd=`pwd`
symbols="ADAUSDT,SOLUSDT,DOGEUSDT"
config="configs/live/_running/tedySUB2/a_tedy_be550.json"
i="HL_tedy_be550"
# twe_long="3"
twe_long="2"
bbuser="hyperliquid_vault_tedybe550"

echo "Running screen $i"
screen -S "$i" -dm bash -c "cd ${current_pwd};python3 passivbot_multi.py -le y -se n -tl ${twe_long} -u ${bbuser} -s ${symbols} -dcp ${config} configs/live/_running/config.hjson "
