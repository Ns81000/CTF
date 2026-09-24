#!/bin/bash
# commit_final.sh -- Phase FINAL section 8: the final commit.
set -e
cd /home/manish/cartographer-build

echo "--- pre-commit tree sweep ---"
find . -name '__pycache__' -type d -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true
find . -name '*.pyc' -not -path './.git/*' -delete 2>/dev/null || true

git add -A
echo "--- staged ---"
git --no-pager diff --cached --stat | tail -30
git --no-pager commit -q -m "phase FINAL-2: pacing fix (N_REQUIRED 320 -> 260), full source audit, repackage

- Stage-3 sample size recalibrated from measured reliability sweeps: 260
  pairs/window = 2080 pairs = 4160 oracle calls, so the whole clean path
  fits the CTF window at a cautious ~2 s/query cadence (~140 min) with
  margin, where 320 pairs (5120 calls) cost ~171 min and blew it
- reliability evidence: 1500-trial model sweeps per candidate
  (logs/runs/pf2_trials_model2.jsonl) + real-binary scaled trials
  (logs/runs/pf2_trials_real.jsonl), fresh random figures every trial
- src/final: pacing model generalized (alternating or jittered per-query
  spacing), N_REQUIRED documented in cartosolve.py, reliability trial
  harness + report added
- section-2 audit: every source file swept (unchecked IO, bounds, integer
  overflow, off-by-one, uninitialised use, format strings, leftover
  debug hooks, hidden env/ifdef flags); vm.c decode over-read fixed
  (8-byte pad on the code image)
- clean rebuild + all suites re-run on the new build"
git --no-pager log --oneline -3
echo "--- working tree after commit ---"
git --no-pager status --short
echo "COMMIT-OK"
