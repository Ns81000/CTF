#!/usr/bin/env bash
# P9 eventgen suite (spec 3, >= 20 checks): generator determinism x2,
# three-callsign cross-contamination, per-player answers.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
SBX="$(mktemp -d /tmp/p9eg.XXXXXX)"
trap 'chmod -R u+w "$SBX" 2>/dev/null; rm -rf "$SBX"' EXIT
PASS=0; FAIL=0
ok() { if [ "$2" = "$3" ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1 (got [$2] want [$3])"; FAIL=$((FAIL+1)); fi; }
okf() { if [ "${2:-1}" -eq 0 ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1"; FAIL=$((FAIL+1)); fi; }
okn() { if [ "${2:-0}" -ge "$3" ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1 (got [$2] want >= $3)"; FAIL=$((FAIL+1)); fi; }
SECRET_HEX="$(python3 -c 'print("a7" * 32)')"

echo "=== three per-player packages (reduced-T for the suite only) ==="
for c in alice bob carol; do
  python3 "$HERE/player_gen.py" --callsign "$c" --out "$SBX/$c" \
      --master-secret-hex "$SECRET_HEX" --reduced-t 100000 \
      >"$SBX/$c.log" 2>&1
  okf "build-$c" $?
  ok "answers-$c" "$(test -f "$SBX/$c/answers.json" && echo yes)" "yes"
  ok "package-$c" "$(test -x "$SBX/$c/prambh/stage0_milestone/milestone" && echo yes)" "yes"
done
python3 "$HERE/player_gen.py" --callsign alice --out "$SBX/alice2" \
    --master-secret-hex "$SECRET_HEX" --reduced-t 100000 >/dev/null 2>&1
okf "build-alice-again" $?

echo
echo "=== determinism ==="
python3 - "$SBX/alice/answers.json" "$SBX/alice2/answers.json" <<'PYEOF'
import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
for k in ("player_context", "stage0_token", "final_title", "launch_phrase"):
    assert a[k] == b[k], (k, a[k], b[k])
print("answers identical")
PYEOF
okf "answers-deterministic" $?
( cd "$SBX/alice/prambh" && find . -type f | sort | while read -r f; do sha256sum "$f"; done ) >"$SBX/a1.txt"
( cd "$SBX/alice2/prambh" && find . -type f | sort | while read -r f; do sha256sum "$f"; done ) >"$SBX/a2.txt"
cmp -s "$SBX/a1.txt" "$SBX/a2.txt"
okf "package-byte-identical" $?

echo
echo "=== cross-contamination (values must not travel) ==="
python3 - "$SBX/alice/answers.json" "$SBX/bob/answers.json" "$SBX/carol/answers.json" <<'PYEOF'
import json, sys
a, b, c = (json.load(open(p)) for p in sys.argv[1:4])
ctx = {a["player_context"], b["player_context"], c["player_context"]}
assert len(ctx) == 3, ctx
assert len({a["stage0_token"], b["stage0_token"], c["stage0_token"]}) == 3
assert len({a["final_title"], b["final_title"], c["final_title"]}) == 3
print("contexts, tokens and titles all differ across players")
PYEOF
okf "per-player-values-differ" $?
for pair in "alice bob" "bob carol" "alice carol"; do
  set -- $pair
  src="$1"; dst="$2"
  tok="$(python3 -c "import json;print(json.load(open('$SBX/$src/answers.json'))['stage0_token'])")"
  title="$(python3 -c "import json;print(json.load(open('$SBX/$src/answers.json'))['final_title'])")"
  n_tok="$(grep -r -o -a -F "$tok" "$SBX/$dst/prambh" | wc -l)"
  n_title="$(grep -r -o -a -F "$title" "$SBX/$dst/prambh" | wc -l)"
  ok "no-$src-token-in-$dst" "$n_tok" "0"
  ok "no-$src-title-in-$dst" "$n_title" "0"
done
okn "doors-differ-between-players" \
  "$(cmp -s "$SBX/alice/prambh/stage3_doors/doors.bin" "$SBX/bob/prambh/stage3_doors/doors.bin" && echo same || echo differ | grep -c differ)" 1
ok "roms-differ-between-players" \
  "$(cmp -s "$SBX/alice/prambh/stage2_loom/loom.rom" "$SBX/bob/prambh/stage2_loom/loom.rom" && echo same_is_bad || echo differ)" "differ"
ok "plates-differ-between-players" \
  "$(cmp -s "$SBX/alice/prambh/plates/depth.png" "$SBX/bob/prambh/plates/depth.png" && echo same_is_bad || echo differ)" "differ"
ok "corpus-differs-between-players" \
  "$(cmp -s "$SBX/alice/prambh/archive/folio_010.txt" "$SBX/bob/prambh/archive/folio_010.txt" && echo same_is_bad || echo differ)" "differ"

echo
echo "=== per-player answers land on their own package only ==="
A_TOK="$(python3 -c "import json;print(json.load(open('$SBX/alice/answers.json'))['stage0_token'])")"
ok "alice-milestone-prints-alice" \
  "$(cd "$SBX/alice/prambh" && ./stage0_milestone/milestone | grep -c -F "$A_TOK")" "1"
B_TOK="$(python3 -c "import json;print(json.load(open('$SBX/bob/answers.json'))['stage0_token'])")"
ok "bob-milestone-prints-bob" \
  "$(cd "$SBX/bob/prambh" && ./stage0_milestone/milestone | grep -c -F "$B_TOK")" "1"
ok "bob-milestone-hides-alice" \
  "$(cd "$SBX/bob/prambh" && ./stage0_milestone/milestone | grep -c -F "$A_TOK")" "0"
A_PH="$(python3 -c "import json;print(json.load(open('$SBX/alice/answers.json'))['launch_phrase'])")"
ok "alice-phrase-opens-alice-capsule" \
  "$(cd "$SBX/alice/prambh" && ./stage0_milestone/milestone open $A_PH | grep -c -E '^[0-9a-f]{64}$')" "1"
okf "alice-doors-open-alice-chamber" \
  "$(cd "$SBX/alice/prambh/stage3_doors" && ./doors open $(python3 -c "
import os, sys
sys.path.insert(0, os.path.join('$ROOT', 'src', 'gen'))
os.environ['PRAMBH_PLAYER_HEX'] = __import__('json').load(open('$SBX/alice/answers.json'))['player_context']
import mint
print(mint.real_phrase())") | grep -q -F 'HALL ' && echo 0 || echo 1)"

echo
echo "=== ARCHIVE-mode regression (no context => archived values) ==="
python3 - <<'PYEOF' >"$SBX/archive.txt"
import sys
sys.path.insert(0, "/home/ns8pc/prambh-build/src/gen")
import mint
print(mint.stage0_token())
print(mint.canary_token())
print(mint.launch_phrase())
print(mint.eyes_ink())
PYEOF
ok "archive-stage0-intact" "$(sed -n 1p "$SBX/archive.txt")" "PRAMBH{zero_b8c1d72c}"
ok "archive-canary-intact" "$(sed -n 2p "$SBX/archive.txt")" "PRAMBH{canary_87eefe3e}"
ok "archive-phrase-intact" "$(sed -n 3p "$SBX/archive.txt")" "fable coil autumn coast reed zinc"
ok "no-master-secret-in-package" \
  "$(grep -r -o -a -F "$SECRET_HEX" "$SBX/alice/prambh" | wc -l)" "0"

echo
echo "P9-EVENTGEN: $PASS PASS, $FAIL FAIL"
[ "$FAIL" -eq 0 ]
