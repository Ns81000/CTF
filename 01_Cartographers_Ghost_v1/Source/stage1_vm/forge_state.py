#!/usr/bin/env python3
r"""s1_forge.py -- write an HMAC-valid .cartographer_state for test harnesses.

INTERNAL test tool (not shipped).  Same semantics as the forge_state() helper
inside src/stage1_vm/test_stage1.sh, kept as a standalone script so later
phases can stage precise escalation/decoy/debugger states without editing the
suite.

    python3 s1_forge.py <state-path> <human|uniform|fast> <first_run_age_ms> <debugger>
"""

import hashlib
import hmac
import struct
import sys
import time

CANONICAL_KEY = bytes.fromhex(
    "f03ea6b5c1b869482723c0d11d635f8e9966c43a0a8def87fd1e2e950c10a7de")
GAPS = {
    "human": [900, 4300, 1500, 8000, 2200, 11000, 700, 3000],
    "uniform": [10] * 8,
    "fast": [900, 4300, 1500, 8000, 2200, 11000, 700, 3000],
}


def main() -> None:
    path, mode = sys.argv[1], sys.argv[2]
    age_ms, dbg = int(sys.argv[3]), int(sys.argv[4])
    now = int(time.time() * 1000)
    gaps = GAPS[mode]
    buf = bytearray(352)
    buf[0:4] = b"CART"
    buf[4] = 1
    struct.pack_into("<Q", buf, 0x08, now - age_ms)
    ts = now - sum(gaps)
    for i, g in enumerate(gaps):
        ts += g
        struct.pack_into("<Q", buf, 0x40 + 8 * i, ts)
    struct.pack_into("<H", buf, 0x38, len(gaps))
    struct.pack_into("<H", buf, 0x3A, len(gaps))
    buf[0x3C] = dbg & 0xFF
    buf[0x140:0x160] = hmac.new(CANONICAL_KEY, bytes(buf[:0x140]),
                                hashlib.sha256).digest()
    open(path, "wb").write(bytes(buf))
    print("forged %s: mode=%s age=%dms dbg=%d" % (path, mode, age_ms, dbg))


if __name__ == "__main__":
    main()
