#!/usr/bin/env python3
"""probe_poison_volume.py -- Phase FINAL-2 evidence script.  INTERNAL only.

The kickoff asks whether the anti-automation trap still has teeth at the NEW
call volume (4160 oracle calls at N_REQUIRED=260) -- i.e. whether a solver who
scripts the whole Stage-3 collection at the new budget walks away with a
poisoned dataset rather than an error.

This drives the real, unscaled shipped oracle with the FULL new budget at a
machine-uniform fixed spacing (the thing a scripted loop naturally does), then
runs the reference attack on the collected dataset.

Expected, by design: the trap fires the moment the ring holds
CARTO_MIN_TIMING_DELTAS deltas, so a scripted run's dataset is a MIX -- the
first couple of pairs under the real key, everything after under the poison
key -- and the reference attack returns NO-CONSENSUS: the solver gets
nothing, silently. (A dataset collected entirely under the poison key, which
is what src/stage3_oracle/test_stage3.sh drives with --poison-converges,
recovers the poison key 0fab297110c73e9f instead. Both outcomes are the trap
working; neither is an error and neither is the real key.)

    python3 src/final/probe_poison_volume.py
"""

import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src" / "stage3_oracle"))

import cartosolve as C          # noqa: E402
import model_oracle as M        # noqa: E402

PKG = os.environ.get("CARTO_PKG", "/tmp/carto_poison_probe")


def main():
    os.environ["CARTO_PKG"] = PKG
    n = int(os.environ.get("CARTO_PROBE_PER_WINDOW", str(C.N_REQUIRED)))
    print("package root : %s" % PKG)
    print("budget       : 8 x %d pairs = %d oracle calls, fixed 0.1 s spacing"
          % (n, 16 * n))
    pace = (0.1, 0.1)                       # machine-uniform on purpose
    t0 = time.time()
    recs = C.collect_pairs(C.READING, n, pace, None, tag="poison",
                           seed=0x0BAD, progress_every=260)
    sd, _ = C.ring_stddev()
    kA, kB, rep = M.attack(recs)
    got = None if kA is None else "%08x%08x" % (kA, kB)
    real = C.model_kdf(C.READING)
    print("collected %d pairs in %.1f s" % (len(recs), time.time() - t0))
    print("ring stddev  : %s ms (poison floor 150.0 ms)"
          % ("n/a" if sd is None else "%.2f" % sd))
    print("attack state : %s" % rep["state"][:3])
    print("recovered K  : %s" % got)
    print("real K       : %08x%08x" % real)
    if got == "0fab297110c73e9f":
        print("RESULT: POISONED-AS-DESIGNED (dataset self-consistent under the "
              "poison key; the scripted run was never told)")
        return 0
    if got is None:
        print("RESULT: NO-CONSENSUS -- AS DESIGNED.  The dataset mixes the "
              "first few clean answers with the poisoned ones, so no key "
              "explains it: the scripted run silently gets nothing.")
        return 0
    if got == "%08x%08x" % real:
        print("RESULT: NOT POISONED -- the trap did not fire at this volume")
        return 1
    print("RESULT: unexpected key recovered: %s" % got)
    return 1


if __name__ == "__main__":
    sys.exit(main())
