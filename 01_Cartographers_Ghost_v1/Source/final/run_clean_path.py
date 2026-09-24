#!/usr/bin/env python3
"""run_clean_path.py -- Phase FINAL calibration Run A (CLEAN PATH).

Solves the whole challenge start to finish with no detours, driving the real
shipped binaries in the package root, and timestamps every step.  The only
wall-clock-dominant step is the Stage-3 chosen-plaintext query budget, so the
pacing is explicit and printed up front.

Env knobs (all optional):
  CARTO_FINAL_PER_WINDOW  pairs per experiment (default 260 -> 2080 pairs,
                          4160 oracle calls: the Phase FINAL-2 calibrated
                          sample size; see SOLVE_PATH_PRIVATE.md section 4)
  CARTO_FINAL_PACE        inter-query spacing: "a,b" alternates, or
                          "jitter:lo,hi" draws a fresh uniform value per
                          query (the cautious/human cadence used for the
                          Phase FINAL-2 upper-bound run)
  CARTO_FINAL_LOG         log path
  CARTO_TEST_TIME_SCALE   divides the pacing (mirrors the library's test-only
                          hook so the SAME run can be exercised in seconds)

Run A is the clean-path measurement; it must be run with
CARTO_TEST_TIME_SCALE unset (scale 1) for the reported number.
"""

import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cartosolve as C                          # noqa: E402

TSCALE = int(os.environ.get("CARTO_TEST_TIME_SCALE", "1") or "1")
PER_WINDOW = int(os.environ.get("CARTO_FINAL_PER_WINDOW", str(C.N_REQUIRED)))
PACE_SPEC = os.environ.get("CARTO_FINAL_PACE", "jitter:0.6,3.4")
PACE = C.parse_pace(PACE_SPEC)
if TSCALE != 1:
    PACE = ((PACE[0], PACE[1] / TSCALE, PACE[2] / TSCALE) if PACE[0] == "jitter"
            else ("alt", PACE[1] / TSCALE, PACE[2] / TSCALE))

LOG = os.environ.get("CARTO_FINAL_LOG",
                     str(C.ROOT / "logs" / "runs" / "final_clean_path.log"))

EXPECT_KEY = "fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f"
EXPECT_READING = C.READING
EXPECT_K = "73070925a159f9e2"
EXPECT_TITLE = ("CARTO{73070925a159f9e2_a5d66f1b2b5f596e_"
                "no_figure_sits_in_every_pixel}")


def main():
    log = C.RunLog(LOG)
    pairs = 8 * PER_WINDOW
    queries = 2 * pairs
    mean, sd = C.pace_stats(PACE)
    log("=== Run A -- CLEAN PATH ===")
    log("time scale            : %d %s" % (TSCALE,
        "(REAL/UNSCALED)" if TSCALE == 1 else "(TEST BUILD -- not a real number)"))
    log("Stage-3 budget        : 8 experiments x %d pairs = %d pairs = %d queries"
        % (PER_WINDOW, pairs, queries))
    log("pacing                : %s  -> mean %.3f s, stddev %.3f s"
        % (PACE_SPEC, mean, sd))
    log("projected Stage-3 time: %.1f min (%.2f s per query)"
        % (queries * mean / 60.0, mean))
    log("poison floor in force : CARTO_STDDEV_LOW_MS = 150.0 ms (stddev margin %.1fx)"
        % (sd * 1000.0 / 150.0))

    C.fresh_state()
    log("state file removed; starting from a fresh ledger")

    # ---------------------------------------------------------- stage 0
    flag0 = C.stage0(log)
    if flag0 != "CARTO{first_ink_in_the_ledger}":
        raise SystemExit("stage 0 flag unexpected: %s" % flag0)
    log.mark("stage0_start")

    # ---------------------------------------------------------- stage 1
    key, token = C.stage1(log)
    if key != EXPECT_KEY:
        raise SystemExit("stage 1 key mismatch: %s" % key)
    log("   (matches the recorded real Stage-2 key material)")
    log.mark("stage1_vm")

    # ------------------------------------------------- stage 2 (read+press)
    reading, info = C.extract_reading(key, log)
    log("   sweep detail: %s" % info)
    if reading is None:
        raise SystemExit("sweep failed: %s" % info.get("error"))
    log("   reading extracted: %s" % reading)
    if reading != EXPECT_READING:
        raise SystemExit("reading mismatch: %r" % reading)
    C.stage2_claim(reading)
    log("   ./stage2_stego/stage2_stego -c '<reading>' accepted it")
    log.mark("stage2_stego")

    # ------------------------------------------------------------ stage 3
    t_queries = time.time()
    records = C.collect_pairs(reading, PER_WINDOW, PACE, log, tag="runA")
    dt = time.time() - t_queries
    log("collection finished in %.1f s (%.2f min); %.3f s per query measured"
        % (dt, dt / 60.0, dt / queries))
    sd_ring, deltas = C.ring_stddev()
    log("ring stddev after collection: %s ms (poison floor 150.0 ms)"
        % ("n/a" if sd_ring is None else "%.1f" % sd_ring))
    kAx, kBx, rep = C.attack(records)
    if kAx is None:
        raise SystemExit("attack: NO-CONSENSUS: %s" % rep)
    kmaster = "%08x%08x" % (kAx, kBx)
    log("attack recovered K = %s (hits A=%s B=%s)"
        % (kmaster, rep["hits_a"], rep["hits_b"]))
    if kmaster != EXPECT_K:
        raise SystemExit("recovered key mismatch: %s" % kmaster)
    log("   (matches the recorded real Stage-3 master key)")
    log.mark("stage3_oracle")

    # ------------------------------------------------------------ stage 4
    engine_ink = key[32:48]
    title = C.assemble(kmaster, engine_ink, reading[len("CARTO{"):-1])
    log("assembled title: %s" % title)
    if title != EXPECT_TITLE:
        raise SystemExit("title mismatch")
    out = C.stage4_validate(title)
    if "the ledger takes the title" not in out:
        raise SystemExit("validator refused the title:\n" + out[:400])
    log("   ./stage4_assembly/validate accepted the title -- SURVEY CLOSED")
    log.mark("stage4_assembly")

    log("RESULT: CLEAN-PATH SOLVE COMPLETE, deterministically")
    log.summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
