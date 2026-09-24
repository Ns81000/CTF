#!/bin/bash
# Stage 1 acceptance -- SERIAL ONLY.
set -u
cd "$(dirname "$0")"
REPO="$(cd ../.. && pwd)"
export PKGTOOLS="$REPO/src/state"
# shellcheck source=/dev/null
. "$REPO/src/final/lib_stage_tests.sh"

CHECKPOINT='CARTO{64c4ad4ea9c40319}'
DECOY='CARTO{f5ea27c63ed89565}'
ALTERNATE='CARTO{788bcd5fb95bb594}'
INK='145e1d23feac3932'
ENGINE="$REPO/cartographer/stage1_engine/engine"
JSON="$REPO/src/stage1_engine/stage1_program.json"
DUMP="$REPO/src/stage1_engine/state_dump.py"

t_init stage1 "$REPO/cartographer"

# ---- the honest run ------------------------------------------------------
t_expect_ok "no arguments" ./stage1_engine/engine
t_has "usage is printed when nothing is asked for" "usage:"
t_has "a fresh record starts on the interior survey" "variant: interior"
t_has "interior steps" "steps:   225433"
t_has "the checkpoint is offered" "$CHECKPOINT"
t_lacks "the engine ink is never printed" "$INK"
t_has "the bench setting is printed" "bench setting:"
t_verify_state

t_expect_ok "the shorter survey" ./stage1_engine/engine -p coast
t_has "coast steps" "steps:   204953"
t_has "coast reaches the same checkpoint" "$CHECKPOINT"

t_expect_ok "the longer survey again" ./stage1_engine/engine -p interior
t_has "the longer survey still reaches the checkpoint" "$CHECKPOINT"
t_expect_ok "the same survey twice" ./stage1_engine/engine -p coast
cp "$OUT" "$WORK/.run1"
t_expect_ok "the same survey a third time" ./stage1_engine/engine -p coast
if cmp -s "$WORK/.run1" "$OUT"; then
    ok "the same survey is byte-identical every run"
else
    bad "the same survey is not reproducible"
fi

# ---- the model must agree -----------------------------------------------
MODEL="$WORK/.model"
python3 "$REPO/src/stage1_engine/model_vm.py" "$JSON" >"$MODEL" 2>&1
if grep -q "coast steps=204953 out=1513351e85d8b50a145e1d23feac393264c4ad4ea9c403191fe981d5c92e67ef" "$MODEL" &&
   grep -q "interior steps=225433 out=1513351e85d8b50a145e1d23feac393264c4ad4ea9c403191fe981d5c92e67ef" "$MODEL"; then
    ok "the independent model reproduces both traces and the 32 bytes"
else
    bad "the model disagrees with the generator"
    cat "$MODEL"
fi
if [ "$(grep -c 'steps=' "$MODEL")" = "2" ]; then
    ok "the model ran both profiles"
else
    bad "the model did not run both profiles"
fi

# ---- the bearing goes on the record, never on the screen ----------------
t_expect_ok "record the bearing" ./stage1_engine/engine -p coast
python3 "$DUMP" "$WORK/.cartographer_state" 10 > "$WORK/.lo"
python3 "$DUMP" "$WORK/.cartographer_state" 11 > "$WORK/.hi"
LO=$(awk '/^ts=/{print $NF}' "$WORK/.lo" | tail -1)
HI=$(awk '/^ts=/{print $NF}' "$WORK/.hi" | tail -1)
if [ -n "$LO" ] && [ -n "$HI" ]; then
    ok "the bearing was written to the record"
else
    bad "no bearing on the record"
fi
if [ "$LO" = "aux=0x1e351315" ] && [ "$HI" = "aux=0x0ab5d885" ]; then
    ok "the recorded bearing is the expected one"
else
    bad "recorded bearing is $LO / $HI"
fi
t_lacks "the bearing low half is not printed" "1e351315"
t_lacks "the bearing high half is not printed" "0ab5d885"

# ---- the decoy branch re-inks the bearing --------------------------------
t_expect_ok "submit the old index key" ./stage1_engine/engine "$DECOY"
t_has "the decoy is corroborated, not refused" "corroborated"
t_lacks "the decoy answer does not leak the checkpoint" "$CHECKPOINT"
python3 "$DUMP" "$WORK/.cartographer_state" 10 > "$WORK/.lo2"
python3 "$DUMP" "$WORK/.cartographer_state" 11 > "$WORK/.hi2"
LO2=$(awk '/^ts=/{print $NF}' "$WORK/.lo2" | tail -1)
HI2=$(awk '/^ts=/{print $NF}' "$WORK/.hi2" | tail -1)
if [ "$LO2" != "$LO" ] || [ "$HI2" != "$HI" ]; then
    ok "the decoy re-inks the bearing"
else
    bad "the decoy did not re-ink the bearing"
fi
if [ "$LO2" = "aux=0xc627eaf5" ] && [ "$HI2" = "aux=0x6595d83e" ]; then
    ok "the decoy bearing comes from the old index key"
else
    bad "decoy bearing is $LO2 / $HI2"
fi

# ---- one refusal line, byte-identical ------------------------------------
t_expect_ok "a wrong key" ./stage1_engine/engine 'CARTO{not_this_one_1}'
cp "$OUT" "$WORK/.r1"
t_expect_ok "another wrong key" ./stage1_engine/engine 'garbage' 'extra'
cp "$OUT" "$WORK/.r2"
if cmp -s "$WORK/.r1" "$WORK/.r2"; then
    ok "every wrong key gets the same answer"
else
    bad "the refusal line varies"
fi
if grep -q "fits no lock" "$WORK/.r1"; then
    ok "the refusal is the documented line"
else
    bad "the refusal line changed"
fi
if [ "$(grep -c 'fits no lock' "$WORK/.r1")" = "1" ]; then
    ok "the refusal is printed exactly once"
else
    bad "the refusal line is printed an unexpected number of times"
fi

# ---- the tracer branch ---------------------------------------------------
if command -v gdb >/dev/null; then
    ( cd "$WORK" && gdb -batch -ex run --args ./stage1_engine/engine -p coast ) \
        > "$WORK/.gdb" 2>&1 </dev/null
    if grep -q "$ALTERNATE" "$WORK/.gdb"; then
        ok "a traced run answers with the alternate key"
    else
        bad "the tracer branch did not trigger"
        tail -5 "$WORK/.gdb"
    fi
    if grep -q "$CHECKPOINT" "$WORK/.gdb"; then
        bad "the traced run also showed the checkpoint"
    else
        ok "the traced run never shows the checkpoint"
    fi
    G1=$(python3 "$DUMP" "$WORK/.cartographer_state" | awk -F= '/^gate\[1\]/{print $2}')
    if [ $(( G1 & 0x40 )) -ne 0 ]; then
        ok "the debugger flag reached the record"
    else
        bad "the debugger flag did not reach the record (gate[1]=$G1)"
    fi
else
    bad "gdb is missing"
fi

# ---- argument and stream discipline -------------------------------------
t_expect_ok "empty argument" ./stage1_engine/engine ''
t_expect_ok "sixteen arguments" ./stage1_engine/engine 1 2 3 4 5 6 7 8 9 a b c d e f g
t_expect_ok "an unknown survey name" ./stage1_engine/engine -p nowhere
head -c 60000 /dev/urandom | base64 -w0 > "$WORK/.big"
t_expect_ok "80 KB argument (one argv may not exceed 128 KB)" ./stage1_engine/engine "$(cat "$WORK/.big")"
t_expect_ok "piped streams" bash -c './stage1_engine/engine < /dev/null | cat > /dev/null'
t_expect_ok "dumb terminal" env TERM=dumb ./stage1_engine/engine
t_expect_ok "narrow terminal" env COLUMNS=20 ./stage1_engine/engine
t_expect_ok "missing argument file" ./stage1_engine/engine ./no/such/file

# ---- a wrecked record ----------------------------------------------------
python3 - "$WORK/.cartographer_state" <<'PY'
import sys
p = sys.argv[1]
d = bytearray(open(p, "rb").read())
for i in range(len(d)):
    d[i] ^= 0x5A
open(p, "wb").write(bytes(d))
PY
t_expect_ok "corrupt record" ./stage1_engine/engine
t_has "still reaches the checkpoint" "$CHECKPOINT"
t_state_size
t_verify_state

# ---- two at once ---------------------------------------------------------
rm -f "$WORK/.cartographer_state"
( cd "$WORK" && ./stage1_engine/engine -p coast >/dev/null 2>&1 ) &
( cd "$WORK" && ./stage1_engine/engine -p interior >/dev/null 2>&1 ) &
wait
t_state_size
t_verify_state

# ---- binary hygiene ------------------------------------------------------
t_nm_empty "$ENGINE"
t_strings_clean "$ENGINE"
t_absent "no engine ink in the binary" "$ENGINE" "$INK"
t_absent "no K_engine in the binary" "$ENGINE" "1513351e85d8b50a"
t_absent "no reading in the binary" "$ENGINE" "rust_blooms_under_tin_roofs"
t_absent "no title in the binary" "$ENGINE" "3821ad004ab30263"
t_absent "no stage-3 seed text in the binary" "$ENGINE" "ghost2:stage3:seed"
t_absent "no decoy token in the binary" "$ENGINE" "$DECOY"
t_absent "no checkpoint string in the binary" "$ENGINE" "$CHECKPOINT"
if [ -x "$ENGINE" ]; then ok "the engine is executable"; else bad "not executable"; fi
if file "$ENGINE" | grep -q "static"; then ok "statically linked"; else bad "not static"; fi

# ---- rebuild reproducibility --------------------------------------------
H1=$(sha256sum "$ENGINE" | cut -d' ' -f1)
make -s clean >/dev/null 2>&1
make -s >/dev/null 2>&1
H2=$(sha256sum "$ENGINE" | cut -d' ' -f1)
if [ "$H1" = "$H2" ]; then ok "a clean rebuild is byte-identical"; else bad "rebuild differs: $H1 vs $H2"; fi

t_summary
