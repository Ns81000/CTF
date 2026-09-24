#!/usr/bin/env python3
"""Surveyor's Eyes plate generator (spec 4.7) - organizer-side.

Three deterministic artifacts, each carrying one 6-glyph code:

  plates/depth.png    single-image random-dot stereogram.  Two depth
                      planes: the survey's code cut NEAREST, a decoy code
                      carried on a second, deeper plane.  The repeat
                      period is jittered per band so a naive
                      autocorrelation of the whole plate smears.
  plates/hue.png      Ishihara-style dots: the survey's code in a hue
                      difference at matched luminance; the luminance
                      channel carries a decoy code.
  plates/sheet_a.png  line screens.  sheet_a carries a fine period
  plates/sheet_b.png  modulation (the survey's code) plus a coarse one
                      (the decoy code); overlaying the pair at the marked
                      bearing resolves the fine bands, the reciprocal
                      bearing resolves the coarse ones.

Every plate also carries the operator Notice in a PNG tEXt chunk.

usage: plate_gen.py <pkgdir>
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "gen"))
import mint  # noqa: E402

W, H = 480, 240
DOT = 3
JITTER_BANDS = 12
BASE_PERIOD = 24
NEAR_SHIFT = 9        # the survey's plane: the nearer (bigger) parallax
DEEP_SHIFT = 4        # the depot's plane: deeper, smaller parallax
MARKED_BEARING = 11.0  # degrees, printed in the viewing notes
NOTICE = ("PRAMBH is a survey, not a service. Its instruments record but "
          "never confirm: no output here will tell you whether anything "
          "worked.")


def _rng(name):
    return np.random.default_rng(int.from_bytes(
        mint.seed("prambh:eyes:plate:%s:v1" % name)[:8], "little"))


def _glyph_mask(text):
    """Render 6 glyphs into a boolean mask (the code's silhouette)."""
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSansMono-Bold.ttf", 120)
    except OSError:
        font = ImageFont.load_default()
    d.text((W // 6, H // 2), text, fill=255, font=font, anchor="mm")
    return np.array(img) > 100


def depth_plate(code, decoy):
    """Random-dot stereogram: nearest plane = code, deeper plane = decoy."""
    rng = _rng("depth")
    near = _glyph_mask(code)
    deep = _glyph_mask(decoy) & ~near
    out = rng.integers(0, 255, size=(H, W, 3), dtype=np.uint8)
    for y in range(H):
        band = (y * JITTER_BANDS) // H
        period = BASE_PERIOD + (band % 3) - 1
        for x in range(W):
            if near[y, x]:
                shift = NEAR_SHIFT
            elif deep[y, x]:
                shift = DEEP_SHIFT
            else:
                shift = 0
            src = x - period + shift
            if src >= 0:
                out[y, x] = out[y, src]
    return Image.fromarray(out)


def hue_plate(code, decoy):
    """Hue difference at matched luminance + a luminance-channel decoy."""
    rng = _rng("hue")
    real = _glyph_mask(code)
    fake = _glyph_mask(decoy) & ~real
    img = np.zeros((H, W, 3), dtype=np.float64)
    step = DOT * 2 + 3
    lum_vals = np.array([140.0, 145.0, 150.0, 155.0, 160.0])
    lum = rng.choice(lum_vals, size=(H, W))
    hue = rng.integers(0, 2, size=(H, W))
    for y in range(0, H, step):
        for x in range(0, W, step):
            jx = int(rng.integers(-1, 2))
            jy = int(rng.integers(-1, 2))
            cx = min(W - 1, max(0, x + jx))
            cy = min(H - 1, max(0, y + jy))
            inside = real[cy, cx]
            lum[cy, cx] = 168.0 if fake[cy, cx] else 145.0
            hue[cy, cx] = 1 if inside else 0
    # full background texture across the whole plate (not just the dots)
    lum_full = rng.choice(lum_vals, size=(H, W))
    hue_full = rng.integers(0, 2, size=(H, W))
    for y in range(0, H, 1):
        lum_full[y] = np.roll(lum_full[y], int(rng.integers(0, W)))
    lum = np.where(real | fake, lum, lum_full)
    hue = np.where(real, hue, hue_full)
    red = np.where(hue == 1, lum, lum * 0.72)
    green = np.where(hue == 1, lum * 0.45, lum * 0.98)
    blue = lum * 0.35
    img = np.dstack([red, green, blue])
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def moire_sheets(code, decoy):
    """Two line screens: fine modulation = code, coarse = decoy."""
    fine = _glyph_mask(code)
    coarse = _glyph_mask(decoy) & ~fine
    ys, xs = np.mgrid[0:H, 0:W]
    period = 8.0 + 5.0 * fine + 2.0 * coarse
    phase = (xs % period) < (period * 0.5)
    a = np.where(phase, 240, 40).astype(np.uint8)
    sheet_a = Image.fromarray(np.dstack([a, a, a]))
    period_b = 8.0 + 5.0 * fine + 2.0 * coarse
    xr = (xs * np.cos(np.deg2rad(1.0)) + ys * np.sin(np.deg2rad(1.0)))
    phase_b = (xr % period_b) < (period_b * 0.5)
    b = np.where(phase_b, 240, 40).astype(np.uint8)
    sheet_b = Image.fromarray(np.dstack([b, b, b]))
    return sheet_a, sheet_b


def save(img, path):
    from PIL.PngImagePlugin import PngInfo
    meta = PngInfo()
    meta.add_text("Notice", NOTICE)
    img.save(path, pnginfo=meta)


def main(argv):
    if len(argv) != 2:
        sys.stderr.write(__doc__)
        return 2
    pk = argv[1]
    pl = os.path.join(pk, "plates")
    os.makedirs(pl, exist_ok=True)
    codes = [mint.eyes_code(i) for i in range(3)]
    decoys = [mint.decoy_eyes_code(k) for k in ("depth", "hue", "moire")]
    save(depth_plate(codes[0], decoys[0]), os.path.join(pl, "depth.png"))
    save(hue_plate(codes[1], decoys[1]), os.path.join(pl, "hue.png"))
    a, b = moire_sheets(codes[2], decoys[2])
    save(a, os.path.join(pl, "sheet_a.png"))
    save(b, os.path.join(pl, "sheet_b.png"))
    print("plates written: depth.png hue.png sheet_a.png sheet_b.png")
    print("survey codes: %s" % ", ".join(codes))
    print("depot copies: %s" % ", ".join(decoys))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
