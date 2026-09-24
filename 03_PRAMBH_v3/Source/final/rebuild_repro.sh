#!/usr/bin/env bash
# rebuild_repro.sh (spec 8): build the package twice from scratch and
# compare every file hash.  Chain-derived files come from the harvested
# runs, so the comparison covers the generators, the tools and the build.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
SBX="$(mktemp -d /tmp/p10reb.XXXXXX)"
trap 'rm -rf "$SBX"' EXIT
PASS=0; FAIL=0
okf() { if [ "${2:-1}" -eq 0 ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1"; FAIL=$((FAIL+1)); fi; }
ok() { if [ "$2" = "$3" ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1"; FAIL=$((FAIL+1)); fi; }

python3 "$HERE/build_package.py" "$SBX/a" >"$SBX/a.log" 2>&1
okf "build-run-1" $?
python3 "$HERE/build_package.py" "$SBX/b" >"$SBX/b.log" 2>&1
okf "build-run-2" $?
( cd "$SBX/a" && find . -type f | sort | while read -r f; do sha256sum "$f"; done ) \
    >"$SBX/a.txt"
( cd "$SBX/b" && find . -type f | sort | while read -r f; do sha256sum "$f"; done ) \
    >"$SBX/b.txt"
cmp -s "$SBX/a.txt" "$SBX/b.txt"
okf "two-builds-byte-identical" $?
ok "file-count-stable" "$(wc -l < "$SBX/a.txt")" "$(wc -l < "$SBX/b.txt")"
if [ -d "$ROOT/prambh" ]; then
  ( cd "$ROOT/prambh" && find . -type f | sort | while read -r f; do sha256sum "$f"; done ) \
      >"$SBX/live.txt"
  cmp -s "$SBX/a.txt" "$SBX/live.txt"
  okf "shipped-package-matches-rebuild" $?
fi
echo
if [ "$FAIL" -eq 0 ]; then echo "REBUILD REPRO OK"; else echo "REBUILD REPRO NOT OK"; fi
[ "$FAIL" -eq 0 ]
