#!/bin/bash
# P4 suite: flood corpus + decoy plates + flood tool (spec 4.3).
cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"
PRIV="$(cd ../.. && pwd)/organizer-private"
PASS=0; FAIL=0
ok() { if [ "$2" = "$3" ]; then echo "PASS $1"; PASS=$((PASS+1)); else echo "FAIL $1 (got [$2] want [$3])"; FAIL=$((FAIL+1)); fi }
okf() { if [ "$2" -eq 0 ]; then echo "PASS $1"; PASS=$((PASS+1)); else echo "FAIL $1 (rc=$2)"; FAIL=$((FAIL+1)); fi }

GEN=/tmp/prambh_flood_gen
PKG=/tmp/prambh_flood_pkg
rm -rf "$GEN" "$PKG"
mkdir -p "$GEN" "$PKG"

python3 corpus_gen.py "$GEN/corpus1" >/dev/null
okf "corpus-gen-run" $?
ok "words-header" "$(test -f flood_words.h && echo yes)" "yes"
python3 corpus_gen.py "$GEN/corpus2" >/dev/null
diff -r "$GEN/corpus1" "$GEN/corpus2" >/dev/null
okf "corpus-byte-identical-regeneration" $?
ok "folio-count" "$(ls "$GEN/corpus1" | wc -l)" "450"
ok "corpus-line-budget" "$(cat "$GEN"/corpus1/*.txt | wc -l | awk '{print ($1>=20000)?"yes":"no"}')" "yes"

python3 ../plates/plate_gen.py "$GEN/plates1" >/dev/null
okf "plate-gen-run" $?
python3 ../plates/plate_gen.py "$GEN/plates2" >/dev/null
diff -r "$GEN/plates1" "$GEN/plates2" >/dev/null
okf "plate-byte-identical-regeneration" $?
ok "plate-count" "$(ls "$GEN/plates1" | wc -l)" "6"
ok "plate-magic" "$(head -c8 "$GEN/plates1/decoy_plate_0.png" | od -An -tx1 | tr -d ' \n')" "89504e470d0a1a0a"

python3 - "$GEN/plates1/decoy_plate_0.png" <<'EOF'
import struct, sys
d = open(sys.argv[1], "rb").read()
p, tags, text = 8, [], None
while p < len(d):
    n = struct.unpack(">I", d[p:p+4])[0]
    tag = d[p+4:p+8].decode()
    tags.append(tag)
    if tag == "tEXt":
        text = d[p+8:p+8+n]
    if tag == "IHDR":
        w, h = struct.unpack(">II", d[p+8:p+16])
        assert (w, h) == (256, 128), "bad size"
    p += 12 + n
assert tags[0] == "IHDR" and tags[-1] == "IEND", tags
assert set(tags) <= {"IHDR", "tEXt", "IDAT", "IEND"}, tags
k, v = text.split(b"\x00", 1)
assert k == b"Notice" and b"Trust timestamps, not moods" in v
EOF
okf "plate-metadata-clean-notice-only" $?
# ---- flood tool build ---------------------------------------------------
musl-gcc -O2 -static -s -o "$PKG/flood" flood.c ../core/carto_sha256.c ../core/sha256ctr.c 2>build.log
okf "build" $?
file "$PKG/flood" | grep -q "static-pie linked\|statically linked"
okf "static-binary" $?
nm "$PKG/flood" 2>&1 | grep -q "no symbols"
okf "nm-empty" $?
S1=$(sha256sum "$PKG/flood" | cut -d' ' -f1)
musl-gcc -O2 -static -s -o "$PKG/flood2" flood.c ../core/carto_sha256.c ../core/sha256ctr.c
ok "deterministic-rebuild" "$(sha256sum "$PKG/flood2" | cut -d' ' -f1)" "$S1"
FL="$PKG/flood"

# ---- flood tool behavior ------------------------------------------------
ERR=$("$FL" 2>&1 >/dev/null); RC=$?
ok "noargs-rc" "$RC" "0"
ok "noargs-stderr-empty" "$ERR" ""
OUT0=$("$FL")
echo "$OUT0" | grep -qF "./flood <token> - <index>"
okf "usage-format" $?
echo "$OUT0" | grep -qF "Trust timestamps, not moods"
okf "notice-printed" $?
echo "$OUT0" | grep -qF "8 pages"
okf "lane-page-count-stated" $?

ERR=$("$FL" a3f9c2d1 - 3 2>&1 >/dev/null); RC=$?
ok "run-rc" "$RC" "0"
ok "run-stderr-empty" "$ERR" ""
P1=$("$FL" a3f9c2d1 - 3)
ok "page-line-count" "$(echo "$P1" | wc -l)" "46"
echo "$P1" | head -1 | grep -qE '^MERU FIELD SURVEY - folio [0-9]{3}-[0-9]{2} / stitch a3f9c2d1$'
okf "page-header-format" $?
ok "page-deterministic" "$("$FL" a3f9c2d1 - 3)" "$P1"
[ "$("$FL" a3f9c2d1 - 4)" != "$P1" ]
okf "index-changes-page" $?
[ "$("$FL" bbbbbbbb - 3)" != "$P1" ]
okf "token-changes-page" $?
"$FL" a3f9c2d1 - 8 | grep -qF "usage:"
okf "page-count-fixed-8" $?
"$FL" a3f9c2d1 - 7 | grep -qE '^MERU FIELD SURVEY'
okf "last-page-valid" $?
"$FL" a3f9c2d1ff - 3 | grep -qF "usage:"
okf "token-max-8" $?
"$FL" "" - 3 | grep -qF "usage:"
okf "empty-token-usage" $?
"$FL" a3f9c2d1 x 3 | grep -qF "usage:"
okf "dash-separator-enforced" $?

# C <-> Python lane parity
PY1=$(python3 -c "
import sys; sys.path.insert(0, '$ROOT/gen'); import mint
print('\n'.join(mint.gen_page_lines('prambh:flood:lane:v1', 'a3f9c2d1', 3)))")
ok "lane-parity-c-py-1" "$P1" "$PY1"
P2=$("$FL" zz - 7)
PY2=$(python3 -c "
import sys; sys.path.insert(0, '$ROOT/gen'); import mint
print('\n'.join(mint.gen_page_lines('prambh:flood:lane:v1', 'zz', 7)))")
ok "lane-parity-c-py-2" "$P2" "$PY2"

# wrong-token lanes carry no needle material
ALL=""
for t in aaaaaaaa 00000000 zzzzzzzz q1w2e3r4; do
  for i in 0 3 7; do ALL="$ALL
$("$FL" "$t" - "$i")"; done
done
echo "$ALL" | grep -q "stitched from the surveyor's original" && BAD=1 || BAD=0
ok "wrong-token-lanes-no-needles" "$BAD" "0"
echo "$ALL" | grep -qE '[0-9a-f]{16,}' && BAD=1 || BAD=0
ok "wrong-token-lanes-no-hex" "$BAD" "0"

# corpus independent checks
python3 check_corpus.py "$GEN/corpus1"
okf "corpus-checker-green" $?

# registries
python3 ../gen/trap_catalogue.py >/dev/null
python3 ../gen/keys.py >/dev/null
grep -q "D-FLOOD-5" "$PRIV/TRAP_CATALOGUE.md"
okf "decoy-folios-registered" $?
grep -q "D-PLATE-6" "$PRIV/TRAP_CATALOGUE.md"
okf "decoy-plates-registered" $?
python3 - "$PRIV/TRAP_CATALOGUE.md" <<'EOF'
import sys
sys.path.insert(0, "../gen")
import mint
cat = open(sys.argv[1]).read()
for c in mint.decoy_plate_codes():
    assert c in cat, c
EOF
okf "plate-codes-in-catalogue" $?
grep -q "real hall" "$PRIV/KEYS_PRAMBH.md"
okf "keys-table-p4-rows" $?

# no real values anywhere in the corpus
python3 - "$GEN/corpus1" <<'EOF'
import os, sys
sys.path.insert(0, "../gen")
import mint
blob = ""
for fn in sorted(os.listdir(sys.argv[1])):
    blob += open(os.path.join(sys.argv[1], fn)).read()
secrets = [mint.capsule_content().hex(), mint.capsule_bin().hex(),
           mint.loom_seed_material(mint.capsule_content()).hex(),
           mint.canary_token(), mint.launch_phrase()] + mint.decoy_plate_codes()
bad = [s for s in secrets if s in blob]
assert not bad, bad
EOF
okf "zero-real-values-in-corpus" $?

rm -rf "$GEN" "$PKG"
echo
echo "P4: $PASS PASS, $FAIL FAIL"

