#!/bin/bash
# test_stage4.sh -- Phase 5 (Stage 4) end-to-end verification. INTERNAL.
# Run:  bash /home/manish/cartographer-build/src/stage4_assembly/test_stage4.sh
# Needs: the built deliverable (make), python3, and the shared package root.
# NOTE: operates on cartographer/.cartographer_state -- run suites SERIALLY.
# Every validator invocation runs FROM the package root (its state path is
# "./.cartographer_state"), exactly as a solver runs it.
set -u
cd "$(dirname "$0")"
R=/home/manish/cartographer-build
BIN="$R/cartographer/stage4_assembly/validate"
PKG="$R/cartographer"
PASS=0
FAIL=0
ok() { echo "[PASS] $1"; PASS=$((PASS+1)); }
no() { echo "[FAIL] $1"; FAIL=$((FAIL+1)); }
STATE="$PKG/.cartographer_state"
runv() { (cd "$PKG" && "$BIN" "$@"); }

# ---- expected values come from the generated layout (internal) ----------
rj() { python3 -c "import json,sys;print(json.load(open('stage4_layout.json'))[sys.argv[1]])" "$1"; }
rji() { python3 -c "import json,sys;print(json.load(open('stage4_layout.json'))['inks'][sys.argv[1]])" "$1"; }
TITLE=$(rj title)
DRAFT=$(rj draft_flag)
DIGEST=$(rj digest)
TITLE_LEN=$(rj title_len)
INK_ENGINE=$(rji engine)
INK_SHEET=$(rji sheet)
INK_ORACLE=$(rji oracle)

# the six orderings of the three inks; the FIRST is the intended reading
PERMS=$(python3 - <<'PYEOF'
import json
l = json.load(open('stage4_layout.json'))
i = l['inks']
o, e, s = i['oracle'], i['engine'], i['sheet']
sep = l['separator']
names = [('oracle', 'engine', 'sheet'), ('engine', 'sheet', 'oracle'),
         ('sheet', 'oracle', 'engine'), ('engine', 'oracle', 'sheet'),
         ('sheet', 'engine', 'oracle'), ('oracle', 'sheet', 'engine')]
print('\n'.join(sep.join(i[n] for n in names[k]) for k in range(6)))
PYEOF
)
P1=$(printf '%s\n' "$PERMS" | sed -n 2p)
P2=$(printf '%s\n' "$PERMS" | sed -n 3p)
P3=$(printf '%s\n' "$PERMS" | sed -n 4p)
P4=$(printf '%s\n' "$PERMS" | sed -n 5p)
P5=$(printf '%s\n' "$PERMS" | sed -n 6p)

echo "== stage4_assembly end-to-end verification =="

# ---- section 1: hygiene --------------------------------------------------
[ -x "$BIN" ] && ok "validator exists and is executable" || no "missing validator"
file "$BIN" | grep -q "statically linked" && ok "statically linked" || no "not static"
file "$BIN" | grep -q "stripped" && ok "stripped (no symtab)" || no "not stripped"
[ "$(strings -n 4 "$BIN" | grep -Eic "GCC|clang|musl|/home/manish|cartographer-build")" = 0 ] \
  && ok "no compiler/path residue" || no "compiler/path residue"

# ---- section 2: D38 secrecy / leak checks --------------------------------
strings "$BIN" | grep -qF "$TITLE" && no "real title leaked into binary" \
  || ok "assembled real flag absent from the binary"
strings "$BIN" | grep -qF "$INK_ENGINE" && no "engine ink leaked" \
  || ok "engine ink (stage-1 key bytes 16..23) absent from the binary"
strings "$BIN" | grep -qF "$INK_ORACLE" && no "oracle ink leaked" \
  || ok "oracle ink (stage-3 master K) absent from the binary"
strings "$BIN" | grep -qF "$INK_SHEET" && no "sheet ink leaked" \
  || ok "sheet ink (reading, frame off) absent from the binary"
strings "$BIN" | grep -qF "CARTO{no_figure_sits_in_every_pixel}" \
  && no "full reading leaked" || ok "stage-2 reading (whole) absent from the binary"
strings "$BIN" | grep -qF "fd3e8049dfdfc32efe22fe823822b8c0" && no "stage-1 token content leaked" \
  || ok "stage-1 token content absent from the binary"
strings "$BIN" | grep -q f03ea6b5 && no "HMAC key leaked" \
  || ok "canonical HMAC key hex absent from binary"
strings "$BIN" | grep -qF "$DRAFT" && ok "struck-draft decoy present (findable)" \
  || no "struck-draft decoy missing"
strings "$BIN" | grep -q "sits at the head of the line" && ok "the riddle verse is shipped (solver-facing)" \
  || no "riddle verse missing"
strings "$BIN" | grep -q "the half of the engine's key material" \
  && ok "the ink descriptions are shipped (fair, value-free)" || no "ink descriptions missing"
python3 - <<'PYEOF'
import hashlib, json, re
l = json.load(open('stage4_layout.json'))
t = l['title']
assert re.match(r"^CARTO\{[a-z0-9_]{8,64}\}$", t), "title violates D11"
assert hashlib.sha256(t.encode()).hexdigest() == l['digest'], "digest drift"
PYEOF
[ $? = 0 ] && ok "title is D11-conforming and digest matches (independent recompute)" \
  || no "title digest mismatch"

# ---- section 3: CLI discipline (every path rc 0, stderr silent) ----------
rm -f "$STATE" "$PKG/.s4err"
out=$(runv 2>"$PKG/.s4err"); rc=$?
[ $rc = 0 ] && ok "no args: rc 0" || no "no-args rc=$rc"
[ ! -s "$PKG/.s4err" ] && ok "no args: stderr silent" || no "no-args stderr not silent"
printf '%s\n' "$out" | grep -q "Stage 4 -- The Title Block" \
  && ok "usage shows the stage banner" || no "usage banner missing"

runv "$TITLE" >"$PKG/.s4ok" 2>"$PKG/.s4err"; rc=$?
[ $rc = 0 ] && ok "correct title: rc 0" || no "correct title rc=$rc"
[ ! -s "$PKG/.s4err" ] && ok "correct title: stderr silent" || no "correct title stderr"
grep -qF "$TITLE" "$PKG/.s4ok" && ok "acceptance echoes the title" || no "title not echoed"
grep -q "The survey is closed" "$PKG/.s4ok" && ok "acceptance closes the survey" || no "no closure text"
grep -q "Stage 4 complete" "$PKG/.s4ok" && ok "acceptance names the final flag as the answer" \
  || no "no completion line"

# ---- section 4: refusal uniformity (D40: no partial-match feedback) ------
REF=""
refusal_case() {  # $1 label, $2 input
  runv "$2" >"$PKG/.s4r" 2>"$PKG/.s4err"; rc=$?
  if [ $rc = 0 ] && [ ! -s "$PKG/.s4err" ]; then ok "$1: rc 0, stderr silent"
  else no "$1: rc=$rc or stderr not silent"; fi
  if [ -z "$REF" ]; then REF="$PKG/.s4ref0"; cp "$PKG/.s4r" "$REF"
  elif cmp -s "$REF" "$PKG/.s4r"; then :; else no "$1: refusal differs"; fi
}
refusal_case "wrong ordering 1 (naive stage order)" "CARTO{$P1}"
refusal_case "wrong ordering 2" "CARTO{$P2}"
refusal_case "wrong ordering 3" "CARTO{$P3}"
refusal_case "wrong ordering 4" "CARTO{$P4}"
refusal_case "wrong ordering 5" "CARTO{$P5}"
refusal_case "engine ink = token content (the near-miss)" \
  "CARTO{${INK_ORACLE}_fd3e8049dfdfc32efe22fe823822b8c0_${INK_SHEET}}"
refusal_case "sheet ink keeps its frame" \
  "CARTO{${INK_ORACLE}_${INK_ENGINE}_CARTO{${INK_SHEET}}}"
refusal_case "oracle ink head/tail swapped" \
  "CARTO{a159f9e273070925_${INK_ENGINE}_${INK_SHEET}}"
refusal_case "engine ink taken from the wrong half (first half)" \
  "CARTO{${INK_ORACLE}_fd3e8049dfdfc32e_${INK_SHEET}}"
refusal_case "garbage input" "hello world"
refusal_case "malformed flag" "CARTO{"
refusal_case "wrong length (one char appended)" "${TITLE}x"
refusal_case "empty argument" ""
[ -n "$REF" ] && ok "every refusal is byte-identical (no partial-match feedback)" \
  || no "no refusal baseline"
if grep -qF "$TITLE" "$REF"; then no "refusal leaks the real title"
else ok "refusal never contains the real title"; fi
if grep -qF "$INK_ENGINE" "$REF" || grep -qF "$INK_ORACLE" "$REF" || grep -qF "$INK_SHEET" "$REF"
then no "refusal leaks an ink"; else ok "refusal leaks no ink value"; fi
runv "$TITLE" extra >"$PKG/.s4r" 2>"$PKG/.s4err"; rc=$?
if [ $rc = 0 ] && [ ! -s "$PKG/.s4err" ] && cmp -s "$REF" "$PKG/.s4r"; then
  ok "extra arguments: rc 0, identical refusal"
else no "extra arguments mishandled"; fi

# ---- section 5: decoy routing (struck draft -> extended branch) ----------
rm -f "$STATE"
runv "$DRAFT" >"$PKG/.s4d" 2>"$PKG/.s4err"; rc=$?
[ $rc = 0 ] && ok "decoy submission exits 0 (no error path)" || no "decoy rc=$rc"
[ ! -s "$PKG/.s4err" ] && ok "decoy submission: stderr silent" || no "decoy stderr"
grep -q "corroborated draft" "$PKG/.s4d" \
  && ok "decoy route is framed as new information, not failure" || no "decoy framing"
grep -qF "$DRAFT" "$PKG/.s4d" && ok "decoy route re-inks the struck draft" || no "draft not re-inked"
if grep -qF "$TITLE" "$PKG/.s4d"; then no "decoy route leaks the real title"
else ok "decoy route never leaks the real title"; fi
(cd "$PKG" && python3 - <<'PYEOF'
import struct
d = open('.cartographer_state', 'rb').read()
mask = struct.unpack_from('<I', d, 0x024 + 4 * 4)[0]
assert mask == 1, "stage-4 decoy bit 0 not persisted (mask=%d)" % mask
PYEOF
)
[ $? = 0 ] && ok "stage-4 decoy bit 0 persisted (branch 1 -> 1u<<0)" || no "decoy bit"
runv "hello again" >"$PKG/.s4r" 2>/dev/null
cmp -s "$REF" "$PKG/.s4r" && ok "post-decoy refusals are unchanged" || no "post-decoy refusal drifted"

# ---- section 6: state lifecycle ------------------------------------------
rm -f "$STATE"
runv "$TITLE" >/dev/null 2>&1
FR1=$(python3 -c "import struct;print(struct.unpack_from('<Q',open('$STATE','rb').read(),0x008)[0])")
AT1=$(python3 -c "import struct;print(struct.unpack_from('<I',open('$STATE','rb').read(),0x010+16)[0])")
runv "$TITLE" >/dev/null 2>&1
FR2=$(python3 -c "import struct;print(struct.unpack_from('<Q',open('$STATE','rb').read(),0x008)[0])")
AT2=$(python3 -c "import struct;print(struct.unpack_from('<I',open('$STATE','rb').read(),0x010+16)[0])")
[ "$AT1" = 1 ] && ok "attempt_count[4] == 1 after first run" || no "attempt 1 = $AT1"
[ "$AT2" = 2 ] && ok "attempt_count[4] == 2 after second run" || no "attempt 2 = $AT2"
[ -n "$FR1" ] && [ "$FR1" = "$FR2" ] && ok "first_run_ms is preserved" || no "first_run drifted"
[ "$(wc -c < "$STATE")" = 352 ] && ok "state file is exactly 352 bytes" \
  || no "state size wrong"
python3 -c "import struct;d=open('$STATE','rb').read();assert struct.unpack_from('<I',d,0x024+16)[0]==0"
[ $? = 0 ] && ok "no decoy bit set by the real title" || no "decoy bit set by real title"
(cd "$PKG" && python3 -c "import hashlib,hmac;d=open('.cartographer_state','rb').read();k=hashlib.sha256(b'cartographer-ghost:phase0 dev key:do-not-ship').digest();assert len(d)==352 and hmac.new(k,d[:0x140],hashlib.sha256).digest()==d[0x140:]") \
  && ok "state HMAC valid (independent python)" || no "state HMAC"
ls "$PKG"/.cartographer_state.tmp >/dev/null 2>&1 && no "tmp residue" || ok "no .tmp residue after runs"

# ---- section 7: escalation presentation (answer invariance, D49) ---------
FORGE="$R/src/stage1_vm/forge_state.py"
rm -f "$STATE"
(cd "$PKG" && python3 "$FORGE" .cartographer_state human 300000 0 >/dev/null)
runv "$TITLE" >"$PKG/.s4h" 2>/dev/null
grep -qF "$TITLE" "$PKG/.s4h" && ok "human-paced ledger: plain variant accepts the real title" \
  || no "human variant rejected the title"
if grep -q "witnessed" "$PKG/.s4h"; then no "human variant should not print the witnessed line"
else ok "human-paced ledger serves the plain variant"; fi
rm -f "$STATE"
(cd "$PKG" && python3 "$FORGE" .cartographer_state uniform 300000 0 >/dev/null)
runv "$TITLE" >"$PKG/.s4u" 2>/dev/null
grep -qF "$TITLE" "$PKG/.s4u" && ok "uniform-timing ledger: witnessed variant accepts the real title" \
  || no "witnessed variant rejected the title"
grep -q "witnessed: the ledger takes the title whether you watch it or not" "$PKG/.s4u" \
  && ok "escalated presentation is the witnessed line" || no "witnessed line missing"
diff <(grep -v witnessed "$PKG/.s4h") <(grep -v witnessed "$PKG/.s4u") >/dev/null \
  && ok "witnessed variant verdict is bit-identical to plain" || no "verdict drifted"
rm -f "$STATE"
(cd "$PKG" && python3 "$FORGE" .cartographer_state uniform 300000 0 >/dev/null)
runv "CARTO{wrong_but_shaped_input_here}" >"$PKG/.s4w" 2>/dev/null
cmp -s "$REF" "$PKG/.s4w" && ok "witnessed ledger: refusals are still identical" \
  || no "witnessed refusal drifted"
rm -f "$STATE"
(cd "$PKG" && python3 "$FORGE" .cartographer_state human 300000 1 >/dev/null)
runv "$TITLE" >"$PKG/.s4dbg" 2>/dev/null
grep -qF "$TITLE" "$PKG/.s4dbg" \
  && ok "a persisted debugger flag does NOT corrupt the real verdict" \
  || no "debugger flag corrupted the verdict"

# ---- section 8: reproducibility + pristine package -----------------------
H1=$(sha256sum "$BIN" | awk '{print $1}')
rm -f "$BIN"
make >/dev/null 2>&1
H2=$(sha256sum "$BIN" | awk '{print $1}')
[ -n "$H1" ] && [ "$H1" = "$H2" ] && ok "validator rebuild reproducible (identical sha256)" \
  || no "rebuild hash drift: $H1 vs $H2"
rm -f "$STATE" "$PKG"/.s4* "$PKG"/.cartographer_state.tmp
LEFT=$(find "$PKG" -maxdepth 1 \( -name '.s4*' -o -name '.cartographer_state*' \) | wc -l)
[ "$LEFT" = 0 ] && ok "package left pristine (test state removed)" || no "leftover files"
find "$R" -maxdepth 1 -newer "$BIN" -type f 2>/dev/null | grep -q . \
  && no "files touched outside the stage dirs" || ok "no writes outside the working directory"

echo
echo "== $PASS tests run, $FAIL failed =="
[ "$FAIL" = 0 ] && echo "ALL TESTS PASSED" || exit 1
