#!/usr/bin/env python3
"""PRAMBH plate renderer (P4 decoys; P8 eye plates reuse this encoder).

Pure-stdlib deterministic PNG writer: IHDR, tEXt(Notice), IDAT, IEND only.
Includes a 5x7 bitmap font so plates need no external image library.
"""
import os
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "gen"))
import mint

NOTICE = ("PRAMBH field tool. Every command ends rc 0. Nothing here confirms "
          "or denies. Trust timestamps, not moods.")

FONT = {
    "0": [0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E],
    "1": [0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E],
    "2": [0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F],
    "3": [0x0E, 0x11, 0x01, 0x06, 0x01, 0x11, 0x0E],
    "4": [0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02],
    "5": [0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E],
    "6": [0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E],
    "7": [0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08],
    "8": [0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E],
    "9": [0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C],
    "a": [0x00, 0x0E, 0x01, 0x0F, 0x11, 0x0F, 0x00],
    "b": [0x10, 0x10, 0x1E, 0x11, 0x11, 0x1E, 0x00],
    "c": [0x00, 0x0E, 0x10, 0x10, 0x10, 0x0E, 0x00],
    "d": [0x01, 0x01, 0x0F, 0x11, 0x11, 0x0F, 0x00],
    "e": [0x00, 0x0E, 0x11, 0x1F, 0x10, 0x0E, 0x00],
    "f": [0x06, 0x08, 0x1E, 0x08, 0x08, 0x08, 0x00],
    " ": [0x00] * 7,
    "-": [0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00],
}


def chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))


def encode_png(w, h, rgb):
    raw = b"".join(b"\x00" + bytes(rgb[y * w * 3:(y + 1) * w * 3])
                   for y in range(h))
    png = [b"\x89PNG\r\n\x1a\n"]
    png.append(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)))
    png.append(chunk(b"tEXt", b"Notice\x00" + NOTICE.encode()))
    png.append(chunk(b"IDAT", zlib.compress(raw, 9)))
    png.append(chunk(b"IEND", b""))
    return b"".join(png)


def draw_text(rgb, w, h, x0, y0, text, scale, color):
    for i, ch in enumerate(text):
        glyph = FONT.get(ch, FONT[" "])
        gx = x0 + i * 6 * scale
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits & (0x10 >> col):
                    for dy in range(scale):
                        for dx in range(scale):
                            x = gx + col * scale + dx
                            y = y0 + row * scale + dy
                            if 0 <= x < w and 0 <= y < h:
                                o = (y * w + x) * 3
                                rgb[o:o + 3] = bytes(color)


def decoy_plate(k):
    w, h = 256, 128
    code = mint.decoy_plate_codes()[k]
    stream = mint.sha256ctr(
        mint.seed("prambh:plates:decoy:bg:v1", struct.pack("<I", k)),
        w * h * 3)
    rgb = bytearray(w * h * 3)
    for y in range(h):
        band = (y // 8) % 3
        for x in range(w):
            o = (y * w + x) * 3
            n = stream[o % len(stream)]
            rgb[o] = (40 + 30 * band + n % 24) & 0xff
            rgb[o + 1] = (36 + 22 * ((band + 1) % 3) + n % 20) & 0xff
            rgb[o + 2] = (52 + 26 * ((band + 2) % 3) + n % 18) & 0xff
    draw_text(rgb, w, h, 8, 8, "survey plate %d" % k, 2, (220, 220, 210))
    draw_text(rgb, w, h, 8, 96, code, 2, (235, 225, 200))
    return encode_png(w, h, bytes(rgb))


def main():
    outdir = sys.argv[1]
    os.makedirs(outdir, exist_ok=True)
    for k in range(6):
        with open(os.path.join(outdir, "decoy_plate_%d.png" % k), "wb") as f:
            f.write(decoy_plate(k))


if __name__ == "__main__":
    main()
