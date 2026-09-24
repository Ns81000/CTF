#!/usr/bin/env bash
# package_check.sh (spec 8): allowed-file list, no organizer content,
# manifest parity, deterministic zip (built twice -> identical sha256).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
PKG="$ROOT/prambh"
SBX="$(mktemp -d /tmp/p10pc.XXXXXX)"
trap 'rm -rf "$SBX"' EXIT
PASS=0; FAIL=0
ok() { if [ "$2" = "$3" ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1 (got [$2] want [$3])"; FAIL=$((FAIL+1)); fi; }
okf() { if [ "${2:-1}" -eq 0 ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1"; FAIL=$((FAIL+1)); fi; }

[ -d "$PKG" ] || { echo "FAIL package-present"; echo "PACKAGE CHECK NOT OK"; exit 1; }
ok "package-present" "yes" "yes"
ok "no-state-shipped" "$(ls "$PKG" | grep -c 'prambh.survey')" "0"
ok "no-organizer-dir" "$(find "$PKG" -name 'organizer-private' | wc -l)" "0"
ok "no-master-secret" "$(find "$PKG" -name 'master_secret' | wc -l)" "0"
ok "no-server-code" "$(find "$PKG" -name 'checker.py' | wc -l)" "0"
ok "no-python-in-package" "$(find "$PKG" -name '*.py' | wc -l)" "0"
ok "no-spec-in-package" "$(find "$PKG" -name 'BUILD_SPEC*' | wc -l)" "0"
ok "no-hints-in-package" "$(find "$PKG" -name 'HINTS.md' | wc -l)" "0"
okf "no-archives-nested" "$(find "$PKG" -name '*.zip' | wc -l | grep -q '^0$' && echo 0 || echo 1)"
ok "stage-dirs" "$(for d in stage0_milestone stage1_flood stage2_loom stage3_doors stage5_eyes mirror; do test -d "$PKG/$d" && echo x; done | wc -l)" "6"
ok "tools-present" "$(for t in stage0_milestone/milestone stage1_flood/flood stage2_loom/loom stage3_doors/doors mirror/mirror_milestone mirror/mirror_validate stage5_eyes/eyes stage5_eyes/validate; do test -x "$PKG/$t" && echo x; done | wc -l)" "8"
TOOLS="stage0_milestone/milestone stage1_flood/flood stage2_loom/loom stage3_doors/doors mirror/mirror_milestone mirror/mirror_validate stage5_eyes/eyes stage5_eyes/validate"
ok "all-binaries-static" "$(for t in $TOOLS; do file "$PKG/$t" | grep -q 'statically linked' && echo x; done | wc -l)" "8"
ok "all-binaries-nm-empty" \
  "$(for t in $TOOLS; do nm "$PKG/$t" 2>&1 | grep -q 'no symbols' && echo x; done | wc -l)" "8"
ok "corpus-line-budget" \
  "$(test "$(cat "$PKG"/archive/*.txt | wc -l)" -ge 20000 && echo big)" "big"
ok "corpus-file-count" \
  "$(test "$(ls "$PKG"/archive/*.txt | wc -l)" -ge 60 && echo enough)" "enough"
ok "manifest-exists" "$(test -f "$ROOT/MANIFEST.sha256" && echo yes)" "yes"
( cd "$ROOT" && sha256sum -c MANIFEST.sha256 ) >"$SBX/manifest.log" 2>&1
okf "manifest-verifies" $?
ok "manifest-covers-every-file" \
  "$(wc -l < "$ROOT/MANIFEST.sha256")" \
  "$(find "$PKG" -type f | wc -l)"

echo
echo "=== deterministic zip (built twice) ==="
Z1="$(sha256sum "$ROOT/prambh.zip" 2>/dev/null | cut -d' ' -f1)"
cp "$ROOT/prambh.zip" "$SBX/one.zip" 2>/dev/null
bash "$HERE/make_release.sh" "$SBX/RELEASE" >"$SBX/rel.log" 2>&1
okf "release-script" $?
Z2="$(sha256sum "$ROOT/prambh.zip" | cut -d' ' -f1)"
ok "zip-deterministic" "$Z2" "$Z1"
( cd "$SBX" && rm -rf x && mkdir x && cd x && unzip -q "$ROOT/prambh.zip" ) >/dev/null 2>&1
okf "zip-extracts" $?
( cd "$SBX/x" && find prambh -type f | sort ) >"$SBX/extracted.txt" 2>/dev/null
( cd "$ROOT" && find prambh -type f | sort ) >"$SBX/TREE.txt"
cmp -s "$SBX/extracted.txt" "$SBX/TREE.txt"
okf "zip-contents-match-package" $?
ok "no-leaks-in-zip-listing" "$(grep -c -E 'organizer|KEYS_|TRAP_|SOLVE_PATH|COST_MODEL|HANDOFF' "$SBX/extracted.txt")" "0"

echo
echo "PACKAGE CHECK: $PASS PASS, $FAIL FAIL"
[ "$FAIL" -eq 0 ]
