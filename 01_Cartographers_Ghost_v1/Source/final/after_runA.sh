#!/bin/bash
# after_runA.sh -- Phase FINAL: wait for calibration Run A to complete, then
# run the remaining, already-individually-proven steps in order, logging
# everything to logs/runs/pf_finalize.log for inspection.
#
#   1. wait for the clean-path run to report RESULT
#   2. print the measured numbers
#   3. full verification chain (src/stage4_assembly/verify.sh) -- also
#      guarantees the shipped build is what is packaged
#   4. section 6: split packaging
#   5. section 7: isolated-package re-verification
#   6. section 8: copy the two folders to D:\gandu\
#   7. hash tables for both folders
#   8. final commit
set -u
R=/home/manish/cartographer-build
L=$R/logs/runs/final_clean_path.log
F=$R/logs/runs/pf_finalize.log
: > "$F"
step() { echo "" >> "$F"; echo "############ $* ############" >> "$F"; date -u >> "$F"; }
log()  { echo "$*" >> "$F"; }

step "1. waiting for Run A"
while ! grep -q 'RESULT: CLEAN-PATH SOLVE COMPLETE' "$L"; do
    if ! pgrep -f run_clean_path.py > /dev/null; then
        log "RUN-PROCESS-GONE WITHOUT RESULT -- aborting"
        tail -20 "$L" >> "$F"
        exit 1
    fi
    sleep 10
done
log "Run A reported completion at $(date -u)"
tail -14 "$L" >> "$F"

step "1b. the measured numbers"
grep -E 'RESULT|ADDED DETOUR|TOTAL|collection finished|ring stddev|attack recovered|accepted the title|MARK ' "$L" >> "$F" 2>/dev/null || true
grep -E 'RESULT|TOTAL|collection finished|ring stddev|attack recovered|accepted the title' \
    "$R/logs/runs/final_decoy_segment.log" >> "$F" 2>/dev/null || true

step "2. tree sweep (__pycache__ / *.pyc)"
find "$R" -name '__pycache__' -type d -not -path '*/.git/*' -exec rm -rf {} + 2>/dev/null || true
find "$R" -name '*.pyc' -not -path '*/.git/*' -delete 2>/dev/null || true
log "remaining: $(find "$R" -name '__pycache__' -o -name '*.pyc' | grep -v '/.git/' | wc -l)"

step "3. full verification chain (shipped build)"
if bash "$R/src/stage4_assembly/verify.sh" > "$R/logs/runs/pf_verify_final.txt" 2>&1; then
    log "verify.sh: GREEN"
    grep -E 'tests run, 0 failed|vectors run, 0 failed|passed, 0 failed|checks, 0 failed|OK$' \
        "$R/logs/runs/pf_verify_final.txt" >> "$F"
else
    log "verify.sh: FAILED"; tail -30 "$R/logs/runs/pf_verify_final.txt" >> "$F"; exit 1
fi

step "4. section 6 -- split packaging"
if bash "$R/src/final/build_package.sh" >> "$F" 2>&1; then log "build_package.sh: OK"
else log "build_package.sh: FAILED"; exit 1; fi

step "5. section 7 -- isolated-package re-verification"
if bash "$R/src/final/verify_isolated.sh" >> "$F" 2>&1; then log "verify_isolated.sh: OK"
else log "verify_isolated.sh: FAILED"; exit 1; fi

step "6. section 8 -- copy both folders to the Windows surface"
if bash "$R/src/final/finalize_windows.sh" >> "$F" 2>&1; then log "finalize_windows.sh: OK"
else log "finalize_windows.sh: FAILED"; exit 1; fi

step "7. hash tables"
bash "$R/src/final/report_hashes.sh" >> "$F" 2>&1 || log "report_hashes.sh: FAILED"

step "8. final commit"
if bash "$R/src/final/commit_final.sh" >> "$F" 2>&1; then log "commit_final.sh: OK"
else log "commit_final.sh: FAILED"; exit 1; fi

step "DONE"
log "ALL STEPS COMPLETED"
