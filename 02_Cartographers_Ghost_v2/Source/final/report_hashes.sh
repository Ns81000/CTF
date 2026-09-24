#!/bin/bash
# report_hashes.sh -- the hashes that name the build.
set -u
cd "$(dirname "$0")/../.." || exit 1
echo "== shipped binaries"
for b in cartographer/stage0_ledger/ledger cartographer/stage1_engine/engine \
         cartographer/stage2_sheet/sheet cartographer/stage3_oracle/oracle \
         cartographer/stage4_seal/seal cartographer/stage5_title/validate; do
    [ -f "$b" ] && printf '%s  %s\n' "$(sha256sum "$b" | awk '{print $1}')" "$b"
done
echo "== carriers"
for c in cartographer/stage2_sheet/survey_frame.png \
         cartographer/stage2_sheet/survey_tape.wav; do
    [ -f "$c" ] && printf '%s  %s\n' "$(sha256sum "$c" | awk '{print $1}')" "$c"
done
echo "== package"
[ -f organizer-private/cartographer.zip ] && \
    printf '%s  %s\n' "$(sha256sum organizer-private/cartographer.zip | awk '{print $1}')" \
        "organizer-private/cartographer.zip"
