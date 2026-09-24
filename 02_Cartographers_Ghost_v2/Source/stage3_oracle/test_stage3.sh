#!/bin/bash
# Stage 3 acceptance -- SERIAL ONLY.
set -u
cd "$(dirname "$0")"
REPO="$(cd ../.. && pwd)"
export PKGTOOLS="$REPO/src/state"
# shellcheck source=/dev/null
. "$REPO/src/final/lib_stage_tests.sh"

READING='CARTO{rust_blooms_under_tin_roofs}'
INK='145e1d23feac3932'
ORACLE_INK='e509312ae8a2e0ad'
COLD_INK='f059e3a8ec8fb6a1'
TALLY='CARTO{a_warm_plate_and_a_full_ring}'
FIG=0001020304050607
HEXFIG=aabbccdd11223344
SRC="$REPO/src/stage3_oracle"
ORA="$REPO/cartographer/stage3_oracle/oracle"
SCALE=1000

t_init stage3 "$REPO/cartographer"
( cd "$REPO/src/state" && make -s >/dev/null 2>&1 )
( cd "$SRC" && make -s all oracle_test seed3 >/dev/null 2>&1 )
cp "$SRC/seed3" "$SRC/oracle_test" "$SRC/collect.py" "$WORK/" 2>/dev/null || true
# refresh the shipped binary in the scratch tree
cp "$ORA" "$WORK/stage3_oracle/oracle" 2>/dev/null || true
cd "$WORK"

ask() {  # ask <binary> <figure> [extra env]
    local bin="$1" fig="$2"
    script -qec "$bin -r $READING -i $INK $fig" /dev/null 2>&1 </dev/null \
        | tr -d '\r'
}

# ---- one refusal shape, and no key-check mode anywhere ------------------
t_expect_ok "no arguments" ./stage3_oracle/oracle
t_has "the usage is printed" "usage:"
t_lacks "the usage names no mechanism" "round"
t_lacks "the usage names no mechanism (tables)" "table"
t_expect_ok "a garbage argument" ./stage3_oracle/oracle nonsense
t_has "garbage gets the plate's one refusal" "turns over and gives nothing"
t_expect_ok "an unknown flag" ./stage3_oracle/oracle -k deadbeef
if grep -qiE "correct|valid|right|wrong" "$OUT"; then
    bad "a verdict word appeared in the output"
else
    ok "no verdict word anywhere in the refusal"
fi
t_expect_ok "a figure without a reading" ./stage3_oracle/oracle "$FIG"
t_expect_ok "a reading without a figure" ./stage3_oracle/oracle -r "$READING"
t_expect_ok "a figure that is not hex" ./stage3_oracle/oracle -r "$READING" -i "$INK" zzzz
t_expect_ok "sixteen arguments" ./stage3_oracle/oracle 1 2 3 4 5 6 7 8 9 a b c d e f g
head -c 60000 /dev/urandom | base64 -w0 > "$WORK/.big"
t_expect_ok "80 KB argument" ./stage3_oracle/oracle "$(cat "$WORK/.big")"
t_expect_ok "an empty argument" ./stage3_oracle/oracle ''

# ---- the plate is cold until the record is warm -------------------------
rm -f .cartographer_state
./seed3 . thin
T=$(script -qec "./oracle_test -t -r $READING" /dev/null 2>&1 </dev/null | tr -d '\r')
if printf '%s' "$T" | grep -q "still cold"; then
    ok "a thin record gets a cold plate and no tally"
else
    bad "a thin record did not get a cold plate"
    printf '%s\n' "$T" | tail -2
fi
./seed3 . human
T=$(script -qec "./oracle_test -t -r $READING" /dev/null 2>&1 </dev/null | tr -d '\r')
if printf '%s' "$T" | grep -q "still cold"; then
    bad "a warm record got a cold plate"
    printf '%s\n' "$T" | tail -4
else
    ok "a warm record is not cold"
fi
./seed3 . human
A=$(script -qec "./oracle_test -r $READING 0001020304050607" /dev/null 2>&1 </dev/null | tr -d '\r')
if printf '%s' "$A" | grep -q "still cold"; then
    ok "a figure with no ink handed over is answered cold"
else
    bad "the plate answered without being given the ink"
fi

# ---- pipe verse: run the oracle WITHOUT a pty so isatty(0)=0 -----------
./seed3 . human
./oracle_test -r "$READING" -i "$INK" "$FIG" > "$WORK/.piped" 2>&1 </dev/null
if grep -q "fed through a pipe" "$WORK/.piped"; then
    ok "a piped ask gets the pipe verse"
else
    bad "the pipe verse did not appear"
    cat "$WORK/.piped"
fi

./seed3 . uniform
ask ./stage3_oracle/oracle "$FIG" > "$WORK/.uniform"
if grep -q "gone smooth" "$WORK/.uniform"; then
    ok "a metronome ask gets the smooth verse"
else
    bad "the smooth verse did not appear"
fi
./seed3 . bursty
ask ./stage3_oracle/oracle "$FIG" > "$WORK/.bursty"
if grep -q "run hot" "$WORK/.bursty"; then
    ok "a burst ask gets the hot verse"
else
    bad "the hot verse did not appear"
fi
./seed3 . replay
ask ./stage3_oracle/oracle "$FIG" > "$WORK/.replay"
if grep -q "too recently" "$WORK/.replay"; then
    ok "a replayed ask gets the replay verse"
else
    bad "the replay verse did not appear"
fi
./seed3 . young
ask ./stage3_oracle/oracle "$FIG" > "$WORK/.young"
if grep -q "still warming" "$WORK/.young"; then
    ok "a young record gets the warming verse"
else
    bad "the warming verse did not appear"
fi

# ---- uppercase figures get the cutting verse ----------------------------
./seed3 . human
ask ./stage3_oracle/oracle "${HEXFIG^^}" > "$WORK/.upper"
if grep -q "does not cut" "$WORK/.upper"; then
    ok "a figure in capitals gets the cutting verse"
else
    bad "the cutting verse did not appear"
    cat "$WORK/.upper"
fi

# ---- the calibrated sitting, on the test build -------------------------
./seed3 . human
script -qec "env CARTO_TEST_TIME_SCALE=$SCALE python3 collect.py $WORK/ds_real --pairs 48 --oracle ./oracle_test" \
    /dev/null > "$WORK/.collect" 2>&1 </dev/null
if grep -q "answers where the plate said nothing: 0" "$WORK/.collect"; then
    ok "the sitting produced an answer for every figure"
else
    bad "some figures got no answer"
    tail -3 "$WORK/.collect"
fi
ANSWERS=$(wc -l < "$WORK/ds_real")
if [ "$ANSWERS" -ge 400 ]; then
    ok "the sitting collected $ANSWERS answers"
else
    bad "only $ANSWERS answers were collected"
fi
python3 "$SRC/model_oracle.py" attack "$WORK/ds_real" > "$WORK/.attack" 2>&1
if grep -q "MATCH" "$WORK/.attack" && grep -q "ink=$ORACLE_INK" "$WORK/.attack"; then
    ok "the planted-bias attack recovers the ink bit-exactly"
else
    bad "the attack did not recover the ink"
    cat "$WORK/.attack"
fi
if grep -q "kA=2a3109e5 kB=ade0a2e8" "$WORK/.attack"; then
    ok "both halves come out as the pinned little-endian halves"
else
    bad "the halves differ from the pinned ones"
fi

# ---- the model agrees with the binary, figure by figure ----------------
./seed3 . human
MATCHES=0
for fig in 0001020304050607 ffeeddccbbaa9988 0123456789abcdef 5a5a5a5a5a5a5a5a 1112131415161718 deadbeefcafebabe; do
    M=$(python3 "$SRC/model_oracle.py" answer "$fig")
    A=$(script -qec "env CARTO_TEST_TIME_SCALE=$SCALE ./oracle_test -r $READING -i $INK $fig" /dev/null 2>&1 </dev/null \
        | tr -d '\r' | awk '/the plate reads:/{print $4}')
    if [ "$M" = "$A" ]; then MATCHES=$((MATCHES + 1)); fi
done
if [ "$MATCHES" = "6" ]; then
    ok "the model matches the binary on six figures"
else
    bad "the model matched only $MATCHES of 6 figures"
fi

# ---- the tally ---------------------------------------------------------
./seed3 . human
T=$(script -qec "env CARTO_TEST_TIME_SCALE=$SCALE ./oracle_test -t -r $READING" /dev/null 2>&1 </dev/null \
    | tr -d '\r')
if printf '%s' "$T" | grep -q "$TALLY"; then
    ok "a warm plate hands over its tally witness"
else
    bad "the tally witness did not appear"
    printf '%s\n' "$T" | tail -2
fi
rm -f .cartographer_state
T=$(./oracle_test -t -r "$READING" 2>&1)
if printf '%s' "$T" | grep -q "$TALLY"; then
    bad "a cold plate handed over the tally"
else
    ok "a cold plate does not hand over the tally"
fi

# ---- the cache trap ----------------------------------------------------
./seed3 . human
A1=$(script -qec "env CARTO_TEST_TIME_SCALE=$SCALE ./oracle_test -r $READING -i $INK $FIG" /dev/null 2>&1 </dev/null | tr -d '\r' | awk '/the plate reads:/{print $4}')
./seed3 . human
A2=$(script -qec "env CARTO_TEST_TIME_SCALE=$SCALE ./oracle_test -r $READING -i $INK $FIG" /dev/null 2>&1 </dev/null | tr -d '\r' | awk '/the plate reads:/{print $4}')
if [ "$A1" = "$A2" ]; then
    ok "a fresh sitting gives the same answer for the same figure"
else
    bad "the plate is not reproducible across sittings"
fi
# the same figure twice in a row comes back from the last plate used
./seed3 . human
A3=$(script -qec "env CARTO_TEST_TIME_SCALE=$SCALE ./oracle_test -r $READING -i $INK $FIG" /dev/null 2>&1 </dev/null | tr -d '\r' | awk '/the plate reads:/{print $4}')
A4=$(script -qec "env CARTO_TEST_TIME_SCALE=$SCALE ./oracle_test -r $READING -i $INK $FIG" /dev/null 2>&1 </dev/null | tr -d '\r' | awk '/the plate reads:/{print $4}')
if [ "$A3" != "$A4" ]; then
    ok "the same figure twice in a row comes back differently (stale plate)"
else
    bad "the cache trap is gone: the same figure twice gave the same answer"
fi
M=$(python3 "$SRC/model_oracle.py" answer "$FIG")
if [ "$A4" != "$M" ]; then
    ok "the stale answer is not the model's answer for that figure"
else
    bad "the stale answer is the real one after all"
fi

# ---- a mixed sitting has no consensus ----------------------------------
./seed3 . uniform
script -qec "env CARTO_TEST_TIME_SCALE=$SCALE python3 collect.py $WORK/ds_poison --pairs 48 --oracle ./oracle_test" \
    /dev/null > "$WORK/.collectp" 2>&1 </dev/null
head -n 200 "$WORK/ds_poison" > "$WORK/.mix1"
tail -n +201 "$WORK/ds_real" >> "$WORK/.mix1"
python3 "$SRC/model_oracle.py" attack "$WORK/.mix1" > "$WORK/.mixed" 2>&1
if grep -q "NO-CONSENSUS" "$WORK/.mixed"; then
    ok "a mixed sitting gives no consensus"
else
    bad "a mixed sitting still gave a consensus"
    cat "$WORK/.mixed"
fi
if grep -qE "kA=|MATCH" "$WORK/.mixed"; then
    bad "the mixed sitting produced a key"
else
    ok "the mixed sitting produced no key at all"
fi

# ---- the static path reaches the cold key, never the ink ---------------
python3 "$SRC/model_oracle.py" static > "$WORK/.static" 2>&1
if grep -q "cold $COLD_INK" "$WORK/.static"; then
    ok "the static derivation gives the cold key"
else
    bad "the static derivation changed"
fi
if grep -q "real $ORACLE_INK" "$WORK/.static" && \
   [ "$(awk '/^cold/{print $2}' "$WORK/.static")" != "$(awk '/^real/{print $2}' "$WORK/.static")" ]; then
    ok "the cold key is not the ink"
else
    bad "cold and real keys collide"
fi
if grep -q "$ORACLE_INK" "$SRC/oracle.c" 2>/dev/null || \
   strings -n 8 "$ORA" | grep -q "$ORACLE_INK"; then
    bad "the ink is present in the oracle"
else
    ok "the oracle holds no ink"
fi

# ---- the shipped build ignores the test hook ---------------------------
./seed3 . bursty
R1=$(ask ./stage3_oracle/oracle "$FIG")
./seed3 . bursty
R2=$(script -qec "env CARTO_TEST_TIME_SCALE=$SCALE ./stage3_oracle/oracle -r $READING -i $INK $FIG" /dev/null 2>&1 </dev/null | tr -d '\r')
if [ "$R1" = "$R2" ]; then
    ok "the shipped build behaves identically with the hook variable set"
else
    bad "the shipped build reacted to the hook variable"
fi
if strings -n 6 "$ORA" | grep -q "CARTO_TEST_TIME_SCALE"; then
    bad "the hook name is in the shipped binary"
else
    ok "the hook name is absent from the shipped binary"
fi

# ---- binary hygiene ---------------------------------------------------
t_nm_empty "$ORA"
t_strings_clean "$ORA"
t_absent "no engine ink in the oracle" "$ORA" "$INK"
t_absent "no reading in the oracle" "$ORA" "rust_blooms_under_tin_roofs"
t_absent "no title in the oracle" "$ORA" "3821ad004ab30263"
# the tally token IS in the binary (it is printed); assert it IS present
if strings -n 8 "$ORA" | grep -qF "$TALLY"; then
    ok "the tally token is embedded in the oracle (expected)"
else
    bad "the tally token is missing from the oracle"
fi
if file "$ORA" | grep -q "static"; then ok "statically linked"; else bad "not static"; fi

# ---- rebuild reproducibility ------------------------------------------
H1=$(sha256sum "$ORA" | cut -d' ' -f1)
( cd "$REPO/src/state" && make -s clean >/dev/null 2>&1 && make -s >/dev/null 2>&1 )
( cd "$SRC" && make -s clean >/dev/null 2>&1 && make -s >/dev/null 2>&1 )
H2=$(sha256sum "$ORA" | cut -d' ' -f1)
if [ "$H1" = "$H2" ]; then ok "a clean rebuild is byte-identical"; else bad "rebuild differs"; fi

t_summary
