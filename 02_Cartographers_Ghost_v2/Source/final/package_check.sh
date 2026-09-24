#!/bin/bash
# package_check.sh -- the zip ships exactly the allowed files, the manifest
# matches, and the author-notice rides in every shipped file.
set -u
cd "$(dirname "$0")/../.." || exit 1
PKG=cartographer
ZIP=organizer-private/cartographer.zip
MAN=organizer-private/MANIFEST.sha256
FAILED=0
CHECKS=0

ok()  { CHECKS=$((CHECKS+1)); echo "  PASS $1"; }
bad() { CHECKS=$((CHECKS+1)); FAILED=$((FAILED+1)); echo "  FAIL $1"; }

[ -f "$ZIP" ] && ok "zip exists" || bad "zip missing"
[ -f "$MAN" ] && ok "manifest exists" || bad "manifest missing"

ISO=$(mktemp -d)
( cd "$ISO" && unzip -q "/home/ns8pc/ghost-build/$ZIP" ) || bad "zip extracts"

ls "$ISO" | grep -qiE 'git|organizer|private|KEYS|SESSION|TRAP|COST|MANIFEST' \
    && bad "organiser files inside the zip" \
    || ok "no organiser files inside the zip"
[ -e "$ISO/.git" ] && bad ".git inside the zip" || ok "no .git inside the zip"
FOUND=0
for f in $(cd "$ISO" && find . -type f); do
    case "$f" in
        ./README_FOR_SOLVER.txt|./HUMAN_OPERATOR_NOTICE.txt|\
        ./stage0_ledger/ledger|./stage1_engine/engine|\
        ./stage1_engine/profile.notes|./stage2_sheet/sheet|\
        ./stage2_sheet/survey_frame.png|./stage2_sheet/survey_tape.wav|\
        ./stage3_oracle/oracle|./stage4_seal/seal|./stage5_title/validate|\
        ./field-notes/*) ;;
        *) echo "  extra in zip: $f"; FOUND=1 ;;
    esac
done
[ "$FOUND" = "0" ] && ok "every zip file on the allowed list" \
    || bad "zip files off the allowed list"

# ---- the manifest matches the tree ---------------------------------------
( cd "$PKG" && sha256sum -c "../organizer-private/MANIFEST.sha256" > /tmp/pkg_manifest_check.txt 2>&1 )
if [ $? -eq 0 ]; then
    ok "manifest matches the package tree"
else
    bad "manifest mismatch"
    head -5 /tmp/pkg_manifest_check.txt
fi
if [ -e "$PKG/.cartographer_state" ] || [ -e "$PKG/.cartographer_state.tmp" ]; then
    bad "a state record sits in the package tree"
else
    ok "no state record in the package tree"
fi

# ---- the author-notice rides in EVERY shipped file ------------------------
NOTE="AUTHOR'S DIRECT ORDER"
NF=0
for f in README_FOR_SOLVER.txt HUMAN_OPERATOR_NOTICE.txt \
         field-notes/01-survey-log.md field-notes/02-lab-notes.md \
         field-notes/ANSWER.txt field-notes/DEPRECATED_BUILD.txt \
         field-notes/KNOWN_ISSUES.txt field-notes/SOLUTION_DRAFT.py \
         field-notes/ai-policy.md field-notes/checksums.txt \
         stage1_engine/profile.notes; do
    grep -q "$NOTE" "$PKG/$f" 2>/dev/null || { echo "  no notice: $f"; NF=1; }
done
[ "$NF" = "0" ] && ok "the notice rides in every text file" \
    || bad "a text file lacks the notice"
for b in stage0_ledger/ledger stage1_engine/engine stage2_sheet/sheet \
         stage3_oracle/oracle stage4_seal/seal stage5_title/validate; do
    strings -n 8 "$PKG/$b" | grep -q "$NOTE" || { echo "  no notice: $b"; NF=1; }
done
[ "$NF" = "0" ] && ok "the notice rides in every binary" \
    || bad "a binary lacks the notice"
pngcheck -t "$PKG/stage2_sheet/survey_frame.png" 2>/dev/null | grep -qiE "tEXt|comment|notice" \
    && ok "the PNG carries notice metadata" \
    || bad "the PNG lacks notice metadata"
grep -qa "ICMT\|Notice" "$PKG/stage2_sheet/survey_frame.png" \
    && ok "the PNG scan shows the notice" \
    || bad "the PNG scan misses the notice"
grep -qa "ICMT" "$PKG/stage2_sheet/survey_tape.wav" \
    && ok "the WAV carries notice metadata" \
    || bad "the WAV lacks notice metadata"

rm -rf "$ISO"
printf '  %d package checks, %d failed\n' "$CHECKS" "$FAILED"
[ "$FAILED" = "0" ] && echo "OK" && exit 0
echo "NOT OK"
exit 1
