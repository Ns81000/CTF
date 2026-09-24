#!/usr/bin/env bash
# P7 suite - the Mirror Room / Duplicate Survey (spec 4.6).  Prints PASS/FAIL.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
RUNS="$ROOT/organizer-private/runs"
SBX="$(mktemp -d /tmp/p7sbx.XXXXXX)"
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

mkdir -p "$PKG/mirror"
cd "$HERE"
echo "=== generate the Duplicate Survey (consts + fiction) ==="
python3 gen_mirror.py "$PKG" >"$SBX/gen.log" 2>&1
okf "gen-mirror" $?
okn "mirror-consts-written" "$(wc -l < mirror_consts.h)" 8
TITLE="$(sed -n 's/^dead-end title accepted by mirror_validate = //p' "$RUNS/mirror_chain.txt")"
[ -n "$TITLE" ] || TITLE="$(sed -n 's/^filed title: //p' "$RUNS/p7_mirror_gen.txt")"
okn "mirror-title-harvested" "${#TITLE}" 20
python3 - "$TITLE" <<'PYEOF'
import hashlib, re, sys
digest = hashlib.sha256(sys.argv[1].encode()).digest()
body = open("mirror_consts.h").read().split("MIRROR_TITLE_DIGEST")[1]
got = bytes(int(v, 16) for v in re.findall(r"0x([0-9a-f]{2})", body))
sys.exit(0 if got == digest else 1)
PYEOF
okf "consts-digest-matches-harvested-title" $?
ok "fiction-folios" "$(ls "$PKG/mirror"/*.txt | wc -l)" "6"
okn "fiction-dated-1981" "$(grep -o -F '1981' "$PKG/mirror"/*.txt | wc -l)" 6
ok "fiction-cites-phantom-plates" \
  "$(grep -o -E 'plate_[0-9]{3}' "$PKG/mirror"/*.txt | wc -l)" \
  "$(grep -o -E 'plate_[0-9]{3}' "$PKG/mirror"/*.txt | sort -u | wc -l)"
ok "fiction-no-verdict-words" \
  "$(grep -o -i -E 'correct|valid|right|wrong' "$PKG/mirror"/*.txt | wc -l)" "0"
ok "fiction-no-mechanism-words" \
  "$(grep -o -i -E 'sha-?256|xor|cipher|feistel|hmac|checksum' "$PKG/mirror"/*.txt | wc -l)" "0"

echo
echo "=== build hygiene: the mirror tools use the same recipe ==="
for tool in mirror_milestone mirror_validate; do
  musl-gcc $CF -o "$PKG/mirror/$tool" "$tool.c" ../chain/chain.c \
      ../core/carto_sha256.c ../core/sha256ctr.c 2>"$SBX/$tool.log"
  okf "$tool-build" $?
  ok "$tool-no-warnings" "$(stat -c%s "$SBX/$tool.log")" "0"
  file "$PKG/mirror/$tool" | grep -q "statically linked"
  okf "$tool-static" $?
  nm "$PKG/mirror/$tool" 2>&1 | grep -q "no symbols"
  okf "$tool-nm-empty" $?
  musl-gcc $CF -o "$SBX/$tool.2" "$tool.c" ../chain/chain.c \
      ../core/carto_sha256.c ../core/sha256ctr.c 2>/dev/null
  cmp -s "$PKG/mirror/$tool" "$SBX/$tool.2"
  okf "$tool-rebuild-deterministic" $?
  strings -n 5 "$PKG/mirror/$tool" | grep -qE 'gcc|clang|musl|/home/|ns8pc'
  ok "$tool-no-toolchain-strings" "$?" "1"
  okn "$tool-carries-canary" \
    "$(count_of "$(mintval 'canary_token()')" "$PKG/mirror/$tool")" 1
done


echo
echo "=== scripted FULL mirror solve (reduced-T build; production run deferred) ==="
# a self-contained tree so the tools' relative includes resolve: d/mirror
# holds the sources + the reduced header, d/core and d/chain are symlinks
D="$SBX/d"
mkdir -p "$D/mirror"
ln -sfn "$ROOT/src/core" "$D/core"
ln -sfn "$ROOT/src/chain" "$D/chain"
cp "$HERE/mirror_milestone.c" "$HERE/mirror_validate.c" "$D/mirror/"
python3 "$HERE/reduced_consts.py" "$D/mirror/mirror_consts.h" 20000 \
    "$(mintval 'mirror_milestone_token()')" >/dev/null 2>&1
okf "reduced-consts-written" $?
( cd "$D/mirror" && musl-gcc -O2 -static -s -std=gnu11 -D_GNU_SOURCE \
     -o "$SBX/mirror_milestone" mirror_milestone.c ../chain/chain.c \
     ../core/carto_sha256.c ../core/sha256ctr.c 2>"$SBX/red.log" )
okf "reduced-milestone-built" $?
( cd "$D/mirror" && musl-gcc -O2 -static -s -std=gnu11 -D_GNU_SOURCE \
     -o "$SBX/mirror_validate" mirror_validate.c ../core/carto_sha256.c \
     ../core/sha256ctr.c 2>>"$SBX/red.log" )
okf "reduced-validator-built" $?
"$SBX/mirror_milestone" >"$SBX/mark.txt" 2>"$SBX/mark.err"
okf "solve-1-marker-rc" $?
ok "solve-1-stderr-silent" "$(stat -c%s "$SBX/mark.err")" "0"
okn "solve-1-has-mark" \
  "$(grep -c -F "$(mintval 'mirror_milestone_token()')" "$SBX/mark.txt")" 1
"$SBX/mirror_milestone" walk >"$SBX/walk.txt" 2>"$SBX/walk.err"
okf "solve-2-walk-rc" $?
ok "solve-2-stderr-silent" "$(stat -c%s "$SBX/walk.err")" "0"
ok "solve-2-record-64-hex" \
  "$(sed -n 's/^duplicate stitch record: //p' "$SBX/walk.txt" | head -1 | wc -c)" "65"
okn "solve-2-mark-format" \
  "$(grep -c -E '^duplicate pass mark: PRAMBH\{[0-9a-f]{16}\}$' "$SBX/walk.txt")" 1
SECOND="$(sed -n 's/^duplicate stitch record: //p' "$SBX/walk.txt" | head -1)"
"$SBX/mirror_milestone" seal "$SECOND" >"$SBX/seal.txt" 2>"$SBX/seal.err"
okf "solve-3-seal-rc" $?
ok "solve-3-stderr-silent" "$(stat -c%s "$SBX/seal.err")" "0"
MTITLE="$(grep -o -E 'PRAMBH\{mirror_[0-9a-f]{16}\}' "$SBX/seal.txt" | head -1)"
okn "solve-3-yields-title" "${#MTITLE}" 20
# the reduced walk's title is a different byte string than the production
# one, so the validator for this lane is rebuilt against the reduced
# title's own digest (the production digest is checked above)
python3 "$HERE/reduced_consts.py" "$D/mirror/mirror_consts.h" 20000 \
    "$(mintval 'mirror_milestone_token()')" "$MTITLE" >/dev/null 2>&1
okf "reduced-digest-written" $?
( cd "$D/mirror" && musl-gcc -O2 -static -s -std=gnu11 -D_GNU_SOURCE \
     -o "$SBX/mirror_validate" mirror_validate.c ../core/carto_sha256.c \
     ../core/sha256ctr.c 2>>"$SBX/red.log" )
okf "reduced-validator-rebuilt" $?
"$SBX/mirror_validate" "$MTITLE" >"$SBX/valid.txt" 2>"$SBX/valid.err"
okf "solve-4-validate-rc" $?
ok "solve-4-stderr-silent" "$(stat -c%s "$SBX/valid.err")" "0"
ok "solve-4-dead-end-line" "$(cat "$SBX/valid.txt")" \
  "the duplicate survey is filed."
"$SBX/mirror_validate" "PRAMBH{anything_else}" >"$SBX/refuse.txt" 2>/dev/null
ok "validate-refuses-others" "$(cat "$SBX/refuse.txt")" \
  "the depot holds no such record."
"$SBX/mirror_validate" >"$SBX/refuse2.txt" 2>/dev/null
ok "validate-noargs-rc" "$?" "0"
okn "validate-noargs-usage" "$(grep -c -F 'depot desk' "$SBX/refuse2.txt")" 1
ok "mirror-tools-ignore-real-state" "$(ls "$PKG" | grep -c 'prambh.survey')" "0"

echo
echo "=== leak lanes: zero real values in mirror/ ==="
LEAK=0
for v in "$TITLE" "$(mintval 'door_ink()')" \
         "$(mintval 'chain2_vector().hex()')" "$(mintval 'stage0_token()')" \
         "$(mintval 'capsule_content().hex()')" "$(mintval 'real_phrase()')" \
         "$(mintval 'loom_seed_material(mint.capsule_content()).hex()')" \
         "$(mintval 'eyes_code(0)')"; do
  for f in "$PKG/mirror"/*; do
    [ "$(count_of "$v" "$f")" -eq 0 ] || LEAK=$((LEAK + 1))
  done
done
ok "mirror-clean-of-real-values" "$LEAK" "0"
okn "mirror-token-registered" \
  "$(grep -c -F "$(mintval 'mirror_milestone_token()')" "$ROOT/organizer-private/TRAP_CATALOGUE.md")" 1

echo
echo "=== behaviour probe (rc 0, silent stderr) ==="
beh() {
  local label="$1"; shift
  timeout 30 "$@" >"$SBX/beh.out" 2>"$SBX/beh.err"
  ok "$label-rc" "$?" "0"
  ok "$label-stderr-silent" "$(stat -c%s "$SBX/beh.err")" "0"
}
yes a | head -c 200000 >"$SBX/big.txt"
beh "beh-milestone-noargs" "$SBX/mirror_milestone"
beh "beh-milestone-unknown" "$SBX/mirror_milestone" frobnicate
beh "beh-milestone-seal-garbage" "$SBX/mirror_milestone" seal zz
beh "beh-milestone-seal-short" "$SBX/mirror_milestone" seal abcd
beh "beh-validate-200kb" "$SBX/mirror_validate" "$(head -c 20000 "$SBX/big.txt")"
beh "beh-validate-empty" "$SBX/mirror_validate" ""
beh "beh-narrow-columns" env COLUMNS=20 "$SBX/mirror_milestone"
beh "beh-term-dumb" env TERM=dumb "$SBX/mirror_validate" x
"$SBX/mirror_milestone" </dev/null >"$SBX/beh.out" 2>"$SBX/beh.err"
ok "beh-devnull-rc" "$?" "0"
ok "beh-devnull-stderr-silent" "$(stat -c%s "$SBX/beh.err")" "0"
printf 'junk\n' | "$SBX/mirror_validate" x >"$SBX/beh.out" 2>"$SBX/beh.err"
ok "beh-piped-stdin-rc" "$?" "0"
ok "beh-piped-stdin-stderr-silent" "$(stat -c%s "$SBX/beh.err")" "0"

echo
echo "P7: $PASS PASS, $FAIL FAIL"
[ "$FAIL" -eq 0 ]
