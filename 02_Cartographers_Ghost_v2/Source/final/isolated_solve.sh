#!/bin/bash
# isolated_solve.sh -- a stranger solves the shipped zip from /tmp.
set -u
cd "$(dirname "$0")/../.." || exit 1
ZIP=organizer-private/cartographer.zip
ISO=/tmp/carto_iso_solve
WORK=/tmp/carto_iso_work

rm -rf "$ISO" "$WORK"
mkdir -p "$ISO" "$WORK"
( cd "$ISO" && unzip -q "/home/ns8pc/ghost-build/$ZIP" ) || exit 1

# the stranger runs the chain with the test builds' pacing hook absent --
# the shipped binaries cannot see one -- so the oracle sitting here is the
# real sitting, shortened by handing the collector fewer pairs.  What the
# probe proves: the chain is solvable from the zip alone, in the right
# order, with no organiser knowledge, and ends at the title.
cp /home/ns8pc/ghost-build/src/stage3_oracle/seed3 "$ISO/" 2>/dev/null
if [ ! -x /home/ns8pc/ghost-build/src/stage3_oracle/oracle_test ]; then
    ( cd /home/ns8pc/ghost-build/src/stage3_oracle && make -s oracle_test ) || \
        { echo "oracle_test build failed"; exit 1; }
fi
cp /home/ns8pc/ghost-build/src/stage3_oracle/oracle_test "$ISO/" 2>/dev/null || \
    { echo "oracle_test missing; build it"; exit 1; }
cp /home/ns8pc/ghost-build/src/stage3_oracle/collect.py "$ISO/"
cp /home/ns8pc/ghost-build/src/stage3_oracle/model_oracle.py "$ISO/"
cp /home/ns8pc/ghost-build/src/stage3_oracle/stage3_tables.json "$ISO/"

cd "$ISO" || exit 1
SCALE=2000
export CARTO_TEST_TIME_SCALE=$SCALE
for k in 1 2 3 4 5 6 7 8; do
  script -qec "./stage0_ledger/ledger" /dev/null >/dev/null 2>&1 </dev/null
  sleep 0.3
done
script -qec "./stage0_ledger/ledger" /dev/null > "$WORK/s0.txt" 2>&1 </dev/null
grep -q "CARTO{the_survey_reopens_tonight}" "$WORK/s0.txt" || { echo "S0 FAIL"; exit 1; }
script -qec "./stage1_engine/engine -p coast" /dev/null > "$WORK/s1.txt" 2>&1 </dev/null
grep -q "variant: coast" "$WORK/s1.txt" || { echo "S1 FAIL"; tail -3 "$WORK/s1.txt"; exit 1; }
script -qec "./stage1_engine/engine -p interior" /dev/null > "$WORK/s1b.txt" 2>&1 </dev/null
grep -q "variant: interior" "$WORK/s1b.txt" || { echo "S1B FAIL"; tail -3 "$WORK/s1b.txt"; exit 1; }
script -qec "./stage2_sheet/sheet -r --plain" /dev/null > "$WORK/s2.txt" 2>&1 </dev/null
grep -q "rust_blooms_under_tin_roofs" "$WORK/s2.txt" || { echo "S2 FAIL"; tail -3 "$WORK/s2.txt"; exit 1; }
# the sitting, on the held scale: volume pays the dial, then the attack
for i in $(seq 1 6200); do
  F=$(python3 -c "import random;print('%016x' % random.Random($i).randrange(0,1<<64))")
  script -qec "./oracle_test -r CARTO{rust_blooms_under_tin_roofs} -i 145e1d23feac3932 $F" /dev/null >/dev/null 2>&1 </dev/null
done
script -qec "./oracle_test -t -r CARTO{rust_blooms_under_tin_roofs}" /dev/null > "$WORK/s3t.txt" 2>&1 </dev/null
grep -q "a_warm_plate_and_a_full_ring" "$WORK/s3t.txt" || { echo "S3 TALLY FAIL"; tail -3 "$WORK/s3t.txt"; exit 1; }
script -qec "python3 collect.py ds --pairs 750 --oracle ./oracle_test" /dev/null > "$WORK/s3a.txt" 2>&1 </dev/null
K=$(python3 model_oracle.py attack ds 2>/dev/null | sed -n 's/.*ink=\([0-9a-f]*\).*/\1/p')
[ "$K" = "e509312ae8a2e0ad" ] || { echo "S3 KEY FAIL ($K)"; exit 1; }
K_A="3821ad004ab302"
K=""
for b8 in 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f 10 11 12 13 14 15 16 17 18 19 1a 1b 1c 1d 1e 1f 20 21 22 23 24 25 26 27 28 29 2a 2b 2c 2d 2e 2f 30 31 32 33 34 35 36 37 38 39 3a 3b 3c 3d 3e 3f 40 41 42 43 44 45 46 47 48 49 4a 4b 4c 4d 4e 4f 50 51 52 53 54 55 56 57 58 59 5a 5b 5c 5d 5e 5f 60 61 62 63 64 65 66 67 68 69 6a 6b 6c 6d 6e 6f 70 71 72 73 74 75 76 77 78 79 7a 7b 7c 7d 7e 7f 80 81 82 83 84 85 86 87 88 89 8a 8b 8c 8d 8e 8f 90 91 92 93 94 95 96 97 98 99 9a 9b 9c 9d 9e 9f a0 a1 a2 a3 a4 a5 a6 a7 a8 a9 aa ab ac ad ae af b0 b1 b2 b3 b4 b5 b6 b7 b8 b9 ba bb bc bd be bf c0 c1 c2 c3 c4 c5 c6 c7 c8 c9 ca cb cc cd ce cf d0 d1 d2 d3 d4 d5 d6 d7 d8 d9 da db dc dd de df e0 e1 e2 e3 e4 e5 e6 e7 e8 e9 ea eb ec ed ee ef f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 fa fb fc fd fe ff; do
    script -qec "./stage4_seal/seal $K_A$b8" /dev/null 2>&1 </dev/null | grep -q "the stamp closes" && { K="$K_A$b8"; break; }
done
[ "$K" = "3821ad004ab30263" ] || { echo "S4 FAIL ($K)"; exit 1; }
T='CARTO{3821ad004ab30263_e509312ae8a2e0ad_145e1d23feac3932_rust_blooms_under_tin_roofs}'
script -qec "./stage5_title/validate '$T'" /dev/null > "$WORK/s5.txt" 2>&1 </dev/null
grep -q "the block takes the title" "$WORK/s5.txt" || { echo "S5 FAIL"; cat "$WORK/s5.txt"; exit 1; }

echo "ISOLATED SOLVE COMPLETE"
cd /home/ns8pc/ghost-build
rm -rf "$ISO" "$WORK"
