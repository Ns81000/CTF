#!/bin/bash
# finish.sh - the end-to-end pipeline the build session leaves running.
# It waits for the parallel chain walks, then builds, checks, releases and
# documents the package.  Each stage is logged to organizer-private/runs/.
set -u
cd /mnt/e/drive-upload/prambh-build
RUNS=organizer-private/runs
LOG=/mnt/e/drive-upload/bin/wsl-jobs/finish.log
: >"$LOG"
say() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }

wait_for() { # wait_for <file> <minutes> <label>
  local f="$1" mins="$2" label="$3" i=0
  while [ ! -s "$f" ]; do
    i=$((i + 1))
    if [ "$i" -gt $((mins * 4)) ]; then
      say "TIMEOUT waiting for $label ($f) after ${mins} min"
      return 1
    fi
    sleep 15
  done
  say "$label is harvested ($f)"
  return 0
}

say "finish pipeline start"

# --- stage A: the seven decoy-chamber walks ----------------------------
if wait_for "$RUNS/door7_walk.txt" 60 "decoy chamber walks"; then
  python3 src/doors/chambers_gen.py >>"$LOG" 2>&1
  say "chambers generated rc=$?"
  bash src/doors/test_doors.sh > "$RUNS/suite_doors.txt" 2>&1
  say "P6 doors suite rc=$? ($(grep -E '^P6: ' "$RUNS/suite_doors.txt" | tail -1))"
fi

# --- stage B: chain #1 and chain #2 ------------------------------------
wait_for "$RUNS/chain1_walk.txt" 90 "chain #1"
wait_for "$RUNS/chain2_walk.txt" 90 "chain #2"

python3 src/final/build_package.py prambh > "$RUNS/p10_build.txt" 2>&1
say "package build rc=$?"

# --- stage C: the P10 lanes -------------------------------------------
bash src/final/leak_grep.sh > "$RUNS/p10_leak_grep.txt" 2>&1
say "leak grep rc=$? ($(grep -E '^LEAKS: ' "$RUNS/p10_leak_grep.txt" | tail -1))"
bash src/final/make_release.sh /mnt/e/drive-upload/prambh/RELEASE \
    > "$RUNS/p10_release.txt" 2>&1
say "release rc=$? ($(grep -E '^zip sha256' "$RUNS/p10_release.txt" | tail -1))"
bash src/final/package_check.sh > "$RUNS/p10_package_check.txt" 2>&1
say "package check rc=$? ($(grep -E '^PACKAGE CHECK' "$RUNS/p10_package_check.txt" | tail -1))"
bash src/final/rebuild_repro.sh > "$RUNS/p10_rebuild_repro.txt" 2>&1
say "rebuild repro rc=$? ($(tail -1 "$RUNS/p10_rebuild_repro.txt"))"
bash src/final/isolated_solve.sh > "$RUNS/p10_isolated_solve.txt" 2>&1
say "isolated solve rc=$? ($(tail -1 "$RUNS/p10_isolated_solve.txt"))"
python3 src/final/attack_static.py > "$RUNS/p10_attack_static.txt" 2>&1
say "attack static rc=$? ($(tail -1 "$RUNS/p10_attack_static.txt"))"
python3 src/final/attack_scripted.py > "$RUNS/p10_attack_scripted.txt" 2>&1
say "attack scripted rc=$? ($(tail -1 "$RUNS/p10_attack_scripted.txt"))"
python3 src/final/floor_proof.py > "$RUNS/p10_floor_proof.txt" 2>&1
say "floor proof rc=$? ($(tail -1 "$RUNS/p10_floor_proof.txt"))"

# --- stage D: every suite, serially ------------------------------------
bash src/final/verify_all.sh > "$RUNS/p10_verify_all.txt" 2>&1
say "verify all rc=$? ($(tail -1 "$RUNS/p10_verify_all.txt"))"

# --- stage E: docs + commit -------------------------------------------
python3 src/gen/docs_gen.py > "$RUNS/p10_docs.txt" 2>&1
say "docs rc=$?"
git add -A
git -c user.name=builder -c user.email=builder@local commit -q \
    -m "p10: package, release, suites, docs (finish pipeline)"
say "commit rc=$? head=$(git log --oneline | head -1)"
say "finish pipeline done"
rm -rf /home/ns8pc/jobs 2>/dev/null || true
touch /mnt/e/drive-upload/bin/wsl-jobs/finish.done
