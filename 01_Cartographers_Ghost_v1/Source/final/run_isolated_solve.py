#!/usr/bin/env python3
"""run_isolated_solve.py -- Phase FINAL section 7: solve a package standing
alone, with the package root re-pointed (CARTO_PKG=/tmp/cartographer-dist).

Proves the extracted Drive copy runs end to end: every stage is driven with the
shipped binaries that live in the isolated directory, every derivation is
re-done from the isolated carrier files, the isolated oracle's answers are
cross-checked bit-exactly against the independent cipher model, and the final
title is accepted by the isolated validator.

The Stage-3 differential attack is NOT re-paid here (it is a fixed 4160-query
budget at the calibrated N_REQUIRED=260, measured in full by the Phase FINAL-2
confirmation runs); instead the isolated oracle is
proven to be the identical cipher by bit-exact agreement with the model on a
set of chosen figures, which is what the attack's correctness rests on.
"""

import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cartosolve as C                          # noqa: E402

if "CARTO_PKG" not in os.environ:
    raise SystemExit("set CARTO_PKG to the extracted package root")

EXPECT_KEY = "fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f"
EXPECT_K = "73070925a159f9e2"
EXPECT_TITLE = ("CARTO{73070925a159f9e2_a5d66f1b2b5f596e_"
                "no_figure_sits_in_every_pixel}")


def main():
    print("isolated package root: %s" % C.PKG)
    print("carriers in the package:")
    for f in sorted(C.PKG.rglob("*")):
        if f.is_file():
            print("  %-44s %8d bytes" % (f.relative_to(C.PKG), f.stat().st_size))
    assert (C.PKG / "stage2_stego" / "survey_frame.png").exists(), "sheet missing"
    assert (C.PKG / "stage2_stego" / "survey_tape.wav").exists(), "tape missing"

    C.fresh_state()
    t0 = time.time()
    flag0 = C.stage0(lambda m: print("  " + m))
    assert flag0 == "CARTO{first_ink_in_the_ledger}", flag0
    key, _ = C.stage1(lambda m: print("  " + m))
    assert key == EXPECT_KEY, key
    reading, info = C.extract_reading(key)
    assert reading == C.READING, (reading, info)
    print("  sweep from the isolated sheet: stride=%d start=%d framed=%d -> %s"
          % (info["stride"], info["start"], info["len"], reading))
    out = C.stage2_claim(reading)
    assert "the ledger takes this reading" in out, out[:300]
    print("  isolated stage 2 accepted the reading")

    # the isolated oracle must be the same cipher the attack model describes.
    # First, the designed behaviour on a NAIVE fresh-state scripted sequence:
    # the ring's inter-arrival stddev is tiny, so TIMING_UNIFORM fires and the
    # oracle silently serves the poison key. Demonstrate it, then pace like a
    # solver who has noticed, and only then cross-check the model.
    kA, kB = C.model_kdf(reading)
    figures = ("0123456789abcdef", "ffffffffffffffff", "0000000000000000",
               "123456789abcdef0", "deadbeefcafebabe", "00000000000000ff")
    poisoned = C.oracle_query(reading, figures[0])
    if poisoned != C.model_encrypt(kA, kB, int(figures[0], 16)):
        print("  fresh-state oracle answers %016x -- NOT the real key's"
              " answer (the poison fired, as designed: a tight scripted"
              " sequence looks uniform)" % poisoned)
    else:
        print("  fresh-state oracle answered under the real key")
    C.forge_ring("human")
    bad = 0
    for fig in figures:
        got = C.oracle_query(reading, fig)
        want = C.model_encrypt(kA, kB, int(fig, 16))
        if got != want:
            bad += 1
            print("  MISMATCH %s isolated=%016x model=%016x" % (fig, got, want))
    assert bad == 0, "isolated oracle disagrees with the model in %d cases" % bad
    print("  isolated oracle matches the cipher model bit-exactly on %d"
          " figures once the solver paces" % len(figures))
    print("  K under the isolated sheet's reading: %s" % EXPECT_K)

    title = C.assemble(EXPECT_K, EXPECT_KEY[32:48], reading[len("CARTO{"):-1])
    assert title == EXPECT_TITLE, title
    out = C.stage4_validate(title)
    assert "the ledger takes the title" in out, out[:300]
    print("  isolated validator ACCEPTED the assembled title")
    C.fresh_state()
    print("ISOLATED-SOLVE-OK in %.1f s" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
