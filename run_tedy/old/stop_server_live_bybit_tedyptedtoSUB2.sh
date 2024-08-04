#!/bin/bash
i="bybit_tedySUB2_multi"
echo "Kill screen for $i"
screen -S "$i" -X quit
