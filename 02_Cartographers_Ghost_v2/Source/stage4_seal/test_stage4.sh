#!/bin/bash
# Stage 4 acceptance -- SERIAL ONLY.
set -u
cd "$(dirname "$0")"
REPO="$(cd ../.. && pwd)"
export PKGTOOLS="$REPO/src/state"
# shellcheck source=/dev/null
. "$REPO/src/final/lib_stage_tests.sh"

KEY=3821ad004ab30263
DECOYKEY=$(python3 -c "import hashlib;print(hashlib.sha256(b'ghost2:stage4:decoy:key:v1').digest()[:8].hex())")
SRC="$REPO/src/stage4_seal"
ORA="$REPO/cartographer/stage4_seal/seal"

t_init stage4 "$REPO/cartographer"
( cd "$REPO/src/state" && make -s >/dev/null 2>&1 )
( cd "$SRC" && make -s all mitm >/dev/null 2>&1 )
cp "$SRC/mitm" "$WORK/" 2>/dev/null || true
cp "$ORA" "$WORK/stage4_seal/seal" 2>/dev/null || true
cd "$WORK"

# ---- the certificate, the rules, and a clean room ------------------------
t_expect_ok "no arguments" ./stage4_seal/seal
t_has "the certificate is shown" "CERTIFICATE"
t_has "the block rule is stated" "the block"
t_has "the closing rule is stated" "the closing rule"
t_has "the notice is on the certificate" "AUTHOR'S DIRECT ORDER"
t_lacks "no mechanism word (Feistel)" "Feistel"
t_lacks "no mechanism word (S-box)" "S-box"
t_lacks "no mechanism word (MITM)" "meet-in-the-middle"
t_lacks "no mechanism word (key bytes)" "subkey"

# ---- the refusal shape ---------------------------------------------------
t_expect_ok "a wrong key" ./stage4_seal/seal 0000000000000000
t_has "the one refusal line" "does not close the stamp"
t_expect_ok "a candidate in capitals" ./stage4_seal/seal 3821AD004AB30263
t_expect_ok "a short candidate" ./stage4_seal/seal 1234
t_expect_ok "a non-hex candidate" ./stage4_seal/seal zzzzzzzzzzzzzzzz
t_expect_ok "an empty argument" ./stage4_seal/seal ''
t_expect_ok "two arguments" ./stage4_seal/seal 1111111111111111 2222222222222222
t_expect_ok "sixteen arguments" ./stage4_seal/seal 1 2 3 4 5 6 7 8 9 a b c d e f g
head -c 60000 /dev/urandom | base64 -w0 > "$WORK/.big"
t_expect_ok "an 80 KB argument" ./stage4_seal/seal "$(cat "$WORK/.big")"
if grep -qF "does not close the stamp" "$OUT"; then
    ok "malformed candidates get the one refusal"
else
    bad "a malformed candidate did not get the refusal"
fi
t_expect_ok "an unknown flag" ./stage4_seal/seal -k deadbeef

# ---- byte-identical refusals, pty and pipe -------------------------------
A1=$(script -qec "./stage4_seal/seal 0000000000000000" /dev/null 2>&1 </dev/null | tr -d '\r')
A2=$(script -qec "./stage4_seal/seal deadbeefdeadbeef" /dev/null 2>&1 </dev/null | tr -d '\r')
if [ "$A1" = "$A2" ] && [ -n "$A1" ]; then
    ok "two wrong candidates are refused byte-identically (pty)"
else
    bad "wrong-candidate refusals differ"
fi
./stage4_seal/seal 0000000000000000 > "$WORK/.p1" 2>&1
./stage4_seal/seal deadbeefdeadbeef > "$WORK/.p2" 2>&1
if cmp -s "$WORK/.p1" "$WORK/.p2"; then
    ok "two wrong candidates are refused byte-identically (pipe)"
else
    bad "piped refusals differ"
fi

# ---- the true key closes the stamp ---------------------------------------
t_expect_ok "the true key is offered" ./stage4_seal/seal "$KEY"
if grep -qF "the stamp closes" "$OUT"; then
    ok "the true key closes the stamp"
else
    bad "the true key did not close the stamp"
fi
if grep -qF "$KEY" "$OUT"; then
    ok "the stamp's face reads back the key"
else
    bad "the closing line did not name the key"
fi

# ---- the record: 1168 bytes, only ever one file --------------------------
t_state_size
t_verify_state
BEFORE=$(ls -A | grep -v '^\.t_\|^\.verify$\|^\.list\|^\.big$\|^\.p[12]$\|^\.mitm$' | sort)
t_run ./stage4_seal/seal
AFTER=$(ls -A | grep -v '^\.t_\|^\.verify$\|^\.list\|^\.big$\|^\.p[12]$\|^\.mitm$' | sort)
if [ "$BEFORE" = "$AFTER" ]; then
    ok "the seal wrote nothing but the record"
else
    bad "the seal created files: $(diff <(printf '%s\n' "$BEFORE") <(printf '%s\n' "$AFTER") | tr '\n' ' ')"
fi

# ---- the drawer: an older stamp, valid-looking and wrong -----------------
t_expect_ok "the drawer opens" ./stage4_seal/seal --decoy
t_has "the drawer has its own certificate" "DRAWER"
if grep -qF "the stamp closes" "$OUT"; then
    bad "the drawer must not confirm a key"
else
    ok "the drawer never confirms anything"
fi
t_expect_ok "the decoy key closes its own stamp" ./stage4_seal/seal --decoy "$DECOYKEY"
if grep -qF "the stamp closes" "$OUT"; then
    ok "the decoy key verifies against the decoy construction"
else
    bad "the decoy key did not verify"
fi
t_expect_ok "the real key refused by the drawer" ./stage4_seal/seal --decoy "$KEY"
if grep -qF "does not close the stamp" "$OUT"; then
    ok "the real key does not close the drawer's stamp"
else
    bad "the drawer confirmed the real key"
fi
D1=$(script -qec "./stage4_seal/seal --decoy" /dev/null 2>&1 </dev/null | tr -d '\r' \
    | grep -oE '^    [0-9a-f]{16} -> [0-9a-f]{16}$' | head -1)
D2=$(script -qec "./stage4_seal/seal" /dev/null 2>&1 </dev/null | tr -d '\r' \
    | grep -oE '^    [0-9a-f]{16} -> [0-9a-f]{16}$' | head -1)
if [ -n "$D1" ] && [ -n "$D2" ] && [ "$D1" != "$D2" ]; then
    ok "the drawer's pairs differ from the stamp's pairs"
else
    bad "the drawer's pairs are not distinct"
fi

# ---- the intended attack, measured ---------------------------------------
MITM_LOG="$WORK/.mitm"
./mitm > "$MITM_LOG" 2>&1
MITM_RC=$?
if [ "$MITM_RC" = "0" ] && grep -q "KEY ${KEY%??}" "$MITM_LOG"; then
    ok "the intended attack recovers the working bytes"
else
    bad "the intended attack did not land on the key"
    cat "$MITM_LOG"
fi
WORK_N=$(awk '/^WORK/{print $2}' "$MITM_LOG")
WALL=$(awk '/^WALL/{print $2}' "$MITM_LOG")
if [ -n "$WORK_N" ]; then
    ok "the attack's work is counted ($WORK_N evaluations)"
else
    bad "the attack's work is missing"
fi
printf '  mitm: work=%s wall=%ss\n' "$WORK_N" "$WALL"

# ---- the closing byte: the certificate leaves it free, the stamp does not -
KEY7="${KEY%??}"
CLOSED=""
CLOSES=0
for b8 in 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f \
          10 11 12 13 14 15 16 17 18 19 1a 1b 1c 1d 1e 1f \
          20 21 22 23 24 25 26 27 28 29 2a 2b 2c 2d 2e 2f \
          30 31 32 33 34 35 36 37 38 39 3a 3b 3c 3d 3e 3f \
          40 41 42 43 44 45 46 47 48 49 4a 4b 4c 4d 4e 4f \
          50 51 52 53 54 55 56 57 58 59 5a 5b 5c 5d 5e 5f \
          60 61 62 63 64 65 66 67 68 69 6a 6b 6c 6d 6e 6f \
          70 71 72 73 74 75 76 77 78 79 7a 7b 7c 7d 7e 7f \
          80 81 82 83 84 85 86 87 88 89 8a 8b 8c 8d 8e 8f \
          90 91 92 93 94 95 96 97 98 99 9a 9b 9c 9d 9e 9f \
          a0 a1 a2 a3 a4 a5 a6 a7 a8 a9 aa ab ac ad ae af \
          b0 b1 b2 b3 b4 b5 b6 b7 b8 b9 ba bb bc bd be bf \
          c0 c1 c2 c3 c4 c5 c6 c7 c8 c9 ca cb cc cd ce cf \
          d0 d1 d2 d3 d4 d5 d6 d7 d8 d9 da db dc dd de df \
          e0 e1 e2 e3 e4 e5 e6 e7 e8 e9 ea eb ec ed ee ef \
          f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 fa fb fc fd fe ff; do
    R=$(./stage4_seal/seal "$KEY7$b8" 2>&1)
    if printf '%s' "$R" | grep -qF "the stamp closes"; then
        CLOSES=$((CLOSES + 1))
        CLOSED="$KEY7$b8"
    fi
done
if [ "$CLOSES" = "1" ] && [ "$CLOSED" = "$KEY" ]; then
    ok "exactly one closing byte exists and the stamp names it"
else
    bad "the closing-byte walk gave $CLOSES closes ($CLOSED)"
fi

# ---- what ships and what must never ship ---------------------------------
t_nm_empty "$ORA"
t_strings_clean "$ORA"
t_absent "no key material in the binary" "$ORA" "$KEY"
t_absent "no seed string in the binary" "$ORA" "ghost2:stage4:key"
if strings -n 4 "$ORA" | grep -qF "ghost2:mask:seal:v1"; then
    ok "the mask seed ships as a public constant (the blob is folded, not plain)"
else
    bad "the mask seed is missing"
fi
t_absent "no decoy seed in the binary" "$ORA" "ghost2:stage4:decoy"
t_absent "no test hook in the binary" "$ORA" "CARTO_TEST_TIME_SCALE"
if strings -n 8 "$ORA" | grep -q "AUTHOR'S DIRECT ORDER"; then
    ok "the notice rides in the binary"
else
    bad "the notice is missing from the binary"
fi
for w in Feistel meet-in-the-middle subkey "S-box" rotl spread; do
    if strings -n 4 "$ORA" | grep -qiF "$w"; then
        bad "a mechanism word ships ($w)"
    else
        ok "no mechanism word ships ($w)"
    fi
done

t_summary
