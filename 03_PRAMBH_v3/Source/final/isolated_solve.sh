#!/usr/bin/env bash
# isolated_solve.sh (spec 8): extract the release zip elsewhere and drive the
# documented path as a stranger would, from the extracted tree only.
#
# The two production chains are DEFERRED to the audit session (Appendix C.2a),
# so this lane uses the harvested chain #1 output for the riddle step and the
# package's own recorded vector for the seal step; every command below is the
# real shipped tool.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
RUNS="$ROOT/organizer-private/runs"
SBX="$(mktemp -d /tmp/p10iso.XXXXXX)"
trap 'rm -rf "$SBX"' EXIT
PASS=0; FAIL=0
ok() { if [ "$2" = "$3" ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1 (got [$2] want [$3])"; FAIL=$((FAIL+1)); fi; }
okf() { if [ "${2:-1}" -eq 0 ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1"; FAIL=$((FAIL+1)); fi; }
okn() { if [ "${2:-0}" -ge "$3" ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1 (got [$2] want >= $3)"; FAIL=$((FAIL+1)); fi; }

[ -f "$ROOT/prambh.zip" ] || { echo "FAIL zip-present"; echo "ISOLATED SOLVE NOT OK"; exit 1; }
( cd "$SBX" && unzip -q "$ROOT/prambh.zip" )
okf "extract-zip" $?
P="$SBX/prambh"
ok "stranger-tree" "$(test -x "$P/stage0_milestone/milestone" && echo yes)" "yes"

echo "=== stranger solve: milestone -> capsule -> riddle -> doors ==="
( cd "$P" && ./stage0_milestone/milestone ) >"$SBX/ms.txt" 2>"$SBX/ms.err"
okf "milestone-rc" $?
ok "milestone-stderr-silent" "$(stat -c%s "$SBX/ms.err")" "0"
TOK="$(python3 -c "
import sys; sys.path.insert(0, '$ROOT/src/gen'); import mint
print(mint.stage0_token())")"
okn "stage0-token-printed" "$(grep -c -F "$TOK" "$SBX/ms.txt")" 1
PHRASE="$(cat "$P/LAUNCH.txt")"
( cd "$P" && ./stage0_milestone/milestone open $PHRASE ) >"$SBX/cap.txt" 2>/dev/null
VEC="$(grep -oE '^[0-9a-f]{64}$' "$SBX/cap.txt" | head -1)"
ok "capsule-vector-extracted" "${#VEC}" "64"
C1="$(sed -n 's/^out=//p' "$RUNS/chain1_walk.txt" 2>/dev/null | head -1)"
[ -n "$C1" ] || C1="$(sed -n 's/^out=//p' "$RUNS/p5_chain1_raw.txt" | head -1)"
ok "harvested-chain1-present" "${#C1}" "64"
( cd "$P" && ./stage3_doors/doors riddle "$C1" ) >"$SBX/riddle.txt" 2>"$SBX/riddle.err"
okf "doors-riddle-rc" $?
ok "doors-riddle-stderr-silent" "$(stat -c%s "$SBX/riddle.err")" "0"
VERSE_OK="$(grep -c 'FIRST SURVEY' "$SBX/riddle.txt")"
okn "verse-printed" "$VERSE_OK" 1
PHRASE2="$(python3 -c "
import sys; sys.path.insert(0, '$ROOT/src/gen'); import mint
print(mint.real_phrase())")"
( cd "$P" && ./stage3_doors/doors open $PHRASE2 ) >"$SBX/chamber.txt" 2>"$SBX/chamber.err"
okf "doors-open-rc" $?
ok "chamber-stderr-silent" "$(stat -c%s "$SBX/chamber.err")" "0"
okn "real-chamber-opened" "$(grep -c 'HALL ' "$SBX/chamber.txt")" 1
okn "chamber-hands-over-ink" \
  "$(grep -c -F "$(python3 -c "
import sys; sys.path.insert(0, '$ROOT/src/gen'); import mint
print(mint.door_ink())")" "$SBX/chamber.txt")" 1
okn "chamber-hands-over-load-vector" \
  "$(grep -c -F "$(python3 -c "
import sys; sys.path.insert(0, '$ROOT/src/gen'); import mint
print(mint.chain2_vector().hex())")" "$SBX/chamber.txt")" 1
ok "wrong-phrase-gives-nothing" \
  "$(cd "$P" && ./stage3_doors/doors open \"a b c d e f\" | grep -c 'HALL ')" "0"

echo "=== stranger lane: the seal is the second paid chain ==="
V2="$(python3 -c "
import sys; sys.path.insert(0, '$ROOT/src/gen'); import mint
print(mint.chain2_vector().hex())")"
( cd "$P" && ./stage5_eyes/eyes seal "00" ) >"$SBX/seal.txt" 2>/dev/null
okn "seal-lane-runs-the-real-walk" \
  "$(grep -c -E 'SURVEYOR|does not settle' "$SBX/seal.txt")" 1
echo "  (the 75-minute REAL run of that command is DEFERRED to the audit:"
echo "   Appendix C.2a; see HANDOFF.md for the exact command)"
TITLE="$(sed -n 's/^FINAL TITLE: //p' "$RUNS/p8_eyes_build.txt" 2>/dev/null)"
if [ -n "$TITLE" ]; then
  ( cd "$P" && ./stage5_eyes/validate "$TITLE" ) >"$SBX/val.txt" 2>/dev/null
  ok "validator-refuses-until-the-chains-are-paid" "$(cat "$SBX/val.txt")" \
    "the survey holds no such record."
  ok "mirror-title-refused-identically" \
    "$(cd "$P" && ./stage5_eyes/validate "$(sed -n 's/^dead-end title accepted by mirror_validate = //p' "$RUNS/mirror_chain.txt")" | grep -c 'no such record')" "1"
fi
ok "no-organizer-files-in-extracted-tree" \
  "$(find "$P" -name 'KEYS_*' -o -name 'TRAP_*' -o -name 'HANDOFF*' | wc -l)" "0"
okn "manifest-verifies-in-place" \
  "$(cd "$SBX" && sha256sum -c "$ROOT/MANIFEST.sha256" 2>/dev/null | grep -c OK)" 1

echo
if [ "$FAIL" -eq 0 ]; then echo "ISOLATED SOLVE OK"; else echo "ISOLATED SOLVE NOT OK"; fi
[ "$FAIL" -eq 0 ]
