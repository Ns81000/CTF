#!/bin/bash
# test_stage1.sh -- Phase 2 end-to-end verification for stage1_vm.
# Internal (not shipped). Runnable verbatim:
#   cd /home/manish/cartographer-build/src/stage1_vm && ./test_stage1.sh
# Requires the built binaries (make / make test) and gdb for the anti-debug
# checks.  State files are verified with an INDEPENDENT python HMAC check
# using the canonical Phase-0 key, never with the C library under test.

set -u

REPO="/home/manish/cartographer-build"
PKG="$REPO/cartographer"
SRC="$REPO/src/stage1_vm"
BIN="$PKG/stage1_vm/stage1_vm"
DBG="$SRC/stage1_vm.dbg"
STATE="$PKG/.cartographer_state"

DECOY_FLAG='CARTO{12f8a367b772817e805725e7292acfb6}'
DECOY_KEY='12f8a367b772817e805725e7292acfb694501c4f16c17ed09d614022e0be7ced'
REAL_KEY='fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f'
DEBUG_KEY='fb48aecdda0e960831b16d45c7efbe485d69b61bda262b5c72af18d9b88d1621'
MODEL_0_KEY=''
MODEL_1_KEY=''
MODEL_D0_KEY=''
MODEL_D1_KEY=''

pass=0
fail=0
ok()  { echo "[PASS] $1"; pass=$((pass+1)); }
bad() { echo "[FAIL] $1"; fail=$((fail+1)); }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

RC=0
run_stage1() {
    ( cd "$PKG" && "$BIN" "$@" >"$TMP/out.txt" 2>"$TMP/err.txt" )
    RC=$?
}

# model <profile> <detect>: echo the python model's KEY=VALUE report.
model() {
    ( cd "$SRC" && python3 model_vm.py --profile "$1" --detect "$2" --emit )
}

# out_field <NAME>: read KEY=... from $TMP/out.txt by parsing the printed
# fields of the binary's own report (independent of the C code path).
parse_out() {
    KEY="$(sed -n 's/^    \([0-9a-f]\{64\}\)$/\1/p' "$TMP/out.txt" | head -1)"
    TOKEN="$(grep -o 'CARTO{[a-z0-9_]\{1,\}}' "$TMP/out.txt" | head -1)"
    VARIANT="$(sed -n 's/^  engine variant : \(.*\)$/\1/p' "$TMP/out.txt" | head -1)"
    STEPS="$(sed -n 's/^  engine steps   : \([0-9]*\)$/\1/p' "$TMP/out.txt" | head -1)"
    LEDGER="$(sed -n 's/^  engine ledger  : \(.*\)$/\1/p' "$TMP/out.txt" | head -1)"
}

# state_field <name>: print one field of the 352-byte state file.
state_field() {
    python3 - "$STATE" "$1" <<'PYEOF'
import struct, sys
data = open(sys.argv[1], "rb").read()
assert len(data) == 352, "state size %d" % len(data)
name = sys.argv[2]
if name == "attempt1":
    print(struct.unpack_from("<5I", data, 0x10)[1])
elif name == "decoy1":
    print(struct.unpack_from("<5I", data, 0x24)[1])
elif name == "ring_count":
    print(struct.unpack_from("<H", data, 0x38)[0])
elif name == "debug":
    print(data[0x3C])
elif name == "first_run":
    print(struct.unpack_from("<Q", data, 0x08)[0])
else:
    raise SystemExit("unknown field " + name)
PYEOF
}

# hmac_ok <path>
hmac_ok() {
    python3 - "$1" <<'PYEOF'
import hmac, hashlib, sys
data = open(sys.argv[1], "rb").read()
if len(data) != 352:
    sys.exit(1)
key = bytes.fromhex("f03ea6b5c1b869482723c0d11d635f8e9966c43a0a8def87fd1e2e950c10a7de")
calc = hmac.new(key, data[:0x140], hashlib.sha256).digest()
sys.exit(0 if hmac.compare_digest(calc, data[0x140:0x160]) else 1)
PYEOF
}

# forge_state <mode> <first_run_age_ms> <debugger>: write a valid state file.
#   mode = human   -> irregular interaction gaps (stddev well above the
#                     uniformity threshold)
#   mode = uniform -> 10 ms gaps (scripted-loop tell)
#   mode = fast    -> human gaps, but reached within the configured window
forge_state() {
    python3 - "$STATE" "$1" "$2" "$3" <<'PYEOF'
import hashlib, hmac, struct, sys, time
path, mode, age_ms, dbg = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
now = int(time.time() * 1000)
first = now - age_ms
gaps = {"human": [900, 4300, 1500, 8000, 2200, 11000, 700, 3000],
        "uniform": [10] * 8,
        "fast": [900, 4300, 1500, 8000, 2200, 11000, 700, 3000]}[mode]
buf = bytearray(352)
buf[0:4] = b"CART"
buf[4] = 1
struct.pack_into("<Q", buf, 0x08, first)
# The ring is placed relative to NOW (its last entry lands ~now) because the
# stage records its own interaction BEFORE evaluating the timing reasons, so
# the freshly appended delta must fit the pattern being forged.
ts = now - sum(gaps)
for i, g in enumerate(gaps):
    ts += g
    struct.pack_into("<Q", buf, 0x40 + 8 * i, ts)
n = len(gaps)
struct.pack_into("<H", buf, 0x38, n)
struct.pack_into("<H", buf, 0x3A, n)
buf[0x3C] = dbg & 0xFF
key = bytes.fromhex("f03ea6b5c1b869482723c0d11d635f8e9966c43a0a8def87fd1e2e950c10a7de")
buf[0x140:0x160] = hmac.new(key, bytes(buf[:0x140]), hashlib.sha256).digest()
open(path, "wb").write(bytes(buf))
PYEOF
}

echo "== stage1_vm end-to-end verification =="

# --- 0. artifacts ---------------------------------------------------------
if [ -x "$BIN" ]; then ok "binary exists and is executable"; else bad "binary missing"; fi
if file "$BIN" | grep -q "statically linked"; then ok "binary statically linked (musl)"; else bad "static link"; fi
if file "$BIN" | grep -q "stripped"; then ok "binary stripped (no symtab)"; else bad "stripped"; fi
SCRUB="$(strings -n 4 "$BIN" | grep -Ei "(GCC|clang|musl|/home/manish|cartographer-build|\.c$|\.h$)" || true)"
if [ -z "$SCRUB" ]; then ok "no debug paths / compiler strings in binary"; else bad "scrub residue: $SCRUB"; fi

# --- 1. independent model pre-computation ---------------------------------
model 0 0 >"$TMP/m00.txt"
model 0 1 >"$TMP/m01.txt"
model 1 0 >"$TMP/m10.txt"
model 1 1 >"$TMP/m11.txt"
M_KEY0="$(sed -n 's/^KEY=//p' "$TMP/m00.txt")"
M_KEY1="$(sed -n 's/^KEY=//p' "$TMP/m10.txt")"
M_KEYD0="$(sed -n 's/^KEY=//p' "$TMP/m01.txt")"
M_KEYD1="$(sed -n 's/^KEY=//p' "$TMP/m11.txt")"
M_STEPS0="$(sed -n 's/^STEPS=//p' "$TMP/m00.txt")"
M_STEPS1="$(sed -n 's/^STEPS=//p' "$TMP/m10.txt")"
M_STEPSD0="$(sed -n 's/^STEPS=//p' "$TMP/m01.txt")"
M_R1="$(sed -n 's/^R1=0x//p' "$TMP/m00.txt")"
M_R2="$(sed -n 's/^R2=0x//p' "$TMP/m00.txt")"
M_R6="$(sed -n 's/^R6=0x//p' "$TMP/m00.txt")"
M_R7="$(sed -n 's/^R7=0x//p' "$TMP/m00.txt")"
if [ "$(sed -n 's/^FAIL=//p' "$TMP/m00.txt")" = "0" ] && \
   [ "$(sed -n 's/^FAIL=//p' "$TMP/m01.txt")" = "0" ] && \
   [ "$(sed -n 's/^FAIL=//p' "$TMP/m11.txt")" = "0" ]; then
    ok "model: no VM fault in any of the four runs"
else
    bad "model: VM fault"
fi
if [ "$M_KEY0" = "$M_KEY1" ]; then ok "model: both variants yield the same key"; else bad "model: variant mismatch"; fi
if [ "$M_KEY0" = "$REAL_KEY" ]; then ok "model key matches the key recorded in the build tables"; else bad "model key drifted from REAL_KEY"; fi
if [ "$M_KEYD0" != "$M_KEY0" ] && [ "$M_KEYD1" != "$M_KEY1" ]; then
    ok "model: detected path yields a different (corrupted) key"
else
    bad "model: detected key equals the real key"
fi
if [ "$M_KEYD0" = "$DEBUG_KEY" ]; then ok "model detected key matches the recorded debug constant"; else bad "debug-path constant drifted"; fi

# --- 2. clean run on a forged human-paced state ---------------------------
forge_state human 600000 0                  # no escalation reasons at all
run_stage1
parse_out
if [ "$RC" -eq 0 ]; then ok "clean run exits 0"; else bad "clean run exit ($RC)"; fi
if [ ! -s "$TMP/err.txt" ]; then ok "clean run: stderr silent"; else bad "clean run wrote to stderr"; fi
if [ "$VARIANT" = "coastal" ]; then ok "clean run serves the standard variant (coastal)"; else bad "variant=$VARIANT"; fi
if [ "$STEPS" = "$M_STEPS0" ]; then ok "engine steps == python model ($STEPS)"; else bad "steps=$STEPS want $M_STEPS0"; fi
if [ -z "$KEY" ]; then ok "clean run does not leak the 64-hex key material"; else bad "key leaked: $KEY"; fi
if [ "$TOKEN" = "CARTO{${REAL_KEY:0:32}}" ]; then ok "token is minted from the first half of the key"; else bad "token/key mismatch"; fi
if python3 -c "import re,sys; sys.exit(0 if re.fullmatch(r'CARTO\{[a-z0-9_]{8,64}\}', sys.argv[1]) else 1)" "$TOKEN"; then
    ok "token matches the canonical flag format (D11)"
else
    bad "token violates the canonical flag format"
fi
if [ -z "$LEDGER" ]; then
    ok "engine ledger is absent from stdout (not leaked)";
else
    bad "ledger mismatch: $LEDGER"
fi
if [ "$(stat -c%s "$STATE" 2>/dev/null)" = "352" ]; then ok "state file is exactly 352 bytes"; else bad "state size"; fi
if hmac_ok "$STATE"; then ok "state HMAC valid (independent python check)"; else bad "state HMAC invalid"; fi
if [ "$(state_field attempt1)" = "1" ]; then ok "attempt_count[1] == 1 after first run"; else bad "attempt_count[1]"; fi
if [ "$(state_field ring_count)" = "9" ]; then ok "interaction ring extended (8 forged + 1 recorded)"; else bad "ring_count"; fi
if [ "$(state_field debug)" = "0" ]; then ok "debugger_detected stays 0 on a clean run"; else bad "debugger flag set on clean run"; fi
FR0="$(state_field first_run)"

# --- 3. determinism -------------------------------------------------------
run_stage1
parse_out
if [ -z "$KEY" ] && [ "$TOKEN" = "CARTO{${REAL_KEY:0:32}}" ] && [ "$STEPS" = "$M_STEPS0" ]; then ok "second run reproduces token and steps exactly"; else bad "non-deterministic"; fi
if [ "$(state_field attempt1)" = "2" ]; then ok "attempt_count[1] == 2 after second run"; else bad "attempts"; fi
if [ "$(state_field first_run)" = "$FR0" ]; then ok "first_run_ms is preserved"; else bad "first_run changed"; fi
if [ ! -e "$STATE.tmp" ]; then ok "no .tmp residue after runs"; else bad ".tmp residue"; fi

# --- 4. escalation variants ------------------------------------------------
forge_state uniform 600000 0                # scripted-loop timing tell
run_stage1
parse_out
if [ "$VARIANT" = "interior" ]; then ok "uniform interaction timing selects the escalated variant"; else bad "variant=$VARIANT"; fi
if [ "$STEPS" = "$M_STEPS1" ]; then ok "escalated variant steps == model ($STEPS)"; else bad "steps=$STEPS want $M_STEPS1"; fi
if [ -z "$KEY" ] && [ "$TOKEN" = "CARTO{${REAL_KEY:0:32}}" ]; then ok "escalated variant yields the identical token"; else bad "escalated token mismatch"; fi
TOKEN_ESC="$TOKEN"
STEPS_ESC="$STEPS"

forge_state fast 1 0                        # 1 ms: below ANY calibrated window
run_stage1
parse_out
if [ "$VARIANT" = "interior" ]; then ok "fast arrival selects the escalated variant"; else bad "variant=$VARIANT"; fi
if [ "$TOKEN" = "$TOKEN_ESC" ] && [ "$STEPS" = "$STEPS_ESC" ]; then ok "fast-arrival variant matches the uniform-timing variant exactly"; else bad "variant output mismatch"; fi

forge_state human 600000 1                  # persisted debugger flag only
run_stage1
parse_out
if [ "$VARIANT" = "interior" ]; then ok "persisted debugger flag escalates the variant"; else bad "variant=$VARIANT"; fi
if [ "$TOKEN" = "CARTO{${REAL_KEY:0:32}}" ]; then ok "persisted debugger flag alone does NOT corrupt the token"; else bad "persisted flag corrupted the token"; fi

# --- 5. decoy routing ------------------------------------------------------
forge_state human 600000 0
run_stage1 "$DECOY_FLAG"
parse_out
if [ "$RC" -eq 0 ]; then ok "decoy submission exits 0 (no error path)"; else bad "decoy exit ($RC)"; fi
if [ ! -s "$TMP/err.txt" ]; then ok "decoy submission: stderr silent"; else bad "decoy stderr"; fi
if [ -z "$KEY" ]; then ok "decoy route does not leak key material"; else bad "decoy key=$KEY"; fi
if [ "$TOKEN" = "$DECOY_FLAG" ]; then ok "decoy token equals the registered policy.h entry"; else bad "decoy token=$TOKEN"; fi
if grep -q "corroborated" "$TMP/out.txt"; then ok "decoy route is framed as new information, not failure"; else bad "extended-branch flavor missing"; fi
if ! grep -q "$REAL_KEY" "$TMP/out.txt"; then ok "decoy route does not leak the real key"; else bad "real key leaked on the decoy route"; fi
if [ "$(state_field decoy1)" = "1" ]; then ok "decoy bit 0 persisted in the state file"; else bad "decoy bit not persisted"; fi
if hmac_ok "$STATE"; then ok "state HMAC valid after decoy routing"; else bad "HMAC broken by decoy routing"; fi

forge_state human 600000 0
run_stage1 "CARTO{not_a_registered_token}"
parse_out
if [ "$TOKEN" = "CARTO{${REAL_KEY:0:32}}" ]; then ok "unknown token still runs the engine normally"; else bad "unknown token changed the token"; fi
if grep -Fq "(the ledger does not recognise that ink)" "$TMP/out.txt"; then ok "unknown token gets a neutral reply"; else bad "neutral reply missing"; fi
if [ "$(state_field decoy1)" = "0" ]; then ok "unknown token sets no decoy bit"; else bad "spurious decoy bit"; fi

REAL_TOKEN="CARTO{${REAL_KEY:0:32}}"
run_stage1 "$REAL_TOKEN"
parse_out
if grep -Fq "(the ledger recognises that ink)" "$TMP/out.txt"; then ok "the engine recognises its own token"; else bad "own token not recognised"; fi
if [ "$TOKEN" = "CARTO{${REAL_KEY:0:32}}" ]; then ok "token self-check does not disturb the token"; else bad "self-check changed the token"; fi

# --- 6. anti-debug: ptrace detection --------------------------------------
DEBUG_TOKEN="CARTO{${DEBUG_KEY:0:32}}"
forge_state human 600000 0
( cd "$PKG" && gdb -batch -q -ex run --args "$BIN" >"$TMP/gdb1.txt" 2>"$TMP/gdb1.err" )
RC=$?
GKEY="$(sed -n 's/^    \([0-9a-f]\{64\}\)$/\1/p' "$TMP/gdb1.txt" | head -1)"
GSTEPS="$(sed -n 's/^  engine steps   : \([0-9]*\)$/\1/p' "$TMP/gdb1.txt" | head -1)"
GTOKEN="$(grep -o 'CARTO{[a-z0-9_]\{1,\}}' "$TMP/gdb1.txt" | head -1)"
if [ "$RC" -eq 0 ]; then ok "debugger run exits 0 (detection stays silent)"; else bad "gdb run exit ($RC)"; fi
if [ "$GTOKEN" = "$DEBUG_TOKEN" ]; then ok "debugger run serves the corrupted constant (same shape, wrong value)"; else bad "gdb token=$GTOKEN"; fi
if [ "$GTOKEN" != "CARTO{${REAL_KEY:0:32}}" ]; then ok "debugger key differs from the real key"; else bad "debugger key equals the real key"; fi
if [ "$GSTEPS" = "$M_STEPSD0" ]; then ok "debugger run executes the detection branch ($GSTEPS steps)"; else bad "gdb steps=$GSTEPS want $M_STEPSD0"; fi
if [ "$GTOKEN" = "CARTO{${DEBUG_KEY:0:32}}" ]; then ok "debugger run still mints a well-formed token"; else bad "gdb token malformed"; fi
if [ "$(state_field debug)" = "1" ]; then ok "debugger_detected flag persisted to the state file"; else bad "debugger flag not set"; fi
if hmac_ok "$STATE"; then ok "state HMAC valid after the debugger run"; else bad "HMAC broken by the debugger run"; fi

# --- 7. anti-debug: timing/single-step detection --------------------------
forge_state human 600000 0
( cd "$PKG" && gdb -batch -q -ex "set confirm off" \
    -ex "break detect_via_ptrace" -ex run -ex "return 0" \
    -ex "break vm_run" -ex continue -ex "stepi 4000" -ex "delete 2" -ex continue \
    --args "$DBG" >"$TMP/gdb2.txt" 2>"$TMP/gdb2.err" )
RC=$?
TKEY="$(sed -n 's/^    \([0-9a-f]\{64\}\)$/\1/p' "$TMP/gdb2.txt" | head -1)"
TTOKEN="$(grep -o 'CARTO{[a-z0-9_]\{1,\}}' "$TMP/gdb2.txt" | head -1)"
if [ "$RC" -eq 0 ]; then ok "timing-path run exits 0"; else bad "timing run exit ($RC)"; fi
if [ "$TTOKEN" = "$DEBUG_TOKEN" ]; then ok "single-stepped trace serves the corrupted constant"; else bad "timing token=$TTOKEN"; fi
if [ "$(state_field debug)" = "1" ]; then ok "timing detection persisted the debugger flag"; else bad "timing detection did not fire"; fi

# --- 8. traps are present and findable in the shipped artifact ------------
if python3 - "$BIN" "$DECOY_KEY" <<'PYEOF'
import sys
blob = open(sys.argv[1], "rb").read()
sys.exit(0 if bytes.fromhex(sys.argv[2]) in blob else 1)
PYEOF
then ok "decoy constant present in the shipped binary (.rodata)"; else bad "decoy constant missing"; fi
if strings -n 8 "$BIN" | grep -Fq "stage2_key_checkpoint"; then ok "decoy lure string present (forgotten-debug framing)"; else bad "lure string missing"; fi
if strings -n 8 "$BIN" | grep -Fq "$DECOY_FLAG"; then ok "registered decoy token is findable in the binary"; else bad "decoy token missing"; fi
if strings -n 6 "$BIN" | grep -Fq "${REAL_KEY:0:32}"; then bad "real key material leaked into the binary"; else ok "real key material absent from the binary"; fi
if strings -n 6 "$BIN" | grep -Fq "$REAL_TOKEN"; then bad "real token leaked into the binary"; else ok "real token absent from the binary"; fi
if strings -n 6 "$BIN" | grep -q "f03ea6b5"; then bad "canonical HMAC key hex found in binary"; else ok "canonical HMAC key hex absent from binary"; fi
if strings -n 8 "$BIN" | grep -Fq "$DEBUG_KEY"; then bad "debug-path key stored in the binary"; else ok "debug-path key is not stored in the binary"; fi

# --- 9. hygiene -----------------------------------------------------------
if ls /tmp/carto_s1_* >/dev/null 2>&1; then bad "stray files outside the package"; else ok "no writes outside the working directory"; fi
rm -f "$STATE" "$STATE.tmp"
if [ ! -e "$STATE" ]; then ok "package left pristine (test state removed)"; else bad "cleanup failed"; fi

echo
echo "== $((pass+fail)) tests run, $fail failed =="
if [ "$fail" -eq 0 ]; then
    echo "ALL TESTS PASSED"
    exit 0
fi
echo "FAILURES PRESENT"
exit 1
