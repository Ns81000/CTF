#!/bin/bash
# s3_test_stage3.sh -- Stage 3 (Phase 4) verification. INTERNAL, not shipped.
# Runnable verbatim:
#   cd /home/manish/cartographer-build/src/stage3_oracle && bash s3_test_stage3.sh
set -e
R=/home/manish/cartographer-build
S=$R/src/stage3_oracle
PKG=$R/cartographer
BIN=$PKG/stage3_oracle/oracle
FORGE=$R/src/stage1_vm/forge_state.py
RD='CARTO{no_figure_sits_in_every_pixel}'
D2='CARTO{b27692a0d5f63d4f1a0c3fb79afbf81b}'
D1='CARTO{fd3e8049dfdfc32efe22fe823822b8c0}'
P=0
F=0
ok() { echo "[PASS] $1"; P=$((P+1)); }
no() { echo "[FAIL] $1"; F=$((F+1)); }

echo "== stage3_oracle end-to-end verification =="

[ -x "$BIN" ] && ok "oracle exists and is executable" || no "oracle missing"
file "$BIN" | grep -q "statically linked" && ok "statically linked" || no "not static"
file "$BIN" | grep -q stripped && ok "stripped (no symtab)" || no "not stripped"
test "$(strings -n 6 "$BIN" | grep -Eic 'GCC|clang|musl|/home/manish|cartographer-build')" -eq 0 && ok "no compiler/path residue" || no "scrub residue"
strings "$BIN" | grep -q f03ea6b5 && no "HMAC key leaked" || ok "canonical HMAC key absent"
strings "$BIN" | grep -q cartographer-ghost:stage3 && no "KDF seed leaked" || ok "KDF derivation seeds absent"
strings "$BIN" | grep -q cartographer-mask-stage3 && no "mask seed string leaked in binary" || ok "mask seed strings absent from binary" 
( cd "$S" && python3 -c "
import pathlib, re
h = pathlib.Path('oracle_blob.h').read_text()
m = re.search(r'kMaskedSeedReal\[32\] = \{(.*?)\};', h, re.S)
b = bytes(int(x, 16) for x in re.findall(r'0x([0-9a-f]{2})', m.group(1)))
assert len(b) == 32 and b in pathlib.Path('$BIN').read_bytes()
" ) && ok "masked KDF seed present in binary" || no "masked seed missing"

# --- oracle CLI: every path is rc 0 with silent stderr --------------------
# (Rapid scripted calls drive the interaction ring uniform, which silently
#  selects the poison key -- by design.  Poison is still rc 0, stderr-silent
#  and well-formed, which is exactly what these checks prove.)
runq() { local e; e=$(mktemp); RC=0; ( cd "$PKG" && "$BIN" "$@" ) >/tmp/s3out.txt 2>"$e" || RC=$?; SZ=$(wc -c <"$e"); rm -f "$e"; }
runq; [ $RC -eq 0 ] && [ $SZ -eq 0 ] && ok "no args: rc 0, stderr silent" || no "no args"
runq -r "$RD"; [ $RC -eq 0 ] && [ $SZ -eq 0 ] && ok "-r only: rc 0, stderr silent" || no "-r only"
runq 0123456789abcdef; [ $RC -eq 0 ] && [ $SZ -eq 0 ] && ok "figure only: rc 0, stderr silent" || no "figure only"
runq -r "$RD" nothex; [ $RC -eq 0 ] && [ $SZ -eq 0 ] && ok "malformed figure: rc 0, stderr silent" || no "malformed"
runq -r "$RD" 0123456789abcdef00; [ $RC -eq 0 ] && [ $SZ -eq 0 ] && ok "too-long figure: rc 0, stderr silent" || no "too-long"
runq -r "$RD" 0123456789abcdef; [ $RC -eq 0 ] && [ $SZ -eq 0 ] && ok "clean query: rc 0, stderr silent" || no "clean query"

# --- state staging helper (HMAC-valid forged state; human vs uniform pace) ---
forge() { python3 "$FORGE" "$PKG/.cartographer_state" "$1" "$2" "$3" >/dev/null; }
ans() { local e; e=$(mktemp); ( cd "$PKG" && "$BIN" "$@" ) 2>"$e" | grep -oE '[0-9a-f]{16}' | tail -1; rm -f "$e"; }

# --- human-paced state -> real key; oracle must equal the model bit-exactly ---
for f in 0123456789abcdef ffffffffffffffff 0000000000000000 123456789abcdef0; do
  forge human 1000000 0
  a=$(ans -r "$RD" "$f")
  b=$(cd "$S" && python3 model_oracle.py --enc "$RD" "$f")
  if [ "$a" = "$b" ]; then ok "human state: oracle == model on $f"; else no "oracle != model on $f ($a vs $b)"; fi
done
forge human 1000000 0
Z1=$(ans -r "$RD" 00000000000000ff)
Z2=$(cd "$S" && python3 model_oracle.py --enc "$RD" 00000000000000ff)
[ "$Z1" = "$Z2" ] && ok "zero-padded 16-hex figure parses == model" || no "zero-padded figure ($Z1 vs $Z2)"

# --- uniform (scripted) state -> poison key silently served (D48) ---
forge uniform 1000000 0
p=$(ans -r "$RD" 0123456789abcdef)
q=$(cd "$S" && python3 model_oracle.py --poison-enc "$RD" 0123456789abcdef)
r=$(cd "$S" && python3 model_oracle.py --enc "$RD" 0123456789abcdef)
[ "$p" = "$q" ] && ok "uniform state: poison key served (== model poison-enc)" || no "poison key mismatch ($p vs $q)"
[ "$p" != "$r" ] && ok "poison answer differs from the real-key answer" || no "poison == real"
p2=$(ans -r "$RD" 0123456789abcdef)
[ "$p" = "$p2" ] && ok "poison is self-consistent (same figure -> same answer)" || no "poison inconsistent"

runq -r "$D2" 0123456789abcdef; [ $RC -eq 0 ] && [ $SZ -eq 0 ] && ok "stage-2 token as reading: rc 0 silent" || no "decoy2"
runq -r "$D1" 0123456789abcdef; [ $RC -eq 0 ] && [ $SZ -eq 0 ] && ok "stage-1 token as reading: rc 0 silent" || no "decoy1"
runq -r 'CARTO{not_the_interior_figure}' 0123456789abcdef; [ $RC -eq 0 ] && [ $SZ -eq 0 ] && ok "wrong reading: rc 0 silent" || no "wrong reading"


# --- state lifecycle (human state, real key) ---
forge human 1000000 0
( cd "$PKG" && "$BIN" -r "$RD" 0123456789abcdef ) >/dev/null
[ "$(wc -c <"$PKG/.cartographer_state")" -eq 352 ] && ok "state file created (352 bytes)" || no "state size"
if ( cd "$PKG" && python3 -c "import hashlib,hmac;d=open('.cartographer_state','rb').read();k=hashlib.sha256(b'cartographer-ghost:phase0 dev key:do-not-ship').digest();assert len(d)==352 and hmac.new(k,d[:0x140],hashlib.sha256).digest()==d[0x140:]" ); then ok "state HMAC valid (independent python)"; else no "state HMAC"; fi
if ( cd "$PKG" && python3 -c "import struct;d=open('.cartographer_state','rb').read();assert struct.unpack_from('<I',d,0x10+12)[0]==1" ); then ok "attempt_count[3] == 1"; else no "attempt[3]"; fi
( cd "$PKG" && "$BIN" -r "$RD" 0123456789abcdef ) >/dev/null
if ( cd "$PKG" && python3 -c "import struct;d=open('.cartographer_state','rb').read();assert struct.unpack_from('<I',d,0x10+12)[0]==2" ); then ok "attempt_count[3] == 2 after second run"; else no "attempt[3] second"; fi
forge human 1000000 0
( cd "$PKG" && "$BIN" -r "$D2" 0123456789abcdef ) >/dev/null
if ( cd "$PKG" && python3 -c "import struct;d=open('.cartographer_state','rb').read();assert struct.unpack_from('<I',d,0x24+12)[0] & 1" ); then ok "stage-3 decoy bit 0 persisted"; else no "decoy bit"; fi

# --- differential-attack proofs (model-side) ---
# Phase FINAL-2: N_REQUIRED was calibrated from 320 down to 260 pairs per
# window (4160 oracle calls) so the query budget fits the CTF window at a
# cautious 2 s/query cadence.  Both sizes are checked: 260 is the shipped
# budget, 320 is the retained control.  The single-pass reliability of both
# (1500-trial sweeps) lives in logs/runs/pf2_trials_model2.jsonl.
AOUT=$(cd "$S" && python3 solve_attack.py --model-true --pairs-per-window 260 2>&1)
echo "$AOUT" | grep -q VERIFIED && ok "attack recovers true key (N=2080, calibrated)" || no "attack true 260"
AOUT320=$(cd "$S" && python3 solve_attack.py --model-true --pairs-per-window 320 2>&1)
echo "$AOUT320" | grep -q VERIFIED && ok "attack recovers true key (N=2560, control)" || no "attack true 320"
POUT=$(cd "$S" && python3 solve_attack.py --poison-converges 2>&1)
echo "$POUT" | grep -q POISON-KEY-RECOVERED && ok "poisoned dataset self-consistent (wrong key)" || no "poison converge"
MOUT=$(cd "$S" && python3 solve_attack.py --mixed 2>&1)
echo "$MOUT" | grep -q NO-CONSENSUS && ok "mixed dataset fails to converge (falsifiable)" || no "mixed"

# --- reproducibility (clean rebuild -> identical sha256) ---
H1=$(sha256sum "$BIN" | awk '{print $1}')
rm -f "$BIN"
( cd "$S" && make >/dev/null 2>&1 )
H2=$(sha256sum "$BIN" | awk '{print $1}')
[ "$H1" = "$H2" ] && ok "oracle rebuild reproducible (identical sha256)" || no "not reproducible"

rm -f "$PKG/.cartographer_state" /tmp/s3out.txt
echo
echo "== $P passed, $F failed =="
[ "$F" -eq 0 ] && echo "ALL TESTS PASSED" || { echo "FAILURES PRESENT"; exit 1; }
