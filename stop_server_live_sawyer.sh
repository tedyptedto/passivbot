#!/bin/bash
i="bybit_sawyer_multi"
echo "Kill screen for $i"
screen -S "$i" -X quit
