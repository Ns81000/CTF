#!/bin/bash
# build_package.sh -- assemble the solver package, zip it, manifest it.
# Refuses to ship anything not on the allowed list, and refuses to ship
# anything carrying organiser content.
set -u
cd "$(dirname "$0")/../.." || exit 1
PKG=cartographer
ZIPDIR=organizer-private
ZIP=$ZIPDIR/cartographer.zip
MAN=organizer-private/MANIFEST.sha256

# ---- the package must exist and be complete ------------------------------
for f in README_FOR_SOLVER.txt HUMAN_OPERATOR_NOTICE.txt \
         stage0_ledger/ledger stage1_engine/engine stage1_engine/profile.notes \
         stage2_sheet/sheet stage2_sheet/survey_frame.png \
         stage2_sheet/survey_tape.wav stage3_oracle/oracle \
         stage4_seal/seal stage5_title/validate; do
    if [ ! -f "$PKG/$f" ]; then
        echo "MISSING $PKG/$f"
        exit 1
    fi
done

# ---- the allowed list (solver-facing files only; the one record the
# tools keep is never packaged) -------------------------------------------
find "$PKG" -type f -not -name '.cartographer_state*' | sed "s|^$PKG/||" | sort > /tmp/pkg_files.$$ || exit 1
cat > /tmp/pkg_allowed.$$ <<'EOF'
HUMAN_OPERATOR_NOTICE.txt
README_FOR_SOLVER.txt
stage0_ledger/ledger
stage1_engine/engine
stage1_engine/profile.notes
stage2_sheet/sheet
stage2_sheet/survey_frame.png
stage2_sheet/survey_tape.wav
stage3_oracle/oracle
stage4_seal/seal
stage5_title/validate
EOF
cat >> /tmp/pkg_allowed.$$ <<'EOF'
field-notes/01-survey-log.md
field-notes/02-lab-notes.md
field-notes/ANSWER.txt
field-notes/DEPRECATED_BUILD.txt
field-notes/KNOWN_ISSUES.txt
field-notes/SOLUTION_DRAFT.py
field-notes/ai-policy.md
field-notes/checksums.txt
EOF
sort -o /tmp/pkg_allowed.$$ /tmp/pkg_allowed.$$
BAD=$(comm -23 /tmp/pkg_files.$$ /tmp/pkg_allowed.$$ | head -5)
if [ -n "$BAD" ]; then
    echo "FILES NOT ON THE ALLOWED LIST:"
    echo "$BAD"
    rm -f /tmp/pkg_files.$$ /tmp/pkg_allowed.$$
    exit 1
fi
MISSING=$(comm -13 /tmp/pkg_files.$$ /tmp/pkg_allowed.$$ | head -5)
if [ -n "$MISSING" ]; then
    echo "ALLOWED FILES MISSING FROM THE PACKAGE:"
    echo "$MISSING"
    rm -f /tmp/pkg_files.$$ /tmp/pkg_allowed.$$
    exit 1
fi
rm -f /tmp/pkg_files.$$ /tmp/pkg_allowed.$$

# ---- organiser content must not be in the package -------------------------
if grep -rqiE 'organizer-private|KEYS_V2|SOLVE_PATH_PRIVATE|SESSION_1_LOG|TRAP_CATALOGUE|COST_MODEL' \
       "$PKG" 2>/dev/null; then
    echo "ORGANISER CONTENT INSIDE THE PACKAGE"
    grep -rliE 'organizer-private|KEYS_V2|SOLVE_PATH_PRIVATE|SESSION_1_LOG|TRAP_CATALOGUE|COST_MODEL' "$PKG"
    exit 1
fi
find "$PKG" -name '*.md' -not -path "$PKG/field-notes/*" | grep -q . && {
    echo "MD OUTSIDE FIELD-NOTES"
    exit 1
}
find "$PKG" \( -name '*.c' -o -name '*.h' -o -name '*.sh' -o -name '*.py' \
    -o -name 'Makefile' -o -name '*.o' -o -name '*.a' \) -not -path "$PKG/field-notes/*" \
    | grep -q . && {
    echo "SOURCE OR BUILD ARTIFACTS INSIDE THE PACKAGE"
    exit 1
}
[ -e "$PKG/.git" -o -e "$PKG/.cartographer_state" ] && {
    echo "STATE OR VCS INSIDE THE PACKAGE"
    exit 1
}

# ---- zip and manifest (deterministic: sorted order, fixed timestamps) -----
mkdir -p "$ZIPDIR"
rm -f "$ZIP" "$MAN"
STAGE=$(mktemp -d) || exit 1
trap 'rm -rf "$STAGE"' EXIT
( cd "$PKG" && find . -type f -not -name '.cartographer_state*' \
    | sed 's|^\./||' | LC_ALL=C sort ) > "$STAGE/list" || exit 1
while IFS= read -r f; do
    mkdir -p "$STAGE/tree/$(dirname "$f")"
    cp -p "$PKG/$f" "$STAGE/tree/$f" || exit 1
done < "$STAGE/list"
find "$STAGE/tree" -exec touch -h -d '2026-01-01 00:00:00 UTC' {} +
( cd "$STAGE/tree" && TZ=UTC zip -q -X "$STAGE/cartographer.zip" -@ < "$STAGE/list" ) || exit 1
mv "$STAGE/cartographer.zip" "$ZIP"
rm -rf "$STAGE"
trap - EXIT
( cd "$PKG" && find . -type f -not -name '.cartographer_state*' | sed 's|^\./||' | LC_ALL=C sort | \
    xargs sha256sum ) > "$MAN"
echo "PACKAGED $(wc -l < "$MAN") files"
printf 'zip   %s\n' "$(sha256sum "$ZIP" | awk '{print $1}')"
