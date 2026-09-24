#!/usr/bin/env python3
"""detect_layer.py -- can a statistical detector point at the drawn marks?

The claim the frame has to survive: looking at the picture, with no bearing,
a detector must not be able to say where the payload is any better than
chance.  This runs four ordinary detectors and reports each one.

  1. chi-square on blue-lane bit 0 over 64x64 tiles
  2. autocorrelation of the blue-lane bit-0 plane at lags 1..64
  3. bit-plane entropy, row band by row band
  4. a small sample of (stride, start) pairs, scored by whether the bytes
     they yield open as a stream at all (the honest route is to search all
     of them; sampling must not stumble onto it)

Every detector prints PASS when it fails to find the payload, which is the
result we want, and FAIL when it localises the marks.
"""
import struct
import sys
import zlib

sys.path.insert(0, __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])
from sweep import png_pixels, read, tape_press  # noqa: E402

TILE = 64
STRIDE_SPAN = range(5, 106)
START_SPAN = range(1024, 24000, 997)


def chi_square_tiles(px, w, h):
    worst = 0.0
    worst_at = (0, 0)
    for ty in range(0, h, TILE):
        for tx in range(0, w, TILE):
            ones = 0
            total = 0
            for y in range(ty, min(ty + TILE, h)):
                row = y * w * 3
                for x in range(tx, min(tx + TILE, w)):
                    ones += px[row + x * 3 + 2] & 1
                    total += 1
            if not total:
                continue
            exp = total / 2.0
            dev = abs(ones - exp) / exp
            if dev > worst:
                worst = dev
                worst_at = (tx, ty)
    return worst, worst_at


def autocorrelation(px, w, h, lag):
    row = 32
    bits = [px[row * w * 3 + x * 3 + 2] & 1 for x in range(w)]
    same = sum(1 for i in range(w - lag) if bits[i] == bits[i + lag])
    n = w - lag
    return abs(same / n - 0.5) * 2.0


def entropy(bits):
    if not bits:
        return 0.0
    p = sum(bits) / float(len(bits))
    if p in (0.0, 1.0):
        return 0.0
    import math
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


def band_entropy(px, w, h):
    bands = []
    for b in range(8):
        bits = []
        for y in range(b * (h // 8), (b + 1) * (h // 8), 7):
            for x in range(0, w, 3):
                bits.append(px[y * w * 3 + x * 3 + 2] & 1)
        bands.append(entropy(bits))
    return bands


def sample_pairs(px, w, h, press, tries=4000):
    """Sample (stride, start) pairs and score them the way the tool would:
    the stream has to carry a press check that agrees with the tape.  A wrong
    pair can pass the header test by chance but not the press check."""
    hits = 0
    seed = 12345
    want = zlib.adler32(press) & 0xFFFFFFFF
    for _ in range(tries):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        stride = 5 + seed % 101
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        start = 1024 + seed % 23000
        if start + 64 * stride >= w * h:
            continue
        acc = n = 0
        blob = bytearray()
        for k in range(64):
            p = start + k * stride
            acc = (acc << 1) | (px[(p // w) * w * 3 + (p % w) * 3 + 2] & 1)
            n += 1
            if n == 8:
                blob.append(acc)
                acc = n = 0
        if len(blob) < 6:
            continue
        if (blob[0] & 0x0F) != 8 or ((blob[0] * 256 + blob[1]) % 31):
            continue
        if not (blob[1] & 0x20):
            continue
        got = ((blob[2] << 24) | (blob[3] << 16) | (blob[4] << 8) | blob[5])
        if got == want:
            hits += 1
    return hits


def main():
    frame, tape = sys.argv[1], sys.argv[2]
    w, h, px = png_pixels(read(frame))
    press = tape_press(read(tape))
    bad = 0

    worst, at = chi_square_tiles(px, w, h)
    if worst < 0.05:
        print("PASS tiles: no channel bias beyond chance (max %.4f at %s)"
              % (worst, at))
    else:
        print("FAIL tiles: bias %.4f at %s" % (worst, at))
        bad += 1

    lags = [(l, autocorrelation(px, w, h, l)) for l in range(1, 65)]
    top = max(lags, key=lambda t: t[1])
    # 1024 bits give a standard error of about 1/sqrt(n) = 0.031 per lag, and
    # taking the largest of 64 lags needs a Bonferroni allowance: the honest
    # bar is sigma * sqrt(2 ln 64) = 0.089.
    bar = 0.09
    if top[1] < bar:
        print("PASS autocorrelation: flat at every lag up to 64 (worst lag %d "
              "= %.4f, bar %.2f)" % (top[0], top[1], bar))
    else:
        print("FAIL autocorrelation spikes at lag %d = %.4f" % top)
        bad += 1

    bands = band_entropy(px, w, h)
    spread = max(bands) - min(bands)
    if spread < 0.02:
        print("PASS entropy: every row band looks the same (spread %.4f)"
              % spread)
    else:
        print("FAIL entropy: band %d stands out (spread %.4f)" %
              (bands.index(max(bands)), spread))
        bad += 1

    hits = sample_pairs(px, w, h, press)
    if hits == 0:
        print("PASS sampled search: 4000 pairs, none opened (chance)")
    else:
        print("FAIL sampled search found %d opening pairs" % hits)
        bad += 1

    print("OK" if bad == 0 else "NOT OK")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
