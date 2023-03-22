#!/bin/bash
nohup python3.9 -u btc.py > btc_output.txt 2>&1 &
nohup python3.9 -u eth.py > eth_output.txt 2>&1 &

