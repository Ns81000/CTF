#!/usr/bin/env python3
"""Carrier plate generator (spec 4.3): the rendered route map.

The needle folio names a box number and a plate id; the plate itself is
the rendered artifact.  Its annotations - the instrument's model number
and the ROM bank - are PIXELS, never text: no PNG chunk, no metadata and
no string dump carries them.  Only the operator Notice is metadata.

usage: carrier_gen.py <platedir>
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "gen"))
sys.path.insert(0, HERE)
import mint  # noqa: E402
from plate_gen import encode_png, draw_text  # noqa: E402

W, H = 256, 128


def carrier_plate():
    stream = mint.sha256ctr(mint.seed("prambh:plates:carrier:v1"), W * H * 3)
    rgb = bytearray(W * H * 3)
    for y in range(H):
        for x in range(W):
            o = (y * W + x) * 3
            n = stream[o % len(stream)]
            rgb[o] = (34 + n % 22) & 0xff
            rgb[o + 1] = (40 + n % 26) & 0xff
            rgb[o + 2] = (30 + n % 18) & 0xff
    seg = 0
    for band in range(9):
        y = 10 + band * 12
        for x in range(6, W - 6, 3):
            o = ((y % H) * W + x) * 3
            tint = 40 + 12 * (seg % 4)
            rgb[o] = (tint + 30) & 0xff
            rgb[o + 1] = (tint + 40) & 0xff
            rgb[o + 2] = (tint + 20) & 0xff
            seg += 1
    # annotations are PIXELS, never stored text
    draw_text(rgb, W, H, 8, 8, "plate %d" % mint.needle_folios()[2], 1,
              (222, 218, 200))
    draw_text(rgb, W, H, 8, 34, mint.loom_model().lower(), 1, (230, 226, 210))
    draw_text(rgb, W, H, 8, 60, "bank %d" % (mint.needle_folios()[2] % 8), 1,
              (228, 224, 208))
    draw_text(rgb, W, H, 8, H - 20, "valley depot", 1, (215, 210, 195))
    return encode_png(W, H, bytes(rgb))



def main(argv):
    if len(argv) != 2:
        sys.stderr.write(__doc__)
        return 2
    outdir = argv[1]
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "carrier.png"), "wb") as f:
        f.write(carrier_plate())
    print("wrote %s/carrier.png" % outdir)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
