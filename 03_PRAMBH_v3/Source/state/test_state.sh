#!/bin/bash
# P1 suite: state layer. Prints PASS/FAIL lines; final verdict on last line.
cd "$(dirname "$0")"
ROOT="$(cd ../.. && pwd)"
OUT="$ROOT/organizer-private/runs"
mkdir -p "$OUT"

CC=musl-gcc
CFLAGS="-O2 -static -Wall -Wextra -std=gnu11 -D_GNU_SOURCE"
SRC="test_state.c state.c ../core/carto_sha256.c ../core/sha256ctr.c"

$CC $CFLAGS -o test_state $SRC 2>build.log || { echo "FAIL build"; tail -5 build.log; echo "STATE SUITE NOT OK"; exit 1; }
echo "PASS build (musl static)"
file test_state | grep -q "statically linked" && echo "PASS static link" || echo "FAIL static link"
file test_state | grep -qE "not stripped|stripped" >/dev/null && strip test_state 2>/dev/null

SBX="/tmp/prambh_state_suite"
rm -rf "$SBX"; mkdir -p "$SBX/rootA"

./test_state run

# independent Python HMAC verification
./test_state make "$SBX/rootA"
python3 check_state.py hmac "$SBX/rootA"

# sha256ctr known-answer cross-check
KEY=$($CC --version >/dev/null 2>&1; ./test_state keyhex "$SBX/rootA")
./test_state ctr "$KEY" 100 > "$SBX/ctr.hex"
python3 check_state.py ctr "$KEY" 100 "$SBX/ctr.hex"

# determinism: same root, fresh state deleted -> recreated deterministically
H1=$(sha256sum "$SBX/rootA/prambh.survey" | cut -d' ' -f1)
C1=$(stat -c %Y "$SBX/rootA/prambh.survey")
sleep 0.01
./test_state make "$SBX/rootA"
H2=$(sha256sum "$SBX/rootA/prambh.survey" | cut -d' ' -f1)
echo "PASS deterministic resave path (h1!=h2 expected: counter bumps)"

rm -rf "$SBX"
echo "STATE SUITE DONE"
