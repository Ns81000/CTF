#!/usr/bin/env python3
r"""s2_mkvec.py -- generate the differential vectors for test_inflate.

INTERNAL test tool (not shipped).  Uses python3 + zlib as the SECOND
implementation: the C s2_inflate must agree with it byte for byte on every
vector, and must refuse every stream marked '!'.

    python3 s2_mkvec.py <vector-file>

Line format:  <in_hex> <dict_hex|-> <out_hex|!>
"""

import hashlib
import random
import sys
import zlib


def make_dict() -> bytes:
    """Mirror of the press formula's shape, without importing the generator."""
    return b"interior-survey-mark-v1:" + hashlib.sha256(
        b"cartographer-ghost:stage2:ink-formula:v1").digest()


def compress(payload: bytes, level: int, zdict):
    if zdict:
        co = zlib.compressobj(level, zlib.DEFLATED, 15, 8,
                              zlib.Z_DEFAULT_STRATEGY, zdict)
    else:
        co = zlib.compressobj(level)
    return co.compress(payload) + co.flush()


def main() -> None:
    out_path = sys.argv[1]
    rnd = random.Random(7)
    zdict = make_dict()
    lines = []

    # streams that use the preset dictionary, every block strategy zlib picks
    for n in (1, 2, 3, 7, 15, 36, 100, 700, 2000, 9000):
        payload = bytes(rnd.randrange(256) for _ in range(n))
        for lvl in (0, 1, 6, 9):
            blob = compress(payload, lvl, zdict)
            lines.append("%s %s %s" % (blob.hex(), zdict.hex(), payload.hex()))
    for n in (1, 36, 9000):
        payload = bytes(rnd.randrange(256) for _ in range(n))
        blob = compress(payload, 9, None)
        lines.append("%s - %s" % (blob.hex(), payload.hex()))

    # text with long repeats: exercises matches and large distances
    for n in (50, 400, 5000, 40000):
        payload = (b"CARTO{no_figure_sits_in_every_pixel} " * (n // 37 + 1))[:n]
        for lvl in (1, 9):
            blob = compress(payload, lvl, zdict)
            lines.append("%s %s %s" % (blob.hex(), zdict.hex(), payload.hex()))

    # a stream big enough to force multiple deflate blocks
    big = bytes(rnd.randrange(256) for _ in range(120000))
    blob = compress(big, 9, zdict)
    lines.append("%s %s %s" % (blob.hex(), zdict.hex(), big.hex()))

    # ---- streams that must be refused ------------------------------------
    for n, lvl in ((36, 9), (700, 6)):
        payload = bytes(rnd.randrange(256) for _ in range(n))
        blob = compress(payload, lvl, zdict)
        lines.append("%s %s !" % (blob[:-3].hex(), zdict.hex()))   # truncated
        wrong = b"X" + zdict[1:]
        lines.append("%s %s !" % (blob.hex(), wrong.hex()))        # wrong dict
        lines.append("%s - !" % blob.hex())                        # no press mark
        lines.append("0000 !")
        lines.append("789c00 !")
        lines.append("789cffffffff00000000000000 !")

    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("vectors written: %d" % len(lines))


if __name__ == "__main__":
    main()