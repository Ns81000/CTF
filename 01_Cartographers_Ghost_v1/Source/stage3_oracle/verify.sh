#!/bin/bash
# s3_verify.sh -- Phase 4 full clean-room verification (INTERNAL, not shipped).
# Runs EVERYTHING serially (the suites share cartographer/.cartographer_state):
#   1. patch policy.h + test_part2.c (stage-3 decoys + test_decoy_count)
#   2. rebuild state library (now has 4 decoys)
#   3. regenerate oracle constants (oracle_blob.h)
#   4. build the oracle
#   5. run the stage3-only test suite
#   6. run phases 0-3 verify.sh (rebuilds/relinks stage0/1/2 against updated lib)
#   7. scrub + reproducibility + smoke run
# Runnable verbatim:
#   bash /home/manish/cartographer-build/src/stage3_oracle/s3_verify.sh
set -e
R=/home/manish/cartographer-build
S=$R/src/stage3_oracle
BIN=$R/cartographer/stage3_oracle/oracle

echo "############ preamble: patch policy.h + test_part2.c ############"
cd "$S" && python3 policy_patch.py

echo
echo "############ 1. state library (rebuilt with 4 decoys) ############"
cd "$R/src/state" && make clean && make

echo
echo "############ 2. regenerate oracle constants ############"
cd "$S" && python3 gen_oracle_constants.py

echo
echo "############ 3. build the oracle ############"
cd "$S" && make

echo
echo "############ 4. stage3_oracle test suite ############"
cd "$S" && bash test_stage3.sh

echo
echo "############ 5. phases 0-3 verify.sh (relinks stage0/1/2) ############"
bash "$R/src/stage2_stego/verify.sh"

echo
echo "############ 6. oracle reproducibility (two clean rebuilds) ############"
H1=$(sha256sum "$BIN" | awk '{print $1}')
rm -f "$BIN"
cd "$S" && make >/dev/null 2>&1
H2=$(sha256sum "$BIN" | awk '{print $1}')
echo "build1=$H1 build2=$H2"
if [ "$H1" = "$H2" ]; then echo "ORACLE-REGEN-REPRODUCIBLE-OK"; else echo "ORACLE-REGEN-REPRO-FAIL"; exit 1; fi

echo
echo "############ 7. artifact inventory + scrub + smoke ############"
ls -l "$R/cartographer/stage3_oracle/"
file "$BIN"
wc -c "$BIN"
strings -n 6 "$BIN" | grep -Ei "GCC|clang|musl|/home/manish|cartographer-build" && echo "SCRUB-RESIDUE" || echo "SCRUB-CLEAN"

echo
echo "############ 8. solver-eye smoke run ############"
cd "$R/cartographer"
rm -f .cartographer_state
echo "--- no-arg usage ---"
./stage3_oracle/oracle
echo "--- clean query ---"
./stage3_oracle/oracle -r 'CARTO{no_figure_sits_in_every_pixel}' 0123456789abcdef
echo "--- decoy query ---"
./stage3_oracle/oracle -r 'CARTO{b27692a0d5f63d4f1a0c3fb79afbf81b}' 0123456789abcdef
rm -f .cartographer_state
echo
echo "############ done ############"
