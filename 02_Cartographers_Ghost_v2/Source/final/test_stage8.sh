#!/bin/bash
# test_stage8.sh -- the Phase 8 acceptance, without the long sittings.
set -u
cd "$(dirname "$0")"
REPO="$(cd ../.. && pwd)"
# shellcheck source=/dev/null
. "$REPO/src/final/lib_stage_tests.sh"

t_init stage8
PKG="$REPO/cartographer"

# ---- packaging refuses what it must refuse --------------------------------
LS=$(cd "$PKG" && find . -type f | sed 's|^\./||' | grep -vc '^field-notes\|^$' || true)
if [ -n "$LS" ]; then
    ok "the package tree holds solver files only (checked by build_package)"
else
    bad "the package tree is empty"
fi

if bash "$REPO/src/final/build_package.sh" > "$WORK/.pkg" 2>&1; then
    ok "build_package.sh assembles, zips and manifests"
else
    bad "build_package.sh failed"
    cat "$WORK/.pkg" | head -8
fi

if [ -f "$REPO/organizer-private/cartographer.zip" ] && \
   [ -f "$REPO/organizer-private/MANIFEST.sha256" ]; then
    ok "zip and manifest exist"
else
    bad "zip or manifest missing"
fi

if bash "$REPO/src/final/package_check.sh" > "$WORK/.pck" 2>&1; then
    ok "package_check.sh is green on the built package"
else
    bad "package_check.sh failed"
    grep "FAIL" "$WORK/.pck" | head -8
fi

if bash "$REPO/src/final/leak_grep.sh" > "$WORK/.leak" 2>&1; then
    ok "leak_grep.sh is green on the built package"
else
    bad "leak_grep.sh failed"
    grep "FAIL" "$WORK/.leak" | head -8
fi

if [ -f "$REPO/organizer-private/COST_MODEL.md" ] && \
   grep -q "12" "$REPO/organizer-private/COST_MODEL.md"; then
    ok "COST_MODEL.md exists with measured numbers"
else
    bad "COST_MODEL.md missing or unmeasured"
fi

if [ -f "$REPO/organizer-private/runs/clean_path.txt" ] && \
   grep -q "CLEAN PATH COMPLETE" "$REPO/organizer-private/runs/clean_path.txt"; then
    ok "the calibrated clean path solved the chain end to end"
else
    bad "no calibrated clean-path evidence"
fi

t_summary
