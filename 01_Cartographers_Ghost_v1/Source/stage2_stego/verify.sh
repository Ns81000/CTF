#!/bin/bash
# s2_verify.sh -- Phase 3 clean-room verification run (INTERNAL, not shipped).
# Runs every phase's suite SERIALLY (they share cartographer/.cartographer_state)
# plus regeneration/reproducibility/hygiene checks.  Runnable verbatim:
#   wsl.exe bash -lc 'bash /home/manish/cartographer-build/src/stage2_stego/verify.sh'
set -u

R=/home/manish/cartographer-build
P="$R/cartographer/stage2_stego"
S="$R/src/stage2_stego"
BIN="$P/stage2_stego"

echo "############ 1. state library (Phase 0) ############"
cd "$R/src/state" && make clean && make test && file test_state

echo
echo "############ 2. stage0_start (Phase 1) ############"
cd "$R/src/stage0" && make && ./test_stage0.sh

echo
echo "############ 3. stage1_vm (Phase 2) ############"
cd "$R/src/stage1_vm" && make test | tail -4

echo
echo "############ 4. stage2_stego (Phase 3) ############"
cd "$S" && make test

echo
echo "############ 5. carrier regeneration determinism ############"
sha256sum "$P/survey_frame.png" "$P/survey_tape.wav" > /home/manish/gen1.txt
cd "$S" && python3 gen_carriers.py > /home/manish/gen_out.txt
sha256sum "$P/survey_frame.png" "$P/survey_tape.wav" > /home/manish/gen2.txt
diff /home/manish/gen1.txt /home/manish/gen2.txt && echo REGEN-DETERMINISTIC-OK
sha256sum "$S/vm_layout.json" 2>/dev/null || true
sha256sum "$S/stage2_blob.h" > /home/manish/hdr1.txt
python3 gen_carriers.py > /dev/null
sha256sum "$S/stage2_blob.h" > /home/manish/hdr2.txt
diff /home/manish/hdr1.txt /home/manish/hdr2.txt && echo HEADER-DETERMINISTIC-OK

echo
echo "############ 6. binary reproducibility (two clean rebuilds) ############"
sha256sum "$BIN"
cd "$S" && rm -f "$BIN" && make > /dev/null 2>&1 && sha256sum "$BIN"
rm -f "$BIN" && make > /dev/null 2>&1 && sha256sum "$BIN"

echo
echo "############ 7. artifact inventory ############"
ls -l "$P"
file "$BIN"
wc -c "$BIN"
strings -n 6 "$BIN" | grep -Ei "GCC|clang|musl|/home/manish|cartographer-build" && echo "SCRUB-RESIDUE" || echo "SCRUB-CLEAN"

echo
echo "############ 8. solver-eye smoke run ############"
cd "$R/cartographer"
rm -f .cartographer_state
./stage2_stego/stage2_stego
echo "--- claim of the real reading ---"
./stage2_stego/stage2_stego -c 'CARTO{no_figure_sits_in_every_pixel}'
echo "--- decoy claim ---"
./stage2_stego/stage2_stego -c 'CARTO{twice_over_the_coast_before_the_interior}'
rm -f .cartographer_state
echo
echo "############ done ############"