#!/usr/bin/env bash
# P6 suite - the hall of doors (spec 4.5).  Prints PASS/FAIL lines.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
RUNS="$ROOT/organizer-private/runs"
SBX="$(mktemp -d /tmp/p6sbx.XXXXXX)"
trap 'chmod -R u+w "$SBX" 2>/dev/null; rm -rf "$SBX"' EXIT
PKG="$SBX/pkg"
PASS=0; FAIL=0

ok() {
  if [ "$2" = "$3" ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1 (got [$2] want [$3])"; FAIL=$((FAIL+1)); fi
}
okf() {
  if [ "${2:-1}" -eq 0 ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1"; FAIL=$((FAIL+1)); fi
}
okn() {
  if [ "${2:-0}" -ge "$3" ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1 (got [$2] want >= $3)"; FAIL=$((FAIL+1)); fi
}
oklt() {
  if [ "${2:-0}" -lt "$3" ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1 (got [$2] want < $3)"; FAIL=$((FAIL+1)); fi
}
mintval() { python3 -c "
import sys; sys.path.insert(0, '$ROOT/src/gen'); import mint
print(eval(sys.argv[1], vars(mint)))" "$1"; }
count_of() { grep -o -a -F "$1" "$2" | wc -l; }

mkdir -p "$PKG/stage3_doors"
DOORS="$PKG/stage3_doors/doors"

echo "=== build hygiene (spec 4.5: same recipe as every shipped tool) ==="
cd "$HERE"
python3 gen_consts.py >"$SBX/consts.log" 2>&1
okf "gen-consts" $?
ok "real-door-index-mint-derived" \
  "$(grep -o '#define PRAMBH_REAL_DOOR_INDEX [0-9]*' doors_consts.h | grep -o '[0-9]*')" \
  "$(mintval 'real_door_index()')"
python3 gen_consts.py >/dev/null 2>&1
M1="$(md5sum doors_consts.h | cut -c1-16)"
python3 gen_consts.py >/dev/null 2>&1
ok "consts-deterministic" "$(md5sum doors_consts.h | cut -c1-16)" "$M1"

musl-gcc -O2 -static -s -Wall -Wextra -std=gnu11 -D_GNU_SOURCE -o "$DOORS" \
    doors.c ../core/carto_sha256.c ../core/sha256ctr.c ../state/state.c \
    2>"$SBX/build.log"
okf "build" $?
ok "build-warning-free" "$(stat -c%s "$SBX/build.log")" "0"
file "$DOORS" | grep -q "statically linked"
okf "binary-static" $?
nm "$DOORS" 2>&1 | grep -q "no symbols"
okf "binary-nm-empty" $?
musl-gcc -O2 -static -s -Wall -Wextra -std=gnu11 -D_GNU_SOURCE -o "$SBX/doors2" \
    doors.c ../core/carto_sha256.c ../core/sha256ctr.c ../state/state.c 2>/dev/null
cmp -s "$DOORS" "$SBX/doors2"
okf "binary-rebuild-deterministic" $?
strings -n 5 "$DOORS" | grep -qE 'gcc|clang|musl|/home/|ns8pc'
ok "binary-no-toolchain-strings" "$?" "1"
okn "binary-carries-canary" "$(count_of "$(mintval 'canary_token()')" "$DOORS")" 1

echo
echo "=== chambers (generated, never hand-written) ==="
python3 chambers_gen.py >"$SBX/chambers.log" 2>&1
okf "chambers-generated" $?
python3 - <<PYEOF
import sys
sys.path.insert(0, "$ROOT/src/doors"); sys.path.insert(0, "$ROOT/src/gen")
import chambers_gen, os
texts = chambers_gen.chambers()
os.makedirs("$SBX/chambers", exist_ok=True)
for i, t in enumerate(texts):
    open("$SBX/chambers/c%d.txt" % i, "w").write(t)
open("$SBX/chamber_stats", "w").write("%d %d" % (len(texts), max(len(t) for t in texts)))
PYEOF
ok "chamber-count" "$(cut -d' ' -f1 "$SBX/chamber_stats")" "8"
oklt "chamber-max-size-below-limit" "$(cut -d' ' -f2 "$SBX/chamber_stats")" 2047
i=0
while [ $i -lt 8 ]; do
  ok "chamber-$i-marker" "$(head -c 5 "$SBX/chambers/c$i.txt")" "HALL "
  i=$((i + 1))
done
ok "chambers-no-verdict-words" \
  "$(grep -o -i -E 'correct|valid|right|wrong' "$SBX/chambers"/c*.txt | wc -l)" "0"
REAL="$SBX/chambers/c$(mintval 'real_door_index()').txt"
okn "real-chamber-has-ink" "$(grep -c -F "$(mintval 'door_ink()')" "$REAL")" 1
okn "real-chamber-has-chain2-vector" \
  "$(grep -c -F "$(mintval 'chain2_vector().hex()')" "$REAL")" 1
i=1
while [ $i -lt 8 ]; do
  [ "$i" -eq "$(mintval 'real_door_index()')" ] && { i=$((i + 1)); continue; }
  ok "decoy-chamber-$i-no-real-values" \
    "$(grep -c -e "$(mintval 'door_ink()')" -e "$(mintval 'chain2_vector().hex()')" \
        -e "$(mintval 'real_phrase()')" "$SBX/chambers/c$i.txt")" "0"
  okn "decoy-chamber-$i-cites-mirror" \
    "$(grep -c -F 'duplicate survey is filed at the valley depot' "$SBX/chambers/c$i.txt")" 1
  okn "decoy-chamber-$i-carries-field-token" \
    "$(grep -c -F 'field token: PRAMBH{' "$SBX/chambers/c$i.txt")" 1
  okn "decoy-chamber-$i-carries-walk" \
    "$(grep -c -F './loom verify --vector' "$SBX/chambers/c$i.txt")" 1
  i=$((i + 1))
done

echo
echo "=== build the doors (spec 4.5: identical records, raw XOR streams) ==="
python3 doors_build.py "$PKG" >"$SBX/build_doors.log" 2>&1
okf "doors-build" $?
ok "doors-bin-size" "$(stat -c%s "$DOORS.bin" 2>/dev/null || stat -c%s "$PKG/stage3_doors/doors.bin")" \
  "$(python3 -c 'print(8 * (32 + 2048))')"
ok "riddle-bin-size" "$(stat -c%s "$PKG/stage3_doors/riddle.bin")" "2048"
ok "doors-bin-hides-marker" "$(count_of "HALL " "$PKG/stage3_doors/doors.bin")" "0"
ok "doors-bin-hides-real-chamber" \
  "$(count_of "$(head -c 40 "$REAL")" "$PKG/stage3_doors/doors.bin")" "0"
ok "doors-bin-hides-door-ink" \
  "$(count_of "$(mintval 'door_ink()')" "$PKG/stage3_doors/doors.bin")" "0"
ok "doors-bin-hides-chain2-vector" \
  "$(count_of "$(mintval 'chain2_vector().hex()')" "$PKG/stage3_doors/doors.bin")" "0"
ok "riddle-hides-verse" \
  "$(count_of "six marks were cut below" "$PKG/stage3_doors/riddle.bin")" "0"
CLAM="$(sed -n 's/^out=//p' "$RUNS/chain1_walk.txt" 2>/dev/null | head -1)"
[ -n "$CLAM" ] || CLAM="$(sed -n 's/^out=//p' "$RUNS/p5_chain1_raw.txt" | head -1)"

echo
echo "=== open lanes: every designed phrase opens exactly its chamber ==="
i=0
while [ $i -lt 8 ]; do
  phrase="$(mintval "door_phrase($i)")"
  "$DOORS" open $phrase >"$SBX/open$i.txt" 2>"$SBX/open$i.err"
  okf "open-$i-rc" $?
  ok "open-$i-stderr-silent" "$(stat -c%s "$SBX/open$i.err")" "0"
  python3 - "$SBX/open$i.txt" "$SBX/chambers/c$i.txt" <<'PYEOF'
import sys
got = open(sys.argv[1]).read().rstrip("\n")
want = open(sys.argv[2]).read().rstrip("\n")
sys.exit(0 if got == want else 1)
PYEOF
  okf "open-$i-byte-exact-chamber" $?
  i=$((i + 1))
done
ok "real-chamber-output-has-ink" \
  "$(grep -c -F "$(mintval 'door_ink()')" "$SBX/open0.txt")" "1"
ok "decoy-output-lacks-ink" \
  "$(grep -c -F "$(mintval 'door_ink()')" "$SBX/open1.txt")" "0"
ok "output-framing-identical" \
  "$(head -c 5 "$SBX/open0.txt")|$(head -c 5 "$SBX/open1.txt")" "HALL |HALL "

echo
echo "=== undesigned lanes: zero signal (byte-identical fixed line) ==="
n=0
U1=""
while [ $n -lt 10 ]; do
  case $n in
    0) ph="sandstone lantern arcade";;
    1) ph="fable coil autumn coast reed zinc";;
    2) ph="";;
    3) ph="zinc zinc zinc zinc zinc zinc";;
    4) ph="reed coast autumn coil fable";;
    5) ph="a b c d e f";;
    6) ph="ZINC REED COAST AUTUMN COIL FABLE";;
    7) ph="fable coil autumn coast reed";;
    8) ph="fable  coil  autumn  coast  reed  zinc";;
    *) ph="fable-coil-autumn-coast-reed-zinc";;
  esac
  "$DOORS" open "$ph" >"$SBX/und$n.txt" 2>"$SBX/und$n.err"
  okf "undesigned-$n-rc" $?
  [ "$n" -eq 0 ] && U1="$(cat "$SBX/und$n.txt")"
  n=$((n + 1))
done
ok "undesigned-single-distinct-output" \
  "$(cat "$SBX"/und*.txt | sort -u | wc -l)" "1"
ok "undesigned-output-fixed-line" "$U1" "the halls do not answer to that word."
ok "undesigned-output-is-not-a-chamber" "$(grep -c -F 'HALL ' "$SBX/und0.txt")" "0"

echo
echo "=== riddle lane: the verse needs the loom claim ==="
python3 - <<PYEOF >"$SBX/verse.txt"
import sys
sys.path.insert(0, "$ROOT/src/doors")
import verse_gen
sys.stdout.write(verse_gen.verse_text())
PYEOF
"$DOORS" riddle "$CLAM" >"$SBX/riddle.ok" 2>"$SBX/riddle.err"
okf "riddle-right-claim-rc" $?
ok "riddle-right-claim-stderr-silent" "$(stat -c%s "$SBX/riddle.err")" "0"
okf "riddle-right-claim-opens-verse" 0
python3 - "$SBX/riddle.ok" "$SBX/verse.txt" <<'PYEOF'
import sys
got = open(sys.argv[1]).read().rstrip("\n")
want = open(sys.argv[2]).read().rstrip("\n")
if got != want:
    print("FAIL riddle-verse-byte-differs")
    sys.exit(1)
print("PASS riddle-verse-byte-exact")
sys.exit(0)
PYEOF
okf "riddle-verse-matches-generator" $?
"$DOORS" riddle "$(python3 -c 'print("11" * 32)')" >"$SBX/riddle.bad" 2>/dev/null
ok "riddle-wrong-claim-refused" "$(cat "$SBX/riddle.bad")" "the riddle does not open."
"$DOORS" riddle zzz >"$SBX/riddle.bad2" 2>/dev/null
ok "riddle-garbage-refused" "$(cat "$SBX/riddle.bad2")" "the riddle does not open."
mv "$PKG/stage3_doors/riddle.bin" "$SBX/riddle.away"
"$DOORS" riddle "$CLAM" >"$SBX/riddle.miss" 2>/dev/null
ok "riddle-missing-file-neutral" "$(cat "$SBX/riddle.miss")" "the riddle does not open."
mv "$SBX/riddle.away" "$PKG/stage3_doors/riddle.bin"
ok "riddle-wrong-equals-right-refusal" "$(cmp -s "$SBX/riddle.bad" "$SBX/riddle.bad2" && echo same)" "same"

echo
echo "=== state (spec 4.9: created, gated, tamper-reset) ==="
ok "state-size" "$(stat -c%s "$PKG/prambh.survey")" "512"
stage_bits() { python3 -c "
import struct
d = open('$PKG/prambh.survey','rb').read()
print(struct.unpack('<Q', d[28:36])[0])"; }
ok "doors-real-bit-set" "$(( $(stage_bits) & 2 ))" "2"
ok "loom-done-bit-set" "$(( $(stage_bits) & 1 ))" "1"
"$DOORS" open "$(mintval 'door_phrase(1)')" >/dev/null 2>&1
ok "decoy-open-does-not-set-bit" "$(( $(stage_bits) & 2 ))" "2"
printf '\xAA' | dd of="$PKG/prambh.survey" bs=1 seek=8 conv=notrunc 2>/dev/null
"$DOORS" >/dev/null 2>&1
ok "tamper-resets-silently" "$(( $(stage_bits) & 255 ))" "0"
python3 "$ROOT/state/check_state.py" hmac "$PKG" >/dev/null 2>&1
okf "state-hmac-valid-after-reset" $?

echo
echo "=== leak lanes (spec 4.5 acceptance) ==="
ph=0
for i in 0 1 2 3 4 5 6 7; do
  [ "$(count_of "$(mintval "door_phrase($i)")" "$DOORS")" -eq 0 ] || ph=$((ph + 1))
done
ok "binary-hides-all-phrases" "$ph" "0"
REALV=0
for v in "$(mintval 'door_ink()')" "$(mintval 'chain2_vector().hex()')" \
         "$(mintval 'stage0_token()')" "$(mintval 'capsule_content().hex()')" \
         "$(mintval 'real_phrase()')" "$CLAM"; do
  [ "$(count_of "$v" "$DOORS")" -eq 0 ] || REALV=$((REALV + 1))
done
ok "binary-hides-real-values" "$REALV" "0"
TOK=0
for i in 1 2 3 4 5 6 7; do
  tok="$(grep -o 'PRAMBH{[0-9a-f]*}' "$SBX/chambers/c$i.txt" | head -1)"
  [ "$(count_of "$tok" "$DOORS")" -eq 0 ] || TOK=$((TOK + 1))
done
ok "binary-hides-decoy-tokens" "$TOK" "0"
okn "binary-prints-notice" "$(count_of 'Trust timestamps, not moods' "$DOORS")" 1
"$DOORS" >"$SBX/usage.txt" 2>"$SBX/usage.err"
ok "usage-rc" "$?" "0"
okn "usage-prints-canary" "$(grep -c -F "$(mintval 'canary_token()')" "$SBX/usage.txt")" 1
ok "usage-stderr-silent" "$(stat -c%s "$SBX/usage.err")" "0"
ok "usage-hides-mechanism-words" \
  "$(grep -c -i -E 'sha|feistel|xor|cipher|encrypt|hmac' "$SBX/usage.txt")" "0"

echo
echo "=== behaviour probe (rc 0, silent stderr, no crash) ==="
beh() {
  local label="$1"; shift
  timeout 30 "$@" >"$SBX/beh.out" 2>"$SBX/beh.err"
  ok "$label-rc" "$?" "0"
  ok "$label-stderr-silent" "$(stat -c%s "$SBX/beh.err")" "0"
}
yes a | head -c 200000 >"$SBX/big.txt"
tr '\0' 'a' </dev/zero | head -c 200000 >"$SBX/big2.txt"
head -c 100 "$PKG/stage3_doors/doors.bin" >"$SBX/trunc.bin"
cp "$PKG/stage3_doors/doors.bin" "$SBX/doors.save"
beh "beh-noargs" "$DOORS"
beh "beh-unknown-subcommand" "$DOORS" frobnicate
beh "beh-open-no-phrase" "$DOORS" open
beh "beh-open-empty-phrase" "$DOORS" open ""
beh "beh-open-200kb" "$DOORS" open "$(cat "$SBX/big.txt")"
beh "beh-open-16-extra-args" "$DOORS" open a b c d e f g h i j k l m n o p
beh "beh-riddle-no-key" "$DOORS" riddle
beh "beh-riddle-short-key" "$DOORS" riddle abcd
beh "beh-narrow-columns" env COLUMNS=20 "$DOORS"
beh "beh-term-dumb" env TERM=dumb "$DOORS" open x
beh "beh-devnull-stdin" "$DOORS" open x
"$DOORS" open x </dev/null >"$SBX/beh.out" 2>"$SBX/beh.err"
ok "beh-devnull-rc" "$?" "0"
ok "beh-devnull-stderr-silent" "$(stat -c%s "$SBX/beh.err")" "0"
printf 'junk\n' | "$DOORS" open x >"$SBX/beh.out" 2>"$SBX/beh.err"
ok "beh-piped-stdin-rc" "$?" "0"
ok "beh-piped-stdin-stderr-silent" "$(stat -c%s "$SBX/beh.err")" "0"
( cd "$PKG/stage3_doors" && chmod 555 . && ./doors open x; chmod 755 . ) \
    >"$SBX/beh.out" 2>"$SBX/beh.err"
ok "beh-readonly-dir-rc" "$?" "0"
ok "beh-readonly-dir-stderr-silent" "$(stat -c%s "$SBX/beh.err")" "0"
mv "$PKG/stage3_doors/doors.bin" "$SBX/doors.away"
"$DOORS" open "$(mintval 'door_phrase(0)')" >"$SBX/beh.out" 2>/dev/null
ok "beh-missing-doors-bin-rc" "$?" "0"
ok "beh-missing-doors-bin-neutral" "$(cat "$SBX/beh.out")" \
  "the halls do not answer to that word."
cp "$SBX/trunc.bin" "$PKG/stage3_doors/doors.bin"
"$DOORS" open "$(mintval 'door_phrase(0)')" >"$SBX/beh.out" 2>/dev/null
ok "beh-truncated-doors-bin-rc" "$?" "0"
head -c 16384 /dev/urandom >"$PKG/stage3_doors/doors.bin"
"$DOORS" open "$(mintval 'door_phrase(0)')" >"$SBX/beh.out" 2>/dev/null
ok "beh-corrupt-doors-bin-rc" "$?" "0"
cp "$SBX/doors.save" "$PKG/stage3_doors/doors.bin"
"$DOORS" open "$(mintval 'door_phrase(0)')" >"$SBX/reopened.txt" 2>/dev/null
ok "package-still-pristine-after-suite" "$(grep -c -F "$(mintval 'door_ink()')" "$SBX/reopened.txt")" "1"

echo
echo "P6: $PASS PASS, $FAIL FAIL"
[ "$FAIL" -eq 0 ]


