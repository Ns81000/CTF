#!/usr/bin/env python3
"""state_dump.py <record> [op]  -- read a v2 record without the C library.

Prints the ring window oldest-first (ts, stage, op, dt, aux) and, when an op
code is given, only those entries.  Used by the stage suites to check what a
tool actually wrote down.
"""
import struct
import sys

RING = 0x060
ENTRY = 16
RING_SIZE = 64
OFF = {"ring_count": 0x058, "ring_head": 0x05A, "first_run": 0x008,
       "gates": 0x040}


def main():
    path = sys.argv[1]
    want = int(sys.argv[2]) if len(sys.argv) > 2 else None
    data = open(path, "rb").read()
    count = struct.unpack_from("<H", data, OFF["ring_count"])[0]
    head = struct.unpack_from("<H", data, OFF["ring_head"])[0]
    occupancy = min(count, RING_SIZE)
    start = (head - occupancy) % RING_SIZE
    print("ring_count=%d head=%d occupancy=%d first_run=%d" %
          (count, head, occupancy,
           struct.unpack_from("<Q", data, OFF["first_run"])[0]))
    for g in range(6):
        bits = struct.unpack_from("<I", data, OFF["gates"] + 4 * g)[0]
        print("gate[%d]=0x%08x" % (g, bits))
    for i in range(occupancy):
        slot = (start + i) % RING_SIZE
        off = RING + slot * ENTRY
        ts = struct.unpack_from("<Q", data, off)[0]
        stage = data[off + 8]
        op = data[off + 9]
        dt = struct.unpack_from("<H", data, off + 10)[0]
        aux = struct.unpack_from("<I", data, off + 12)[0]
        if want is None or op == want:
            print("ts=%d stage=%d op=%d dt=%d aux=0x%08x" %
                  (ts, stage, op, dt, aux))
    return 0


if __name__ == "__main__":
    sys.exit(main())
