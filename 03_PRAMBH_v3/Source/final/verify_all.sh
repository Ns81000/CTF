#!/usr/bin/env bash
# verify_all.sh (spec 8): run EVERY suite serially and report the verdicts.
# Usage: bash src/final/verify_all.sh          (all suites)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
RUNS="$ROOT/organizer-private/runs"
mkdir -p "$RUNS"
FAILS=0
run_suite() { # run_suite <label> <dir> <suite>
  local label="$1" dir="$2" suite="$3"
  local out="$RUNS/suite_${label}.txt"
  ( cd "$ROOT/$dir" && bash "$suite" ) >"$out" 2>&1
  local rc=$?
  local line
  line="$(grep -E '^[A-Z0-9-]+: [0-9]+ PASS' "$out" | tail -1)"
  if [ "$rc" -eq 0 ]; then
    echo "PASS suite-$label   $line"
  else
    echo "FAIL suite-$label   $line  (see runs/suite_${label}.txt)"
    FAILS=$((FAILS + 1))
  fi
}
run_suite state   src/state   test_state.sh
run_suite chain   src/chain   test_chain.sh
run_suite stage0  src/stage0  test_stage0.sh
run_suite flood   src/flood   test_flood.sh
run_suite loom    src/loom    test_loom.sh
run_suite doors   src/doors   test_doors.sh
run_suite mirror  src/mirror  test_mirror.sh
run_suite eyes    src/eyes    test_eyes.sh
run_suite server  src/server  test_server.sh
run_suite eventgen src/gen    test_eventgen.sh
echo
if [ "$FAILS" -eq 0 ]; then echo "VERIFY ALL OK"; else echo "VERIFY ALL NOT OK ($FAILS suites failed)"; fi
[ "$FAILS" -eq 0 ]
