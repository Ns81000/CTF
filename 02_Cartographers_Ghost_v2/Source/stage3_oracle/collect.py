#!/usr/bin/env python3
"""collect.py -- drive the plate and write down what it answered.

  collect.py <out-file> [--pairs N] [--oracle PATH] [--reading R] [--ink I]

The figures are laid out in families: within a family the two figures differ
by exactly one bit in one byte of one half, and every other byte is shared,
so the difference between the two answers is about that byte alone.
"""
import os
import random
import subprocess
import sys

READING = "CARTO{rust_blooms_under_tin_roofs}"
INK = "145e1d23feac3932"
BITS_R = (0, 1, 2, 3)
BITS_L = (5, 6, 7, 4)


def families(pairs, seed=7):
    rng = random.Random(seed)
    out = []
    for half in ("L", "R"):
        for j in range(4):
            bit = 1 << (BITS_R[j] if half == "R" else BITS_L[j])
            bases = [rng.randrange(0, 0x100) for _ in range(pairs)]
            for v in bases:
                other = rng.randrange(0, 0x100000000)
                if half == "R":
                    lh = other.to_bytes(4, "little")
                    rh = bytearray(4)
                    for bi in range(4):
                        rh[bi] = rng.randrange(0, 0x100) if bi != j else v
                    fa = lh + bytes(rh)
                    rh[j] = v ^ bit
                    fb = lh + bytes(rh)
                else:
                    rh = other.to_bytes(4, "little")
                    lh = bytearray(4)
                    for bi in range(4):
                        lh[bi] = rng.randrange(0, 0x100) if bi != j else v
                    fa = bytes(lh) + rh
                    lh[j] = v ^ bit
                    fb = bytes(lh) + rh
                out.append(fa.hex())
                out.append(fb.hex())
    return out


def figures(pairs, seed=7, jitter=1):
    """The crafted families, plus ordinary figures so the sitting looks like
    a sitting: volume is what the volume gate asks for."""
    figs = families(pairs, seed)
    rng = random.Random(seed + 1)
    for _ in range(jitter * 64):
        figs.append(rng.randrange(0, 1 << 64).to_bytes(8, "little").hex())
    rng.shuffle(figs)
    # Ensure no two adjacent figures share the same 16-bit prefix (avoid duplicate query trap and stale key)
    for i in range(1, len(figs)):
        if figs[i][:4] == figs[i - 1][:4]:
            for k in range(i + 1, len(figs)):
                if figs[k][:4] != figs[i - 1][:4]:
                    figs[i], figs[k] = figs[k], figs[i]
                    break
    return figs


def main():
    out = sys.argv[1]
    pairs = 64
    oracle = "./stage3_oracle/oracle"
    reading, ink = READING, INK
    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a == "--pairs":
            pairs = int(args[i + 1])
        elif a == "--oracle":
            oracle = args[i + 1]
        elif a == "--reading":
            reading = args[i + 1]
        elif a == "--ink":
            ink = args[i + 1]
    figs = figures(pairs)
    rows = []
    for fig in figs:
        cmd = "%s -r '%s' -i %s %s" % (oracle, reading, ink, fig)
        res = subprocess.run(
            ["script", "-qec", cmd, "/dev/null"],
            capture_output=True, text=True, stdin=subprocess.DEVNULL)
        for line in res.stdout.replace('\r', '').splitlines():
            if "the plate reads:" in line:
                rows.append((fig, line.split(":")[1].strip()))
                break
        else:
            rows.append((fig, "??"))
    with open(out, "w", newline="\n") as fh:
        for fig, ans in rows:
            fh.write("%s %s\n" % (fig, ans))
    print("collected %d answers (%d figures) into %s"
          % (len(rows), len(figs), out))
    print("answers where the plate said nothing: %d"
          % sum(1 for f, a in rows if a == "??"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
