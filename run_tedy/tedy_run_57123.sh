#!/bin/bash

cd ~/Documents/passivbot5.4.2tedy

# Get script from 'old' and after 
# Changed "i" to better name
# Changed "bbuser" to use HL account

#   Tedy1
current_pwd=`pwd`
symbols="XRPUSDT,MATICUSDT,DOGEUSDT"
config="configs/live/_running/tedy/a_57123_long_we_1.json"
i="HL_tedy_57123"
twe_long="2"
bbuser="hyperliquid_vault_tedy57123"

echo "Running screen $i"
screen -S "$i" -dm bash -c "cd ${current_pwd};python3 passivbot_multi.py -le y -se n -tl ${twe_long} -u ${bbuser} -s ${symbols} -dcp ${config} configs/live/_running/config.hjson "


