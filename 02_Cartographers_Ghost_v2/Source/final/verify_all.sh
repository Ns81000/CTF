#!/bin/bash
# verify_all.sh -- state + all stage suites SERIAL + determinism +
# reproducibility + scrub + inventory + isolated solve + leak grep.
set -u
cd "$(dirname "$0")/../.." || exit 1
FAILED=0

step() {  # step <desc> <key> <cmd...>
    local desc="$1" key="$2"
    shift 2
    echo "== $desc =="
    if "$@" > "organizer-private/runs/verify_$key.log" 2>&1; then
        echo "  PASS $desc"
    else
        echo "  FAIL $desc (see organizer-private/runs/verify_$key.log)"
        FAILED=$((FAILED + 1))
    fi
}

# the suites, in tower order
step "state suite" statelog bash src/state/test_state.sh
step "stage0 suite" stage0log bash src/stage0_ledger/test_stage0.sh
step "stage1 suite" stage1log bash src/stage1_engine/test_stage1.sh
step "stage2 suite" stage2log bash src/stage2_sheet/test_stage2.sh
step "stage3 suite" stage3log bash src/stage3_oracle/test_stage3.sh
step "stage4 suite" stage4log bash src/stage4_seal/test_stage4.sh
step "stage5 suite" stage5log bash src/stage5_title/test_stage5.sh
step "stage7 suite" stage7log bash src/final/test_stage7.sh

# packaging, built from the verified tree
step "build package" buildlog bash src/final/build_package.sh
step "leak grep" leaklog bash src/final/leak_grep.sh
step "package check" packlog bash src/final/package_check.sh
step "rebuild reproducible" rebuildlog bash src/final/rebuild_repro.sh
step "static path probe" staticlog python3 src/final/static_path_probe.py
step "behaviour probe" behaviourlog python3 src/final/behaviour_probe.py

# scrub the tree back to pristine before the isolated solve
rm -f cartographer/.cartographer_state cartographer/.cartographer_state.tmp
find cartographer -name '*.log' -o -name '.t_*' -o -name '.verify' | head -3
step "isolated solve" isolatelog bash src/final/isolated_solve.sh

# inventory
step "report hashes" hasheslog bash src/final/report_hashes.sh
ls organizer-private/cartographer.zip organizer-private/MANIFEST.sha256 \
    >/dev/null 2>&1 && echo "  PASS deliverables present" || {
    echo "  FAIL deliverables missing"; FAILED=$((FAILED + 1)); }

if [ "$FAILED" = "0" ]; then
    echo "VERIFY ALL OK"
    exit 0
fi
echo "VERIFY ALL NOT OK ($FAILED failed)"
exit 1
