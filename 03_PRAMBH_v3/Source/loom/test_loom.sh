#!/usr/bin/env bash
# P5 suite - MERU-8 loom emulator, real + decoy cartridges, diagnostic lane,
# decoy registry and the reduced-T wall-clock projection (spec 4.4 / 6 P5 /
# Appendix C.2).  Prints PASS/FAIL lines and a final count.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
SBX="$(mktemp -d /tmp/p5sbx.XXXXXX)"
trap 'chmod -R u+w "$SBX" 2>/dev/null; rm -rf "$SBX"' EXIT
PASS=0; FAIL=0

ok() { # ok <label> <actual> <expected>
  if [ "$2" = "$3" ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1 (got [$2] want [$3])"; FAIL=$((FAIL+1)); fi
}
okf() { # okf <label> <rc>
  if [ "${2:-1}" -eq 0 ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1"; FAIL=$((FAIL+1)); fi
}
okn() { # okn <label> <value> <min>   -- value >= min
  if [ "${2:-0}" -ge "$3" ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1 (got [$2] want >= $3)"; FAIL=$((FAIL+1)); fi
}

mintval() { python3 -c "
import sys; sys.path.insert(0, '$ROOT/src/gen'); import mint
print(eval(sys.argv[1], vars(mint)))" "$1"; }

PARAMS="$ROOT/src/chain/chain_params.json"
prod() { python3 -c "
import json
p = json.load(open('$PARAMS'))
print(p['budgets']['chain1']['T'] if '$1' == 'T' else p['table_bytes'])" ; }

echo "=== build hygiene (spec 4.4: musl-static, stripped, nm empty) ==="
cd "$HERE"
python3 gen_rom.py "$SBX/prod" >"$SBX/genrom.log" 2>&1
okf "gen-rom-production" $?

okn "prod-rom-size" "$(stat -c%s "$SBX/prod/loom.rom")" 300
okn "decoy-rom-count" "$(ls "$SBX/prod/roms" | wc -l)" 3

# regeneration must not change the committed production header or the ROMs
python3 gen_rom.py "$SBX/prod2" >/dev/null 2>&1
cmp -s "$SBX/prod/loom.rom" "$SBX/prod2/loom.rom"
okf "rom-regeneration-deterministic" $?
for r in tide_merc6 star_merc3 grav_merc9; do
  cmp -s "$SBX/prod/roms/$r.rom" "$SBX/prod2/roms/$r.rom"
  okf "decoy-rom-deterministic-$r" $?
done
git -C "$ROOT" diff --quiet -- src/loom/params.h src/loom/debug_rom.h
okf "generated-headers-in-tree" $?

ok "params-T-matches-chain_params" \
  "$(grep -o 'PRAMBH_CHAIN_T_DEFAULT [0-9]*ull' params.h | grep -o '[0-9]*')" "$(prod T)"
ok "params-S-matches-chain_params" \
  "$(grep -o 'PRAMBH_CHAIN_S_DEFAULT [0-9]*u' params.h | grep -o '[0-9]*')" "$(prod S)"
ok "params-T-is-production-not-test" "$(prod T)" "7705630875"

LOOM="$SBX/loom"
musl-gcc -O2 -static -s -o "$LOOM" loom.c meru1.c ../chain/chain.c \
    ../core/carto_sha256.c ../core/sha256ctr.c 2>"$SBX/build.log"
okf "build" $?
file "$LOOM" | grep -q "statically linked"
okf "binary-static" $?
nm "$LOOM" 2>&1 | grep -q "no symbols"
okf "binary-nm-empty" $?
readelf -S "$LOOM" | grep -q "\.symtab"
ok "binary-stripped" "$?" "1"
musl-gcc -O2 -static -s -o "$SBX/loom2" loom.c meru1.c ../chain/chain.c \
    ../core/carto_sha256.c ../core/sha256ctr.c 2>/dev/null
cmp -s "$LOOM" "$SBX/loom2"
okf "binary-rebuild-deterministic" $?
strings -n 5 "$LOOM" | grep -qE 'gcc|clang|musl|/home/|ns8pc'
ok "binary-no-toolchain-strings" "$?" "1"
ok "binary-notice-present" \
  "$(strings -n 5 "$LOOM" | grep -c 'Trust timestamps, not moods')" "1"

echo
echo "=== datasheet (spec 4.4: field-notes/meru1_datasheet.txt) ==="
python3 gen_datasheet.py "$SBX/meru1_datasheet.txt" >"$SBX/ds.log" 2>&1
okf "datasheet-generated" $?
okn "datasheet-size" "$(stat -c%s "$SBX/meru1_datasheet.txt")" 2000
python3 gen_datasheet.py "$SBX/meru1_datasheet2.txt" >/dev/null 2>&1
cmp -s "$SBX/meru1_datasheet.txt" "$SBX/meru1_datasheet2.txt"
okf "datasheet-deterministic" $?
OPS_N="$(python3 -c "
import sys; sys.path.insert(0, '$HERE')
from opcodes import OPS
print(len(OPS))")"
okn "loom-documents-at-least-60-opcodes" "$OPS_N" 60
ok "datasheet-documents-all-opcodes" \
  "$(awk '/6\.  INSTRUCTION SET/,/Operation summaries/' \
      "$SBX/meru1_datasheet.txt" | grep -cE '^  \$[0-9A-F]{2}   ')" "$OPS_N"
ok "datasheet-opcode-count-generated" \
  "$(grep -o 'INSTRUCTION SET ([0-9]* operations)' "$SBX/meru1_datasheet.txt" \
      | grep -o '[0-9]*')" "$OPS_N"
grep -q "MERU-8 SURVEY LOOM" "$SBX/meru1_datasheet.txt"
okf "datasheet-model-name" $?
ok "datasheet-filename-in-core-comment" \
  "$(grep -o 'field-notes/meru1_datasheet.txt' meru1.h loom.c | wc -l)" "2"
ok "datasheet-stale-name-gone" "$(grep -o 'meru8_datasheet' loom.c meru1.h | wc -l)" "0"
ok "datasheet-no-real-values" \
  "$(grep -c -e "$(mintval 'stage0_token()')" -e "$(mintval 'canary_token()')" \
      -e "$(mintval 'capsule_content().hex()')" "$SBX/meru1_datasheet.txt")" "0"
okn "datasheet-rom-limit" \
  "$(grep -c '28672' "$SBX/meru1_datasheet.txt")" 1

echo
echo "=== selftest cartridge: C emulator vs Python model (all 64 opcodes) ==="
python3 selftest.py "$SBX/selftest.rom" 2>"$SBX/st.log"
okf "selftest-assembled" $?
"$LOOM" run "$SBX/selftest.rom" >"$SBX/st.c" 2>"$SBX/st.c.err"
okf "selftest-c-rc" $?
ok "selftest-c-stderr-silent" "$(stat -c%s "$SBX/st.c.err")" "0"
python3 model_loom.py "$SBX/selftest.rom" >"$SBX/st.py" 2>"$SBX/st.py.err"
okf "selftest-model-rc" $?
cmp -s "$SBX/st.c" "$SBX/st.py"
okf "selftest-c-vs-python-bit-equality" $?
ok "selftest-dump-lines" "$(wc -l < "$SBX/st.c")" "7"
grep -q "MERU-8 SELFTEST" "$SBX/st.c"
okf "selftest-banner" $?

echo
echo "=== real cartridge vs native walk (reduced T, Appendix C.2) ==="
RT=20000; RS=65536
python3 gen_rom.py "$SBX/test" --T $RT --S $RS --decoy-T 3000 --no-params \
    >"$SBX/genrom2.log" 2>&1
okf "gen-rom-reduced" $?
ok "no-params-kept-production-header" \
  "$(grep -o 'PRAMBH_CHAIN_T_DEFAULT [0-9]*ull' params.h | grep -o '[0-9]*')" "$(prod T)"

VEC="$(mintval 'capsule_content().hex()')"
"$LOOM" claim "$SBX/test/loom.rom" --vector "$VEC" >"$SBX/real.c" 2>"$SBX/real.c.err"
okf "real-claim-rc" $?
ok "real-claim-stderr-silent" "$(stat -c%s "$SBX/real.c.err")" "0"
CLAIM="$(tail -1 "$SBX/real.c")"
ok "real-claim-hex-length" "${#CLAIM}" "64"
echo "$CLAIM" | grep -qE '^[0-9a-f]{64}$'
okf "real-claim-hex-format" $?
grep -qE '^chain checkpoint token: PRAMBH\{[0-9a-f]{16}\}$' "$SBX/real.c"
okf "real-token-format" $?
python3 model_loom.py "$SBX/test/loom.rom" "$VEC" >"$SBX/real.py" 2>/dev/null
"$LOOM" run "$SBX/test/loom.rom" --vector "$VEC" >"$SBX/real.run" 2>/dev/null
cmp -s "$SBX/real.run" "$SBX/real.py"
okf "real-c-vs-python-bit-equality" $?
"$LOOM" claim "$SBX/test/loom.rom" --vector "$VEC" >"$SBX/real.c2" 2>/dev/null
cmp -s "$SBX/real.c" "$SBX/real.c2"
okf "real-two-run-determinism" $?

"$LOOM" verify --vector "$VEC" --T $RT --S $RS >"$SBX/verify.txt" 2>"$SBX/verify.err"
okf "verify-rc" $?
ok "verify-stderr-silent" "$(stat -c%s "$SBX/verify.err")" "0"
INK="$(grep 'loom ink' "$SBX/verify.txt" | awk '{print $4}')"
ok "verify-ink-8-bytes" "${#INK}" "16"
ok "verify-ink-is-claim-head" "$INK" "${CLAIM:0:16}"
ok "verify-checkpoint-is-claim-window" \
  "$(grep 'checkpoint' "$SBX/verify.txt" | awk '{print $3}')" "PRAMBH{${CLAIM:16:16}}"
"$LOOM" verify --vector "$(python3 -c 'print("11" * 32)')" --T $RT --S $RS \
  | grep -q "PRAMBH{${CLAIM:16:16}}"
ok "verify-other-vector-differs" "$?" "1"
"$LOOM" verify --vector "$VEC" --T $((RT * 2)) --S $RS \
  | grep -q "PRAMBH{${CLAIM:16:16}}"
ok "verify-other-T-differs" "$?" "1"
"$LOOM" run "$SBX/test/loom.rom" >"$SBX/real.zero" 2>/dev/null
python3 model_loom.py "$SBX/test/loom.rom" >"$SBX/real.zero.py" 2>/dev/null
cmp -s "$SBX/real.zero" "$SBX/real.zero.py"
okf "real-zero-vector-parity" $?

echo
echo "=== decoy cartridges (reduced T; production values are registered) ==="
python3 - <<PYEOF >"$SBX/registry.tsv"
import sys
sys.path.insert(0, "$ROOT/src/gen")
import loom_decoys
for rid, rom, key, out, tok, rc in loom_decoys.rows():
    print("\t".join([rid, rom or "-", key, out or "-", tok, rc or "-"]))
PYEOF
didx=0
for r in tide_merc6 star_merc3 grav_merc9; do
  didx=$((didx + 1))
  "$LOOM" claim "$SBX/test/roms/$r.rom" >"$SBX/$r.c" 2>"$SBX/$r.err"
  okf "decoy-$didx-claim-rc" $?
  ok "decoy-$didx-stderr-silent" "$(stat -c%s "$SBX/$r.err")" "0"
  dc="$(tail -1 "$SBX/$r.c")"
  echo "$dc" | grep -qE '^[0-9a-f]{64}$'
  okf "decoy-$didx-claim-hex" $?
  "$LOOM" run "$SBX/test/roms/$r.rom" >"$SBX/$r.run" 2>/dev/null
  python3 model_loom.py "$SBX/test/roms/$r.rom" >"$SBX/$r.py" 2>/dev/null
  cmp -s "$SBX/$r.run" "$SBX/$r.py"
  okf "decoy-$didx-c-vs-python" $?
  ok "decoy-$didx-differs-from-real" "$(echo "$dc" | grep -c -F "$CLAIM")" "0"
  key="$(sed -n "${didx}p" "$SBX/registry.tsv" | cut -f3)"
  pan="$(python3 -c "
import sys; sys.path.insert(0, '$ROOT/src/gen'); import loom_decoys
print(loom_decoys.cart_pan($didx - 1))")"
  python3 - "$SBX/test/roms/$r.rom" "$pan" <<'PYEOF'
import sys
rom = open(sys.argv[1], "rb").read()
sys.exit(0 if bytes.fromhex(sys.argv[2]) in rom else 1)
PYEOF
  okf "decoy-$didx-rom-carries-mint-pan" $?
  nw="$(../chain/prambh_chain walk --seed-hex "$key" --s 4194304 --t 3000)"
  ok "decoy-$didx-native-walk-parity" "$nw" "$dc"
done
ok "decoy-tokens-pairwise-distinct" \
  "$(for r in tide_merc6 star_merc3 grav_merc9; do tail -1 "$SBX/$r.c" | cut -c1-16; done | sort -u | wc -l)" "3"


echo
echo "=== diagnostic lane (anti-debug, spec 4.4) ==="
DBG="$(python3 - <<PYEOF
import sys
sys.path.insert(0, "$ROOT/src/gen")
import loom_decoys
print("\t".join(loom_decoys.rows()[3][2:5]))
PYEOF
)"
DBGPAN="$(echo "$DBG" | cut -f1)"
DBGTOK="$(echo "$DBG" | cut -f3)"

strace -f -o "$SBX/strace.log" "$LOOM" run "$SBX/test/loom.rom" \
    >"$SBX/dbg.strace" 2>"$SBX/dbg.strace.err"
okf "strace-lane-rc" $?
ok "strace-lane-stderr-silent" "$(stat -c%s "$SBX/dbg.strace.err")" "0"
grep -q -F "$DBGTOK" "$SBX/dbg.strace"
okf "strace-lane-debug-token" $?
grep -q "not a survey record" "$SBX/dbg.strace"
okf "strace-lane-framing" $?
gdb -batch -ex run --args "$LOOM" run "$SBX/test/loom.rom" \
    >"$SBX/dbg.gdb" 2>/dev/null
okf "gdb-lane-rc" $?
grep -q -F "$DBGTOK" "$SBX/dbg.gdb"
okf "gdb-lane-debug-token" $?
ok "clean-run-hides-debug-token" "$(grep -c -F "$DBGTOK" "$SBX/real.c")" "0"
python3 -c "
import sys; sys.path.insert(0, '$ROOT/src/gen'); import loom_decoys
sys.exit(0 if loom_decoys.debug_token_from_pan('$DBGPAN') == '$DBGTOK' else 1)"
okf "debug-token-rederived-from-pan" $?
grep -q '/proc/self/status' loom.c
okf "tracerpid-reads-proc-status" $?
grep -q 'TracerPid:' loom.c
okf "tracerpid-field-parsed" $?

echo
echo "=== decoy registry (harvested once, never recomputed) ==="
ok "registry-row-count" "$(wc -l < "$SBX/registry.tsv")" "4"
ok "registry-ids" \
  "$(cut -f1 "$SBX/registry.tsv" | tr '\n' ',')" "D-ROM-1,D-ROM-2,D-ROM-3,D-DBG,"
k=0
while [ $k -lt 4 ]; do
  k=$((k + 1))
  line="$(sed -n "${k}p" "$SBX/registry.tsv")"
  rid="$(echo "$line" | cut -f1)"
  rom="$(echo "$line" | cut -f2)"
  key="$(echo "$line" | cut -f3)"
  outh="$(echo "$line" | cut -f4)"
  tok="$(echo "$line" | cut -f5)"
  ok "registry-$rid-token-in-harvest" \
    "$(grep -c -F "$tok" "$ROOT/organizer-private/runs/p5_decoy_tokens.txt")" "1"
  ok "registry-$rid-token-in-catalogue" \
    "$(grep -c -F "$tok" "$ROOT/organizer-private/TRAP_CATALOGUE.md")" "1"
  ok "registry-$rid-token-in-keys" \
    "$(grep -c -F "$tok" "$ROOT/organizer-private/KEYS_PRAMBH.md")" "1"
  ok "registry-$rid-id-in-catalogue" \
    "$(grep -c -F "$rid" "$ROOT/organizer-private/TRAP_CATALOGUE.md")" "1"
  python3 -c "
import sys; sys.path.insert(0, '$ROOT/src/gen'); import loom_decoys
sys.exit(0 if loom_decoys.check_pan('$rid', '$key') else 1)"
  okf "registry-$rid-key-mint-derived" $?
  if [ "$rom" != "-" ]; then
    python3 -c "
import sys; sys.path.insert(0, '$ROOT/src/gen'); import loom_decoys
r = [x for x in loom_decoys.rows() if x[0] == '$rid'][0]
sys.exit(0 if r[3].startswith(r[4][7:-1]) else 1)"
    okf "registry-$rid-token-is-claim-head" $?
  fi
done
git -C "$ROOT" diff --quiet -- organizer-private/runs/p5_decoy_tokens.txt
okf "harvest-file-unchanged" $?
ok "registry-tokens-differ-from-real-values" \
  "$(python3 - <<PYEOF
import sys
sys.path.insert(0, "$ROOT/src/gen")
import mint, loom_decoys
real = {mint.stage0_token(), mint.canary_token(), mint.capsule_content().hex(),
        mint.loom_seed_material(mint.capsule_content()).hex(),
        mint.capsule_bin().hex()}
print(sum(1 for r in loom_decoys.rows() if r[4] in real))
PYEOF
)" "0"



echo
echo "=== canary (spec 4.10: on every shipped tool's usage screen) ==="
CANARY="$(mintval 'canary_token()')"
python3 "$ROOT/src/gen/gen_canary.py" >/dev/null 2>&1
okf "canary-header-generated" $?
git -C "$ROOT" diff --quiet -- src/core/canary.h
okf "canary-header-in-tree" $?
ok "canary-header-matches-mint" \
  "$(grep -o -F "$CANARY" "$ROOT/src/core/canary.h" | wc -l)" "1"
"$LOOM" >"$SBX/usage.txt" 2>"$SBX/usage.err"
ok "usage-screen-rc" "$?" "0"
ok "canary-on-usage-screen" "$(grep -c -F "$CANARY" "$SBX/usage.txt")" "1"
ok "notice-on-usage-screen" \
  "$(grep -c -F 'Trust timestamps, not moods' "$SBX/usage.txt")" "1"
ok "usage-screen-stderr-silent" "$(stat -c%s "$SBX/usage.err")" "0"

echo
echo "=== leak / hygiene greps (spec 4.4) ==="
count_of() { grep -o -a -F "$1" "$2" | wc -l; }
ok "loom-hides-capsule-content" \
  "$(count_of "$(mintval 'capsule_content().hex()')" "$LOOM")" "0"
ok "loom-hides-chain-seed" \
  "$(count_of "$(mintval 'loom_seed_material(capsule_content()).hex()')" "$LOOM")" "0"
ok "loom-hides-stage0-token" \
  "$(count_of "$(mintval 'stage0_token()')" "$LOOM")" "0"
lw=0
for w in $(mintval 'launch_phrase()'); do
  grep -a -q -F "$w" "$LOOM" && lw=$((lw + 1))
done
ok "loom-hides-launch-words" "$lw" "0"
okn "loom-prints-canary-notice" "$(count_of "$(mintval 'canary_token()')" "$LOOM")" 1
for lbl in prambh:doors prambh:mirror prambh:eyes prambh:final prambh:capsule; do
  ok "loom-hides-later-label-${lbl#prambh:}" "$(count_of "$lbl" "$LOOM")" "0"
done
ok "real-rom-hides-real-values" \
  "$(count_of "$(mintval 'capsule_content().hex()')" "$SBX/prod/loom.rom")" "0"
i=0
while [ $i -lt 4 ]; do
  i=$((i + 1))
  tok="$(sed -n "${i}p" "$SBX/registry.tsv" | cut -f5)"
  ok "loom-hides-registry-token-$i" "$(count_of "$tok" "$LOOM")" "0"
done
nr=0
for f in "$SBX/prod/loom.rom" "$SBX/prod/roms"/*.rom; do
  for v in "$(mintval 'capsule_content().hex()')" "$(mintval 'stage0_token()')" \
           "$(mintval 'canary_token()')" "$(mintval 'loom_seed_material(capsule_content()).hex()')"; do
    [ "$(count_of "$v" "$f")" -eq 0 ] || nr=$((nr + 1))
  done
done
ok "production-cartridges-hide-real-values" "$nr" "0"

echo
echo "=== behaviour probe (rc 0, silent stderr, no crash) ==="
beh() {
  local label="$1"; shift
  timeout 30 "$@" >"$SBX/beh.out" 2>"$SBX/beh.err"
  ok "$label-rc" "$?" "0"
  ok "$label-stderr-silent" "$(stat -c%s "$SBX/beh.err")" "0"
}
mkdir -p "$SBX/ro"
cp "$LOOM" "$SBX/ro/loom"
cp "$SBX/test/loom.rom" "$SBX/ro/loom.rom"
chmod 555 "$SBX/ro"
head -c 200000 /dev/urandom >"$SBX/big.bin"
head -c 16 "$SBX/test/loom.rom" >"$SBX/trunc.rom"
head -c 8000 /dev/zero >"$SBX/oversize.rom"
beh "beh-noargs" "$LOOM"
beh "beh-unknown-subcommand" "$LOOM" frobnicate
beh "beh-empty-arg" "$LOOM" run ""
beh "beh-missing-rom" "$LOOM" run "$SBX/nope.rom"
beh "beh-dir-as-rom" "$LOOM" run "$SBX/prod"
beh "beh-truncated-rom" "$LOOM" run "$SBX/trunc.rom"
beh "beh-oversize-rom" "$LOOM" run "$SBX/oversize.rom"
beh "beh-200kb-arg" "$LOOM" run "$SBX/big.bin"
beh "beh-16-extra-args" "$LOOM" run "$SBX/test/loom.rom" a b c d e f g h \
    i j k l m n o p
beh "beh-bad-vector" "$LOOM" run "$SBX/test/loom.rom" --vector zz
beh "beh-verify-garbage-flags" "$LOOM" verify --T notanumber --S notanumber
beh "beh-narrow-columns" env COLUMNS=20 "$LOOM"
beh "beh-term-dumb" env TERM=dumb "$LOOM" verify --vector "$VEC" --T 1000 --S 1024
( cd "$SBX/ro" && ./loom run loom.rom ) >"$SBX/beh.out" 2>"$SBX/beh.err"
ok "beh-readonly-dir-rc" "$?" "0"
ok "beh-readonly-dir-stderr-silent" "$(stat -c%s "$SBX/beh.err")" "0"
printf 'garbage\n' | "$LOOM" verify --vector "$VEC" --T 1000 --S 1024 \
    >"$SBX/beh.out" 2>"$SBX/beh.err"
ok "beh-piped-stdin-rc" "$?" "0"
ok "beh-piped-stdin-stderr-silent" "$(stat -c%s "$SBX/beh.err")" "0"
"$LOOM" verify --vector "$VEC" --T 1000 --S 1024 </dev/null \
    >"$SBX/beh.out" 2>"$SBX/beh.err"
ok "beh-devnull-stdin-rc" "$?" "0"
ok "beh-devnull-stdin-stderr-silent" "$(stat -c%s "$SBX/beh.err")" "0"

echo
echo "=== organizer chain tool: in-tree binary matches its source ==="
( cd ../chain && musl-gcc -O2 -static -s -Wall -Wextra -std=gnu11 -D_GNU_SOURCE \
    -o "$SBX/prambh_chain" prambh_chain.c chain.c ../core/carto_sha256.c \
    ../core/sha256ctr.c 2>"$SBX/chainbuild.log" )
okf "chain-tool-fresh-build" $?
cmp -s "$SBX/prambh_chain" ../chain/prambh_chain
okf "chain-tool-in-tree-matches-source" $?

echo
echo "=== reduced-T wall-clock PROJECTION (Appendix C.2; NOT the REAL run) ==="
python3 project_wallclock.py --loom "$LOOM" >"$SBX/proj.txt" 2>&1
okf "projection-script" $?
tail -24 "$SBX/proj.txt"
grep -q "PASS native-per-step-linear" "$SBX/proj.txt"
okf "proj-per-step-linear" $?
grep -q "PASS regression-vs-walkonly" "$SBX/proj.txt"
okf "proj-walkonly-agrees" $?
grep -q "PASS rom-vs-native-parity" "$SBX/proj.txt"
okf "proj-rom-vs-native-parity" $?
grep -q "PASS emulation-slower-than-native" "$SBX/proj.txt"
okf "proj-emulation-slower" $?
grep -q "PASS memory-vs-work-split" "$SBX/proj.txt"
okf "proj-latency-split-measured" $?
if grep -q "PASS projected-in-target-band" "$SBX/proj.txt"; then
  echo "PASS proj-projection-in-band"; PASS=$((PASS+1))
elif grep -q "NOTE contended measurement" "$SBX/proj.txt"; then
  echo "NOTE proj-projection-in-band deferred: machine contended at measurement"
  echo "     (the idle re-run owns the band check; the number stays PROJECTED)"
else
  echo "FAIL proj-projection-in-band"; FAIL=$((FAIL+1))
fi
test -s "$ROOT/organizer-private/runs/p5_projection.txt"
okf "proj-report-written" $?
test -s "$ROOT/organizer-private/runs/p5_projection.json"
okf "proj-json-written" $?
python3 -c "
import json
d = json.load(open('$ROOT/organizer-private/runs/p5_projection.json'))
assert d['linearity_deviation'] < 0.30, d['linearity_deviation']
assert d['emu_step_ns'] > d['native_step_ns']
assert d['native_prod_s'] > 0 and d['emu_prod_s'] > d['native_prod_s']
assert len(d['samples']) == 6"
okf "proj-json-consistent" $?
grep -q "PROJECTED" "$ROOT/organizer-private/runs/p5_projection.txt"
okf "proj-numbers-marked-projected" $?

echo
echo "P5: $PASS PASS, $FAIL FAIL"
echo "(deferred to the audit session per Appendix C.2a: the full REAL-T emulated"
echo " cartridge run and the full REAL-T native walk - see HANDOFF.md)"
[ "$FAIL" -eq 0 ]

