#!/bin/bash
# Stage 2 acceptance -- SERIAL ONLY.
set -u
cd "$(dirname "$0")"
REPO="$(cd ../.. && pwd)"
export PKGTOOLS="$REPO/src/state"
# shellcheck source=/dev/null
. "$REPO/src/final/lib_stage_tests.sh"

READING='CARTO{rust_blooms_under_tin_roofs}'
DECOY='CARTO{the_coast_was_drawn_twice}'
BEARING=771760977412952853
# one parameter off: the same bearing with its survey point moved by one mark
NEARBEARING=$(python3 -c "print(771760977412952853 + (1 << 32))")
SRC="$REPO/src/stage2_sheet"
PKG="$REPO/cartographer"
SHEET="$PKG/stage2_sheet/sheet"

t_init stage2 "$PKG"
cp "$SRC/paced_rec" "$WORK/" 2>/dev/null || true
mkdir -p "$WORK/carriers"
# the tool is always run from the package root, so the suite runs there too
cd "$WORK"
seed_warm() {
    rm -f "$WORK/.cartographer_state"
    ./paced_rec . >/dev/null 2>&1
}

# ---- carriers regenerate identically ------------------------------------
for i in 1 2 3; do
    python3 "$SRC/gen_carriers.py" "$WORK/carriers" >/dev/null 2>&1
    sha256sum "$WORK/carriers/survey_frame.png" "$WORK/carriers/survey_tape.wav" \
        >> "$WORK/.hashes"
done
if [ "$(sort -u "$WORK/.hashes" | wc -l)" = "2" ]; then
    ok "the carriers are byte-identical across three regenerations"
else
    bad "carrier regeneration is not deterministic"
fi
if cmp -s "$WORK/carriers/survey_frame.png" "$PKG/stage2_sheet/survey_frame.png" &&
   cmp -s "$WORK/carriers/survey_tape.wav" "$PKG/stage2_sheet/survey_tape.wav"; then
    ok "the shipped carriers are exactly what the generator makes"
else
    bad "the shipped carriers differ from a fresh generation"
fi

# ---- the carriers are structurally sound --------------------------------
if pngcheck "$PKG/stage2_sheet/survey_frame.png" >/dev/null 2>&1; then
    ok "pngcheck accepts the frame"
else
    bad "pngcheck rejects the frame"
fi
if file "$PKG/stage2_sheet/survey_frame.png" | grep -q "1024 x 1024"; then
    ok "the frame is 1024x1024"
else
    bad "frame dimensions changed"
fi
if file "$PKG/stage2_sheet/survey_tape.wav" | grep -q "PCM, 16 bit, mono 8000 Hz"; then
    ok "the tape is PCM16 mono 8 kHz"
else
    bad "tape format changed"
fi

# ---- no mechanism words, and no real values, in the carriers ------------
python3 - "$PKG/stage2_sheet/survey_frame.png" <<'PY' > "$WORK/.meta"
import struct, sys
d = open(sys.argv[1], "rb").read()
off = 8
while off + 12 <= len(d):
    ln = struct.unpack_from(">I", d, off)[0]
    typ = d[off+4:off+8]
    if typ == b"tEXt":
        print(d[off+8:off+8+ln].decode("latin-1"))
    off += 12 + ln
PY
if grep -Eiq "blue|lsb|stride|dict|dictionary|eight marks|channel" "$WORK/.meta"; then
    bad "the frame metadata names a mechanism"
else
    ok "the frame metadata names no mechanism"
fi
if grep -qF "$READING" "$WORK/.meta" || grep -qi "rust_blooms" "$WORK/.meta"; then
    bad "the frame metadata carries the reading"
else
    ok "the frame metadata carries no reading"
fi

# ---- the press, three ways ----------------------------------------------
python3 - "$PKG/stage2_sheet/survey_tape.wav" "$WORK/press.bin" <<'PY'
import sys
d = open(sys.argv[1], "rb").read()
i = d.find(b"prES")
assert i > 0, "no prES chunk"
n = int.from_bytes(d[i+4:i+8], "little")
assert n == 56, "chunk is %d bytes" % n
open(sys.argv[2], "wb").write(d[i+8:i+8+56])
PY
if [ "$(stat -c %s "$WORK/press.bin")" = "56" ]; then
    ok "a raw byte read gives the 56-byte press"
else
    bad "raw press read is wrong"
fi
if head -c 24 "$WORK/press.bin" | grep -q "ghost2:stage2:press:tag:"; then
    ok "the press opens with its tag"
else
    bad "the press tag changed"
fi
TAIL=$(tail -c 32 "$WORK/press.bin" | xxd -p | tr -d '\n')
if [ "$TAIL" = "c3240a6373072eab57aca45dc3cbcad60ae7136b103e2313a7058bdf4520878b" ]; then
    ok "the press tail is the pinned digest"
else
    bad "press tail is $TAIL"
fi
if exiftool -v3 "$PKG/stage2_sheet/survey_tape.wav" 2>/dev/null | grep -q "'prES' chunk (56 bytes"; then
    ok "exiftool -v3 shows the press chunk and its size"
else
    bad "exiftool -v3 does not show the press chunk"
fi
CLEN=$(exiftool -b -Comment "$PKG/stage2_sheet/survey_frame.png" | wc -c)
if [ "$CLEN" != "56" ]; then
    ok "the comment route is re-encoded ($CLEN bytes, not 56) - documented"
else
    bad "the comment route returns the press unchanged; the trap is gone"
fi

# ---- the three lanes -----------------------------------------------------
MODEL="$SRC/sweep.py"
FRAME="$PKG/stage2_sheet/survey_frame.png"
TAPE="$PKG/stage2_sheet/survey_tape.wav"
python3 "$MODEL" "$FRAME" "$TAPE" --bearing "$BEARING" --dump "$WORK" > "$WORK/.lanes" 2>&1
OUT="$WORK/.lanes"
t_has "the drawn lane gives the reading" "$READING"
if grep -q "next mark: b'run\|next mark:" "$WORK/.lanes" &&
   ! grep -q "next mark: b'CARTO{" "$WORK/.lanes"; then
    ok "the near-miss lane gives readable words, never a mark"
else
    bad "the near-miss lane is wrong"
fi
python3 "$MODEL" "$FRAME" "$TAPE" --naive > "$WORK/.naive" 2>&1
OUT="$WORK/.naive"
t_has "the first row carries the decoy" "$DECOY"
t_lacks "the decoy is not the reading" "$READING"

python3 - "$SRC/gen_carriers.py" <<'PY' > "$WORK/.sep"
import sys
sys.path.insert(0, sys.argv[1].rsplit("/", 1)[0])
import gen_carriers as G
bearing = 771760977412952853
stride, start, real = G.real_positions(bearing)
near = G.near_miss_positions(stride, start)
print("overlap", len(set(real[:2048]) & set(near[:2048])))
print("stride", stride, "start", start)
PY
if grep -q "overlap 0" "$WORK/.sep"; then
    ok "the two lanes share no mark"
else
    bad "the lanes overlap"
fi
if grep -q "stride 8 start 2629" "$WORK/.sep"; then
    ok "the lane arithmetic matches the pinned bearing"
else
    bad "lane arithmetic moved"
fi

# the near-miss lane must not answer the press check, so a sweep that filters
# candidates by the press cannot land on it by accident
python3 - "$FRAME" "$WORK/press.bin" "$SRC/sweep.py" <<'PY' > "$WORK/.near"
import sys, struct
sys.path.insert(0, sys.argv[3].rsplit("/", 1)[0])
import sweep as S
w, h, px = S.png_pixels(S.read(sys.argv[1]))
blob = S.take_bytes(px, w, [2629 + 1 + k * 8 for k in range(0, 2048)], 256)
ln = struct.unpack_from("<H", blob, 0)[0]
print("near payload len", ln, "fdict", (blob[3] & 0x20) != 0)
PY
if grep -q "fdict False" "$WORK/.near"; then
    ok "the near-miss lane carries no press check"
else
    bad "the near-miss lane carries a press check (a sweep would find both)"
fi

# ---- the detector has to fail to point at the marks ---------------------
python3 "$SRC/detect_layer.py" "$FRAME" "$TAPE" > "$WORK/.detect" 2>&1
if grep -q "^OK$" "$WORK/.detect" && ! grep -q "FAIL" "$WORK/.detect"; then
    ok "no statistical detector localises the marks"
else
    bad "a detector localised the marks"
    cat "$WORK/.detect"
fi
if [ "$(grep -c '^PASS' "$WORK/.detect")" = "4" ]; then
    ok "all four detectors ran"
else
    bad "not all detectors ran"
fi

# ---- the tool ------------------------------------------------------------
t_expect_ok "no arguments" ./stage2_sheet/sheet
t_has "the audit names the frame" "frame: present and in one piece"
t_has "the audit names the tape" "tape:  present and in one piece"
t_has "a cold bench is described honestly" "not warm"
t_expect_ok "piped reveal" bash -c "./stage2_sheet/sheet -r -b $BEARING | cat > /dev/null"
t_run bash -c "./stage2_sheet/sheet -r -b $BEARING | cat"
t_has "a piped reveal asks for a hand" "reads a hand, not a pipe"
t_lacks "a piped reveal says nothing else" "$READING"
if [ "$(grep -c '' "$OUT")" = "1" ]; then
    ok "a piped reveal prints exactly one line"
else
    bad "a piped reveal printed extra lines"
fi

# ---- a terminal, but a cold record --------------------------------------
rm -f "$WORK/.cartographer_state"
script -qec "./stage2_sheet/sheet -r -b $BEARING" /dev/null \
    > "$WORK/.tty_cold" 2>&1 </dev/null
if grep -q "not warm" "$WORK/.tty_cold" && ! grep -q "$READING" "$WORK/.tty_cold"; then
    ok "a terminal with a cold record gets flavour, not the reading"
else
    bad "cold reveal leaked or changed"
    tail -3 "$WORK/.tty_cold"
fi

# ---- a terminal, a warm record, and a bearing ---------------------------
rm -f "$WORK/.cartographer_state"
./paced_rec . >/dev/null 2>&1
script -qec "./stage2_sheet/sheet -r -b $BEARING" /dev/null \
    > "$WORK/.tty_ok" 2>&1 </dev/null
if grep -qF "$READING" "$WORK/.tty_ok"; then
    ok "a warm bench at a terminal reads the frame out"
else
    bad "the warm reveal did not read the frame"
    tail -6 "$WORK/.tty_ok"
fi
if grep -q "the box is the survey's own" "$WORK/.tty_ok"; then
    ok "the reveal says plainly what the box is"
else
    bad "the reveal does not explain its box"
fi

# ---- colour, width, and the plain fallback ------------------------------
seed_warm
FRAME_BIT=$(python3 -c "print(open('$WORK/press.bin','rb').read()[24] & 1)")
if [ "$FRAME_BIT" = "1" ]; then COLOUR=rust; else COLOUR=tin; fi
script -qec "./stage2_sheet/sheet -r -b $BEARING --plain" /dev/null \
    > "$OUT" 2>&1 </dev/null
t_has "the plain form spells the colour as a word" "the last stroke dried: $COLOUR"
if grep -q $'\033\[3[0-9]m' "$OUT"; then
    bad "the plain form still used a colour escape"
else
    ok "the plain form uses no escapes at all"
fi
script -qec "./stage2_sheet/sheet -r -b $BEARING" /dev/null \
    > "$WORK/.colour" 2>&1 </dev/null
if grep -q "the last stroke is the colour it dried as" "$WORK/.colour"; then
    ok "the default form states the colour rule in its own words"
else
    bad "the colour rule is not stated"
fi
if grep -q $'\033\[3[0-9]m' "$WORK/.colour"; then
    ok "the colour is carried by the terminal"
else
    bad "no colour escape in the default output"
fi
if sed 's/\x1b\[[0-9;]*m//g' "$WORK/.colour" | grep -q "the last stroke is the colour"; then
    ok "the colour line is legible after a capture"
else
    bad "the colour line breaks a capture"
fi
script -qec "stty cols 40; ./stage2_sheet/sheet -r -b $BEARING --plain" /dev/null \
    > "$WORK/.narrow" 2>&1 </dev/null
if grep -q "too narrow to lay it out" "$WORK/.narrow"; then
    ok "a narrow room is told it is narrow"
else
    bad "the width rule did not fire"
fi
if grep -qF "$READING" "$WORK/.narrow"; then
    bad "the narrow room still got the layout"
else
    ok "the narrow room does not get the layout"
fi
if grep -q -- "the last stroke dried: $COLOUR" "$WORK/.narrow"; then
    ok "the plain word survives a narrow room (the fallback is fair)"
else
    bad "the plain fallback was lost in a narrow room"
fi
python3 - "$WORK/.tty_ok" <<'PY'
import sys, re
raw = open(sys.argv[1], "rb").read().decode("latin-1")
open(sys.argv[1] + ".stripped", "w").write(re.sub(r"\x1b\[[0-9;]*m", "", raw))
PY
if grep -qF "$READING" "$WORK/.tty_ok.stripped"; then
    ok "stripping the escapes leaves the reading intact"
else
    bad "the reading did not survive a stripped capture"
fi

# ---- a bearing read from the record instead of the argument -------------
rm -f "$WORK/.cartographer_state"
./stage1_engine/engine -p coast >/dev/null 2>&1
./paced_rec . >/dev/null 2>&1
script -qec "./stage2_sheet/sheet -r" /dev/null > "$WORK/.fromstate" 2>&1 </dev/null
if grep -qF "$READING" "$WORK/.fromstate"; then
    ok "the bearing can come from the record the engine wrote"
else
    bad "the record's bearing was not used"
    tail -4 "$WORK/.fromstate"
fi
rm -f "$WORK/.cartographer_state"
seed_warm
script -qec "./stage2_sheet/sheet -r" /dev/null > "$WORK/.nobear" 2>&1 </dev/null
OUT="$WORK/.nobear"
t_has "a record with no bearing laid says so" "no bearing has been laid"

# ---- the near-miss parameters through the tool --------------------------
seed_warm
script -qec "./stage2_sheet/sheet -r -b $NEARBEARING" /dev/null \
    > "$WORK/.nearmiss" 2>&1 </dev/null
if grep -qF "$READING" "$WORK/.nearmiss"; then
    bad "the near-miss parameters returned the reading"
else
    ok "the near-miss parameters do not return the reading"
fi
if grep -q "the sheet spells:" "$WORK/.nearmiss"; then
    ok "the near-miss parameters still spell something out"
else
    bad "the near-miss parameters spell nothing"
fi

# ---- press mode ---------------------------------------------------------
t_expect_ok "the right press" ./stage2_sheet/sheet -p "$WORK/press.bin" -R "$WORK/ink.zlib"
t_has "the press and the frame agree" "the press and the frame agree"
head -c 56 /dev/urandom > "$WORK/bad.bin"
t_expect_ok "a wrong press" ./stage2_sheet/sheet -p "$WORK/bad.bin" -R "$WORK/ink.zlib"
cp "$OUT" "$WORK/.p1"
t_expect_ok "a missing press file" ./stage2_sheet/sheet -p "$WORK/nothere.bin" -R "$WORK/ink.zlib"
if cmp -s "$WORK/.p1" "$OUT"; then
    ok "every failed press check gets the same line"
else
    bad "press refusals differ"
fi

# ---- argument and stream discipline -------------------------------------
t_expect_ok "empty argument" ./stage2_sheet/sheet ''
t_expect_ok "sixteen arguments" ./stage2_sheet/sheet 1 2 3 4 5 6 7 8 9 a b c d e f g
t_expect_ok "an unknown flag" ./stage2_sheet/sheet --nonsense
head -c 60000 /dev/urandom | base64 -w0 > "$WORK/.big"
t_expect_ok "80 KB argument" ./stage2_sheet/sheet "$(cat "$WORK/.big")"
t_expect_ok "dumb terminal" env TERM=dumb ./stage2_sheet/sheet
t_expect_ok "narrow columns" env COLUMNS=20 ./stage2_sheet/sheet

# ---- a wrecked record ---------------------------------------------------
python3 - "$WORK/.cartographer_state" <<'PY'
import sys, os
p = sys.argv[1]
if not os.path.exists(p):
    raise SystemExit(0)
d = bytearray(open(p, "rb").read())
for i in range(len(d)):
    d[i] ^= 0x5A
open(p, "wb").write(bytes(d))
PY
t_expect_ok "corrupt record" ./stage2_sheet/sheet
t_state_size
t_verify_state

# ---- what the tool wrote down -------------------------------------------
rm -f "$WORK/.cartographer_state"
t_expect_ok "reveal with the bearing on the command line" \
    bash -c "./stage2_sheet/sheet -r -b $BEARING | cat"
python3 "$REPO/src/stage1_engine/state_dump.py" "$WORK/.cartographer_state" 4 > "$WORK/.reveals"
if grep -q "op=4" "$WORK/.reveals"; then
    ok "the reveal was recorded on the record"
else
    bad "the reveal was not recorded"
fi
rm -f "$WORK/.cartographer_state"
t_expect_ok "press mode" ./stage2_sheet/sheet -p "$WORK/press.bin" -R "$WORK/ink.zlib"
python3 "$REPO/src/stage1_engine/state_dump.py" "$WORK/.cartographer_state" 7 > "$WORK/.presses"
if grep -q "op=7" "$WORK/.presses"; then
    ok "the press check was recorded on the record"
else
    bad "the press check was not recorded"
fi
G2=$(python3 "$REPO/src/stage1_engine/state_dump.py" "$WORK/.cartographer_state" | awk -F= '/^gate\[2\]/{print $2}')
if [ $(( G2 & 0x10 )) -ne 0 ]; then
    ok "the press bit is evidence-backed on the record"
else
    bad "the press bit is missing (gate[2]=$G2)"
fi

# ---- binary hygiene -----------------------------------------------------
t_nm_empty "$SHEET"
t_strings_clean "$SHEET"
t_absent "no reading in the sheet" "$SHEET" "rust_blooms_under_tin_roofs"
t_absent "no engine ink in the sheet" "$SHEET" "145e1d23feac3932"
t_absent "no title in the sheet" "$SHEET" "3821ad004ab30263"
t_absent "no bearing in the sheet" "$SHEET" "0ab5d885"
t_absent "no lane arithmetic word in the sheet" "$SHEET" "stride"
if file "$SHEET" | grep -q "static"; then ok "statically linked"; else bad "not static"; fi

# ---- rebuild reproducibility -------------------------------------------
H1=$(sha256sum "$SHEET" | cut -d' ' -f1)
( cd "$SRC" && make -s clean >/dev/null 2>&1 && make -s >/dev/null 2>&1 )
H2=$(sha256sum "$SHEET" | cut -d' ' -f1)
if [ "$H1" = "$H2" ]; then ok "a clean rebuild is byte-identical"; else bad "rebuild differs"; fi

t_summary
