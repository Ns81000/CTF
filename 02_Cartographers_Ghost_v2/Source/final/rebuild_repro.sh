#!/bin/bash
# rebuild_repro.sh -- clean rebuild twice, identical hashes of every binary.
set -u
cd "$(dirname "$0")/../.." || exit 1

first() {
    for b in cartographer/stage0_ledger/ledger cartographer/stage1_engine/engine \
             cartographer/stage2_sheet/sheet cartographer/stage3_oracle/oracle \
             cartographer/stage4_seal/seal cartographer/stage5_title/validate; do
        sha256sum "$b" | awk '{print $1}'
    done
}

H1=$(first)
for d in state stage0_ledger stage1_engine stage2_sheet stage3_oracle \
         stage4_seal stage5_title; do
    ( cd "src/$d" && make -s clean >/dev/null 2>&1 ) || exit 1
done
( cd src/state && make -s >/dev/null 2>&1 ) || exit 1
( cd src/stage0_ledger && make -s all >/dev/null 2>&1 ) || exit 1
( cd src/stage1_engine && make -s all >/dev/null 2>&1 ) || exit 1
( cd src/stage2_sheet && make -s all >/dev/null 2>&1 ) || exit 1
( cd src/stage3_oracle && make -s all >/dev/null 2>&1 ) || exit 1
( cd src/stage4_seal && make -s all >/dev/null 2>&1 ) || exit 1
( cd src/stage5_title && make -s all >/dev/null 2>&1 ) || exit 1
H2=$(first)
H3=$(first | head -1)
if [ "$H1" = "$H2" ]; then
    echo "REBUILD REPRODUCIBLE"
    exit 0
fi
echo "REBUILD DRIFT"
diff <(printf '%s\n' "$H1") <(printf '%s\n' "$H2")
exit 1
