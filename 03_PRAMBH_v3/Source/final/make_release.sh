#!/usr/bin/env bash
# Deterministic release (spec 6 P10 / 8): clamp mtimes, sorted staging,
# MANIFEST.sha256, TZ=UTC zip -X -@, copy to the RELEASE folder.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
PKG="$ROOT/prambh"
OUTDIR="${1:-/mnt/e/drive-upload/prambh/RELEASE}"
SBX="$(mktemp -d /tmp/p10rel.XXXXXX)"
trap 'rm -rf "$SBX"' EXIT

[ -d "$PKG" ] || { echo "FAIL package-missing ($PKG)"; echo "RELEASE NOT OK"; exit 1; }
find "$PKG" -exec touch -d 2026-01-01T00:00:00Z {} + 2>/dev/null
( cd "$ROOT" && find prambh -type f | sort ) > "$SBX/files.txt"
( cd "$ROOT" && while read -r f; do sha256sum "$f"; done < "$SBX/files.txt" ) \
    > "$SBX/MANIFEST.sha256"
cp "$SBX/MANIFEST.sha256" "$ROOT/MANIFEST.sha256"
rm -f "$ROOT/prambh.zip"
( cd "$ROOT" && TZ=UTC zip -X -q -@ "$ROOT/prambh.zip" < "$SBX/files.txt" )
rc=$?
[ "$rc" -eq 0 ] && echo "PASS zip-built" || { echo "FAIL zip-built"; echo "RELEASE NOT OK"; exit 1; }
Z1="$(sha256sum "$ROOT/prambh.zip" | cut -d' ' -f1)"
echo "zip sha256: $Z1"
echo "files: $(wc -l < "$SBX/files.txt")  manifest: $(sha256sum "$ROOT/MANIFEST.sha256" | cut -d' ' -f1)"
mkdir -p "$OUTDIR"
cp "$ROOT/prambh.zip" "$OUTDIR/prambh.zip"
cp "$ROOT/MANIFEST.sha256" "$OUTDIR/MANIFEST.sha256"
# depot seal encryption (outer encrypted package per room briefing)
openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt \
    -in "$ROOT/prambh.zip" -out "$OUTDIR/prambh.zip.enc" \
    -pass pass:"gate hearth zinc field"
echo "copied to $OUTDIR"
ls -la "$OUTDIR"
echo "RELEASE OK"
