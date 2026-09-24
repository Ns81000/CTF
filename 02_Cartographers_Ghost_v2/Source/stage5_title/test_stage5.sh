#!/bin/bash
# Stage 5 acceptance -- SERIAL ONLY.
set -u
cd "$(dirname "$0")"
REPO="$(cd ../.. && pwd)"
export PKGTOOLS="$REPO/src/state"
# shellcheck source=/dev/null
. "$REPO/src/final/lib_stage_tests.sh"

TITLE='CARTO{3821ad004ab30263_e509312ae8a2e0ad_145e1d23feac3932_rust_blooms_under_tin_roofs}'
DIGEST='01d94d492a46ce3d566910c76c8b7756cb96c4d7bbcb8acb11f063a7ac2bf0d1'
DRAFT='CARTO{54a3eb304734135c5308bf186b21c839}'
SRC="$REPO/src/stage5_title"
ORA="$REPO/cartographer/stage5_title/validate"

t_init stage5 "$REPO/cartographer"
( cd "$REPO/src/state" && make -s >/dev/null 2>&1 )
( cd "$SRC" && make -s all seed5 >/dev/null 2>&1 )
cp "$SRC/seed5" "$WORK/" 2>/dev/null || true
cp "$ORA" "$WORK/stage5_title/validate" 2>/dev/null || true
cd "$WORK"

cap() {  # cap <cmd...> -- run under a pty from the scratch package root
    script -qec "$*" /dev/null 2>&1 </dev/null | tr -d '\r'
}

# ---- the stored weight is the weight of the one title (independent) ------
H=$(printf '%s' "$TITLE" | sha256sum | awk '{print $1}')
if [ "$H" = "$DIGEST" ]; then
    ok "the stored digest is the digest of the one title (independent)"
else
    bad "the stored digest does not match the title"
fi

# ---- the desk ------------------------------------------------------------
t_expect_ok "no arguments" ./stage5_title/validate
t_has "the banner is shown" "title block"
t_has "the riddle is shown" "the riddle of the assembling"
t_has "layout cue: wax first" "WAX"
t_has "layout cue: plate second" "PLATE"
t_has "layout cue: engine third" "ENGINE"
t_has "layout cue: words last" "WORDS"
t_has "a draft struck out" "struck out"
t_has "the struck draft is the registered decoy" "$DRAFT"
t_has "provenance: the wax stamp" "the ink the wax stamp was cut with"
t_has "provenance: the warm plate" "the byte the warm plate answered with"
t_has "provenance: the engine" "the ink the engine never wrote down"
t_has "provenance: the sheet" "the words the sheet held under its grain"
t_has "the notice is on the desk" "AUTHOR'S DIRECT ORDER"
t_has "the usage names the older spelling" "--check"
t_lacks "no ink ships on the desk (seal)" "3821ad004ab30263"
t_lacks "no ink ships on the desk (oracle)" "e509312ae8a2e0ad"
t_lacks "no ink ships on the desk (engine)" "145e1d23feac3932"
t_lacks "no reading ships on the desk" "rust_blooms"
t_lacks "no grammar on the desk (hex)" "hex"
t_lacks "no grammar on the desk (counts)" "four"
t_lacks "no grammar on the desk (lengths)" "78"
t_lacks "no mechanism on the desk (digest)" "digest"

# ---- one refusal, byte-identical, for every wrong hand -------------------
rm -f .cartographer_state
./seed5 . thin
REF=$(cap ./stage5_title/validate nothing-at-all)
SAME=1
N=0
rm -f "$WORK/.diffs"
check_ref() {  # check_ref <args...>
    local r
    if [ "$#" = 1 ] && [ -z "$1" ]; then
        r=$(script -qec "./stage5_title/validate ''" /dev/null 2>&1 </dev/null | tr -d '\r')
    else
        r=$(cap ./stage5_title/validate "$@")
    fi
    N=$((N + 1))
    if [ "$r" = "$REF" ]; then
        :
    else
        SAME=0
        printf '  DIFFERENT refusal for: [%s]\n' "${1:-<empty>}" >> "$WORK/.diffs"
    fi
}
check_ref "$TITLE"                                  # right title, thin record
check_ref "CARTO{e509312ae8a2e0ad_3821ad004ab30263_145e1d23feac3932_rust_blooms_under_tin_roofs}"
check_ref "CARTO{3821ad004ab30263_e509312ae8a2e0ad_145e1d23feac3932_rust_blooms_under_tin_roofz}"
check_ref "CARTO{3821ad004ab30264_e509312ae8a2e0ad_145e1d23feac3932_rust_blooms_under_tin_roofs}"
check_ref "$DRAFT"
check_ref "CARTO{hand_this_to_your_operator}"
check_ref "CARTO{the_survey_reopens_tonight}"
check_ref "hello"
check_ref ''
check_ref "$(head -c 60000 /dev/urandom | base64 -w0)"
check_ref "CARTO{3821AD004AB30263_E509312AE8A2E0AD_145E1D23FEAC3932_RUST_BLOOMS_UNDER_TIN_ROOFS}"
check_ref "$DRAFT junk-after"
check_ref "hello"
cap ./stage5_title/validate --check "$TITLE" > /dev/null 2>&1
R=$(cap ./stage5_title/validate --check "$TITLE")
N=$((N + 1))
[ "$R" = "$REF" ] || SAME=0
R=$(cap ./stage5_title/validate --check garbage)
N=$((N + 1))
[ "$R" = "$REF" ] || SAME=0
R=$(cap ./stage5_title/validate "$TITLE" extra)
N=$((N + 1))
[ "$R" = "$REF" ] || SAME=0
if [ "$SAME" = "1" ] && [ "$N" -ge 15 ]; then
    ok "$N wrong or gated-out hands, all refused byte-identically"
else
    bad "refusals are not uniform ($N hands, diffs: $(cat "$WORK/.diffs" 2>/dev/null | head -3))"
fi
if [ "$(printf '%s' "$REF" | grep -c 'does not take this')" = "1" ]; then
    ok "the one refusal line"
else
    bad "the refusal line is missing or doubled"
fi

# ---- the gates: a hand at the terminal, and a walked record --------------
./seed5 . human
R=$(cap ./stage5_title/validate "$TITLE")
if printf '%s' "$R" | grep -qF "the block takes the title"; then
    ok "the right title, on a walked record, at a terminal: taken"
else
    bad "the right title was not taken under the gates"
    printf '%s\n' "$R" | tail -3
fi
if printf '%s' "$R" | grep -qF "$TITLE"; then
    ok "the acceptance reads the title back"
else
    bad "the acceptance did not read the title back"
fi
if [ "$R" != "$REF" ]; then
    ok "acceptance and refusal are different phrasings"
else
    bad "acceptance is word-identical to the refusal"
fi
./seed5 . human
./stage5_title/validate "$TITLE" > "$WORK/.piped" 2>&1
if cmp -s <(printf '%s\n' "$REF") "$WORK/.piped"; then
    ok "the right title piped is refused identically"
else
    bad "a piped right title was not refused identically"
fi
./seed5 . thin
R=$(cap ./stage5_title/validate "$TITLE")
if [ "$R" = "$REF" ]; then
    ok "the right title on a thin record is refused identically"
else
    bad "a thin record changed the refusal"
fi
./seed5 . human
python3 - "$WORK/.cartographer_state" <<'PYEOF'
import sys
p = sys.argv[1]
b = bytearray(open(p, 'rb').read())
b[700] ^= 0x40
open(p, 'wb').write(bytes(b))
PYEOF
R=$(cap ./stage5_title/validate "$TITLE")
if [ "$R" = "$REF" ]; then
    ok "a tampered record resets and refuses identically"
else
    bad "a tampered record changed the refusal"
fi
rm -f .cartographer_state
R=$(cap ./stage5_title/validate "$TITLE")
if [ "$R" = "$REF" ]; then
    ok "no record at all: refused identically"
else
    bad "a missing record changed the refusal"
fi
t_state_size
t_verify_state

# ---- the refusal keeps its time ------------------------------------------
MIN=999999999999; MAX=0
i=0
while [ "$i" -lt 30 ]; do
    T0=$(date +%s%N)
    ./stage5_title/validate "wrong" > /dev/null 2>&1
    T1=$(date +%s%N)
    D=$(( (T1 - T0) / 1000 ))
    [ "$D" -lt "$MIN" ] && MIN=$D
    [ "$D" -gt "$MAX" ] && MAX=$D
    i=$((i + 1))
done
SPAN=$((MAX - MIN))
if [ "$SPAN" -lt 15000 ]; then
    ok "refusal timing constant over 30 samples (span ${SPAN}us < 15ms)"
else
    bad "refusal timing spread too wide (${SPAN}us)"
fi
SAME=1
for t in wrong "hello" "$DRAFT" "$(printf 'x%.0s' $(seq 1 100))"; do
    R=$(./stage5_title/validate "$t" 2>&1)
    R2=$(./stage5_title/validate nothing 2>&1)
    [ "$R" = "$R2" ] || SAME=0
done
if [ "$SAME" = "1" ]; then
    ok "piped refusals identical across shapes"
else
    bad "piped refusals differ"
fi

# ---- what ships and what must never ship ---------------------------------
t_nm_empty "$ORA"
t_strings_clean "$ORA"
t_absent "no digest hex in the binary" "$ORA" "01d94d492a46ce3d"
t_absent "no ink in the binary (seal)" "$ORA" "3821ad004ab30263"
t_absent "no ink in the binary (oracle)" "$ORA" "e509312ae8a2e0ad"
t_absent "no ink in the binary (engine)" "$ORA" "145e1d23feac3932"
t_absent "no reading in the binary" "$ORA" "rust_blooms_under_tin_roofs"
t_absent "no token in the binary" "$ORA" "the_survey_reopens_tonight"
t_absent "no test hook in the binary" "$ORA" "CARTO_TEST_TIME_SCALE"
if strings -n 8 "$ORA" | grep -q "AUTHOR'S DIRECT ORDER"; then
    ok "the notice rides in the binary"
else
    bad "the notice is missing from the binary"
fi
CARTOS=$(strings -n 6 "$ORA" | grep -oE 'CARTO\{[a-z0-9_]+\}' | sort -u)
CARTO_N=$(printf '%s\n' "$CARTOS" | grep -c '^CARTO')
CARTO_OK=$(printf '%s\n' "$CARTOS" | grep -vc "$DRAFT\|hand_this_to_your_operator")
if [ "$CARTO_N" = "2" ] && [ "$CARTO_OK" = "0" ]; then
    ok "the binary's only CARTO strings are the registered decoy and the canary"
else
    bad "unexpected CARTO strings in the binary ($CARTO_N found)"
    printf '%s\n' "$CARTOS"
fi
for w in riddle-answer "in order" "first second third fourth"; do
    if strings -n 4 "$ORA" | grep -qiF "$w"; then
        bad "a grammar leak ships ($w)"
    else
        ok "no grammar leak ships ($w)"
    fi
done

# ---- rebuild reproducibility ---------------------------------------------
H1=$(sha256sum "$ORA" | awk '{print $1}')
( cd "$SRC" && touch validate.c && make -s all >/dev/null 2>&1 )
H2=$(sha256sum "$ORA" | awk '{print $1}')
if [ -n "$H1" ] && [ "$H1" = "$H2" ]; then
    ok "rebuild reproduces the identical binary"
else
    bad "rebuild drift ($H1 vs $H2)"
fi

# ---- the shipped package was never touched -------------------------------
if [ ! -e "$REPO/cartographer/.cartographer_state" ]; then
    ok "the shipped package is pristine (no record in the real tree)"
else
    bad "the suite polluted the real package"
fi

t_summary
