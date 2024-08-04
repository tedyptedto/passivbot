#!/bin/bash
i="bybit_tedy_multi"
echo "Kill screen for $i"
screen -S "$i" -X quit
