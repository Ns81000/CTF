#!/usr/bin/env python3
"""watch_runA.py -- non-invasive poll of the background calibration run.

Reads ONLY the run log and the ledger's interaction ring (no binary is
executed, so the run's state is never touched).
"""
import pathlib
import struct
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cartosolve as C                          # noqa: E402

LOG = C.ROOT / "logs" / "runs" / "final_clean_path.log"
STATE = C.PKG / ".cartographer_state"


def main():
    lines = LOG.read_text().splitlines()
    print("log lines: %d" % len(lines))
    for l in lines[-6:]:
        print("  " + l)
    if STATE.exists():
        sd, deltas = C.ring_stddev()
        n = len(deltas)
        print("ring: %d entries, %d deltas, stddev=%.1f ms, mean=%.1f ms"
              % (n + 1, n, sd if sd else -1,
                 sum(deltas) / n if n else -1))
        if n:
            print("last 8 deltas (ms): %s" % [int(d) for d in deltas[-8:]])
        poison = "YES" if (sd is not None and sd <= 150.0) else "no"
        print("poisoned right now: %s (floor 150.0 ms)" % poison)
    else:
        print("no ledger present")
    print("now: %s" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
