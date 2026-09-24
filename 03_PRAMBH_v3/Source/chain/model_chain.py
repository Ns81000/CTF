#!/usr/bin/env python3
"""Independent Python model of PRAMBH-CHAIN (spec 4.1), EXACT construction.

Bit-exact reference used to cross-check the C implementation and the
loom emulator at small parameters.  Also implements the reduced-table
(checkpoint) attack used to measure memory-hardness, plus mutation
modes for sensitivity tests.

usage:
  model_chain.py walk <seed-hex> <S-bytes> <T-steps>
  model_chain.py attack <seed-hex> <S-bytes> <T-steps> <checkpoints>
  model_chain.py mutate <seed-hex> <S> <T> <kind>   # sensitivity probes
      kinds: fill-swap | walk-no-t | walk-t-offby1 | bad-fill-label |
             bad-run-label | bad-S | bad-T
"""
import hashlib
import struct
import sys
import time

FILL_LABEL = b"prambh:chain:fill:v1"
RUN_LABEL = b"prambh:chain:run:v1"


def fill(seed, nbytes, steps, label=FILL_LABEL, s_override=None,
         t_override=None, swap=None):
    n = nbytes // 32
    S = s_override if s_override is not None else nbytes
    T = t_override if t_override is not None else steps
    table = bytearray(nbytes)
    prev = hashlib.sha256(label + seed + struct.pack("<Q", S)
                          + struct.pack("<Q", T)).digest()
    table[0:32] = prev
    for i in range(1, n):
        j = i
        if swap is not None and i == swap:
            j = i + 1
        elif swap is not None and i == swap + 1:
            j = i - 1
        prev_j = bytes(table[(j - 1) * 32:j * 32]) if j != i else prev
        prev = hashlib.sha256(prev_j + struct.pack("<Q", j)).digest()
        table[i * 32:(i + 1) * 32] = prev
    return table


def walk(seed, table, steps, with_t=True, t_offby1=False,
         run_label=RUN_LABEL):
    n = len(table) // 32
    s = hashlib.sha256(run_label + seed
                       + bytes(table[(n - 1) * 32:n * 32])).digest()
    for t in range(1, steps + 1):
        idx = struct.unpack("<Q", s[:8])[0] % n
        msg = s + bytes(table[idx * 32:(idx + 1) * 32])
        if with_t:
            msg += struct.pack("<Q", t - 1 if t_offby1 else t)
        s = hashlib.sha256(msg).digest()
    return s


def attack(seed, nbytes, steps, checkpoints):
    """Reduced-table attack: keep `checkpoints` evenly spaced blocks,
    recompute from the nearest earlier checkpoint on every miss."""
    n = nbytes // 32
    gap = max(1, n // checkpoints)
    kept = {}
    recomputes = 0
    table = fill(seed, nbytes, steps)
    for i in range(0, n, gap):
        kept[i] = bytes(table[i * 32:(i + 1) * 32])
    del table

    def block(i):
        nonlocal recomputes
        base = (i // gap) * gap
        prev = kept[base]
        for j in range(base + 1, i + 1):
            prev = hashlib.sha256(prev + struct.pack("<Q", j)).digest()
            recomputes += 1
        return prev

    s = hashlib.sha256(RUN_LABEL + seed + kept[(n - 1) // gap * gap]).digest()
    # note: attack must reproduce s0 exactly; n-1 may not be a checkpoint
    s = hashlib.sha256(RUN_LABEL + seed + block(n - 1)).digest()
    t0 = time.monotonic()
    for t in range(1, steps + 1):
        idx = struct.unpack("<Q", s[:8])[0] % n
        s = hashlib.sha256(s + block(idx) + struct.pack("<Q", t)).digest()
    dt = time.monotonic() - t0
    return s, recomputes, dt


if __name__ == "__main__":
    mode = sys.argv[1]
    seed = bytes.fromhex(sys.argv[2])
    nbytes = int(sys.argv[3])
    steps = int(sys.argv[4])
    if mode == "walk":
        print(walk(seed, fill(seed, nbytes, steps), steps).hex())
    elif mode == "attack":
        out, rec, dt = attack(seed, nbytes, steps, int(sys.argv[5]))
        print(out.hex())
        print("recomputes %d walk_seconds %.3f" % (rec, dt), file=sys.stderr)
    elif mode == "walktable":
        tbl = bytearray(open(sys.argv[5], "rb").read())
        print(walk(seed, tbl, steps).hex())
    elif mode == "mutate":
        kind = sys.argv[5]
        if kind == "fill-swap":
            print(walk(seed, fill(seed, nbytes, steps, swap=10), steps).hex())
        elif kind == "walk-no-t":
            print(walk(seed, fill(seed, nbytes, steps), steps,
                       with_t=False).hex())
        elif kind == "walk-t-offby1":
            print(walk(seed, fill(seed, nbytes, steps), steps,
                       t_offby1=True).hex())
        elif kind == "bad-fill-label":
            print(walk(seed, fill(seed, nbytes, steps,
                                  label=b"prambh:chain:fill:v2"),
                       steps).hex())
        elif kind == "bad-run-label":
            print(walk(seed, fill(seed, nbytes, steps), steps,
                       run_label=b"prambh:chain:run:v2").hex())
        elif kind == "bad-S":
            print(walk(seed, fill(seed, nbytes, steps,
                                  s_override=nbytes + 32), steps).hex())
        elif kind == "bad-T":
            print(walk(seed, fill(seed, nbytes, steps,
                                  t_override=steps + 1), steps).hex())
