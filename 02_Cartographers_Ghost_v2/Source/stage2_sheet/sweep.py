#!/usr/bin/env python3
"""sweep.py -- the independent extraction model for stage 2.

Reads the two carriers the way a solver would and prints what is in them.
It shares no code with the sheet tool: the frame is decoded here from the
PNG specification, and the layers are read out from the mark arithmetic.

  sweep.py <frame.png> <tape.wav> [--bearing N] [--naive] [--dump DIR]
"""
import struct
import sys
import zlib

W = H = 1024


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def png_pixels(data):
    off = 8
    idat = b""
    w = h = 0
    while off + 12 <= len(data):
        ln = struct.unpack_from(">I", data, off)[0]
        typ = data[off + 4:off + 8]
        body = data[off + 8:off + 8 + ln]
        if typ == b"IHDR":
            w, h, depth, ctype = struct.unpack_from(">IIBB", body, 0)
            assert depth == 8 and ctype == 2, "unexpected frame format"
        elif typ == b"IDAT":
            idat += body
        off += 12 + ln
    raw = zlib.decompress(idat)
    stride = w * 3
    out = bytearray(h * stride)
    prev = bytearray(stride)
    for y in range(h):
        f = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for x in range(stride):
            a = line[x - 3] if x >= 3 else 0
            b = prev[x]
            c = prev[x - 3] if x >= 3 else 0
            if f == 1:
                line[x] = (line[x] + a) & 0xFF
            elif f == 2:
                line[x] = (line[x] + b) & 0xFF
            elif f == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 0xFF
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 0xFF
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return w, h, out


def tape_press(data):
    assert data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    off = 12
    while off + 8 <= len(data):
        cid = data[off:off + 4]
        ln = struct.unpack_from("<I", data, off + 4)[0]
        if cid == b"prES":
            return data[off + 8:off + 8 + ln]
        off += 8 + ln + (ln & 1)
    raise SystemExit("no press on the tape")


def lane_bit(px, w, pos, lane=2):
    stride = w * 3
    x = pos % w
    y = pos // w
    return px[y * stride + x * 3 + lane] & 1


def lane_at(px, w, pos, lane):
    stride = w * 3
    x = pos % w
    y = pos // w
    return px[y * stride + x * 3 + lane]


def take_bytes(px, w, positions, count):
    out = bytearray()
    acc = 0
    n = 0
    for pos in positions[:count * 8]:
        acc = (acc << 1) | lane_bit(px, w, pos)
        n += 1
        if n == 8:
            out.append(acc)
            acc = n = 0
    return bytes(out)


def read_lane(px, w, stride, start, press, cap=8192):
    pos = [start + k * stride for k in range(cap)]
    blob = take_bytes(px, w, pos, cap // 8)
    ln = struct.unpack_from("<H", blob, 0)[0]
    if ln == 0 or ln > len(blob) - 2:
        return None, blob
    try:
        co = zlib.decompressobj(15, zdict=press)
        text = co.decompress(blob[2:2 + ln]) + co.flush()
    except zlib.error:
        return None, blob
    return text, blob


def naive(px, w):
    bits = []
    for k in range(1024):
        i = k * 3 + (k % 3)
        bits.append(px[i] & 1)
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        b = 0
        for k in range(8):
            b = (b << 1) | bits[i + k]
        out.append(b)
    return out


def main():
    frame, tape = sys.argv[1], sys.argv[2]
    rest = sys.argv[3:]
    bearing = None
    for i, a in enumerate(rest):
        if a == "--bearing":
            bearing = int(rest[i + 1], 0)
    px = None
    if "--naive" in rest:
        w, h, px = png_pixels(read(frame))
        print("naive lane:", bytes(naive(px, w)).split(b"\x00")[0].decode(
            "latin-1"))
        return 0
    w, h, px = png_pixels(read(frame))
    press = tape_press(read(tape))
    stride = 5 + ((bearing & 0xFFFFFFFF) % 101)
    start = 1024 + ((bearing >> 32) % 24000)
    print("stride=%d start=%d press=%d bytes" % (stride, start, len(press)))
    text, blob = read_lane(px, w, stride, start, press)
    print("drawn lane:", text if text else "(nothing readable)")
    text2, blob2 = read_lane(px, w, stride, start + 1, press)
    print("lane at the next mark:", text2 if text2 else "(nothing readable)")
    if "--dump" in rest:
        d = rest[rest.index("--dump") + 1]
        with open(d + "/press.bin", "wb") as fh:
            fh.write(press)
        with open(d + "/ink.zlib", "wb") as fh:
            fh.write(blob[2:2 + struct.unpack_from("<H", blob, 0)[0]])
        print("dumped press.bin and ink.zlib to", d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
