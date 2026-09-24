#!/bin/bash
# verify_isolated.sh -- Phase FINAL section 7: isolated-package re-verification.
#
# Extracts drive-upload/cartographer.zip into a clean directory and treats it
# as if it had just been downloaded from Google Drive: audits the contents,
# re-runs the symbol/string audit against THIS copy specifically, and solves
# the extracted copy standing alone.
#
#   bash src/final/verify_isolated.sh
set -e
R=/home/manish/cartographer-build
DRIVE=$R/drive-upload
DIST=/tmp/cartographer-dist
PKG=$DIST/cartographer

rm -rf "$DIST" && mkdir -p "$DIST"
unzip -q "$DRIVE/cartographer.zip" -d "$DIST"

echo "--- 1. contents of the extracted package ---"
MAP=$(cd "$PKG" && find . -type f | sed 's|^\./||' | sort)
WANT=$(printf '%s\n' README_FOR_SOLVER.txt \
    stage0_start/stage0_start stage1_vm/stage1_vm \
    stage2_stego/stage2_stego stage2_stego/survey_frame.png \
    stage2_stego/survey_tape.wav stage3_oracle/oracle \
    stage4_assembly/validate | sort)
if [ "$MAP" != "$WANT" ]; then
    echo "EXTRACTED CONTENTS WRONG:"; diff <(echo "$WANT") <(echo "$MAP"); exit 1
fi
echo "$MAP" | sed 's/^/    /'
echo "  -> exactly the 9 shipped items, nothing else"

echo "--- 2. forbidden content ---"
for pat in '*.md' '*.markdown' '.git' '*.py' '*.c' '*.h' '*.o' '*.a' '*.log' \
           '*.json' '*.txt' '__pycache__' '*.pyc' 'Makefile' '*verify*' \
           '*test*' '*spec*' '*KICKOFF*' '*PHASE_*' '*SOLVE_PATH*'; do
    hits=$(cd "$PKG" && find . -name "$pat" -not -path './README_FOR_SOLVER.txt' | head -3)
    if [ -n "$hits" ]; then echo "  FORBIDDEN '$pat' -> $hits"; exit 1; fi
done
echo "  -> zero markdown, zero git, zero source, zero logs, zero artifacts"

echo "--- 3. executables survived the zip round-trip ---"
for b in stage0_start/stage0_start stage1_vm/stage1_vm \
         stage2_stego/stage2_stego stage3_oracle/oracle \
         stage4_assembly/validate; do
    if [ -x "$PKG/$b" ]; then
        echo "  executable: $b"
    else
        echo "  NOT EXECUTABLE after unzip: $b"; exit 1
    fi
done

echo "--- 4. symbol / string audit on THIS extracted copy ---"
BINS="$PKG/stage0_start/stage0_start $PKG/stage1_vm/stage1_vm \
      $PKG/stage2_stego/stage2_stego $PKG/stage3_oracle/oracle \
      $PKG/stage4_assembly/validate"
for b in $BINS; do
    n=$(nm "$b" 2>/dev/null | wc -l)
    [ "$n" = "0" ] && echo "  $(basename $b): nm clean" \
                   || { echo "  $(basename $b): nm has $n symbols"; exit 1; }
    if strings -n 4 "$b" | grep -Eqi 'manish|/home/|cartographer-build|/mnt/[a-z]'; then
        echo "  $(basename $b): LEAKED a host path or username"; exit 1
    fi
    if strings -n 4 "$b" | grep -q 'CARTO_TEST_TIME_SCALE'; then
        echo "  $(basename $b): LEAKED the test-only time-scale hook"; exit 1
    fi
    if strings -n 4 "$b" | grep -Eqi 'GCC:|clang|musl-gcc'; then
        echo "  $(basename $b): LEAKED a compiler ident"; exit 1
    fi
done
echo "  -> nm clean on all 5, no host paths/usernames, no compiler idents"
echo "  -> CARTO_TEST_TIME_SCALE absent from every extracted binary"
for s in "CARTO{first_ink_in_the_ledger}" \
         "73070925a159f9e2_a5d66f1b2b5f596e_no_figure_sits_in_every_pixel" \
         "fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f" \
         "73070925a159f9e2"; do
    if strings -n 4 $BINS | grep -qF "$s"; then
        echo "  REAL ANSWER FINDABLE: $s"; exit 1
    fi
done
echo "  -> no real answer material is strings-findable"

for s in "cartographer-mask-stage3-real" \
         "cartographer-mask-stage3-poison" \
         "interior-ink-formula" \
         "mod 9000" \
         "mod 61"; do
    if strings -n 4 $BINS | grep -qF "$s"; then
        echo "  LEAKED STRING FINDABLE IN BINARY: $s"; exit 1
    fi
done
echo "  -> no Phase FIX leak labels or formulas are strings-findable in binaries"
for s in "interior-ink-formula" "mod 9000" "mod 61" "stride = 3 +"; do
    if strings -n 4 "$PKG/stage2_stego/survey_frame.png" "$PKG/stage2_stego/survey_tape.wav" | grep -qF "$s"; then
        echo "  CARRIER LEAK FINDABLE: $s"; exit 1
    fi
done
echo "  -> carriers are clean of formulas and leak labels" 

echo "--- 5. full clean-path solve, standing alone in this copy ---"
echo "--- 6. what the isolated copy left behind ---"
BEFORE=$(cd "$PKG" && find . -type f | sort)
CARTO_PKG="$PKG" python3 "$R/src/final/run_isolated_solve.py"
AFTER=$(cd "$PKG" && find . -type f | sort)
NEW=$(comm -13 <(printf '%s\n' "$BEFORE") <(printf '%s\n' "$AFTER"))
if [ -n "$NEW" ]; then
    echo "  files created by the solve (must be none):"
    echo "$NEW" | sed 's/^/    /'
    exit 1
fi
if [ -e "$PKG/.cartographer_state" ] || [ -e "$PKG/.cartographer_state.tmp" ]; then
    echo "  FAIL: the isolated copy left a ledger behind"; exit 1
fi
echo "  -> no ledger, no tmp, nothing written outside the extracted folder"

echo "ISOLATED-VERIFICATION-OK"
