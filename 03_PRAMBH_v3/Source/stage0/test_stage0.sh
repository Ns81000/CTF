#!/usr/bin/env bash
# P3 suite - Stage 0 milestone + capsule (spec 4.2).  Prints PASS/FAIL lines.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
SBX="$(mktemp -d /tmp/p3sbx.XXXXXX)"
trap 'rm -rf "$SBX"' EXIT
PASS=0; FAIL=0

ok() { # ok <label> <actual> <expected>
  if [ "$2" = "$3" ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1 (got [$2] want [$3])"; FAIL=$((FAIL+1)); fi
}
okf() { # okf <label> <rc>  -- pass if rc==0
  if [ "${2:-1}" -eq 0 ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1"; FAIL=$((FAIL+1)); fi
}

mintval() { python3 -c "
import sys; sys.path.insert(0, '$ROOT/gen'); import mint
print(eval(sys.argv[1], vars(mint)))" "$1"; }

# ---- build -------------------------------------------------------------
cd "$HERE"
python3 gen_consts.py >/dev/null
PKG="$SBX/pkg"; mkdir -p "$PKG/stage0_milestone" "$PKG/field-notes"
MS="$PKG/stage0_milestone/milestone"
musl-gcc -O2 -static -s -o "$MS" milestone.c \
  ../core/carto_sha256.c ../core/sha256ctr.c ../state/state.c 2>"$SBX/build.log"
okf "build" $?

file "$MS" | grep -q "statically linked"
okf "static-binary" $?

nm "$MS" 2>&1 | grep -q "no symbols"
okf "nm-empty" $?

musl-gcc -O2 -static -s -o "$SBX/ms2" milestone.c \
  ../core/carto_sha256.c ../core/sha256ctr.c ../state/state.c
cmp -s "$MS" "$SBX/ms2"
okf "deterministic-rebuild" $?

python3 - <<EOF
import sys; sys.path.insert(0, "$ROOT/gen"); import mint
open("$PKG/capsule.bin", "wb").write(mint.capsule_bin())
open("$PKG/LAUNCH.txt", "w").write(mint.launch_phrase() + "\n")
EOF

ok "capsule-size" "$(stat -c%s "$PKG/capsule.bin")" "32"
ok "capsule-matches-mint" "$(xxd -p -c64 "$PKG/capsule.bin")" \
   "$(mintval 'capsule_bin().hex()')"
ok "launch-txt" "$(cat "$PKG/LAUNCH.txt")" "$(mintval 'launch_phrase()')"

# ---- no-args behavior --------------------------------------------------
OUT1="$("$MS" 2>"$SBX/e1")"; RC=$?
ok "noargs-rc" "$RC" "0"
ok "noargs-stderr-empty" "$(stat -c%s "$SBX/e1")" "0"

TOKEN="$(mintval 'stage0_token()')"
echo "$OUT1" | grep -qF "$TOKEN"
okf "token-present" $?

echo "$OUT1" | grep -qE 'PRAMBH\{zero_[0-9a-f]{8}\}'
okf "token-format" $?

OUT2="$("$MS" 2>/dev/null)"
ok "token-stable" "$OUT2" "$OUT1"

echo "$OUT1" | grep -qF "field-notes/"
okf "points-to-field-notes" $?

echo "$OUT1" | grep -qF "Trust timestamps, not moods"
okf "notice-printed" $?

CANARY="$(mintval 'canary_token()')"
echo "$OUT1" | grep -qF "$CANARY"
okf "canary-printed" $?

if echo "$OUT1" | grep -qiE 'correct|valid|right|wrong'; then
  echo "FAIL verdict-words"; FAIL=$((FAIL+1));
else echo "PASS verdict-words"; PASS=$((PASS+1)); fi

# ---- state -------------------------------------------------------------
STATE="$PKG/prambh.survey"
ok "state-exists" "$(test -f "$STATE" && echo yes)" "yes"
ok "state-size" "$(stat -c%s "$STATE")" "512"
python3 "$ROOT/state/check_state.py" hmac "$PKG" >/dev/null
okf "state-hmac-independent" $?

field() { python3 -c "import struct; d=open('$STATE','rb').read(); print(struct.unpack('<Q', d[$1:$1+8])[0])"; }
FR1="$(field 12)"
C1="$(field 20)"
"$MS" >/dev/null
FR2="$(field 12)"
C2="$(field 20)"
ok "first-run-stable" "$FR1" "$FR2"
okf "counter-increments" "$([ "$C2" -gt "$C1" ] && echo 0 || echo 1)"

# tamper in payload region -> reset
printf '\xAA' | dd of="$STATE" bs=1 seek=10 conv=notrunc 2>/dev/null
"$MS" >/dev/null
FR3="$(field 12)"
if [ "$FR3" != "$FR1" ]; then echo "PASS tamper-payload-resets"; PASS=$((PASS+1));
else echo "FAIL tamper-payload-resets"; FAIL=$((FAIL+1)); fi

# tamper in HMAC region -> reset
FR4="$(field 12)"
printf '\xAA' | dd of="$STATE" bs=1 seek=500 conv=notrunc 2>/dev/null
"$MS" >/dev/null
FR5="$(field 12)"
if [ "$FR5" != "$FR4" ]; then echo "PASS tamper-hmac-resets"; PASS=$((PASS+1));
else echo "FAIL tamper-hmac-resets"; FAIL=$((FAIL+1)); fi

# foreign state from another package -> reset
PKG2="$SBX/pkg2"; mkdir -p "$PKG2/stage0_milestone" "$PKG2/field-notes"
cp "$MS" "$PKG2/stage0_milestone/"
cp "$PKG/capsule.bin" "$PKG2/"
( cd "$PKG2" && ./stage0_milestone/milestone >/dev/null )
cp "$PKG2/prambh.survey" "$PKG/prambh.survey"
FR6="$(field 12)"
"$MS" >/dev/null
FR7="$(field 12)"
if [ "$FR7" != "$FR6" ]; then echo "PASS foreign-state-resets"; PASS=$((PASS+1));
else echo "FAIL foreign-state-resets"; FAIL=$((FAIL+1)); fi

# only file a run creates is the state file
PKG3="$SBX/pkg3"; mkdir -p "$PKG3/stage0_milestone" "$PKG3/field-notes"
cp "$MS" "$PKG3/stage0_milestone/"; cp "$PKG/capsule.bin" "$PKG3/"
( cd "$PKG3" && ./stage0_milestone/milestone >/dev/null )
NEW="$(cd "$PKG3" && find . -type f | sort)"
ok "only-state-written" "$NEW" \
   "$(printf './capsule.bin\n./prambh.survey\n./stage0_milestone/milestone')"


# ---- capsule open ------------------------------------------------------
PHRASE="$(mintval 'launch_phrase()')"
OPEN1="$("$MS" open $PHRASE 2>"$SBX/e2")"; RC=$?
ok "open-rc" "$RC" "0"
ok "open-stderr-empty" "$(stat -c%s "$SBX/e2")" "0"

vec_of() { echo "$1" | awk '/^[0-9a-f]{64}$/ {print; exit}'; }
V_REAL="$(vec_of "$OPEN1")"
ok "open-real-vector" "$V_REAL" "$(mintval 'capsule_content().hex()')"

echo "$V_REAL" | grep -qE '^[0-9a-f]{64}$'
okf "vector-format" $?

# the four designed wrong phrases -> registered decoy vectors
i=1
while [ $i -le 4 ]; do
  DP="$(mintval "decoy_capsule_phrases()[$((i-1))]")"
  DV="$(vec_of "$("$MS" open $DP 2>/dev/null)")"
  ok "decoy-lane-$i" "$DV" "$(mintval "capsule_open(decoy_capsule_phrases()[$((i-1))]).hex()")"
  i=$((i+1))
done

# undesigned phrase -> format-valid, unregistered, != real
VU="$(vec_of "$("$MS" open frobnicate the gazebo quietly 2>/dev/null)")"
echo "$VU" | grep -qE '^[0-9a-f]{64}$'
okf "undesigned-format-valid" $?
if [ "$VU" != "$V_REAL" ]; then echo "PASS undesigned-differs"; PASS=$((PASS+1));
else echo "FAIL undesigned-differs"; FAIL=$((FAIL+1)); fi

# empty phrase -> format-valid
VE="$(vec_of "$("$MS" open "" 2>/dev/null)")"
echo "$VE" | grep -qE '^[0-9a-f]{64}$'
okf "empty-phrase-format-valid" $?

# missing capsule -> neutral line, rc 0, stderr silent
mv "$PKG/capsule.bin" "$SBX/capsule.away"
OUT_MISS="$("$MS" open whatever phrase 2>"$SBX/e3")"; RC=$?
ok "missing-capsule-rc" "$RC" "0"
ok "missing-capsule-stderr" "$(stat -c%s "$SBX/e3")" "0"
echo "$OUT_MISS" | grep -qF "capsule housing is empty"
okf "missing-capsule-neutral" $?
mv "$SBX/capsule.away" "$PKG/capsule.bin"

# truncated capsule -> neutral line
head -c 16 "$PKG/capsule.bin" > "$PKG/capsule.trunc"
mv "$PKG/capsule.trunc" "$PKG/capsule.bin"
OUT_TR="$("$MS" open whatever phrase 2>/dev/null)"; RC=$?
ok "trunc-capsule-rc" "$RC" "0"
echo "$OUT_TR" | grep -qF "capsule housing is empty"
okf "trunc-capsule-neutral" $?
python3 -c "
import sys; sys.path.insert(0, '$ROOT/gen'); import mint
open('$PKG/capsule.bin', 'wb').write(mint.capsule_bin())"

# state still consistent after opens (counter increments, no crash)
C3="$(field 20)"
"$MS" open "$PHRASE" >/dev/null
C4="$(field 20)"
okf "state-consistent-after-open" "$([ "$C4" -gt "$C3" ] && echo 0 || echo 1)"


# ---- leak / hygiene checks --------------------------------------------
# launch phrase words must not appear in the binary
LEAK=0
for w in $PHRASE; do
  if grep -a -q -F "$w" "$MS"; then LEAK=1; echo "  (leak word: $w)"; fi
done
ok "launch-phrase-not-in-binary" "$LEAK" "0"

grep -a -q -F "$(mintval 'capsule_content().hex()')" "$MS"
ok "capsule-content-not-in-binary" "$?" "1"

grep -a -q -F "$(mintval 'loom_seed_material(capsule_content()).hex()')" "$MS"
ok "loom-seed-not-in-binary" "$?" "1"

grep -a -q -F "prambh:loom" "$MS"
ok "no-later-stage-labels" "$?" "1"

strings "$MS" | grep -qF "Trust timestamps, not moods"
okf "notice-in-binary" $?

# stage0 token label used exactly once in the mint (derivation hygiene)
ok "stage0-label-once" \
   "$(grep -c 'prambh:stage0:token' "$ROOT/gen/mint.py")" "1"

# token grammar: canary does not mirror final-title shape
echo "$CANARY" | grep -qE '^PRAMBH\{canary_[0-9a-f]{8}\}$'
okf "canary-format" $?

RROOT="$(cd "$HERE/../.." && pwd)"
# registries regenerate and cover stage 0
python3 "$ROOT/gen/trap_catalogue.py" >/dev/null
okf "trap-catalogue-written" $?
grep -qF "$CANARY" "$RROOT/organizer-private/TRAP_CATALOGUE.md"
okf "canary-registered" $?
grep -qF "D-CAP-4" "$RROOT/organizer-private/TRAP_CATALOGUE.md"
okf "decoy-lanes-registered" $?
python3 "$ROOT/gen/keys.py" >/dev/null
okf "keys-table-written" $?

echo
echo "P3: $PASS PASS, $FAIL FAIL"
[ "$FAIL" -eq 0 ]

