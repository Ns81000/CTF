#!/bin/bash
cd /home/ns8pc/prambh-build/src/chain
bash test_chain.sh > ../../organizer-private/runs/p2_chain.txt 2>&1
python3 calibrate.py > ../../organizer-private/runs/p2_calib_tail.txt 2>&1
touch /tmp/p2_done
