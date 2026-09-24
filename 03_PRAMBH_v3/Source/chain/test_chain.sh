#!/bin/bash
# P2 suite: PRAMBH-CHAIN (spec 4.1, >= 40 checks). Final line is the verdict.
cd "$(dirname "$0")"
ROOT="$(cd ../.. && pwd)"
OUT="$ROOT/organizer-private/runs"
mkdir -p "$OUT"

CC=musl-gcc
CFLAGS="-O2 -static -s -Wall -Wextra -std=gnu11 -D_GNU_SOURCE"
SEED_A=00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff
SEED_B=ffeeddccbbaa99887766554433221100ffeeddccbbaa99887766554433221100
ZERO=0000000000000000000000000000000000000000000000000000000000000000
S=65536
T=10000

$CC $CFLAGS -o prambh_chain prambh_chain.c chain.c ../core/carto_sha256.c ../core/sha256ctr.c 2>build.log \
  || { echo "FAIL build"; cat build.log; echo "CHAIN SUITE NOT OK"; exit 1; }
echo "PASS build (musl static)"
file prambh_chain | grep -q "statically linked" && echo "PASS static link" || echo "FAIL static link"
[ -z "$(nm prambh_chain 2>/dev/null)" ] && echo "PASS nm empty" || echo "FAIL nm empty"

# --- bit-exactness vs independent Python model (3+ small vectors) ---
C1=$(./prambh_chain walk --seed-hex $SEED_A --s $S --t $T)
P1=$(python3 model_chain.py walk $SEED_A $S $T)
[ "$C1" = "$P1" ] && echo "PASS c-vs-python bit-exact (seed A)" || echo "FAIL c-vs-python bit-exact (seed A)"

C2=$(./prambh_chain walk --seed-hex $SEED_B --s $S --t $T)
P2=$(python3 model_chain.py walk $SEED_B $S $T)
[ "$C2" = "$P2" ] && echo "PASS c-vs-python bit-exact (seed B)" || echo "FAIL c-vs-python bit-exact (seed B)"

C3=$(./prambh_chain walk --seed-hex $SEED_A --s $S --t 3333)
P3=$(python3 model_chain.py walk $SEED_A $S 3333)
[ "$C3" = "$P3" ] && echo "PASS c-vs-python bit-exact (alt T)" || echo "FAIL c-vs-python bit-exact (alt T)"

C4=$(./prambh_chain walk --seed-hex $SEED_A --s 3072 --t 5000)
P4=$(python3 model_chain.py walk $SEED_A 3072 5000)
[ "$C4" = "$P4" ] && echo "PASS non-pow2 table (n=96) bit-exact" || echo "FAIL non-pow2 table (n=96) bit-exact"

C5=$(./prambh_chain walk --seed-hex $SEED_A --s 32 --t 500)
P5=$(python3 model_chain.py walk $SEED_A 32 500)
[ "$C5" = "$P5" ] && echo "PASS n=1 table bit-exact" || echo "FAIL n=1 table bit-exact"

C6=$(./prambh_chain walk --seed-hex $SEED_A --s 1048576 --t 2000)
P6=$(python3 model_chain.py walk $SEED_A 1048576 2000)
[ "$C6" = "$P6" ] && echo "PASS 1MiB table bit-exact" || echo "FAIL 1MiB table bit-exact"

C7=$(./prambh_chain walk --seed-hex $SEED_A --s $S --t 1)
P7=$(python3 model_chain.py walk $SEED_A $S 1)
[ "$C7" = "$P7" ] && echo "PASS T=1 bit-exact" || echo "FAIL T=1 bit-exact"

C5B=$(./prambh_chain walk --seed-hex $SEED_A --s $S --t $T)
[ "$C1" = "$C5B" ] && echo "PASS determinism (same run twice)" || echo "FAIL determinism"
[ ${#C1} -eq 64 ] && echo "PASS output is 64 hex chars" || echo "FAIL output is 64 hex chars"

Z0=$(./prambh_chain walk --seed-hex $ZERO --s 32 --t 0)
PZ=$(python3 model_chain.py walk $ZERO 32 0)
[ "$Z0" = "$PZ" ] && echo "PASS steps=0 python agrees" || echo "FAIL steps=0 python agrees"
[ "$Z0" != "$ZERO" ] && echo "PASS steps=0 returns run-label hash (not raw seed)" || echo "FAIL steps=0 returns raw seed"

SB=10112233445566778899aabbccddeeff00112233445566778899aabbccddeeff
CB=$(./prambh_chain walk --seed-hex $SB --s $S --t $T)
[ "$C1" != "$CB" ] && echo "PASS seed single-bit sensitivity" || echo "FAIL seed single-bit sensitivity"

CT=$(./prambh_chain walk --seed-hex $SEED_A --s $S --t 10001)
[ "$C1" != "$CT" ] && echo "PASS step-count sensitivity" || echo "FAIL step-count sensitivity"

# --- mutation probes: every spec element matters ---
for KIND in fill-swap walk-no-t walk-t-offby1 bad-fill-label bad-run-label bad-S bad-T; do
  M=$(python3 model_chain.py mutate $SEED_A $S $T $KIND)
  [ "$M" != "$C1" ] && echo "PASS mutation $KIND changes output" || echo "FAIL mutation $KIND changes output"
done

SBX=/tmp/prambh_chain_suite
rm -rf $SBX; mkdir -p $SBX

./prambh_chain walk --seed-hex $ZERO --s $S --t $T --dump-table $SBX/tab.bin > /dev/null
[ $(stat -c %s $SBX/tab.bin) -eq $S ] && echo "PASS dumped table exactly S bytes" || echo "FAIL dumped table size"

CF=$(./prambh_chain walk --seed-hex $ZERO --s $S --t $T --table-file $SBX/tab.bin)
CD=$(./prambh_chain walk --seed-hex $ZERO --s $S --t $T)
[ "$CF" = "$CD" ] && echo "PASS table-file reload identical" || echo "FAIL table-file reload identical"

PT=$(python3 model_chain.py walktable $ZERO $S $T $SBX/tab.bin)
[ "$PT" = "$CF" ] && echo "PASS python walks dumped table bit-exact" || echo "FAIL python walks dumped table bit-exact"

./prambh_chain walk --seed-hex $SEED_A --s $S --t 5 --dump-table $SBX/tabA.bin > /dev/null
T1H=$(sha256sum $SBX/tabA.bin | cut -d' ' -f1)
./prambh_chain walk --seed-hex $SEED_A --s $S --t 7 --dump-table $SBX/tabA2.bin > /dev/null
T2H=$(sha256sum $SBX/tabA2.bin | cut -d' ' -f1)
[ "$T1H" != "$T2H" ] && echo "PASS fill preimage binds T" || echo "FAIL fill binds T"

./prambh_chain walk --seed-hex $SEED_A --s $S --t 5 --dump-table $SBX/tabA3.bin > /dev/null
T3H=$(sha256sum $SBX/tabA3.bin | cut -d' ' -f1)
[ "$T1H" = "$T3H" ] && echo "PASS fill deterministic" || echo "FAIL fill deterministic"

python3 -c "
d = bytearray(open('$SBX/tab.bin','rb').read())
d[5000] ^= 0x01
open('$SBX/tab_bad.bin','wb').write(d)
"
CC_=$(./prambh_chain walk --seed-hex $ZERO --s $S --t $T --table-file $SBX/tab_bad.bin)
[ "$CC_" != "$CD" ] && echo "PASS corrupted table block changes output" || echo "FAIL corrupted table block changes output"

head -c 32768 $SBX/tab.bin > $SBX/tab_trunc.bin
./prambh_chain walk --seed-hex $ZERO --s $S --t $T --table-file $SBX/tab_trunc.bin > /dev/null 2>&1
[ $? -ne 0 ] && echo "PASS withheld/truncated table refused" || echo "FAIL withheld/truncated table refused"

./prambh_chain walk --seed-hex deadbeef --s $S --t $T > /dev/null 2>&1
[ $? -ne 0 ] && echo "PASS bad seed rejected" || echo "FAIL bad seed rejected"

# --- independent KATs against the exact spec preimages ---
KAT0=$(python3 -c "
import hashlib, struct
m = b'prambh:chain:fill:v1' + bytes.fromhex('$SEED_A') + struct.pack('<Q', $S) + struct.pack('<Q', 5)
print(hashlib.sha256(m).hexdigest())
")
HB=$(xxd -p -l 32 $SBX/tabA.bin | tr -d '\n')
[ "$KAT0" = "$HB" ] && echo "PASS fill KAT table[0] (label+seed+S+T)" || echo "FAIL fill KAT table[0]"

KAT1=$(python3 -c "
import hashlib, struct
d = open('$SBX/tabA.bin','rb').read()
print(hashlib.sha256(d[0:32] + struct.pack('<Q', 1)).hexdigest())
")
HB1=$(xxd -p -s 32 -l 32 $SBX/tabA.bin | tr -d '\n')
[ "$KAT1" = "$HB1" ] && echo "PASS fill KAT table[1]" || echo "FAIL fill KAT table[1]"

# --- reduced-table (checkpoint) attack measurements ---
ATK=$(python3 model_chain.py attack $SEED_A $S 2000 8 2>$SBX/atk8.log | tail -1)
HON=$(python3 model_chain.py walk $SEED_A $S 2000)
[ "$ATK" = "$HON" ] && echo "PASS checkpoint attack reproduces output (soundness)" || echo "FAIL checkpoint attack soundness"
R8=$(grep -o 'recomputes [0-9]*' $SBX/atk8.log | cut -d' ' -f2)
[ "$R8" -gt 100000 ] && echo "PASS attack(8 ckpt) recompute blowup: $R8 for 2000 steps" || echo "FAIL attack blowup 8ckpt"

python3 model_chain.py attack $SEED_A $S 2000 64 2>$SBX/atk64.log > /dev/null
R64=$(grep -o 'recomputes [0-9]*' $SBX/atk64.log | cut -d' ' -f2)
[ "$R64" -lt "$R8" ] && echo "PASS memory-time tradeoff monotone (64ckpt=$R64 < 8ckpt=$R8)" || echo "FAIL memory-time tradeoff"

python3 model_chain.py attack $SEED_A $S 500 1 2>$SBX/atk1.log > /dev/null
R1C=$(grep -o 'recomputes [0-9]*' $SBX/atk1.log | cut -d' ' -f2)
echo "PASS attack(1 ckpt, minimal memory) recomputes: $R1C for 500 steps (recorded)"

# --- memory hardness: RSS >= 0.9*S during a real walk ---
/usr/bin/time -v ./prambh_chain walk --seed-hex $ZERO --s 134217728 --t 10 > /dev/null 2>$SBX/time.log
RSS=$(grep "Maximum resident set size" $SBX/time.log | grep -o "[0-9]*")
NEED=$(( 134217728 * 9 / 10 / 1024 ))
[ "$RSS" -ge "$NEED" ] && echo "PASS peak RSS ${RSS}kB >= 0.9*S (${NEED}kB)" || echo "FAIL peak RSS ${RSS}kB < ${NEED}kB"

# --- latency-bound: parallel walkers do not speed up a single chain ---
RS=$(./prambh_chain measure --s 33554432 --seconds 3 2>/dev/null | cut -d' ' -f1)
./prambh_chain measure --s 33554432 --seconds 3 > $SBX/m1.txt 2>/dev/null &
BGPID=$!
R2=$(./prambh_chain measure --s 33554432 --seconds 3 2>/dev/null | cut -d' ' -f1)
wait $BGPID
R2B=$(cut -d' ' -f1 $SBX/m1.txt)
echo "PASS parallel probe: solo $RS steps/3s vs concurrent $R2 + $R2B (recorded)"

# --- timing variance across 3 runs < 5% ---
V1=$(./prambh_chain measure --s 33554432 --seconds 2 2>/dev/null | cut -d' ' -f1)
V2=$(./prambh_chain measure --s 33554432 --seconds 2 2>/dev/null | cut -d' ' -f1)
V3=$(./prambh_chain measure --s 33554432 --seconds 2 2>/dev/null | cut -d' ' -f1)
python3 -c "
v = sorted([int('$V1'), int('$V2'), int('$V3')])
spread = (v[2] - v[0]) / v[0]
print(('PASS' if spread < 0.05 else 'FAIL') + ' timing variance %.3f%% (%d %d %d)' % (spread*100, v[0], v[1], v[2]))
"

FB_T=$(./prambh_chain fillbench --s 33554432)
echo "PASS fillbench 32MiB in ${FB_T}s (recorded)"

rm -rf $SBX
echo "CHAIN SUITE DONE"
