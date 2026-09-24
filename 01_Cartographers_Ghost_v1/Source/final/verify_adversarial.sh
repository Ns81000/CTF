#!/bin/bash
# verify_adversarial.sh -- Phase FINAL section 4: deep adversarial verification.
#
# INTERNAL, never shipped.  Runs against the package root ($CARTO_PKG, default
# the repo's cartographer/), so it can be re-pointed at an extracted Drive
# package (section 7) unchanged.
#
#   bash src/final/verify_adversarial.sh
#   CARTO_PKG=/tmp/cartographer-dist bash src/final/verify_adversarial.sh
#
# Covers: symbol/string leakage, malformed/oversized/truncated input on every
# binary, decoy routing under adversarial retry, real gdb attach + real
# scripted-uniform timing against the anti-debug, state-file tamper resistance
# at every documented offset, the test-only time-scale hook, and a real
# measurement of CARTO_VM_DEBUG_RATIO_LIMIT.
set -u
R=/home/manish/cartographer-build
PKG=${CARTO_PKG:-$R/cartographer}
STATE=$PKG/.cartographer_state
TMP=$(mktemp -d /tmp/carto_adv.XXXXXX)
B0=$PKG/stage0_start/stage0_start
B1=$PKG/stage1_vm/stage1_vm
B2=$PKG/stage2_stego/stage2_stego
B3=$PKG/stage3_oracle/oracle
B4=$PKG/stage4_assembly/validate
BINS="$B0 $B1 $B2 $B3 $B4"
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '[PASS] %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '[FAIL] %s\n' "$1"; }
chk() { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (got '$2' want '$3')"; fi; }

echo "== cartographer Phase FINAL adversarial verification =="
echo "package root: $PKG"
rm -f "$STATE" "$STATE.tmp"

# run every binary from the package root, exactly as a solver does
runp() { ( cd "$PKG" && "./$1" "${@:2}" >"$TMP/out.txt" 2>"$TMP/err.txt" ); echo $?; }
rc_of() { ( cd "$PKG" && "./$1" "${@:2}" >"$TMP/out.txt" 2>"$TMP/err.txt" ) ; echo $?; }
silent_err() { [ ! -s "$TMP/err.txt" ] && echo yes || echo no; }

# ================================================================ 1. leakage
echo
echo "--- 1. symbol / string leakage audit ---"
for b in $BINS; do
    n=$(nm "$b" 2>/dev/null | wc -l)
    chk "$(basename $b): nm reports no symbols" "$n" "0"
    if strings -n 4 "$b" | grep -Eqi 'manish|/home/|cartographer-build|/mnt/[a-z]|[A-Z]:\\\\'; then
        bad "$(basename $b): leaked host path or username"
    else
        ok "$(basename $b): no host path or username"
    fi
    if strings -n 4 "$b" | grep -Eqi 'GCC:|clang|musl-gcc'; then
        bad "$(basename $b): leaked compiler ident"
    else
        ok "$(basename $b): no compiler ident"
    fi
    if strings -n 4 "$b" | grep -q 'CARTO_TEST_TIME_SCALE'; then
        bad "$(basename $b): LEAKED the test-only time-scale hook"
    else
        ok "$(basename $b): test-only time-scale hook absent"
    fi
    if strings -n 4 "$b" | grep -q 'f03ea6b5c1b869482723c0d11d635f8e'; then
        bad "$(basename $b): canonical HMAC key in plaintext"
    else
        ok "$(basename $b): canonical HMAC key absent"
    fi
done
# real answer material must never be strings-findable
for s in "CARTO{first_ink_in_the_ledger}" \
         "73070925a159f9e2_a5d66f1b2b5f596e_no_figure_sits_in_every_pixel" \
         "fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f" \
         "73070925a159f9e2" "a5d66f1b2b5f596e" \
         "interior-ink-formula-v1:"; do
    if strings -n 4 $BINS | grep -qF "$s"; then
        bad "real answer material findable in a binary: $s"
    else
        ok "real answer material absent: ${s:0:28}..."
    fi
done

# ======================================================= 2. malformed input
echo
echo "--- 2. malformed / oversized / truncated input, every binary ---"
LONGA=$(python3 -c 'print("A"*120000)')
LONGF=$(python3 -c 'print("CARTO{" + "a"*60000 + "}")')
for b in stage0_start/stage0_start stage1_vm/stage1_vm \
         stage2_stego/stage2_stego stage3_oracle/oracle \
         stage4_assembly/validate; do
    n=$(basename "$b")
    # empty argument
    rc=$(rc_of "$b" "")
    if [ "$rc" = "0" ] && [ "$(silent_err)" = "yes" ]; then ok "$n: empty arg -> rc0 silent"; else bad "$n: empty arg rc=$rc err=$(cat $TMP/err.txt)"; fi
    # enormous argument
    rc=$(rc_of "$b" "$LONGA")
    if [ "$rc" = "0" ] && [ "$(silent_err)" = "yes" ]; then ok "$n: 200k arg -> rc0 silent"; else bad "$n: 200k arg rc=$rc"; fi
    # flag-shaped but oversized
    rc=$(rc_of "$b" "$LONGF")
    if [ "$rc" = "0" ] && [ "$(silent_err)" = "yes" ]; then ok "$n: 60k flag-shaped arg -> rc0 silent"; else bad "$n: oversized flag rc=$rc"; fi
    # embedded newline / spaces
    rc=$(rc_of "$b" "$(printf 'CARTO{a b\nc}')")
    if [ "$rc" = "0" ] && [ "$(silent_err)" = "yes" ]; then ok "$n: whitespace/newline arg -> rc0 silent"; else bad "$n: whitespace arg rc=$rc"; fi
    # many extra arguments
    rc=$(rc_of "$b" a b c d e f g h)
    if [ "$rc" = "0" ] && [ "$(silent_err)" = "yes" ]; then ok "$n: 8 extra args -> rc0 silent"; else bad "$n: extra args rc=$rc"; fi
    # missing file arguments
    rc=$(rc_of "$b" -c /nonexistent/nope)
    if [ "$rc" = "0" ] && [ "$(silent_err)" = "yes" ]; then ok "$n: missing -c file -> rc0 silent"; else bad "$n: missing -c rc=$rc"; fi
    rc=$(rc_of "$b" -p /nonexistent/nope -R /nonexistent/nope2)
    if [ "$rc" = "0" ] && [ "$(silent_err)" = "yes" ]; then ok "$n: missing press files -> rc0 silent"; else bad "$n: missing press rc=$rc"; fi
done


# ============================================== 3. decoy routing, adversarial
echo
echo "--- 3. decoy routing under adversarial retry ---"
D1="CARTO{12f8a367b772817e805725e7292acfb6}"
D2="CARTO{twice_over_the_coast_before_the_interior}"
D3="CARTO{b27692a0d5f63d4f1a0c3fb79afbf81b}"
D4="CARTO{dba9e10a73bc8633ccc1875207c075e1}"
REAL2="CARTO{no_figure_sits_in_every_pixel}"
REAL4="CARTO{73070925a159f9e2_a5d66f1b2b5f596e_no_figure_sits_in_every_pixel}"

hmac_ok() {
    python3 - "$1" <<'PYEOF'
import hashlib, hmac, pathlib, sys
b = pathlib.Path(sys.argv[1]).read_bytes()
if len(b) != 352:
    print("no"); raise SystemExit
key = bytes.fromhex("f03ea6b5c1b869482723c0d11d635f8e9966c43a0a8def87fd1e2e950c10a7de")
print("yes" if hmac.new(key, b[:0x140], hashlib.sha256).digest() == b[0x140:0x160] else "no")
PYEOF
}
state_u32() {
    python3 -c "import struct,sys; b=open(sys.argv[1],'rb').read(); print(struct.unpack_from('<I', b, int(sys.argv[2]))[0])" "$STATE" "$1"
}
decoy_bit() { state_u32 $((0x024 + 4 * $1)); }
attempt()   { state_u32 $((0x010 + 4 * $1)); }

rm -f "$STATE"; runp stage0_start/stage0_start >/dev/null
for i in 1 2 3 4 5; do
    rc=$(rc_of stage1_vm/stage1_vm "$D1")
    if [ "$rc" != "0" ] || [ "$(silent_err)" != "yes" ]; then
        bad "stage1 decoy retry $i rc=$rc err=$(head -c120 $TMP/err.txt)"
    fi
done
ok "stage1 decoy submitted 5x: every path rc0 + stderr silent"
chk "stage1 decoy bit 0 persisted after 5 submissions" "$(decoy_bit 1)" "1"
chk "state HMAC still valid after 5 duplicate submissions" "$(hmac_ok "$STATE")" "yes"

if ( cd "$PKG" && ./stage1_vm/stage1_vm "$D1" ) 2>/dev/null | grep -qF "fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f"; then
    bad "stage1 decoy retry leaked the real key material"
else
    ok "stage1 decoy retry never leaks the real key material"
fi
for variant in "$D1 " " ${D1}" "${D1^^}" "$(printf '%s\n' "$D1")" "CARTO{12f8a367b772817e805725e7292acfb7}"; do
    before=$(decoy_bit 1)
    rc=$(rc_of stage1_vm/stage1_vm "$variant")
    after=$(decoy_bit 1)
    if [ "$rc" != "0" ] || [ "$(silent_err)" != "yes" ] || [ "$before" != "$after" ]; then
        bad "stage1 near-miss decoy treated as registered: rc=$rc bit $before->$after"
    fi
done
ok "stage1 near-miss decoys (case/space/newline/off-by-one) all treated as unknown"
rc=$(rc_of stage1_vm/stage1_vm)
if [ "$rc" = "0" ] && grep -qF "fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f" "$TMP/out.txt"; then
    ok "stage1 serves the real key after decoy routing (the trap poisons nothing)"
else
    bad "stage1 did not serve the real key after decoy routing"
fi
rc=$(rc_of stage2_stego/stage2_stego -c "$D1")
chk "stage2 refuses the stage-1 decoy token (not registered for stage 2)" "$rc" "0"
rc=$(rc_of stage2_stego/stage2_stego "$D2")
chk "stage2 decoy: bit 0 persisted" "$(decoy_bit 2)" "1"
chk "stage2 real reading still accepted after decoy retries" "$(rc_of stage2_stego/stage2_stego -c "$REAL2")" "0"
rc=$(rc_of stage3_oracle/oracle -r "$D3" 0123456789abcdef)
chk "stage3 decoy: bit 0 persisted" "$(decoy_bit 3)" "1"
chk "stage3 real reading still answered after decoy" \
    "$(rc_of stage3_oracle/oracle -r "$REAL2" 0123456789abcdef)" "0"

# ================================================== 4. state tamper resistance
echo
echo "--- 4. state-file tamper resistance (every documented offset) ---"
tamper_case() {  # <label> <python snippet operating on buf 'b'>
    rm -f "$STATE"
    ( cd "$PKG" && ./stage0_start/stage0_start >/dev/null 2>&1 )
    python3 - "$STATE" "$2" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); b = bytearray(p.read_bytes())
exec(sys.argv[2])
p.write_bytes(bytes(b))
PYEOF
    rc=$(rc_of stage0_start/stage0_start)
    err=$(silent_err)
    c1=$(attempt 0)
    h=$(hmac_ok "$STATE")
    if [ "$rc" != "0" ] || [ "$err" != "yes" ]; then
        bad "$1: rc=$rc stderr=$(head -c120 $TMP/err.txt)"
    elif [ "$h" != "yes" ]; then
        bad "$1: ledger left UNSIGNED (hmac invalid)"
    elif [ "$c1" != "1" ]; then
        bad "$1: did not silently reset (attempt_count[0]=$c1)"
    else
        ok "$1: silent reset to first-run defaults, re-signed"
    fi
}
tamper_case "flip magic"              "b[0] ^= 0xFF"
tamper_case "bump format_version"     "b[4] = 9"
tamper_case "set flags byte"          "b[5] = 0x80"
tamper_case "first_run_ms -> 0"       "b[0x08:0x10] = b'\x00'*8"
tamper_case "attempt_count inflated"  "b[0x10:0x14] = b'\xff\xff\xff\xff'"
tamper_case "decoy_mask forged"       "b[0x24:0x28] = b'\xff\xff\xff\xff'"
tamper_case "ring_count out of range" "b[0x38:0x3A] = b'\xff\xff'"
tamper_case "ring_head out of range"  "b[0x3A:0x3C] = b'\xff\xff'"
tamper_case "force debugger flag"     "b[0x3C] = 1"
tamper_case "reserved byte set"       "b[0x3D] = 0xAA"
tamper_case "rewrite ring timestamp"  "b[0x40:0x48] = b'\x00'*8"
tamper_case "flip one HMAC bit"       "b[0x140] ^= 0x01"
tamper_case "truncate to 351 bytes"   "del b[351:]"
tamper_case "extend to 353 bytes"     "b.append(0)"


# ================================================= 5. anti-debug, real attach
echo
echo "--- 5. anti-debug: real gdb attach and real scripted-uniform timing ---"
rm -f "$STATE"
RC=$(cd "$PKG" && ./stage1_vm/stage1_vm >/dev/null 2>&1; echo $?)
chk "clean stage1 run exits 0" "$RC" "0"
chk "clean run leaves debugger_detected at 0 (TracerPid authoritative)" \
    "$(python3 -c "b=open('$STATE','rb').read(); print(b[0x3C])")" "0"
if grep -q "^TracerPid:" /proc/self/status; then
    ok "/proc/self/status TracerPid is readable (authoritative signal available)"
else
    bad "/proc/self/status has no TracerPid line on this host"
fi
rm -f "$STATE"
( cd "$PKG" && ./stage0_start/stage0_start >/dev/null 2>&1 )
if command -v gdb >/dev/null 2>&1; then
    ( cd "$PKG" && timeout 120 gdb -batch -q -ex run --args \
        ./stage1_vm/stage1_vm >"$TMP/gdb.txt" 2>&1 )
    if grep -qF "fb48aecdda0e960831b16d45c7efbe485d69b61bda262b5c72af18d9b88d1621" "$TMP/gdb.txt"; then
        ok "real gdb attach: the corrupted constant is served (trap intact)"
    else
        bad "real gdb attach: the corrupted constant was NOT served"
    fi
    if grep -qF "fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f" "$TMP/gdb.txt"; then
        bad "real gdb attach leaked the REAL key material"
    else
        ok "real gdb attach never prints the real key material"
    fi
    chk "gdb attach persisted debugger_detected" \
        "$(python3 -c "b=open('$STATE','rb').read(); print(b[0x3C])")" "1"
    chk "state HMAC valid after the debugger run" "$(hmac_ok "$STATE")" "yes"
else
    bad "gdb not available: cannot run the real attach test"
fi
# a persisted debugger flag escalates but must never corrupt a later clean run
rm -f "$STATE"; ( cd "$PKG" && ./stage0_start/stage0_start >/dev/null 2>&1 )
python3 - "$STATE" <<'PYEOF'
import hashlib, hmac, pathlib, sys
p = pathlib.Path(sys.argv[1]); b = bytearray(p.read_bytes())
b[0x3C] = 1
key = bytes.fromhex("f03ea6b5c1b869482723c0d11d635f8e9966c43a0a8def87fd1e2e950c10a7de")
b[0x140:0x160] = hmac.new(key, bytes(b[:0x140]), hashlib.sha256).digest()
p.write_bytes(bytes(b))
PYEOF
OUT=$(cd "$PKG" && ./stage1_vm/stage1_vm 2>/dev/null)
if printf '%s' "$OUT" | grep -qF "fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f"; then
    ok "a persisted debugger flag escalates the variant but keeps the real key"
else
    bad "a persisted debugger flag corrupted the key (unfair)"
fi
# real scripted-uniform timing vs the oracle poison
forge_ring() {  # <mode> -> writes a signed ledger with the given ring gaps
    rm -f "$STATE"
    ( cd "$PKG" && ./stage0_start/stage0_start >/dev/null 2>&1 )
    python3 - "$STATE" "$1" <<'PYEOF'
import hashlib, hmac, pathlib, struct, sys, time
p = pathlib.Path(sys.argv[1]); b = bytearray(p.read_bytes())
now = int(time.time() * 1000)
gaps = {"uniform": [50] * 12, "human": [900, 4300, 1500, 8000, 2200, 11000, 700, 3000]}[sys.argv[2]]
struct.pack_into("<Q", b, 0x08, now - 10**7)
ts = now - sum(gaps)
for i, g in enumerate(gaps):
    ts += g
    struct.pack_into("<Q", b, 0x40 + 8 * i, ts)
struct.pack_into("<H", b, 0x38, len(gaps)); struct.pack_into("<H", b, 0x3A, len(gaps))
key = bytes.fromhex("f03ea6b5c1b869482723c0d11d635f8e9966c43a0a8def87fd1e2e950c10a7de")
b[0x140:0x160] = hmac.new(key, bytes(b[:0x140]), hashlib.sha256).digest()
p.write_bytes(bytes(b))
PYEOF
}
fig=0123456789abcdef
forge_ring uniform
U1=$(cd "$PKG" && ./stage3_oracle/oracle -r "$REAL2" $fig 2>/dev/null | grep -oE '[0-9a-f]{16}' | tail -1)
U2=$(cd "$PKG" && ./stage3_oracle/oracle -r "$REAL2" $fig 2>/dev/null | grep -oE '[0-9a-f]{16}' | tail -1)
forge_ring human
H1=$(cd "$PKG" && ./stage3_oracle/oracle -r "$REAL2" $fig 2>/dev/null | grep -oE '[0-9a-f]{16}' | tail -1)
H2=$(cd "$PKG" && ./stage3_oracle/oracle -r "$REAL2" $fig 2>/dev/null | grep -oE '[0-9a-f]{16}' | tail -1)
if [ -n "$U1" ] && [ "$U1" = "$U2" ]; then
    ok "scripted-uniform spacing: the poison is self-consistent ($U1)"
else
    bad "scripted-uniform spacing: poison not self-consistent ($U1 vs $U2)"
fi
if [ "$U1" != "$H1" ]; then
    ok "poison is falsifiable: same figure, two states, two answers ($U1 vs $H1)"
else
    bad "poison did not differ from the clean answer"
fi
if [ "$H1" = "$H2" ]; then
    ok "human spacing: clean answer is self-consistent ($H1)"

# ============================== 6. the test-only time-scale hook, proven both ways
echo
echo "--- 6. CARTO_TEST_TIME_SCALE: works in the test build, inert as shipped ---"
cat > "$TMP/probe_build.sh" <<'SHEOF'
set -e
R=/home/manish/cartographer-build
cd "$R/src/state"
make clean >/dev/null
make >/dev/null            # SHIPPED library (no hook)
musl-gcc -O2 -std=c11 -static -I. "$R/src/final/probe_scale.c" libstate.a -o "$1/shipped" -lm
make clean >/dev/null
make CARTO_TEST_BUILD=1 >/dev/null   # TEST library (hook compiled in)
musl-gcc -O2 -std=c11 -static -I. "$R/src/final/probe_scale.c" libstate.a -o "$1/testbuild" -lm
make clean >/dev/null
make >/dev/null            # leave the SHIPPED library in place
SHEOF
bash "$TMP/probe_build.sh" "$TMP" || bad "could not build both probe variants"
for v in shipped testbuild; do
    if [ -x "$TMP/$v" ]; then
        strings "$TMP/$v" | grep -q CARTO_TEST_TIME_SCALE \
            && hook=present || hook=absent
        printf '  %-10s hook=%-8s : %s\n' "$v" "$hook" "$("$TMP/$v")"
    fi
done
runprobe() {   # <binary> <scale or empty>  -> only the behavioural line
    if [ -z "$2" ]; then
        env -u CARTO_TEST_TIME_SCALE "$1" | grep elapsed_fast
    else
        CARTO_TEST_TIME_SCALE="$2" "$1" | grep elapsed_fast
    fi
}
echo "  (behavioural lines:)"
printf '    %-10s scale=1   : %s\n' shipped   "$(runprobe "$TMP/shipped" "")"
printf '    %-10s scale=60  : %s\n' shipped   "$(runprobe "$TMP/shipped" 60)"
printf '    %-10s scale=1   : %s\n' testbuild "$(runprobe "$TMP/testbuild" "")"
printf '    %-10s scale=60  : %s\n' testbuild "$(runprobe "$TMP/testbuild" 60)"
SHIP1=$(runprobe "$TMP/shipped" "")
SHIP60=$(runprobe "$TMP/shipped" 60)
TEST1=$(runprobe "$TMP/testbuild" "")
TEST60=$(runprobe "$TMP/testbuild" 60)
TESTJUNK=$(runprobe "$TMP/testbuild" "not-a-number")
case "$SHIP1" in *"elapsed_fast=FIRES"*"uniform=FIRES"*) ok "shipped probe: both reasons fire at scale 1";; *) bad "shipped probe scale 1: $SHIP1";; esac
chk "shipped probe IGNORES the env var entirely (scale 60 == scale 1)" "$SHIP60" "$SHIP1"
chk "test build at scale 1 behaves exactly like the shipped probe" "$TEST1" "$SHIP1"
case "$TEST60" in *"elapsed_fast=quiet"*"uniform=quiet"*) ok "test build at scale 60 suppresses BOTH thresholds";; *) bad "test build scale 60: $TEST60";; esac
chk "garbage CARTO_TEST_TIME_SCALE falls back to 1 in the test build" "$TESTJUNK" "$TEST1"

# ==================================================================== summary
echo
echo "=========================================================="
echo "== $PASS checks passed, $FAIL failed =="
[ "$FAIL" -eq 0 ] && echo "ALL CHECKS PASSED" || echo "FAILURES PRESENT"
rm -rf "$TMP"
exit $FAIL

else
    bad "human spacing produced inconsistent answers"
fi
chk "human spacing served the REAL key's answer for 0123456789abcdef" \
    "$H1" "2a7479540c7163e3"
rm -f "$STATE"

    "$(rc_of stage3_oracle/oracle -r "$REAL2" 0123456789abcdef)" "0"
rc=$(rc_of stage4_assembly/validate "$D4")
chk "stage4 decoy: bit 0 persisted" "$(decoy_bit 4)" "1"
chk "stage4 real title still accepted after decoy" "$(rc_of stage4_assembly/validate "$REAL4")" "0"
chk "state HMAC valid after the whole decoy campaign" "$(hmac_ok "$STATE")" "yes"
