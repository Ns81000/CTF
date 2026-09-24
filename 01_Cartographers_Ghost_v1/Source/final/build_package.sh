#!/bin/bash
# build_package.sh -- Phase FINAL section 6: SPLIT PACKAGING.
#
# Produces two SEPARATE outputs that must never be mixed:
#   drive-upload/cartographer.zip   <- solver-facing ONLY: 5 binaries,
#                                      2 carriers, README_FOR_SOLVER.txt
#   organizer-private/              <- never shipped: the private writeup,
#                                      hints, room text, the build spec and
#                                      the whole internal log history
set -e
R=/home/manish/cartographer-build
DRIVE=$R/drive-upload
ORG=$R/organizer-private
P=$DRIVE/cartographer

for f in SOLVE_PATH_PRIVATE.md HINTS.md TRYHACKME_ROOM_TEXT.md \
         src/final/README_FOR_SOLVER.txt; do
    [ -f "$R/$f" ] || { echo "MISSING canonical source: $R/$f"; exit 1; }
done

rm -rf "$DRIVE" "$ORG"
mkdir -p "$P/stage0_start" "$P/stage1_vm" "$P/stage2_stego" \
         "$P/stage3_oracle" "$P/stage4_assembly" "$ORG"

# ---------------------------------------------------- 6a. the Drive package
cp "$R/cartographer/stage0_start/stage0_start"      "$P/stage0_start/"
cp "$R/cartographer/stage1_vm/stage1_vm"            "$P/stage1_vm/"
cp "$R/cartographer/stage2_stego/stage2_stego"      "$P/stage2_stego/"
cp "$R/cartographer/stage2_stego/survey_frame.png"  "$P/stage2_stego/"
cp "$R/cartographer/stage2_stego/survey_tape.wav"   "$P/stage2_stego/"
cp "$R/cartographer/stage3_oracle/oracle"           "$P/stage3_oracle/"
cp "$R/cartographer/stage4_assembly/validate"       "$P/stage4_assembly/"
cp "$R/src/final/README_FOR_SOLVER.txt"             "$P/README_FOR_SOLVER.txt"
chmod 755 "$P"/*/[a-z]*
chmod 644 "$P/README_FOR_SOLVER.txt" "$P/stage2_stego/survey_frame.png" \
          "$P/stage2_stego/survey_tape.wav"

# hard assertion: nothing but the nine permitted files, inside or below
MAP=$(cd "$P" && find . -type f | sed 's|^\./||' | sort)
WANT=$(printf '%s\n' README_FOR_SOLVER.txt \
    stage0_start/stage0_start stage1_vm/stage1_vm \
    stage2_stego/stage2_stego stage2_stego/survey_frame.png \
    stage2_stego/survey_tape.wav stage3_oracle/oracle \
    stage4_assembly/validate | sort)
if [ "$MAP" != "$WANT" ]; then
    echo "DRIVE PACKAGE CONTENTS WRONG:"; diff <(echo "$WANT") <(echo "$MAP"); exit 1
fi
echo "6a: drive package has exactly the 9 permitted files"

for pat in '*.md' '*.py' '*.c' '*.h' '*.o' '*.a' '*.log' '*.txt' '*.json' \
           '.git*' '__pycache__' '*.pyc' 'Makefile' '*verify*' '*test*'; do
    hits=$(cd "$P" && find . -name "$pat" -not -path './README_FOR_SOLVER.txt' | head -5)
    if [ -n "$hits" ]; then echo "6a: FORBIDDEN MATCH '$pat': $hits"; exit 1; fi
done
echo "6a: no markdown / source / logs / git / build artifacts in the drive package"

cd "$DRIVE" && rm -f cartographer.zip && zip -qr cartographer.zip cartographer
echo "6a: $DRIVE/cartographer.zip  ($(stat -c%s cartographer.zip) bytes)"
unzip -l cartographer.zip | tail -3

# ------------------------------------------------ 6b. the organizer bundle
cp "$R/SOLVE_PATH_PRIVATE.md" "$ORG/"
cp "$R/HINTS.md" "$ORG/"
cp "$R/TRYHACKME_ROOM_TEXT.md" "$ORG/"
mkdir -p "$ORG/docs" "$ORG/logs/runs"
cp "$R/docs/BUILD_SPEC.md" "$ORG/docs/"
cp "$R"/logs/*.md "$ORG/logs/"
cp "$R"/logs/runs/* "$ORG/logs/runs/"
cp "$R/src/final/README_FOR_SOLVER.txt" "$ORG/README_FOR_SOLVER.txt.solver-copy"

echo "6b: organizer-private/ ($(find "$ORG" -type f | wc -l) files)"
find "$ORG" -type f | sed "s|$ORG/|    |" | sort

# hard assertion: no organizer content ever reached the drive package
if unzip -l "$DRIVE/cartographer.zip" | grep -Eqi 'SOLVE_PATH|HINTS|TRYHACKME|BUILD_SPEC|PHASE_|KICKOFF|\.md$'; then
    echo "6b: ORGANIZER CONTENT LEAKED INTO THE DRIVE ZIP"; exit 1
fi
echo "6b: drive zip contains zero organizer content"
echo "SPLIT-PACKAGING-OK"
