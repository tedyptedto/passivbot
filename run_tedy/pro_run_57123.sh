#!/bin/bash

cd ~/passivbot5.4.2pro

# Get script from 'old' and after 
# Changed "i" to better name
# Changed "bbuser" to use HL account

#   Tedy1
current_pwd=`pwd`
# symbols="MATICUSDT,DOGEUSDT,AVAXUSDT,SOLUSDT,DOTUSDT,UNIUSDT,XRPUSDT,ADAUSDT,TRXUSDT,LTCUSDT"
symbols="DOGEUSDT,AVAXUSDT,SOLUSDT,XRPUSDT,ADAUSDT,LTCUSDT"
config="configs/live/_running/pro/a_57123_long_we_pro.json"
i="HL_pro_57123"
twe_long="2.5"
bbuser="hyperliquid_pro57123"

echo "Running screen $i"
screen -S "$i" -dm bash -c "cd ${current_pwd}; while true; do python3 passivbot_multi.py -le y -se n -tl ${twe_long} -u ${bbuser} -s ${symbols} -dcp ${config} configs/live/_running/config.hjson; echo 'Waiting 2.5 minutes before restart...'; sleep 150; done"


