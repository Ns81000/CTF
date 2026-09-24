#!/bin/bash
# test_stage2.sh -- Phase 3 end-to-end verification for stage2_stego.
# Internal (not shipped).  Runnable verbatim:
#   cd /home/manish/cartographer-build/src/stage2_stego && ./test_stage2.sh
#
# Independent by construction: the sheet/tape layers are extracted here with a
# PYTHON reader that shares no code with gen_carriers.py (its own bit reader,
# its own sweep arithmetic, its own stride formula applied to the Stage 1
# real/debug/decoy candidates), the state file is verified with a python HMAC
# check using the canonical Phase-0 key, and s2_inflate is differentially
# tested against python zlib.

set -u

REPO="/home/manish/cartographer-build"
PKG="$REPO/cartographer"
SRC="$REPO/src/stage2_stego"
BIN="$PKG/stage2_stego/stage2_stego"
SHEET="$PKG/stage2_stego/survey_frame.png"
TAPE="$PKG/stage2_stego/survey_tape.wav"
STATE="$PKG/.cartographer_state"

REAL_KEY='fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f'
DEBUG_KEY='fb48aecdda0e960831b16d45c7efbe485d69b61bda262b5c72af18d9b88d1621'
DECOY1_KEY='12f8a367b772817e805725e7292acfb694501c4f16c17ed09d614022e0be7ced'
DECOY2_FLAG='CARTO{twice_over_the_coast_before_the_interior}'
DECOY1_FLAG='CARTO{12f8a367b772817e805725e7292acfb6}'

pass=0
fail=0
ok()  { echo "[PASS] $1"; pass=$((pass+1)); }
bad() { echo "[FAIL] $1"; fail=$((fail+1)); }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

RC=0
run_s2() {
    ( cd "$PKG" && "$BIN" "$@" >"$TMP/out.txt" 2>"$TMP/err.txt" )
    RC=$?
}

# forge_state <mode> <first_run_age_ms> <debugger>: HMAC-valid state file.
forge_state() {
    python3 - "$STATE" "$1" "$2" "$3" <<'PYEOF'
import hashlib, hmac, struct, sys, time
path, mode, age_ms, dbg = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
now = int(time.time() * 1000)
gaps = {"human": [900, 4300, 1500, 8000, 2200, 11000, 700, 3000],
        "uniform": [10] * 8,
        "fast": [900, 4300, 1500, 8000, 2200, 11000, 700, 3000]}[mode]
buf = bytearray(352)
buf[0:4] = b"CART"
buf[4] = 1
struct.pack_into("<Q", buf, 0x08, now - age_ms)
ts = now - sum(gaps)
for i, g in enumerate(gaps):
    ts += g
    struct.pack_into("<Q", buf, 0x40 + 8 * i, ts)
struct.pack_into("<H", buf, 0x38, len(gaps))
struct.pack_into("<H", buf, 0x3A, len(gaps))
buf[0x3C] = dbg & 0xFF
key = bytes.fromhex("f03ea6b5c1b869482723c0d11d635f8e9966c43a0a8def87fd1e2e950c10a7de")
buf[0x140:0x160] = hmac.new(key, bytes(buf[:0x140]), hashlib.sha256).digest()
open(path, "wb").write(bytes(buf))
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

# state_field <name>
state_field() {
    python3 - "$STATE" "$1" <<'PYEOF'
import struct, sys
data = open(sys.argv[1], "rb").read()
assert len(data) == 352, "state size %d" % len(data)
name = sys.argv[2]
if name == "attempt2":
    print(struct.unpack_from("<5I", data, 0x10)[2])
elif name == "decoy2":
    print(struct.unpack_from("<5I", data, 0x24)[2])
elif name == "ring_count":
    print(struct.unpack_from("<H", data, 0x38)[0])
elif name == "debug":
    print(data[0x3C])
else:
    raise SystemExit("unknown field " + name)
PYEOF
}

echo "== stage2_stego end-to-end verification =="

# ---------------------------------- differential test: C inflate vs python zlib
python3 "$SRC/mkvec.py" "$TMP/vectors.txt" >/dev/null
INFLATE_OUT="$("$SRC/test_inflate" "$TMP/vectors.txt" 2>&1)"
INFLATE_RC=$?
VECS="$(printf '%s' "$INFLATE_OUT" | sed -n 's/^== \([0-9]*\) vectors run.*/\1/p')"
echo "$INFLATE_OUT" | tail -3
if [ "$INFLATE_RC" -eq 0 ]; then
    ok "hand-rolled s2_inflate agrees with python zlib on $VECS vectors, refuses all bad streams"
else
    bad "s2_inflate differential failures (rc=$INFLATE_RC)"
fi
# ---------------------------------------------------------------- artifacts
if [ -x "$BIN" ]; then ok "binary exists and is executable"; else bad "binary missing"; fi
if file "$BIN" | grep -q "statically linked"; then ok "binary statically linked (musl)"; else bad "static link"; fi
if file "$BIN" | grep -q "stripped"; then ok "binary stripped (no symtab)"; else bad "stripped"; fi
SCRUB="$(strings -n 4 "$BIN" | grep -Ei "(GCC|clang|musl|/home/manish|cartographer-build|\.c$|\.h$)" || true)"
if [ -z "$SCRUB" ]; then ok "no debug paths / compiler strings in binary"; else bad "scrub residue: $SCRUB"; fi
if [ -f "$SHEET" ]; then ok "sheet carrier present"; else bad "sheet carrier missing"; fi
if [ -f "$TAPE" ]; then ok "tape carrier present"; else bad "tape carrier missing"; fi

# ------------------------------------------------------- independent reader
# Reads the sheet/tape with its own code and prints KEY=VALUE lines.
python3 - "$SHEET" "$TAPE" "$REAL_KEY" "$DEBUG_KEY" "$DECOY1_KEY" "$TMP/ink.bin" >"$TMP/reader.txt" <<'PYEOF'
import struct, sys, zlib, hashlib

sheet = open(sys.argv[1], "rb").read()
tape = open(sys.argv[2], "rb").read()
real, dbg, dec1 = (bytes.fromhex(a) for a in sys.argv[3:6])

# ---- PNG: own parser (critical + text chunks) --------------------------
assert sheet[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
i, idat, texts = 8, b"", {}
while i + 8 <= len(sheet):
    ln = struct.unpack(">I", sheet[i:i + 4])[0]
    typ = sheet[i + 4:i + 8]
    data = sheet[i + 8:i + 8 + ln]
    crc = struct.unpack(">I", sheet[i + 8 + ln:i + 12 + ln])[0]
    assert crc == zlib.crc32(typ + data) & 0xFFFFFFFF, "bad chunk crc %s" % typ
    if typ == b"IHDR":
        w, h, depth, ctype = struct.unpack(">IIBB", data[:10])
    elif typ == b"IDAT":
        idat += data
    elif typ == b"tEXt":
        k, v = data.split(b"\x00", 1)
        texts[k.decode()] = v.decode("latin-1")
    i += 12 + ln
assert (w, h, depth, ctype) == (512, 512, 8, 2), "unexpected sheet shape"
raw = zlib.decompress(idat)
img = bytearray()
p = 0
for y in range(h):
    assert raw[p] == 0, "unexpected filter type at row %d" % y
    img += raw[p + 1:p + 1 + w * 3]
    p += 1 + w * 3
print("PNG_W=%d" % w)
print("PNG_H=%d" % h)
print("TEXT_COMMENT=%s" % texts.get("Comment", ""))
print("TEXT_FIELDNOTE=%s" % texts.get("FieldNote", ""))
print("SHEET_SHA=%s" % hashlib.sha256(sheet).hexdigest())

# ---- decoy layer: naive whole-image LSB, marks 0..511, R,G,B -----------
stream = bytearray()
for bit_i in range(512 * 3):
    stream.append(img[(bit_i // 3) * 3 + (bit_i % 3)] & 1)
digest = bytearray()
for byte_i in range(64):
    v = 0
    for k in range(8):
        v = (v << 1) | stream[8 * byte_i + k]
    digest.append(v)
print("DECOY_NAIVE_HEX=%s" % digest.hex())
print("DECOY_NAIVE_FLAG=%s" % digest.decode("latin-1").split("\x00")[0])

# ---- real layer: blue LSB, stride/start from a candidate key ----------
def sweep(key, label):
    r6 = int.from_bytes(key[0:8], "little")
    r7 = int.from_bytes(key[8:16], "little")
    s = 3 + (r6 % 61)
    p0 = 512 + (r7 % 9000)
    bits, k = [], p0
    while k < 512 * 512:
        bits.append(img[k * 3 + 2] & 1)
        k += s
    out = bytearray()
    for j in range(0, len(bits) - 7, 8):
        v = 0
        for b in bits[j:j + 8]:
            v = (v << 1) | b
        out.append(v)
    framed = struct.unpack("<H", out[:2])[0]
    print("%s_STRIDE=%d" % (label, s))
    print("%s_START=%d" % (label, p0))
    print("%s_FRAMED=%d" % (label, framed))
    ink = bytes(out[2:2 + framed])
    print("%s_INK_HEX=%s" % (label, ink.hex()))
    print("%s_HAS_CARTO=%d" % (label, 1 if b"CARTO{" in ink else 0))
    try:
        reading = zlib.decompress(ink)        # no press mark: must be refused
        print("%s_NO_MARK=PARSED:%s" % (label, reading.decode("latin-1")))
    except Exception:                         # noqa: BLE001
        print("%s_NO_MARK=REFUSED" % label)
    return ink

ink_real = sweep(real, "REAL")
import os
open(sys.argv[6], "wb").write(struct.pack("<H", len(ink_real)) + ink_real)
sweep(dbg, "DEBUG")
sweep(dec1, "DECOY1")

# ---- tape: LIST/INFO parsing, RIFF sizes, sample LSBs -----------------
assert tape[:4] == b"RIFF" and tape[8:12] == b"WAVE", "not a WAVE"
assert struct.unpack("<I", tape[4:8])[0] == len(tape) - 8, "RIFF size wrong"
i, chunks, data = 12, {}, b""
while i + 8 <= len(tape):
    cid = tape[i:i + 4]
    ln = struct.unpack("<I", tape[i + 4:i + 8])[0]
    chunks[cid] = tape[i + 8:i + 8 + ln]
    if cid == b"data":
        data = chunks[cid]
    i += 8 + ln + (ln & 1)
fmt = struct.unpack("<HHIIHH", chunks[b"fmt "][:16])
print("FMT_CHANNELS=%d" % fmt[1])
print("FMT_RATE=%d" % fmt[2])
print("FMT_BITS=%d" % fmt[5])
info = chunks[b"LIST"]
assert info[:4] == b"INFO", "LIST is not INFO"
j, names = 4, {}
while j + 8 <= len(info):
    sid = info[j:j + 4]
    ln = struct.unpack("<I", info[j + 4:j + 8])[0]
    names[sid] = info[j + 8:j + 8 + ln]
    j += 8 + ln + (ln & 1)
print("INFO_CHUNKS=%s" % ",".join(sorted(k.decode() for k in names)))
press = names.get(b"ICMT", b"")
print("PRESS_HEX=%s" % press.hex())
print("TAPE_TITLE=%s" % names.get(b"INAM", b"").rstrip(b"\x00").decode("latin-1"))
print("PRESSED=%s" % zlib.decompressobj(15, press).decompress(ink_real).decode("latin-1"))

msg = b"the tape hums; the figure is not in the sound"
samples = struct.unpack("<%dh" % (len(data) // 2), data)
bitstr = "".join(str(s & 1) for s in samples[:len(msg) * 8])
print("SAMPLE_LSB=%s" % "".join(
    chr(int(bitstr[k * 8:k * 8 + 8], 2)) for k in range(len(msg))))
print("TAPE_SHA=%s" % hashlib.sha256(tape).hexdigest())
PYEOF
RC=$?
rfield() { sed -n "s/^$1=//p" "$TMP/reader.txt" | head -1; }
READING="$(rfield PRESSED)"

if [ "$(rfield PNG_W)" = "512" ] && [ "$(rfield PNG_H)" = "512" ]; then
    ok "sheet verified independently as a 512x512 PNG"
else
    bad "sheet geometry unexpected"
fi
if [ "$(rfield DECOY_NAIVE_FLAG)" = "$DECOY2_FLAG" ]; then
    ok "naive whole-image LSB layer carries the registered decoy at the head"
else
    bad "naive LSB layer is '$(rfield DECOY_NAIVE_FLAG)'"
fi
if [ "$(rfield REAL_STRIDE)" = "46" ] && [ "$(rfield REAL_START)" = "5070" ]; then
    ok "real sweep derives stride 46 / start mark 5070 from the Stage 1 real key"
else
    bad "real sweep: stride=$(rfield REAL_STRIDE) start=$(rfield REAL_START)"
fi
if [ "$READING" = "CARTO{no_figure_sits_in_every_pixel}" ]; then
    ok "blue-channel layer decompresses to the interior reading"
else
    bad "pressed reading is '$READING'"
fi
if [ "$(rfield REAL_NO_MARK)" = "REFUSED" ]; then
    ok "naive zlib decompression of the ink is refused (the press mark is required)"
else
    bad "naive decompression succeeded: $(rfield REAL_NO_MARK)"
fi
if [ "$(rfield DEBUG_STRIDE)" != "46" ] || [ "$(rfield DEBUG_START)" != "5070" ]; then
    ok "debugger-path key draws a different sweep (stride $(rfield DEBUG_STRIDE), start $(rfield DEBUG_START))"
else
    bad "debugger-path key draws the same sweep"
fi
if [ "$(rfield DECOY1_STRIDE)" != "46" ] || [ "$(rfield DECOY1_START)" != "5070" ]; then
    ok "stage-1 decoy key draws a different sweep (stride $(rfield DECOY1_STRIDE), start $(rfield DECOY1_START))"
else
    bad "stage-1 decoy key draws the same sweep"
fi
if [ "$(rfield DECOY1_NO_MARK)" = "REFUSED" ] && [ "$(rfield DECOY1_HAS_CARTO)" = "0" ]; then
    ok "a wrong Stage 1 key yields garbage that does not parse and does not error"
else
    bad "wrong Stage 1 key produced parseable/CARTO-shaped output"
fi
if [ "$(rfield DEBUG_NO_MARK)" = "REFUSED" ] && [ "$(rfield DEBUG_HAS_CARTO)" = "0" ]; then
    ok "the debugger-path key's sweep also yields unparseable garbage"
else
    bad "debugger-path sweep produced parseable output"
fi
if [ "$(rfield INFO_CHUNKS)" = "ICMT,INAM" ]; then
    ok "tape carries INAM + ICMT metadata"
else
    bad "tape metadata chunks: $(rfield INFO_CHUNKS)"
fi
if [ "$(rfield PRESSED)" = "CARTO{no_figure_sits_in_every_pixel}" ]; then
    ok "the press mark extracted from the tape's metadata decrypts the ink"
else
    bad "press formula from the tape failed"
fi
if [ "$(rfield SAMPLE_LSB)" = "the tape hums; the figure is not in the sound" ]; then
    ok "tape sample LSBs carry the irrelevant pattern (not the figure)"
else
    bad "sample LSB pattern unexpected: $(rfield SAMPLE_LSB)"
fi
if [ -n "$(rfield TEXT_FIELDNOTE)" ] && [ -n "$(rfield TEXT_COMMENT)" ]; then
    ok "sheet carries the field note and the (flavor-only) comment"
# --------------------------------------------- the manual-step trap is real
DEFAULT_C="$(exiftool "$TAPE" 2>/dev/null | sed -n 's/^Comment *: //p' | head -1)"
PLAIN_LEN="$(exiftool -Comment -b "$TAPE" 2>/dev/null | wc -c)"
LATIN1_C="$(python3 -c "
import sys
blob=open(sys.argv[1],'rb').read(); i=blob.find(b'ICMT')
print(blob[i+8:i+8+56].decode('latin-1'))" "$TAPE")"
PRESS_HEX="$(rfield PRESS_HEX)"

if [ -n "$DEFAULT_C" ] && [ "$DEFAULT_C" != "$LATIN1_C" ]; then
    ok "exiftool default output mangles the binary press mark (text-habit shortcut fails)"
else
    bad "exiftool default output reproduced the mark byte-exactly"
fi
if [ -n "$PLAIN_LEN" ] && [ "$PLAIN_LEN" -gt 56 ]; then
    ok "exiftool -b -Comment silently re-encodes the mark (${PLAIN_LEN} bytes for 56)"
else
    bad "exiftool -b returned '${PLAIN_LEN}' bytes (expected a longer re-encoding)"
fi
TAILHEX="$(printf '%s' "$PRESS_HEX" | tail -c 32)"
SPACED="$(printf '%s' "$TAILHEX" | sed 's/../& /g' | sed 's/ $//')"
V3OUT="$(exiftool -v3 "$TAPE" 2>/dev/null | tr -d '\n' || true)"
if printf '%s' "$V3OUT" | grep -qi "$SPACED"; then
    ok "exiftool -v3 prints the exact mark bytes (documented, fair resolution)"
else
    bad "exiftool -v3 did not expose the raw mark bytes"
fi
if [ "$(python3 -c "
import sys
blob=open(sys.argv[1],'rb').read(); i=blob.find(b'ICMT')
print(blob[i+8:i+8+56].hex())" "$TAPE")" = "$PRESS_HEX" ]; then
    ok "the mark is recoverable byte-exactly from the raw file"
else
    bad "raw-file mark disagrees with the parsed metadata"
fi
if convert "$SHEET" -depth 8 -crop 1x1+0+0 txt:- >/dev/null 2>&1; then
    ok "ImageMagick can read the sheet (a tool route exists as well)"
else
    bad "ImageMagick could not read the sheet"
fi

# ------------------------------------------------------------ claim verdicts
forge_state human 600000 0
run_s2 -c "$READING"
if [ "$RC" -eq 0 ]; then ok "clean run exits 0"; else bad "clean run exit ($RC)"; fi
if [ ! -s "$TMP/err.txt" ]; then ok "clean run: stderr silent"; else bad "clean run wrote to stderr"; fi
if grep -q "takes this reading" "$TMP/out.txt"; then ok "claim mode accepts the real reading"; else bad "acceptance text missing"; fi
if grep -qF "$READING" "$TMP/out.txt"; then ok "acceptance echoes the reading"; else bad "acceptance did not echo"; fi
TOKEN="$(grep -oE 'CARTO\{[0-9a-f]{32}\}' "$TMP/out.txt" | head -1)"
EXPECTED_TOKEN="$(python3 -c "import hashlib,sys; print('CARTO{'+hashlib.sha256(sys.argv[1].encode()).hexdigest()[:32]+'}')" "$READING")"
if [ "$TOKEN" = "$EXPECTED_TOKEN" ]; then ok "stage 2 checkpoint token minted from the reading digest"; else bad "token=$TOKEN want $EXPECTED_TOKEN"; fi
if grep -q "ledger knows this one" "$TMP/out.txt"; then ok "carrier audit recognises the shipped sheet and tape"; else bad "carrier audit did not recognise them"; fi
if grep -q "plain audit" "$TMP/out.txt"; then ok "human-paced ledger serves the plain audit variant"; else bad "plain audit variant not served"; fi
if [ "$(state_field attempt2)" = "1" ]; then ok "stage 2 attempt counter bumped"; else bad "attempt2=$(state_field attempt2)"; fi
if [ "$(state_field decoy2)" = "0" ]; then ok "no decoy bit set by the real reading"; else bad "unexpected decoy bits"; fi
if hmac_ok "$STATE"; then ok "state HMAC valid (independent python check)"; else bad "state HMAC invalid"; fi
if [ "$(stat -c%s "$STATE")" = "352" ]; then ok "state file is exactly 352 bytes"; else bad "state size"; fi

# second run: counters advance, token unchanged
run_s2 -c "$READING"
if [ "$(state_field attempt2)" = "2" ]; then ok "attempt counter advances across runs"; else bad "attempt2=$(state_field attempt2)"; fi
if grep -qF "$EXPECTED_TOKEN" "$TMP/out.txt"; then ok "checkpoint token is stable across runs"; else bad "token drifted"; fi
if [ "$(state_field debug)" = "0" ]; then ok "debugger flag stays 0 on clean runs"; else bad "debugger flag set spuriously"; fi

# ------------------------------------------------------------- press mode
# ($TMP/ink.bin was written by the independent reader: the framed marks swept
#  from the sheet with the Stage 1 real key, exactly as a solver would have it.)
printf '%s' "$PRESS_HEX" | xxd -r -p >"$TMP/mark.bin"
forge_state human 600000 0
run_s2 -p "$TMP/mark.bin" -R "$TMP/ink.bin"
if [ "$RC" -eq 0 ]; then ok "press mode exits 0"; else bad "press mode exit ($RC)"; fi
if grep -q "the press accepts this ink" "$TMP/out.txt"; then ok "press mode accepts the ink with the tape's mark"; else bad "press mode did not accept the ink"; fi
if grep -q "takes this reading" "$TMP/out.txt"; then ok "the pressed reading verifies against the ledger"; else bad "pressed reading not accepted"; fi
forge_state human 600000 0
WRONG_HEX="$(printf '%s' "$PRESS_HEX" | sed 's/^\(.\{20\}\)..../\1ffff/')"
if [ ${#WRONG_HEX} -ne ${#PRESS_HEX} ]; then bad "wrong-mark fixture malformed"; fi
run_s2 -p "$WRONG_HEX" -R "$TMP/ink.bin"
if grep -q "noise at the head" "$TMP/out.txt"; then
    ok "a wrong press mark is refused at the head (DICTID), without diagnosing"
else
    bad "wrong press mark was not refused at the head"
fi
if grep -q "carry it to the oracle" "$TMP/out.txt"; then bad "wrong mark leaked the real verdict"; else ok "wrong press mark never leaks the real reading"; fi
forge_state human 600000 0
run_s2 -p "$TMP/mark.bin" -R "$TMP/missing.bin"
if grep -q "the ink is not beside the tool" "$TMP/out.txt"; then ok "a missing ink is reported plainly, not as an error"; else bad "missing ink handling"; fi

# ------------------------------------------------------------ decoy routing
forge_state human 600000 0
run_s2 -c "$DECOY2_FLAG"
if [ "$RC" -eq 0 ]; then ok "decoy claim exits 0 (no error path)"; else bad "decoy claim exit ($RC)"; fi
if [ ! -s "$TMP/err.txt" ]; then ok "decoy claim: stderr silent"; else bad "decoy claim wrote to stderr"; fi
if grep -q "the ledger knows this ink" "$TMP/out.txt"; then ok "decoy claim routes into the extended branch"; else bad "decoy branch not routed"; fi
if grep -q "coast survey" "$TMP/out.txt"; then ok "decoy branch is framed as new information, not failure"; else bad "decoy framing missing"; fi
if grep -qF "$READING" "$TMP/out.txt"; then bad "decoy branch leaked the real reading"; else ok "decoy branch never leaks the real reading"; fi
if [ "$(state_field decoy2)" = "1" ]; then ok "stage 2 decoy bit 0 persisted (branch 1 -> 1u<<0)"; else bad "decoy2=$(state_field decoy2)"; fi
if hmac_ok "$STATE"; then ok "state HMAC valid after decoy routing"; else bad "HMAC broken by decoy routing"; fi
# decoy claim runs on a fresh (fast-arrival) ledger: it must also select the
# extended audit variant and STILL never leak the reading.
forge_state fast 1 0                        # 1 ms: below ANY calibrated window
run_s2 -c "$DECOY2_FLAG"
if grep -q "extended audit" "$TMP/out.txt"; then ok "decoy claim also selects the extended audit variant"; else bad "extended variant not selected"; fi

# the stage-1 decoy token lands in the same plain refusal, byte for byte
forge_state human 600000 0
run_s2 -c "$DECOY1_FLAG"
UNKNOWN_OUT="$(cat "$TMP/out.txt")"
run_s2 -c "CARTO{not_the_answer_at_all}"
UNKNOWN_OUT2="$(cat "$TMP/out.txt")"
if [ "$UNKNOWN_OUT" = "$UNKNOWN_OUT2" ]; then ok "refusals are textually identical: no partial-match feedback"; else bad "refusal text differs between wrong readings"; fi
if grep -q "does not know that reading" "$TMP/out.txt"; then ok "the stage-1 decoy token gets only a plain refusal (no oracle)"; else bad "stage-1 decoy handling differs"; fi

# ---------------------------------------------------------------- escalation
forge_state uniform 600000 0
run_s2 -c "$READING"
if grep -q "extended audit" "$TMP/out.txt"; then ok "uniform interaction timing selects the extended audit variant"; else bad "uniform timing did not escalate"; fi
if grep -q -v "does not know that reading" "$TMP/out.txt" && grep -q "takes this reading" "$TMP/out.txt"; then ok "escalated variant still accepts the real reading"; else bad "escalated variant rejected the reading"; fi
if [ "$(state_field debug)" = "0" ]; then ok "escalation does not touch the debugger flag"; else bad "escalation set the debugger flag"; fi

# a persisted debugger flag escalates the audit but never corrupts the answer
forge_state human 600000 1
run_s2 -c "$READING"
if grep -q "extended audit" "$TMP/out.txt"; then ok "a persisted debugger flag selects the extended audit variant"; else bad "debugger flag did not escalate"; fi
if grep -q "takes this reading" "$TMP/out.txt"; then ok "a persisted debugger flag does NOT corrupt the real verdict"; else bad "debugger flag corrupted the verdict"; fi
if [ "$(state_field debug)" = "1" ]; then ok "debugger flag is preserved across the stage 2 run"; else bad "debugger flag lost"; fi
# ------------------------------------------------------- trap visibility
if python3 - "$BIN" <<'PYEOF'
import sys
blob = open(sys.argv[1], "rb").read()
needles = [b"twice_over_the_coast_before_the_interior",
           b"stage2_key_checkpoint (pre-interior)",
           b"the interior figure stands"]
missing = [n for n in needles if n not in blob]
prefix = [b"interior-survey-mark", b"the press keeps no mark"]
if not any(p in blob for p in prefix):
    missing.append(b"press-mark prefix (one of 3 variants)")
if missing:
    print("missing:", missing)
sys.exit(0 if not missing else 1)
PYEOF
then
    ok "shipped binary carries the decoy flag, the spent-press note, the audit text and the mark prefix"
else
    bad "trap material missing from the binary"
fi
if strings -n 6 "$BIN" | grep -q "no_figure_sits_in_every_pixel"; then bad "real reading leaked into the binary"; else ok "real reading absent from the binary"; fi
if strings -n 6 "$BIN" | grep -q "$(printf '%s' "$REAL_KEY" | cut -c1-32)"; then bad "stage 1 real key leaked into the binary"; else ok "stage 1 real key absent from the binary"; fi
if strings -n 6 "$BIN" | grep -qi "$(printf '%s' "$PRESS_HEX" | tail -c 33)"; then bad "press formula stored in the binary"; else ok "press formula is not in the binary (tape only)"; fi
if strings -n 6 "$BIN" | grep -q "f03ea6b5"; then bad "canonical HMAC key hex found in binary"; else ok "canonical HMAC key hex absent from binary"; fi
if python3 - "$BIN" <<'PYEOF'
import sys
blob = open(sys.argv[1], "rb").read()
# an extractor would have to carry one of these to sweep by itself
for bad in (b"pixel_stride", b"stride = 46", b"start_mark", b"5070"):
    if bad in blob:
        sys.exit(1)
sys.exit(0)
PYEOF
then
    ok "no sweep constants or pixel-stride logic are compiled into the binary"
else
    bad "the binary appears to carry sweep derivation constants"
fi
if python3 - "$SHEET" "$TAPE" <<'PYEOF'
import sys
for path in sys.argv[1:]:
    blob = open(path, "rb").read()
    for bad in (b"no_figure_sits_in_every_pixel", b"stage2_key_checkpoint"):
        if bad in blob:
            sys.exit(1)
sheet = open(sys.argv[1], "rb").read()
sys.exit(0 if sheet.find(b"FieldNote") > 0 else 1)
PYEOF
then
    ok "carriers leak neither the reading nor the sweep constants"
else
    bad "carrier leak detected"
fi
if python3 - "$SHEET" <<'PYEOF'
import struct, sys
sheet = open(sys.argv[1], "rb").read()
i, texts = 8, b""
while i + 8 <= len(sheet):
    ln = struct.unpack(">I", sheet[i:i + 4])[0]
    if sheet[i + 4:i + 8] == b"tEXt":
        texts += sheet[i + 8:i + 8 + ln]
    i += 12 + ln
has_note = b"FieldNote" in texts
has_math = b"mod 9000" in texts or b"mod 61" in texts or b"stride =" in texts
sys.exit(0 if (has_note and not has_math) else 1)
PYEOF
then
    ok "the sheet's field note does not leak the sweep math (requires reversing stage2_stego)"
else
    bad "field note leaked the sweep math or is missing"
fi

# ---------------------------------------------------------------- hygiene
rm -f "$STATE" "$STATE.tmp"
if [ ! -e "$STATE" ] && [ ! -e "$STATE.tmp" ]; then ok "package left pristine (test state removed)"; else bad "cleanup failed"; fi
if ls /tmp/carto_s2_* >/dev/null 2>&1; then bad "stray files outside the package"; else ok "no writes outside the working directory"; fi

echo
echo "== $((pass+fail)) tests run, $fail failed =="
if [ "$fail" -eq 0 ]; then
    echo "ALL TESTS PASSED"
    exit 0
fi
echo "FAILURES PRESENT"
exit 1
else
    bad "sheet text chunks missing"
fi
if [ "$RC" -eq 0 ]; then ok "independent python reader parsed both carriers"; else bad "reader failed (rc=$RC)"; fi