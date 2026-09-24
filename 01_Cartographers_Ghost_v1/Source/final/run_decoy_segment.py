#!/usr/bin/env python3
"""run_decoy_segment.py -- Phase FINAL calibration Run B (DECOY DETOUR ONLY).

Measures ONLY the added cost of the decoy detour, not the whole chain again.
It starts from a state already at Stage 1 (Stage 0 is run purely to mint a
valid ledger and is excluded from the timing), then:

  1. submits the Stage-1 decoy token  -> the engine "corroborates" it and
     re-inks the forgotten checkpoint key (the 1-1.5 h trap's entry point);
  2. follows that key to its dead end: the swept bytes neither parse nor
     inflate, and the Stage-2 verifier refuses them -- with no error and no
     diagnosis, exactly as designed;
  3. takes the Stage-2 naive whole-image LSB bait -> the coast flag, which is
     ACCEPTED into an extended branch framed as progress;
  4. feeds the Stage-2 checkpoint token back to the oracle -> the Stage-3
     decoy branch, i.e. the detour deepens one more stage;
  5. hands the struck draft to the Stage-4 block -> corroborated draft;
  6. recovers: re-runs the engine cleanly, re-derives the real sweep,
     re-presses the ink, and stops the clock the moment the real reading is
     accepted -- i.e. back on the real path at the START of Stage 3.

The clock covers the whole detour+recovery segment and nothing else.
"""

import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cartosolve as C                          # noqa: E402

LOG = os.environ.get("CARTO_FINAL_LOG",
                     str(C.ROOT / "logs" / "runs" / "final_decoy_segment.log"))
EXPECT_KEY = "fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f"


def main():
    log = C.RunLog(LOG)
    log("=== Run B -- DECOY DETOUR SEGMENT (added cost only) ===")

    # untimed preamble: get the ledger to Stage 1 and note what it looks like
    C.fresh_state()
    C.stage0(log)
    log("preamble: stage 0 run; the timed segment starts here (state is at "
        "Stage 1)")
    t_start = time.time()
    log.t0 = t_start

    # ---------------------------------------------------- 1. take the bait
    decoy_key, decoy_token = C.stage1(log, token=C.DECOY_S1_TOK, tag="decoy")
    if decoy_token != C.DECOY_S1_TOK:
        raise SystemExit("decoy route did not re-ink the decoy token: %s"
                         % decoy_token)
    log.mark("detour: stage-1 decoy accepted")

    # ------------------------------------- 2. follow it to the dead end
    reading_bad, info_bad = C.extract_reading(decoy_key, log)
    log("   decoy sweep: stride=%d start=%d framed_len=%s -> %s"
        % (info_bad["stride"], info_bad["start"], info_bad["len"],
           "unparseable/inflate-refused" if reading_bad is None else reading_bad))
    if reading_bad is not None:
        raise SystemExit("the decoy sweep was supposed to be garbage")
    # the same bytes handed to the verifier as a claim: a plain refusal
    claim = C.bit_claim(decoy_key)
    out = C.stage2_claim(claim)
    if "the ledger does not know that reading" not in out:
        raise SystemExit("stage 2 did not refuse the decoy claim:\n" + out[:300])
    log("   stage2_stego refused the decoy reading with no diagnosis "
        "(dead end confirmed)")
    log.mark("detour: stage-2 dead end reached")

    # --------------------------------- 3. the naive whole-image LSB bait
    w, h, img = C.sheet_marks()
    naive = C.naive_lsb_decoy(img)
    coast = C.flag_from_bytes(naive)
    log("   naive whole-image LSB read yields: %s" % coast)
    if coast != C.DECOY_S2_FLAG:
        raise SystemExit("naive LSB bait mismatch: %s" % coast)
    out = C.stage2_claim(coast)
    if "the ledger knows this ink" not in out:
        raise SystemExit("stage 2 did not route the naive-LSB decoy:\n" + out[:300])
    log("   stage2_stego ACCEPTED it into the extended branch (reads as "
        "progress)")
    log.mark("detour: stage-2 decoy branch")

    # ------------------------- 4. feed the checkpoint back to the oracle
    out = C.oracle_query_raw(C.DECOY_S3_TOK, "0123456789abcdef")
    if "re-inked checkpoint" not in out:
        raise SystemExit("oracle did not route the checkpoint token:\n" + out[:300])
    log("   oracle ACCEPTED the Stage-2 checkpoint token as a reading "
        "(re-inked checkpoint branch)")
    log.mark("detour: stage-3 decoy branch")

    # ------------------------------ 5. the struck draft at the title block
    out = C.stage4_validate(C.DECOY_S4_FLAG)
    if "corroborated draft" not in out:
        raise SystemExit("validator did not route the struck draft:\n" + out[:300])
    log("   validator ACCEPTED the struck draft as a corroborated draft")
    log.mark("detour: stage-4 decoy branch")

    # ------------------------------------------------------- 6. recovery
    log("recovery: re-running the engine cleanly")
    real_key, real_token = C.stage1(log, tag="recover")
    if real_key != EXPECT_KEY:
        raise SystemExit("recovery key mismatch: %s" % real_key)
    reading, info = C.extract_reading(real_key, log)
    if reading != C.READING:
        raise SystemExit("recovery reading mismatch: %r" % reading)
    out = C.stage2_claim(reading)
    if "the ledger takes this reading" not in out:
        raise SystemExit("stage 2 refused the recovered reading:\n" + out[:300])
    log.mark("recovery: real reading accepted")

    t_end = time.time()
    detour = t_end - t_start
    log("RESULT: detour segment complete; real path resumed at the START of "
        "Stage 3")
    log("ADDED DETOUR COST: %.2f s (%.2f min)" % (detour, detour / 60.0))
    log.summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
