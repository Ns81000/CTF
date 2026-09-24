#!/bin/bash
set -u
cd "$(dirname "$0")/../.." || exit 1
PKG=cartographer
FAILED=0
CHECKS=0
DUMP=$(mktemp)

{
for b in "$PKG"/stage0_ledger/ledger "$PKG"/stage1_engine/engine \
         "$PKG"/stage2_sheet/sheet "$PKG"/stage3_oracle/oracle \
         "$PKG"/stage4_seal/seal "$PKG"/stage5_title/validate; do
    [ -f "$b" ] && strings -n 4 "$b"
done
for c in "$PKG"/stage2_sheet/survey_frame.png \
         "$PKG"/stage2_sheet/survey_tape.wav; do
    [ -f "$c" ] && strings -n 4 "$c"
done
} > "$DUMP"

absent() {
    CHECKS=$((CHECKS + 1))
    if grep -qiF -- "$1" "$DUMP" \
        || grep -rqiF -- "$1" "$PKG" --include='*.txt' --include='*.md' \
             --include='*.py' --include='*.json' 2>/dev/null; then
        if [ -n "$TRAILER_ABSENT" ]; then
            hit=0
            for w in $TRAILER_ABSENT; do
                if [ "$1" = "$w" ]; then hit=1; fi
            done
            if [ $hit = 1 ] && grep -qiF -- "$1" "$DUMP" >/dev/null; then
                echo "  FAIL leak: $1"
                FAILED=$((FAILED + 1))
                return
            fi
            echo "  PASS exception documented: $1"
            return
        fi
        echo "  FAIL leak: $1"
        FAILED=$((FAILED + 1))
    else
        echo "  PASS no leak: $1"
    fi
}

present() {
    CHECKS=$((CHECKS + 1))
    if grep -qiF -- "$1" "$DUMP" >/dev/null 2>&1 \
        || grep -rqiF -- "$1" "$PKG" --include='*' >/dev/null 2>&1; then
        echo "  PASS present by design: $1"
    else
        echo "  FAIL missing by design: $1"
        FAILED=$((FAILED + 1))
    fi
}

TRAILER_ABSENT=""
TRAILER_PRESENT=""

while [ $# -gt 0 ]; do
    case "$1" in
        --except) TRAILER_ABSENT="$TRAILER_ABSENT $2"; shift 2 ;;
        --only)   TRAILER_PRESENT="$TRAILER_PRESENT $2"; shift 2 ;;
        *) echo "unknown flag $1"; exit 2 ;;
    esac
done

# the design-correct exceptions (front door, registered decoys, reward,
# press metadata by honour, mask constants by the state pattern)
absent "the_survey_reopens_tonight"
absent "3821ad004ab30263_e509312ae8a2e0ad_145e1d23feac3932_rust_blooms_under_tin_roofs"
present "54a3eb304734135c5308bf186b21c839"
present "a_warm_plate_and_a_full_ring"

# inks and their kin (absent from the package), full strings
absent "145e1d23feac3932"
absent "rust_blooms_under_tin_roofs"
absent "rust_blooms"
absent "tin_roofs"
absent "e509312ae8a2e0ad"
absent "3821ad004ab30263"
absent "e509312ae8a2e0adeb4c0b2517a3f842ca5aff0d7bce2c117f47a2dcf028e034"
absent "f059e3a8ec8fb6a1"
absent "64c4ad4ea9c40319"
absent "f5ea27c63ed89565"
absent "bab073aec06d6b60"
absent "1513351e85d8b50a"
absent "040ec499dd20e571"
absent "771760977412952853"
absent "01d94d492a46ce3d"
absent "01d94d49"
# naive-layer decoy: registered, shipped as a decoy per spec 4.3.  read the
# lane the same way the stage-2 suite does (sweep.py --naive on the shipped
# frame; the stage-2 suite asserts this exact lane and token independently)
CHECKS=$((CHECKS + 1))
if PYTHONDONTWRITEBYTECODE=1 python3 src/stage2_sheet/sweep.py \
        "$PKG/stage2_sheet/survey_frame.png" "$PKG/stage2_sheet/survey_tape.wav" \
        --naive 2>/dev/null | grep -q "the_coast_was_drawn_twice"; then
    echo "  PASS the naive lane lands exactly on the registered decoy"
else
    echo "  FAIL the naive lane does not read the registered decoy"
    FAILED=$((FAILED + 1))
fi

# the press metadata lives in the tape by design (the honest route reads
# it raw); the generator and the suites already assert it byte-exactly
present "c3240a6373072eab"

# exact seed strings
absent "ghost2:stage0:token:v1"
absent "ghost2:stage1:key:v1"
absent "ghost2:stage1:vm:map:v1"
absent "ghost2:stage1:bytecode:v1"
absent "ghost2:stage1:decoy:key:v1"
absent "ghost2:stage1:debug:key:v1"
absent "ghost2:stage2:reading:v1"
absent "ghost2:stage2:press:v1"
absent "ghost2:stage2:decoy:layer:v1"
absent "ghost2:stage2:middle:layer:v1"
absent "ghost2:stage2:dither:v1"
absent "ghost2:stage2:tape:v1"
absent "ghost2:stage3:cipher:v1"
absent "ghost2:stage3:seed:v1"
absent "ghost2:stage3:tally:v1"
absent "ghost2:stage3:cold:v1"
absent "ghost2:stage4:cipher:v1"
absent "ghost2:stage4:key:v1"
absent "ghost2:stage4:decoy:key:v1"
absent "ghost2:stage5:title:v1"
absent "ghost2:stage5:decoy:draft:v1"
absent "CARTO_TEST_TIME_SCALE"

# machine provenance
absent "ns8pc"
absent "/home/"
absent "drive-upload"

# v1 leftovers
absent "stage2_stego"
absent "s2_inflate_payload_marker"

printf '  %d leak checks, %d failed\n' "$CHECKS" "$FAILED"
rm -f "$DUMP"
if [ "$FAILED" = "0" ]; then
    echo "OK"
    exit 0
fi
echo "NOT OK"
exit 1
