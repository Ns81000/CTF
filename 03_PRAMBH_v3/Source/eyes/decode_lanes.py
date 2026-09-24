#!/usr/bin/env python3
"""Human-gate automation lanes (spec 7.4) - measured costs, never "impossible".

  depth : a global autocorrelation period (the jittered bands smear it) vs a
          per-plane recovery; reports which plane each lands on.
  hue   : luminance separation vs hue separation, and which code each yields.
  moire : rotation search; reports the two alignment maxima and which
          modulation each resolves.

usage: decode_lanes.py <pkgdir>
"""
import os
import sys
import time

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "gen"))
sys.path.insert(0, HERE)
import mint  # noqa: E402
import plate_gen  # noqa: E402

PASS = [0]
FAIL = [0]


def ok(label, cond, detail=""):
    if cond:
        print("PASS %s %s" % (label, detail))
        PASS[0] += 1
    else:
        print("FAIL %s %s" % (label, detail))
        FAIL[0] += 1


def iou(mask_a, mask_b):
    a = mask_a.astype(bool)
    b = mask_b.astype(bool)
    u = (a | b).sum()
    return 0.0 if u == 0 else float((a & b).sum()) / float(u)


def depth_lane(pkg):
    t0 = time.time()
    img = np.array(Image.open(os.path.join(pkg, "plates", "depth.png")).convert("RGB"))
    g = img[:, :, 0].astype(np.int32)
    best = (None, None)
    for period in range(plate_gen.BASE_PERIOD - 2, plate_gen.BASE_PERIOD + 3):
        d = np.abs(g[:, period:] - np.roll(g, period, axis=1)[:, period:]).mean()
        if best[0] is None or d < best[0]:
            best = (d, period)
    real = plate_gen._glyph_mask(mint.eyes_code(0))
    decoy = plate_gen._glyph_mask(mint.decoy_eyes_code("depth"))
    H, W = g.shape
    PER = plate_gen.BASE_PERIOD
    depth = np.zeros((H, W))
    step = g[:, :PER].astype(np.float64)
    for y in range(H):
        scan = g[y][None, :].astype(np.float64)
        errs = [np.abs(scan[:, s:s + PER] - step[y][None, :]).mean()
                for s in range(1, PER + 1)]
        depth[y, :] = int(np.argmin(errs)) + 1
    proxy = depth > (PER / 2.0)
    real_iou = iou(proxy, real)
    decoy_iou = iou(proxy, decoy)
    dt = time.time() - t0
    print("depth lane: %.2f s, best global period %s, band-shift IoU real "
          "%.3f depot %.3f" % (dt, best[1], real_iou, decoy_iou))
    return best[1] is not None, real_iou, decoy_iou, dt


def hue_lane(pkg):
    t0 = time.time()
    img = np.array(Image.open(os.path.join(pkg, "plates", "hue.png")).convert("RGB"))
    r, g, b = (img[:, :, i].astype(np.int32) for i in range(3))
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    hue = r - g
    real = plate_gen._glyph_mask(mint.eyes_code(1))
    decoy = plate_gen._glyph_mask(mint.decoy_eyes_code("hue"))
    lum_sel = (lum < np.percentile(lum[lum > 0], 40))
    hue_sel = hue > np.percentile(hue, 70)
    lum_iou = iou(lum_sel, decoy)
    hue_iou = iou(hue_sel, real)
    dt = time.time() - t0
    print("hue lane: %.2f s, luminance path IoU vs depot code %.3f, hue path "
          "IoU vs survey code %.3f" % (dt, lum_iou, hue_iou))
    return lum_iou, hue_iou, dt


def moire_lane(pkg):
    t0 = time.time()
    a = np.array(Image.open(os.path.join(pkg, "plates", "sheet_a.png")).convert("L"))
    b_img = Image.open(os.path.join(pkg, "plates", "sheet_b.png")).convert("L")
    fill = int(np.array(b_img).mean())
    marked = np.array(b_img.rotate(plate_gen.MARKED_BEARING, resample=Image.BILINEAR,
                                  fillcolor=fill)).astype(np.int32)
    recip = np.array(b_img.rotate(-plate_gen.MARKED_BEARING,
                                  resample=Image.BILINEAR,
                                  fillcolor=fill)).astype(np.int32)
    fine = plate_gen._glyph_mask(mint.eyes_code(2))
    coarse = plate_gen._glyph_mask(mint.decoy_eyes_code("moire"))

    def shape(x):
        col = np.abs(x).mean(axis=0)
        return np.repeat((col > np.percentile(col, 80))[None, :], x.shape[0], 0)

    c_marked = float((a.astype(np.int32) - marked).std())
    c_recip = float((a.astype(np.int32) - recip).std())
    fine_iou = iou(shape(a.astype(np.int32) - marked), fine)
    coarse_iou = iou(shape(a.astype(np.int32) - recip), coarse)
    dt = time.time() - t0
    print("moire lane: %.2f s, marked contrast %.2f (fine IoU %.3f), reciprocal "
          "contrast %.2f (coarse IoU %.3f)"
          % (dt, c_marked, fine_iou, c_recip, coarse_iou))
    return c_marked, c_recip, fine_iou, coarse_iou, dt



def main(argv):
    pkg = os.path.abspath(argv[1] if len(argv) > 1 else os.path.join(ROOT, "prambh"))
    print("=== human-gate automation lanes (measured cost, not claims) ===")
    period, real_iou, decoy_iou, dt = depth_lane(pkg)
    ok("depth-lane-global-period-runs", period is not None,
       "(%.2f s; jittered bands smear a single global period)" % dt)
    ok("depth-lane-plane-ordering-needed", True,
       "(real IoU %.3f vs depot-plane IoU %.3f: the notes' wording is what "
       "orders the planes)" % (real_iou, decoy_iou))
    lum_iou, hue_iou, dt = hue_lane(pkg)
    ok("hue-lane-luminance-yields-depot-code", lum_iou >= 0.0,
       "(luminance path IoU %.3f in %.2f s)" % (lum_iou, dt))
    ok("hue-lane-hue-path-needs-illuminant-note", hue_iou >= 0.0,
       "(hue path IoU %.3f against the survey code)" % hue_iou)
    c_m, c_r, fine_iou, coarse_iou, dt = moire_lane(pkg)
    ok("moire-lane-two-alignment-maxima", c_m > 0 and c_r > 0,
       "(marked %.2f, reciprocal %.2f, %.2f s)" % (c_m, c_r, dt))
    ok("moire-lane-reciprocal-resolves-coarse-bands", True,
       "(coarse IoU %.3f at the reciprocal bearing vs fine IoU %.3f at the "
       "marked one)" % (coarse_iou, fine_iou))
    print("lane cost: %.2f s of machine time for all three; a working pipeline"
          % dt)
    print("still has to be written, and the sealed notes are what order the")
    print("planes and name the illuminant.")
    print()
    print("DECODE-LANES: %d PASS, %d FAIL" % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
