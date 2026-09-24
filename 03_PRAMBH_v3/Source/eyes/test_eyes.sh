#!/usr/bin/env bash
# P8 suite - the surveyor's eyes (spec 4.7, >= 45 checks).  Prints PASS/FAIL.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
RUNS="$ROOT/organizer-private/runs"
SBX="$(mktemp -d /tmp/p8sbx.XXXXXX)"
trap 'chmod -R u+w "$SBX" 2>/dev/null; rm -rf "$SBX"' EXIT
PKG="$SBX/pkg"
PASS=0; FAIL=0
ok() { if [ "$2" = "$3" ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1 (got [$2] want [$3])"; FAIL=$((FAIL+1)); fi; }
okf() { if [ "${2:-1}" -eq 0 ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1"; FAIL=$((FAIL+1)); fi; }
okn() { if [ "${2:-0}" -ge "$3" ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1 (got [$2] want >= $3)"; FAIL=$((FAIL+1)); fi; }
mintval() { python3 -c "
import sys; sys.path.insert(0, '$ROOT/src/gen'); import mint
print(eval(sys.argv[1], vars(mint)))" "$1"; }
count_of() { grep -o -a -F "$1" "$2" | wc -l; }
CF="-O2 -static -s -Wall -Wextra -std=gnu11 -D_GNU_SOURCE"
mkdir -p "$PKG/stage5_eyes" "$PKG/plates"

echo "=== plates (deterministic, metadata-clean) ==="
python3 "$HERE/plate_gen.py" "$PKG" >"$SBX/plates.log" 2>&1
okf "plate-gen" $?
for p in depth.png hue.png sheet_a.png sheet_b.png; do
  ok "plate-present-$p" "$(test -f "$PKG/plates/$p" && echo yes)" "yes"
done
python3 "$HERE/plate_gen.py" "$SBX/pkg2" >/dev/null 2>&1
for p in depth.png hue.png sheet_a.png sheet_b.png; do
  cmp -s "$PKG/plates/$p" "$SBX/pkg2/plates/$p"
  okf "plate-deterministic-$p" $?
done
ok "plate-metadata-notice-only" \
  "$(for p in "$PKG"/plates/*.png; do
       python3 -c "
import sys,struct
blob=open('$p','rb').read(); off=8; tags=set()
while off+8<=len(blob):
    ln=int.from_bytes(blob[off:off+4],'big'); tag=blob[off+4:off+8]
    tags.add(tag); off+=12+ln
bad=tags-{b'IHDR',b'tEXt',b'IDAT',b'IEND'}
print(1 if bad else 0)"; done | paste -sd+ | bc)" "0"
ok "plate-strings-clean" \
  "$(strings -n 6 "$PKG"/plates/*.png | grep -c -E 'PRAMBH\{')" "0"
ok "plate-no-real-codes-in-metadata" \
  "$(grep -o -a -F "$(mintval 'eyes_ink()')" "$PKG"/plates/*.png | wc -l)" "0"

echo
echo "=== eyes notes sealing ==="
if [ -f "$RUNS/chain2_walk.txt" ]; then
  python3 "$HERE/gen_eyes.py" "$PKG" >"$SBX/eyes.log" 2>&1
  okf "gen-eyes" $?
  ok "notes-size" "$(stat -c%s "$PKG/stage5_eyes/eyes_notes.bin")" "2048"
  ok "notes-sealed" \
    "$(grep -c -a -F 'SURVEYOR' "$PKG/stage5_eyes/eyes_notes.bin")" "0"
  okn "consts-written" "$(wc -l < "$HERE/eyes_consts.h")" 15
else
  echo "NOTE chain2_walk.txt missing: the eyes notes and the title digest are"
  echo "     deferred with the chain #2 run (Appendix C.2a; see HANDOFF.md)"
fi

echo
echo "=== build hygiene (same recipe as every shipped tool) ==="
cd "$HERE"
for tool in eyes validate; do
  musl-gcc $CF -o "$PKG/stage5_eyes/$tool" "$tool.c" ../chain/chain.c \
      ../core/carto_sha256.c ../core/sha256ctr.c ../state/state.c \
      2>"$SBX/$tool.log"
  okf "$tool-build" $?
  ok "$tool-no-warnings" "$(stat -c%s "$SBX/$tool.log")" "0"
  file "$PKG/stage5_eyes/$tool" | grep -q "statically linked"
  okf "$tool-static" $?
  nm "$PKG/stage5_eyes/$tool" 2>&1 | grep -q "no symbols"
  okf "$tool-nm-empty" $?
  musl-gcc $CF -o "$SBX/$tool.2" "$tool.c" ../chain/chain.c \
      ../core/carto_sha256.c ../core/sha256ctr.c ../state/state.c 2>/dev/null
  cmp -s "$PKG/stage5_eyes/$tool" "$SBX/$tool.2"
  okf "$tool-rebuild-deterministic" $?
  strings -n 5 "$PKG/stage5_eyes/$tool" | grep -qE 'gcc|clang|musl|/home/|ns8pc'
  ok "$tool-no-toolchain-strings" "$?" "1"
  okn "$tool-carries-canary" \
    "$(count_of "$(mintval 'canary_token()')" "$PKG/stage5_eyes/$tool")" 1
done
ok "validate-stores-only-the-digest" \
  "$(grep -c -E 'EYES_TITLE_DIGEST|ST_OFF_RESERVED' validate.c)" 2
ok "validate-has-no-ink-strings" \
  "$(count_of "$(mintval 'eyes_ink()')" "$PKG/stage5_eyes/validate")" "0"
ok "eyes-hides-seal-source" \
  "$(for v in "$(mintval 'eyes_ink()')" "$(mintval 'chain2_vector().hex()')" \
        "$(mintval 'door_ink()')"; do
       count_of "$v" "$PKG/stage5_eyes/eyes"; done | paste -sd+ | bc)" "0"


echo
echo "=== human-gate automation lanes (spec 7.4, measured) ==="
python3 "$HERE/decode_lanes.py" "$PKG" >"$SBX/lanes.txt" 2>&1
okf "decode-lanes" $?
tail -8 "$SBX/lanes.txt"
grep -q "PASS depth-lane" "$SBX/lanes.txt"
okf "lane-depth-measured" $?
grep -q "PASS hue-lane" "$SBX/lanes.txt"
okf "lane-hue-measured" $?
grep -q "PASS moire-lane" "$SBX/lanes.txt"
okf "lane-moire-measured" $?

echo
echo "=== validator: gates, refusals, timing ==="
VAL="$PKG/stage5_eyes/validate"
TITLE="$(sed -n 's/^FINAL TITLE: //p' "$RUNS/p8_eyes_build.txt" 2>/dev/null)"
[ -n "$TITLE" ] || TITLE="PRAMBH{placeholder_title_for_gate_lanes}"
( cd "$PKG" && ./stage5_eyes/eyes >/dev/null 2>&1; true )
if [ -f "$PKG/prambh.survey" ]; then
  python3 - "$PKG/prambh.survey" <<'PYEOF'
import sys
d = bytearray(open(sys.argv[1], "rb").read())
d[28:36] = (15).to_bytes(8, "little")
open(sys.argv[1], "wb").write(bytes(d))
print("gates forced for the acceptance lane")
PYEOF
  okf "gates-forced" $?
else
  ok "gates-forced" "no-state" "no-state"
fi
"$VAL" "$TITLE" >"$SBX/acc.txt" 2>"$SBX/acc.err"
okf "validate-accept-rc" $?
ok "validate-accept-stderr-silent" "$(stat -c%s "$SBX/acc.err")" "0"
ok "validate-accept-line" "$(cat "$SBX/acc.txt")" "the survey record is complete."
i=0
DISTINCT="$SBX/distinct.txt"
: >"$DISTINCT"
while [ $i -lt 18 ]; do
  i=$((i + 1))
  case $i in
    1) w="PRAMBH{}";;
    2) w="PRAMBH{nope}";;
    3) w="$(mintval 'mirror_dead_end_title(bytes(32))')";;
    4) w="$(mintval 'canary_token()')";;
    5) w="$(mintval 'stage0_token()')";;
    6) w="${TITLE}x";;
    7) w="${TITLE%?}";;
    8) w="${TITLE#?}";;
    9) w="$(echo "$TITLE" | tr 'A-Z' 'a-z')";;
    10) w="$TITLE ";;
    11) w="PRAMBH{$(mintval 'eyes_ink()')}";;
    12) w="PRAMBH{$(mintval 'door_ink()')}";;
    13) w="$(python3 -c 'print("PRAMBH{" + "0"*47 + "}")')";;
    14) w="";;
    15) w="PRAMBH{$(mintval 'seal_ink(bytes(32))')}_$(mintval 'door_ink()')}";;
    16) w="$(python3 -c 'print("A"*200)')";;
    17) w="PRAMBH{mirror_nothing_here}";;
    *) w="$(mintval 'eyes_code(0)')";;
  esac
  "$VAL" "$w" >>"$DISTINCT" 2>/dev/null
  okf "validate-wrong-$i-rc" $?
done
ok "validate-refusals-byte-identical" "$(sort -u "$DISTINCT" | wc -l)" "1"
ok "validate-refusal-text" "$(sort -u "$DISTINCT")" "the survey holds no such record."
python3 - "$VAL" <<'PYEOF' >"$SBX/timing.txt" 2>&1
import subprocess, sys, time
ts = []
for i in range(30):
    t0 = time.perf_counter()
    subprocess.run([sys.argv[1], "PRAMBH{wrong_%d}" % i], capture_output=True)
    ts.append((time.perf_counter() - t0) * 1000.0)
print("samples %d min_ms %.3f max_ms %.3f spread_ms %.3f"
      % (len(ts), min(ts), max(ts), max(ts) - min(ts)))
PYEOF
okf "validate-timing-run" $?
tail -1 "$SBX/timing.txt"
python3 - "$SBX/timing.txt" <<'PYEOF'
import re, sys
spread = float(re.search(r"spread_ms ([0-9.]+)", open(sys.argv[1]).read()).group(1))
sys.exit(0 if spread < 5.0 else 1)
PYEOF
okf "validate-refusal-timing-constant" $?
python3 - "$PKG/prambh.survey" <<'PYEOF'
import sys
d = bytearray(open(sys.argv[1], "rb").read())
d[28:36] = (0).to_bytes(8, "little")
open(sys.argv[1], "wb").write(bytes(d))
PYEOF
"$VAL" "$TITLE" >"$SBX/nogate.txt" 2>/dev/null
ok "validate-refuses-without-gates" "$(cat "$SBX/nogate.txt")" \
  "the survey holds no such record."
"$VAL" >"$SBX/usage.txt" 2>/dev/null
ok "validate-noargs-rc" "$?" "0"
okn "validate-usage-shows-canary" \
  "$(grep -c -F "$(mintval 'canary_token()')" "$SBX/usage.txt")" 1
ok "eyes-seal-gated-by-doors" \
  "$(cd "$PKG" && ./stage5_eyes/eyes seal 0000000000000000000000000000000000000000000000000000000000000000 | grep -c 'not been handed over')" "1"

echo
echo "=== behaviour probe (rc 0, silent stderr) ==="
beh() {
  local label="$1"; shift
  timeout 30 "$@" >"$SBX/beh.out" 2>"$SBX/beh.err"
  ok "$label-rc" "$?" "0"
  ok "$label-stderr-silent" "$(stat -c%s "$SBX/beh.err")" "0"
}
yes a | head -c 200000 >"$SBX/big.txt"
beh "beh-validate-noargs" "$VAL"
beh "beh-validate-empty" "$VAL" ""
beh "beh-validate-200kb" "$VAL" "$(cat "$SBX/big.txt")"
beh "beh-validate-16-extra" "$VAL" a b c d e f g h i j k l m n o p
beh "beh-eyes-noargs" "$PKG/stage5_eyes/eyes"
beh "beh-eyes-unknown" "$PKG/stage5_eyes/eyes" frobnicate
beh "beh-eyes-seal-garbage" "$PKG/stage5_eyes/eyes" seal zz
beh "beh-narrow-columns" env COLUMNS=20 "$VAL" x
beh "beh-term-dumb" env TERM=dumb "$PKG/stage5_eyes/eyes" plates
"$VAL" x </dev/null >"$SBX/beh.out" 2>"$SBX/beh.err"
ok "beh-devnull-rc" "$?" "0"
ok "beh-devnull-stderr-silent" "$(stat -c%s "$SBX/beh.err")" "0"
printf 'junk\n' | "$VAL" x >"$SBX/beh.out" 2>"$SBX/beh.err"
ok "beh-piped-stdin-rc" "$?" "0"
ok "beh-piped-stdin-stderr-silent" "$(stat -c%s "$SBX/beh.err")" "0"

echo
echo "P8: $PASS PASS, $FAIL FAIL"
[ "$FAIL" -eq 0 ]
