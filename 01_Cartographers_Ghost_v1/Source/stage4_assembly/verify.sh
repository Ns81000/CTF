#!/bin/bash
# s4_verify.sh -- Phase 5 full clean-room verification (INTERNAL, not shipped).
# Runs EVERYTHING serially (the suites share cartographer/.cartographer_state):
#   1. regenerate stage4_blob.h + stage4_layout.json (deterministic)
#   2. policy_patch4.py  (4 decoy rows + test_part2.c row 0..3 assertions)
#   3. rebuild state library + run its 27-test suite
#   4. relink stage0/1/2/3 against the updated library (policy.h changed)
#   5. build the validator
#   6. suites in order: stage0 36, stage1 8+65, stage2 58+71, stage3 33,
#      stage4 N   (SERIAL -- they share the package-root state file)
#   7. reproducibility + artifact inventory + scrub + solver-eye smoke run
# Runnable verbatim:
#   bash /home/manish/cartographer-build/src/stage4_assembly/verify.sh
set -e
set -o pipefail
R=/home/manish/cartographer-build
S4=$R/src/stage4_assembly
BIN=$R/cartographer/stage4_assembly/validate
LOG=$R/logs/runs/p5_suites_run.txt

echo "############ preamble: regenerate stage4 blob + patch policy.h ############"
cd "$S4" && python3 gen_title_blob.py
python3 policy_patch4.py

echo
echo "############ 1. state library (rebuilt with 4 decoys) ############"
cd "$R/src/state" && make clean >/dev/null && make test 2>&1 | tail -12

echo
echo "############ 2. relink stages 0-3 against the updated library ############"
cd "$R/src/stage0" && make >/dev/null 2>&1 && echo "stage0_start relinked"
cd "$R/src/stage1_vm" && make >/dev/null 2>&1 && echo "stage1_vm relinked"
cd "$R/src/stage2_stego" && make >/dev/null 2>&1 && echo "stage2_stego relinked"
cd "$R/src/stage3_oracle" && make >/dev/null 2>&1 && echo "oracle relinked"

echo
echo "############ 3. build the validator ############"
cd "$S4" && make

echo
echo "############ 4. suites, serially (they share the state file) ############"
: > "$LOG"
echo "### stage0 (36)" >> "$LOG"; cd "$R/src/stage0" && bash test_stage0.sh >> "$LOG" 2>&1
echo "### stage1 (8 + 65)" >> "$LOG"; cd "$R/src/stage1_vm" && make test >> "$LOG" 2>&1
echo "### stage2 (58 + 71)" >> "$LOG"; cd "$R/src/stage2_stego" && make test >> "$LOG" 2>&1
echo "### stage3 (33)" >> "$LOG"; cd "$R/src/stage3_oracle" && bash test_stage3.sh >> "$LOG" 2>&1
echo "### stage4" >> "$LOG"
cd "$S4"
if bash test_stage4.sh | tee -a "$LOG"; then :; else echo "STAGE4 SUITE FAILED"; exit 1; fi
echo "-- summary of the four earlier suites (full output: $LOG) --"
grep -E "checks, 0 failed|tests run, 0 failed|passed, 0 failed|vectors run, 0 failed|ALL (TESTS|CHECKS) PASSED" "$LOG" | tail -14

echo
echo "############ 5. validator reproducibility (two clean builds) ############"
H1=$(sha256sum "$BIN" | awk '{print $1}')
rm -f "$BIN"
cd "$S4" && make >/dev/null 2>&1
H2=$(sha256sum "$BIN" | awk '{print $1}')
echo "build1=$H1 build2=$H2"
if [ "$H1" = "$H2" ]; then echo "VALIDATE-REGEN-REPRODUCIBLE-OK"; else echo "VALIDATE-REPRO-FAIL"; exit 1; fi

echo
echo "############ 6. artifact inventory + scrub ############"
ls -l "$R/cartographer/stage4_assembly/"
file "$BIN"
wc -c "$BIN"
strings -n 4 "$BIN" | grep -Ei "GCC|clang|musl|/home/manish|cartographer-build" && echo "SCRUB-RESIDUE" || echo "SCRUB-CLEAN"

echo
echo "############ 7. solver-eye smoke run ############"
cd "$R/cartographer"
rm -f .cartographer_state
echo "--- no-arg usage (usage + the riddle) ---"
./stage4_assembly/validate
echo "--- correct title ---"
./stage4_assembly/validate "$(cd "$S4" && python3 -c 'import json;print(json.load(open("stage4_layout.json"))["title"])')"
echo "--- struck-draft decoy ---"
./stage4_assembly/validate "$(cd "$S4" && python3 -c 'import json;print(json.load(open("stage4_layout.json"))["draft_flag"])')"
rm -f .cartographer_state
echo
echo "############ done ############"
