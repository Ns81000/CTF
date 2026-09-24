#!/usr/bin/env bash
# Leak grep (spec 7 lane 5 / 8): every real value, seed label, ink, glyph
# code, phrase, component digest, secret and FORBIDDEN v2 value must be
# ABSENT from the package; every registered decoy must be PRESENT exactly
# where documented.  Writes organizer-private/runs/leaks.txt.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
PKG="$ROOT/prambh"
OUT="$ROOT/organizer-private/runs/leaks.txt"
PASS=0; FAIL=0
: >"$OUT"

say() { echo "$1" | tee -a "$OUT" >/dev/null; }
ok() { if [ "$2" = "$3" ]; then echo "PASS $1" | tee -a "$OUT" >/dev/null; PASS=$((PASS+1));
  else echo "FAIL $1 (got [$2] want [$3])" | tee -a "$OUT" >/dev/null; FAIL=$((FAIL+1)); fi; }
okn() { if [ "${2:-0}" -ge "$3" ]; then echo "PASS $1" | tee -a "$OUT" >/dev/null; PASS=$((PASS+1));
  else echo "FAIL $1 (got [$2] want >= $3)" | tee -a "$OUT" >/dev/null; FAIL=$((FAIL+1)); fi; }
mintval() { python3 -c "
import sys; sys.path.insert(0, '$ROOT/src/gen'); import mint
print(eval(sys.argv[1], {'mint': mint, **vars(mint)}))" "$1"; }
count_all() { grep -r -o -a -F "$1" "$PKG" 2>/dev/null | wc -l; }

say "# PRAMBH leak grep - machine-readable report (spec 7 lane 5)"
say "# package: $PKG"
say "# generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

say ""
say "## real values that must be ABSENT"
C1="$(sed -n 's/^out=//p' "$ROOT/organizer-private/runs/chain1_walk.txt" 2>/dev/null | head -1)"
[ -n "$C1" ] || C1="$(sed -n 's/^out=//p' "$ROOT/organizer-private/runs/p5_chain1_raw.txt" | head -1)"
C2="$(sed -n 's/^out=//p' "$ROOT/organizer-private/runs/chain2_walk.txt" 2>/dev/null | head -1)"
[ -n "$C2" ] || C2="$(python3 -c "print('0'*64)")"
TITLE="$(python3 -c "
import sys; sys.path.insert(0, '$ROOT/src/gen'); import mint
print(mint.final_title(bytes.fromhex('$C2'), bytes.fromhex('$C1')))" 2>/dev/null || echo NONE)"

ABSENT=(
  "$(mintval 'capsule_content().hex()')"
  "$(mintval 'loom_seed_material(mint.capsule_content()).hex()')"
  "$(mintval 'door_ink()')"
  "$(mintval 'real_phrase()')"
  "$(mintval 'chain2_vector().hex()')"
  "$(mintval 'chain2_seed().hex()')"
  "$(mintval 'eyes_ink()')"
  "$(mintval 'eyes_code(0)')"
  "$C1" "$C2" "$TITLE"
)
for v in "${ABSENT[@]}"; do
  [ "$v" = "NONE" ] && continue
  n="$(count_all "$v")"
  ok "absent:${v:0:16}" "$n" "0"
done
# the Stage-0 token is printed by the milestone BY DESIGN (spec 4.2), so
# this lane asserts it lives nowhere else in the package.
ST0="$(mintval 'stage0_token()')"
ST0_FILES="$(grep -r -l -a -F "$ST0" "$PKG" | wc -l)"
ST0_MILE="$(grep -r -l -a -F "$ST0" "$PKG" | grep -c 'stage0_milestone/milestone')"
okn "stage0-token-present-in-milestone" "$ST0_FILES" 1
ok "stage0-token-lives-nowhere-else" "$ST0_MILE" "$ST0_FILES"
okn "canary-present-by-design" "$(count_all "$(mintval 'canary_token()')")" 4
say ""
say "## derivation-label scope (each tool carries only its own stage labels)"
okn "label-scope-loom-own" \
  "$(grep -c -a -F 'prambh:loom:seed' "$PKG/stage2_loom/loom")" 1
ok "label-scope-loom-others" \
  "$(for l in prambh:doors prambh:eyes prambh:mirror prambh:canary; do
       grep -c -a -F "$l" "$PKG/stage2_loom/loom"; done | paste -sd+ | bc)" "0"
ok "label-scope-milestone-others" \
  "$(for l in prambh:loom prambh:doors prambh:eyes prambh:mirror; do
       grep -c -a -F "$l" "$PKG/stage0_milestone/milestone"; done | paste -sd+ | bc)" "0"
ok "label-scope-doors-others" \
  "$(for l in prambh:loom:seed prambh:eyes prambh:mirror; do
       grep -c -a -F "$l" "$PKG/stage3_doors/doors"; done | paste -sd+ | bc)" "0"

say ""
say "## forbidden v2 values (must be ABSENT)"
for v in CARTO{the_survey_reopens_tonight} 145e1d23feac3932 e509312ae8a2e0ad \
         3821ad004ab30263 rust_blooms_under_tin_roofs CARTO{64c4ad4ea9c40319} \
         f5ea27c63ed89565 CARTO{hand_this_to_your_operator} \
         'CARTO{a_warm_plate_and_a_full_ring}' 01d94d492a46ce3d; do
  ok "forbidden-absent:${v:0:14}" "$(count_all "$v")" "0"
done
ok "forbidden-prefix-absent" "$(count_all 'CARTO{')" "0"
ok "no-organizer-content" "$(count_all 'organizer-private')" "0"

say ""
say "## registered decoys that must be PRESENT exactly where documented"
okn "canary-in-notice-file" \
  "$(grep -c -F "$(mintval 'canary_token()')" "$PKG/HUMAN_OPERATOR_NOTICE.txt" 2>/dev/null || echo 0)" 1
okn "launch-sheet-archive" \
  "$(grep -c -F "$(mintval 'launch_phrase()')" "$PKG/LAUNCH.txt" 2>/dev/null || echo 0)" 1
okn "canary-in-rom-text" \
  "$(grep -r -l -a -F "$(mintval 'canary_token()')" "$PKG/stage2_loom" 2>/dev/null | wc -l)" 1
okn "canary-in-mirror-binaries" \
  "$(grep -r -l -a -F "$(mintval 'canary_token()')" "$PKG/mirror" 2>/dev/null | wc -l)" 1
okn "canary-in-plate-notice-chunk" \
  "$(grep -r -l -a -F 'Notice' "$PKG/plates" 2>/dev/null | wc -l)" 1
i=1
for rid in D-ROM-1 D-ROM-2 D-ROM-3; do
  tok="$(sed -n "${i}p" "$ROOT/organizer-private/runs/p5_decoy_tokens.txt" | sed -n 's/.*token=\(PRAMBH{[^}]*}\).*/\1/p')"
  i=$((i+1))
  ok "decoy-registered:$rid" \
    "$(grep -c -F "$tok" "$ROOT/organizer-private/TRAP_CATALOGUE.md")" "1"
done
ok "decoy-plates-present" "$(ls "$PKG/plates"/decoy_plate_*.png 2>/dev/null | wc -l)" "6"
ok "decoy-folios-present" \
  "$(for f in 386 364 192 237 374; do test -f "$PKG/archive/folio_$f.txt" && echo x; done | wc -l)" "5"
ok "needle-folios-in-field-notes" "$(ls "$PKG/field-notes"/folio_*.txt 2>/dev/null | wc -l)" "5"
ok "datasheet-present" "$(test -f "$PKG/field-notes/meru1_datasheet.txt" && echo 1)" "1"
ok "carrier-present" "$(test -f "$PKG/plates/carrier.png" && echo 1)" "1"
ok "no-master-secret-in-package" "$(count_all 'PRAMBH_MASTER' )" "0"

say ""
echo "LEAKS: $PASS PASS, $FAIL FAIL"
echo "LEAKS: $PASS PASS, $FAIL FAIL" >>"$OUT"
[ "$FAIL" -eq 0 ]
