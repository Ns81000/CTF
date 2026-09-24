#!/bin/bash
# test_stage0.sh -- Phase 1 end-to-end verification for stage0_start.
# Internal (not shipped to solvers). Runnable verbatim:
#   cd /home/manish/cartographer-build/src/stage0 && ./test_stage0.sh
# Requires the built binary at ../../cartographer/stage0_start/stage0_start.
# Verifies the state file with an INDEPENDENT python HMAC check (canonical
# key from PHASE_0_LOG.md), not with the C library under test.

set -u

REPO="/home/manish/cartographer-build"
PKG="$REPO/cartographer"
BIN="$PKG/stage0_start/stage0_start"
STATE="$PKG/.cartographer_state"
EXPECTED_FLAG="CARTO{first_ink_in_the_ledger}"

pass=0
fail=0

ok()  { echo "[PASS] $1"; pass=$((pass+1)); }
bad() { echo "[FAIL] $1"; fail=$((fail+1)); }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# run_stage0: execute the binary from the package root.
# stdout -> $TMP/out.txt ; stderr -> $TMP/err.txt ; exit code -> $RC
RC=0
run_stage0() {
    ( cd "$PKG" && "$BIN" >"$TMP/out.txt" 2>"$TMP/err.txt" )
    RC=$?
}

# parse_state <path>: parse the 352-byte state file; print KEY=VALUE lines.
parse_state() {
    python3 - "$1" <<'PYEOF'
import struct, sys
data = open(sys.argv[1], "rb").read()
assert len(data) == 352, "expected 352-byte state file, got %d" % len(data)
assert data[0:4] == b"CART", "bad magic"
assert data[4] == 1, "bad format_version"
assert data[5] == 0, "flags byte must be 0"
first_run = struct.unpack_from("<Q", data, 0x08)[0]
attempts = struct.unpack_from("<5I", data, 0x10)
decoys = struct.unpack_from("<5I", data, 0x24)
ring_count, ring_head = struct.unpack_from("<HH", data, 0x38)
debug = data[0x3C]
ring = [struct.unpack_from("<Q", data, 0x40 + 8*i)[0] for i in range(32)]
print("FIRST_RUN=%d" % first_run)
print("ATTEMPT0=%d" % attempts[0])
print("DECOY0=%d" % decoys[0])
print("RING_COUNT=%d" % ring_count)
print("RING_HEAD=%d" % ring_head)
print("DEBUG=%d" % debug)
print("RING0=%d" % ring[0])
print("RING1=%d" % ring[1])
PYEOF
}

# snapshot: eval parse_state output into globals (FIRST_RUN ATTEMPT0 ...).
snapshot() {
    local out
    if ! out="$(parse_state "$STATE")"; then
        bad "state file parse/shape"
        return 1
    fi
    eval "$out"
    return 0
}

# hmac_ok <path>: independent HMAC-SHA256 verification with the canonical key.
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

echo "== stage0_start end-to-end verification =="

# --- 0. artifact sanity ---------------------------------------------------
if [ -x "$BIN" ]; then ok "binary exists and is executable"; else bad "binary exists/executable"; fi
if file "$BIN" | grep -q "statically linked"; then ok "binary statically linked (musl)"; else bad "static link"; fi
if file "$BIN" | grep -q "stripped"; then ok "binary stripped (no symtab)"; else bad "stripped"; fi

# --- 1. fresh run ----------------------------------------------------------
rm -f "$STATE" "$STATE.tmp"
NOW_BEFORE=$(date +%s%3N)
run_stage0
if [ "$RC" -eq 0 ]; then ok "first run exits 0"; else bad "first run exit code ($RC)"; fi
if [ ! -s "$TMP/err.txt" ]; then ok "first run: stderr silent"; else bad "first run wrote to stderr"; fi
if [ "$(grep -cF "    $EXPECTED_FLAG" "$TMP/out.txt")" = "1" ]; then ok "first run prints exact flag line once"; else bad "flag line wrong/missing"; fi
if grep -q "First entry inked" "$TMP/out.txt"; then ok "first-entry timestamp printed"; else bad "no first-entry line"; fi

# --- 2. state file after first run ----------------------------------------
if [ -f "$STATE" ]; then ok ".cartographer_state created"; else bad "state file missing"; fi
if [ "$(stat -c%s "$STATE" 2>/dev/null)" = "352" ]; then ok "state file is exactly 352 bytes"; else bad "state size"; fi
if hmac_ok "$STATE"; then ok "state HMAC valid (independent python check)"; else bad "state HMAC invalid"; fi
NOW_AFTER=$(date +%s%3N)
snapshot || true
if [ "${FIRST_RUN:-0}" -ge $((NOW_BEFORE - 300000)) ] && [ "${FIRST_RUN:-0}" -le $((NOW_AFTER + 300000)) ]; then ok "first_run_ms ~= wall clock at creation"; else bad "first_run_ms out of range"; fi
if [ "${ATTEMPT0:-99}" = "1" ]; then ok "attempt_count[0] == 1 after first run"; else bad "attempt[0]=${ATTEMPT0:-unset}"; fi
if [ "${RING_COUNT:-99}" = "1" ] && [ "${RING_HEAD:-99}" = "1" ]; then ok "interaction ring: 1 entry, head=1"; else bad "ring after first run"; fi
if [ "${DEBUG:-1}" = "0" ]; then ok "debugger flag is 0"; else bad "debugger flag"; fi
if [ "${RING0:-1}" = "${FIRST_RUN:-0}" ]; then ok "ring_ts[0] == first_run_ms (same clock read)"; else bad "ring0 != first_run"; fi
if [ "${DECOY0:-1}" = "0" ]; then ok "no decoy bits on stage 0"; else bad "decoy mask nonzero"; fi
FR1="${FIRST_RUN:-0}"

# --- 3. second run (ungated win repeats, ledger persists) -------------------
run_stage0
if [ "$RC" -eq 0 ]; then ok "second run exits 0"; else bad "second run exit ($RC)"; fi
if [ ! -s "$TMP/err.txt" ]; then ok "second run: stderr silent"; else bad "second run wrote to stderr"; fi
if [ "$(grep -cF "    $EXPECTED_FLAG" "$TMP/out.txt")" = "1" ]; then ok "second run prints flag (ungated every run)"; else bad "flag missing on second run"; fi
snapshot || true
if [ "${ATTEMPT0:-99}" = "2" ]; then ok "attempt_count[0] == 2 after second run"; else bad "attempt[0]=${ATTEMPT0:-unset}"; fi
if [ "${RING_COUNT:-99}" = "2" ] && [ "${RING_HEAD:-99}" = "2" ]; then ok "ring: 2 entries, head=2"; else bad "ring after second run"; fi
if [ "${FIRST_RUN:-1}" = "$FR1" ]; then ok "first_run_ms stable across runs"; else bad "first_run_ms changed"; fi
if [ "${RING1:-0}" -ge "${RING0:-1}" ]; then ok "ring timestamps monotonic"; else bad "ring order"; fi
if [ ! -e "$STATE.tmp" ]; then ok "no .tmp residue"; else bad ".tmp residue present"; fi

# --- 4. tamper handling: silent self-defeating reset ------------------------
python3 - "$STATE" <<'PYEOF'
import sys
p = sys.argv[1]
data = bytearray(open(p, "rb").read())
data[0x100] ^= 0xFF
open(p, "wb").write(bytes(data))
PYEOF
run_stage0
if [ "$RC" -eq 0 ]; then ok "run after tamper exits 0 (no error path)"; else bad "tamper run exit ($RC)"; fi
if [ ! -s "$TMP/err.txt" ]; then ok "tampered run: stderr silent (no diagnostics)"; else bad "tamper stderr output"; fi
if [ "$(grep -cF "    $EXPECTED_FLAG" "$TMP/out.txt")" = "1" ]; then ok "flag still handed over after tamper reset"; else bad "flag missing after tamper"; fi
if hmac_ok "$STATE"; then ok "state rewritten valid after tamper"; else bad "post-tamper HMAC invalid"; fi
snapshot || true
if [ "${FIRST_RUN:-0}" -ne "$FR1" ]; then ok "first_run_ms reset (tamper was self-defeating)"; else bad "first_run_ms not reset"; fi
if [ "${ATTEMPT0:-99}" = "1" ] && [ "${RING_COUNT:-99}" = "1" ]; then ok "counters reset to fresh defaults"; else bad "counters not reset"; fi
if [ "${FIRST_RUN:-0}" -ge $((NOW_AFTER - 300000)) ]; then ok "reset first_run_ms ~= now"; else bad "reset first_run_ms stale"; fi

# --- 5. shipped-artifact hygiene --------------------------------------------
if strings -n 6 "$BIN" | grep -q "f03ea6b5"; then bad "canonical key hex FOUND in binary"; else ok "canonical HMAC key hex absent from binary"; fi
if strings -n 8 "$BIN" | grep -Fq "$EXPECTED_FLAG"; then bad "flag plaintext FOUND in binary"; else ok "flag plaintext absent (masked blob only)"; fi
SCRUB="$(strings -n 4 "$BIN" | grep -Ei "(GCC|clang|musl|/home/manish|cartographer-build|\.c$|\.h$)" || true)"
if [ -z "$SCRUB" ]; then ok "no debug paths / compiler strings in binary"; else bad "scrub residue: $SCRUB"; fi

# --- 6. canonical flag format enforcement -----------------------------------
if python3 - "$EXPECTED_FLAG" <<'PYEOF'
import re, sys
sys.exit(0 if re.fullmatch(r"[A-Z]{5}[{][a-z0-9_]{8,64}[}]", sys.argv[1]) else 1)
PYEOF
then ok "stage-0 flag matches canonical format (CARTO{[a-z0-9_]{8,64}})"; else bad "flag violates canonical format"; fi

# --- 7. leave the package pristine (Phase 7 ships a clean folder) ------------
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

