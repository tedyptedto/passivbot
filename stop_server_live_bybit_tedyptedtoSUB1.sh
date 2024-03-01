#!/bin/bash
i="bybit_tedySUB1_multi"
echo "Kill screen for $i"
screen -S "$i" -X quit
