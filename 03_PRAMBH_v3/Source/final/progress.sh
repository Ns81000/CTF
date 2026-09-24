#!/bin/bash
# progress.sh - live progress view for the PRAMBH pre-audit build
# (chain #1, chain #2, finish.sh pipeline).  Foreground: it refreshes in
# place every 10 s; exits by itself when finish.done appears.
# usage:  wsl.exe -d Ubuntu -- bash /mnt/e/drive-upload/prambh-build/src/final/progress.sh
#         ...add --once for a single frame (used by tests)
set -u
ROOT=/mnt/e/drive-upload/prambh-build
RUNS=$ROOT/organizer-private/runs
DONE_FLAG=/mnt/e/drive-upload/bin/wsl-jobs/finish.done
LOG=/mnt/e/drive-upload/bin/wsl-jobs/finish.log
TARGET=4500            # nominal seconds per chain (75 min, calibrated T)
W=40

et2s() { # [[hh:]mm:]ss -> seconds (runs are < 24 h)
  local t="${1// /}" a b c
  IFS=: read -r a b c <<<"$t"
  if [ -n "${c:-}" ]; then echo $((10#$a * 3600 + 10#$b * 60 + 10#$c))
  elif [ -n "${b:-}" ]; then echo $((10#$a * 60 + 10#$b))
  else echo $((10#$a)); fi
}

bar() { # bar <pct>  (assignments split: one `local` line cannot see its own earlier arg under set -u)
  local p="${1:-0}"
  local f=$((p * W / 100)) i s=""
  for ((i = 0; i < W; i++)); do [ "$i" -lt "$f" ] && s+="#" || s+="-"; done
  printf '%s' "$s"
}

seed1=$(python3 -c "import sys; sys.path.insert(0,'$ROOT/src/gen'); import mint; print(mint.loom_seed_material(mint.capsule_content()).hex())" 2>/dev/null || echo none)
seed2=$(python3 -c "import sys; sys.path.insert(0,'$ROOT/src/gen'); import mint; print(mint.chain2_seed().hex())" 2>/dev/null || echo none)

stage_of() { # last matching marker in finish.log -> pct + label
  local last="" pct=3 lbl="starting"
  local table="4:waiting for the chains|6:chambers generated|8:P6 doors suite|\
55:chain #1 harvested|65:chain #2 harvested|70:package build|74:leak grep|\
78:release|82:package check|86:rebuild repro|88:isolated solve|\
90:attack static|92:attack scripted|93:floor proof|97:verify all|99:docs"
  [ -f "$LOG" ] || { echo "$pct|$lbl"; return; }
  local IFS='|' entry
  for entry in $table; do
    local p="${entry%%:*}" m="${entry#*:}"
    if grep -q "$m" "$LOG" 2>/dev/null; then pct=$p; lbl=$m; fi
  done
  echo "$pct|$lbl"
}

frame() {
  local now pct el eta pid
  now=$(date -u +%H:%M:%S)
  printf '\033[2J\033[H'
  echo "PRAMBH pre-audit build - live progress          $now UTC"
  echo "=================================================================="
  for n in 1 2; do
    case $n in
      1) local hex=$seed1 label="chain #1 (loom ink)   " out=chain1_walk.txt;;
      2) local hex=$seed2 label="chain #2 (seal ink)   " out=chain2_walk.txt;;
    esac
    if [ -s "$RUNS/$out" ]; then
      printf '%s [%s] 100%%  harvested -> %s\n' "$label" "$(bar 100)" "$out"
    else
      pid=$(pgrep -f "$hex" | head -1 || true)
      if [ -n "$pid" ]; then
        el=$(et2s "$(ps -o etime= -p "$pid")")
        pct=$((el * 100 / TARGET)); [ "$pct" -gt 99 ] && pct=99
        eta=$((TARGET - el)); [ "$eta" -lt 0 ] && eta=0
        printf '%s [%s] %3d%%  elapsed %2dm%02ds  eta %2dm%02ds  (nominal 75m)\n' \
          "$label" "$(bar "$pct")" "$pct" $((el / 60)) $((el % 60)) \
          $((eta / 60)) $((eta % 60))
      else
        printf '%s [DEAD]  process gone and %s missing -> restart with\n' \
          "$label" "$out"
        echo "        the Start-Process command from your builder session."
      fi
    fi
  done
  if [ -f "$DONE_FLAG" ]; then
    echo "------------------------------------------------------------------"
    echo "pipeline             [$(bar 100)] 100%%  FINISH.SH DONE"
    echo "RELEASE:"
    ls -la /mnt/e/drive-upload/prambh/RELEASE 2>/dev/null || echo "  (missing!)"
    echo
    echo "DONE - tell your builder session to verify and report."
    return 9
  fi
  local st; st=$(stage_of); pct=${st%%|*}; lbl=${st#*|}
  printf 'pipeline             [%s] %3d%%  stage: %s\n' "$(bar "$pct")" "$pct" "$lbl"
  echo "=================================================================="
  echo "refreshing every 10 s - Ctrl+C stops WATCHING only; the build keeps running"
  return 0
}

while true; do
  frame && { [ "${1:-}" = "--once" ] && break; sleep 10; } || break
done
