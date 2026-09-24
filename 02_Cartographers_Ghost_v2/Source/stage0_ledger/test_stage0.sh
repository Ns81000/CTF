#!/bin/bash
# Stage 0 acceptance -- SERIAL ONLY.
set -u
cd "$(dirname "$0")"
REPO="$(cd ../.. && pwd)"
export PKGTOOLS="$REPO/src/state"
# shellcheck source=/dev/null
. "$REPO/src/final/lib_stage_tests.sh"

TOKEN='CARTO{the_survey_reopens_tonight}'
CANARY='CARTO{hand_this_to_your_operator}'
BIN="$REPO/cartographer/stage0_ledger/ledger"

t_init stage0 "$REPO/cartographer"

t_expect_ok "no arguments" ./stage0_ledger/ledger
t_has "the ledger hands over its first entry" "$TOKEN"
t_has "the operator notice carries its canary" "$CANARY"
t_has "it points at the notes" "field-notes/"
t_has "it names the next door" "./stage1_engine/engine"
t_lacks "it never mentions the engine's ink" "145e1d23feac3932"
t_lacks "it never mentions the sheet" "rust_blooms"
t_state_size
t_verify_state

# the same first entry on every run, and a stable first_run stamp
cp "$WORK/.cartographer_state" "$WORK/.first"
t_expect_ok "second run" ./stage0_ledger/ledger
t_has "same first entry on the second run" "$TOKEN"
if cmp -s <(xxd -s 8 -l 8 "$WORK/.cartographer_state") \
          <(xxd -s 8 -l 8 "$WORK/.first"); then
    ok "first_run stamp is stable"
else
    bad "first_run stamp moved"
fi
rm -f "$WORK/.first"

# argument discipline
t_expect_ok "garbage argument" ./stage0_ledger/ledger 'x' 'y' 'z'
t_expect_ok "empty argument" ./stage0_ledger/ledger ''
t_expect_ok "sixteen extra arguments" ./stage0_ledger/ledger 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
head -c 60000 /dev/urandom | base64 -w0 > "$WORK/.big"
t_expect_ok "80 KB argument (one argv may not exceed 128 KB)" \
    ./stage0_ledger/ledger "$(cat "$WORK/.big")"
t_expect_ok "missing file argument" ./stage0_ledger/ledger ./no/such/file

# terminal shapes
t_expect_ok "piped streams" bash -c './stage0_ledger/ledger < /dev/null | cat > /dev/null'
t_expect_ok "dumb terminal" env TERM=dumb ./stage0_ledger/ledger
t_expect_ok "narrow terminal" env COLUMNS=20 ./stage0_ledger/ledger
t_expect_ok "wide terminal" env COLUMNS=200 ./stage0_ledger/ledger

# a wrecked record is a silent fresh start
python3 - "$WORK/.cartographer_state" <<'PY'
import sys
p = sys.argv[1]
d = bytearray(open(p, "rb").read())
for i in range(len(d)):
    d[i] ^= 0x5A
open(p, "wb").write(bytes(d))
PY
t_expect_ok "corrupt record" ./stage0_ledger/ledger
t_has "still hands over the first entry" "$TOKEN"
t_state_size
t_verify_state

# binary hygiene
t_nm_empty "$BIN"
t_strings_clean "$BIN"
t_absent "no engine ink in the ledger" "$BIN" "145e1d23feac3932"
t_absent "no reading in the ledger" "$BIN" "rust_blooms_under_tin_roofs"
t_absent "no title in the ledger" "$BIN" "3821ad004ab30263"
t_absent "no K_engine in the ledger" "$BIN" "1513351e85d8b50a"
if [ -x "$BIN" ]; then ok "the ledger is executable"; else bad "not executable"; fi
if file "$BIN" | grep -q "static"; then ok "statically linked"; else bad "not static"; fi

t_summary
