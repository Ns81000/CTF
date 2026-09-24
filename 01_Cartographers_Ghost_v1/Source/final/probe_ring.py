#!/usr/bin/env python3
"""probe_ring.py -- Phase FINAL-2 diagnostic.  INTERNAL, never shipped.

Answers, for the SCALED TEST BUILD, the only question that matters for the
trial harness: are the sampled ciphertexts the clean-key ones?

It collects a handful of figures sequentially in an isolated package root
(the same isolation trial_attack.py uses), then checks every answer against
the python model under BOTH the real key and the poison key, prints the
oracle's own "oracle mode" line, and dumps the interaction ring deltas and
the stddev the library would compute.
"""

import json
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src" / "stage3_oracle"))

READING = "CARTO{no_figure_sits_in_every_pixel}"
STATE = "./.cartographer_state"


def main():
    scale = int(os.environ.get("CARTO_FINAL_TSCALE", "60"))
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    pkg = pathlib.Path("/tmp/carto_probe")
    if pkg.exists():
        shutil.rmtree(pkg)
    (pkg / "stage3_oracle").mkdir(parents=True)
    (pkg / "stage2_stego").mkdir(parents=True)
    shutil.copy2(ROOT / "cartographer" / "stage3_oracle" / "oracle",
                 pkg / "stage3_oracle" / "oracle")
    for c in ("survey_frame.png", "survey_tape.wav"):
        shutil.copy2(ROOT / "cartographer" / "stage2_stego" / c,
                     pkg / "stage2_stego" / c)
    os.environ["CARTO_PKG"] = str(pkg)
    import cartosolve as C
    import model_oracle as M

    kA, kB, digest = M.kdf_real(READING.encode())
    pkA, pkB, _ = M.kdf_poison(digest)
    pace = (0.15 / scale, 1.85 / scale)
    os.environ["CARTO_TEST_TIME_SCALE"] = str(scale)   # scales the poison
    # floor by the same factor as the pacing (test build only)

    bins = []
    for i in range(n):
        p = 0x1122334455667788 + i * 0x0101010101010101
        out = subprocess.run([str(pkg / "stage3_oracle" / "oracle"),
                              "-r", READING, "%016x" % p], cwd=str(pkg),
                             capture_output=True, text=True)
        c = int(C.ANSWER_RE.search(out.stdout).group(1), 16)
        real_ok = (c == M.encrypt(kA, kB, p))
        pois_ok = (c == M.encrypt(pkA, pkB, p))
        mode = [l.strip() for l in out.stdout.splitlines()
                if "oracle mode" in l]
        bins.append((real_ok, pois_ok, mode[0] if mode else "?"))
        time.sleep(pace[i % 2])

    sd, deltas = C.ring_stddev()
    print("scale                     : %d" % scale)
    print("scaled poison floor (ms)  : %.4f" % (M and (150.0 / scale)))
    print("ring stddev (ms)          : %s" % ("n/a" if sd is None
                                               else "%.4f" % sd))
    print("ring deltas (ms)          : %s"
          % ("n/a" if deltas is None else
             [round(d, 3) for d in (deltas or [])[-12:]]))
    print("answers matching REAL key : %d/%d" % (sum(b[0] for b in bins), n))
    print("answers matching POISON   : %d/%d" % (sum(b[1] for b in bins), n))
    print("oracle mode lines         : %s"
          % sorted({b[2] for b in bins}))
    raw = pathlib.Path(pkg / STATE).read_bytes()
    print("state size                : %d bytes" % len(raw))
    print("first_run_ms / ring_count : %d / %d"
          % (struct.unpack_from("<Q", raw, 8)[0],
             struct.unpack_from("<H", raw, 56)[0]))
    print("debugger_detected / decoy : %d / %s"
          % (raw[60], list(struct.unpack_from("<3I", raw, 36))))
    print(json.dumps({"real": sum(b[0] for b in bins),
                      "poison": sum(b[1] for b in bins),
                      "ring_sd_ms": sd}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
