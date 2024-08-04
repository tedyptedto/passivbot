#!/bin/bash
i="bybit_pro_multi"
echo "Kill screen for $i"
screen -S "$i" -X quit
