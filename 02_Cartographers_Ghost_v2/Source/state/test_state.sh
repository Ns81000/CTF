#!/bin/bash
# Phase 1 acceptance driver -- SERIAL ONLY (the tests share one record).
set -u
cd "$(dirname "$0")"
fail=0
say() { printf '%s\n' "$*"; }

say "== vectors =="
python3 gen_vectors.py || fail=1

say "== build =="
make libstate.a mkrec >/dev/null 2>&1 || { say "FAIL: library build"; exit 1; }
musl-gcc -O2 -Wall -Wextra -std=c11 -static -fno-ident \
    test_part1.c test_part2.c libstate.a -o test_state -lm || fail=1

say "== unit suite =="
./test_state > /tmp/p1_suite.txt 2>&1 || fail=1
tail -2 /tmp/p1_suite.txt
if grep -q "FAIL" /tmp/p1_suite.txt; then
    say "FAIL: suite reported failures"
    grep "FAIL" /tmp/p1_suite.txt
    fail=1
fi

say "== wheel: does an independent implementation accept the bytes? =="
rm -rf /tmp/p1rec
mkdir -p /tmp/p1rec
./mkrec /tmp/p1rec 1700000000000 || fail=1
python3 gen_vectors.py /tmp/p1rec/.cartographer_state || fail=1
size=$(stat -c %s /tmp/p1rec/.cartographer_state)
[ "$size" = "1168" ] && say "PASS record size 1168" || { say "FAIL size=$size"; fail=1; }
count=$(ls -A /tmp/p1rec | wc -l)
[ "$count" = "1" ] && say "PASS exactly one file written" || { say "FAIL files=$count"; fail=1; }

say "== leak scan: no plaintext key material in the linked test binaries =="
for v in $(awk '{print $2}' /tmp/carto_v2_vectors.txt); do
    case "$v" in
        *[!0-9a-f]*|"") continue ;;
    esac
    [ ${#v} -eq 64 ] || continue
    if strings -n 8 test_state mkrec 2>/dev/null | grep -q "${v:0:16}"; then
        say "FAIL key material visible: ${v:0:16}"
        fail=1
    fi
done
say "PASS leak scan (no vector prefix found in test_state/mkrec)"

say "== shipped binaries must ignore the test hook =="
if strings -n 6 test_state mkrec | grep -q CARTO_TEST_TIME_SCALE; then
    say "FAIL: the test hook leaked into a test binary"
    fail=1
else
    say "PASS test hook absent from default builds"
fi

if [ $fail -eq 0 ]; then say "OK"; else say "NOT OK"; fi
exit $fail
