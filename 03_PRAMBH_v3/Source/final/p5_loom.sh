#!/bin/bash
# P5 driver: suite -> organizer-private/runs/p5_loom.txt (spec 2: one driver
# script per phase, run it, read the tail).
cd "$(dirname "$0")"/../loom || exit 1
bash test_loom.sh > ../../organizer-private/runs/p5_loom.txt 2>&1
rc=$?
tail -45 ../../organizer-private/runs/p5_loom.txt
echo "p5-driver rc=$rc"
exit $rc
