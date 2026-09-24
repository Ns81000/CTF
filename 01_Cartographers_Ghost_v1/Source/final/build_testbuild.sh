#!/bin/bash
# Phase FINAL: build the SCALED TEST BUILD.
#
# The escalation/rate-limit logic lives in the shared state library, so the
# test-only hook is enabled by compiling libstate.a with
# -DCARTO_TEST_TIME_SCALE_ENABLE and relinking the stage binaries against it.
# The stage sources are unchanged, and every shipped build (default CFLAGS)
# carries neither the hook nor the environment-variable name.
#
#   CARTO_TEST_TIME_SCALE=60 src/final/build_testbuild.sh
#   CARTO_TEST_TIME_SCALE=60 CARTO_FINAL_PER_WINDOW=260 python3 src/final/run_clean_path.py
#
# Restore the shipped build afterwards with: bash src/stage4_assembly/verify.sh
set -e
R=/home/manish/cartographer-build

echo "--- library: test build (-DCARTO_TEST_TIME_SCALE_ENABLE) ---"
cd "$R/src/state" && make clean >/dev/null && make CARTO_TEST_BUILD=1 >/dev/null
if strings "$R/src/state/state_policy.o" | grep -q CARTO_TEST_TIME_SCALE; then
    echo "  test library carries the hook: OK"
else
    echo "  test library MISSING the hook: BAD"
    exit 1
fi

echo "--- relink stages 0-3 + rebuild validator against the test library ---"
cd "$R/src/stage0"        && make >/dev/null 2>&1 && echo "  stage0_start"
cd "$R/src/stage1_vm"     && make >/dev/null 2>&1 && echo "  stage1_vm"
cd "$R/src/stage2_stego"  && make >/dev/null 2>&1 && echo "  stage2_stego"
cd "$R/src/stage3_oracle" && make >/dev/null 2>&1 && echo "  oracle"
cd "$R/src/stage4_assembly" && make >/dev/null 2>&1 && echo "  validate"

echo "--- audit: every stage binary must be scale-free in a SHIPPED build ---"
echo "  (this is the TEST build, so the hook IS expected below)"
for b in stage0_start/stage0_start stage1_vm/stage1_vm \
         stage2_stego/stage2_stego stage3_oracle/oracle \
         stage4_assembly/validate; do
    if strings "$R/cartographer/$b" | grep -q CARTO_TEST_TIME_SCALE; then
        echo "  $b: hook present (test build)"
    else
        echo "  $b: hook absent -- test build did NOT take effect"
        exit 1
    fi
done
echo "TESTBUILD-READY"
