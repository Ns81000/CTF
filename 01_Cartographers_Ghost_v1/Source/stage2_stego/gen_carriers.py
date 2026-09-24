#!/usr/bin/env python3
r"""gen_carriers.py -- Phase 3 build-time generator for the Stage 2 stego
carriers and the expected-payload digest header.

INTERNAL build-time tool. NOT shipped to solvers. Full design record:
logs/PHASE_3_LOG.md.

Writes (all deterministic -- re-running produces byte-identical files):
    ../../cartographer/stage2_stego/survey_frame.png   the interior sheet
    ../../cartographer/stage2_stego/survey_tape.wav    the survey tape
    stage2_blob.h                                      expected payload digest

Sheet layers (spec Phase 3):
  * decoy -- naive whole-image LSB read: the opening DECOY_MARKS marks carry
             the decoy flag in all three channel LSBs (R,G,B per mark,
             MSB-first bit packing, low bit plane only).  Any naive LSB sweep
             surfaces it at the head of the stream.
  * real  -- BLUE CHANNEL ONLY, bit 0, one mark in every STRIDE marks, from
             mark START to the far edge: LE16(len) || zlib(PAYLOAD, zdict=DICT).
             (The decoy layer is confined to the opening so the two layers
             cannot share a bit plane -- see PHASE_3_LOG D33.)
Tape:
  * the zlib preset dictionary (the "press formula") lives as raw bytes in the
    INFO/ICMT metadata block -- not in the samples, and never in any binary.
  * the samples carry an irrelevant LSB pattern (a cheap micro-distraction).

Stride/start derive from the Stage 1 REAL key material (PHASE_2_LOG D23/D27):
    R6 = LE64(K[0:8]),  R7 = LE64(K[8:16])
    STRIDE = 3 + (R6 % 61)
    START  = 512 + (R7 % 9000)
"""

import hashlib
import math
import pathlib
import re
import struct
import zlib

HERE = pathlib.Path(__file__).resolve().parent
PKG = (HERE / ".." / ".." / "cartographer" / "stage2_stego").resolve()
POLICY = (HERE / ".." / "state" / "policy.h").resolve()

# ---------------------------------------------------------------- constants
REAL_KEY = bytes.fromhex(
    "fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f")
PAYLOAD = b"CARTO{no_figure_sits_in_every_pixel}"
DECOY_FLAG = b"CARTO{twice_over_the_coast_before_the_interior}"
DICT_NAME = b"interior-survey-mark-v1:"
FORMULA_SEED = b"cartographer-ghost:stage2:ink-formula:v1"
DICT = DICT_NAME + hashlib.sha256(FORMULA_SEED).digest()

# The ".rodata spent press" advertisement: a plausible-looking why-this-stage-
# fails artifact.  The record is kept live in the binary by a never-taken
# branch, exactly as Phase 2 kept its forgotten-debug constant.  It holds no
# derivation of its own (see logs/PHASE_3_LOG.md D38).
SPENT_PRESS_SEED = b"cartographer-ghost:stage2:decoy:spent-press:v1"
SPENT_PRESS_NOTE = ("stage2_key_checkpoint (pre-interior) -- the press this "
                    "sheet was struck from; do not re-cut")

W, H = 512, 512
DECOY_MARKS = 512          # opening marks reserved for the naive LSB layer
START_BASE = 512           # the real sweep begins at or past the opening
START_MOD = 9000
STRIDE_ADD = 3
STRIDE_MOD = 61

SAMPLE_RATE = 8000
SAMPLE_COUNT = 4000        # 0.5 s of 16-bit mono PCM
SAMPLE_MSG = b"the tape hums; the figure is not in the sound"
TAPE_TITLE = "interior survey tape 2"

COMMENT = ("the old man drew the coast twice over before the fog took him, and "
           "the interior only once, by lamplight. the blue of the ink is where "
           "the figure sits; the engine sets the sweep. if the "
           "press refuses, it wants the tape's whole mark.")
FIELD_NOTE = (
    "interior sheet no. 2 -- field note. the surveyor's graticule marks the "
    "interior sheet; blue ink holds the surveyor's impression. the engine sets "
    "the sweep across the sheet, eight marks to a letter. the press keeps the "
    "whole mark left on the tape.")
def bits_msb(data: bytes):
    """Bit stream: most significant bit of each byte first."""
    for byte in data:
        for i in range(7, -1, -1):
            yield (byte >> i) & 1


def pack_msb(bits):
    """Inverse of bits_msb for a whole number of bytes."""
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        v = 0
        for b in bits[i:i + 8]:
            v = (v << 1) | b
        out.append(v)
    return bytes(out)


def derive(key: bytes):
    r6 = int.from_bytes(key[0:8], "little")
    r7 = int.from_bytes(key[8:16], "little")
    stride = STRIDE_ADD + (r6 % STRIDE_MOD)
    start = START_BASE + (r7 % START_MOD)
    return r6, r7, stride, start


def base_sheet():
    """A plausible graticule sheet: paper grain, rule lines, faint contours."""
    img = bytearray(W * H * 3)
    for y in range(H):
        for x in range(W):
            g = 232 - ((x * 7 + y * 11) % 13)
            if x % 32 == 0 or y % 32 == 0:
                g -= 38
            if (x * x + y * y) % 4096 < 300:
                g -= 22
            if (x * 5 + y) % 8192 < 240:
                g -= 12
            v = max(0, min(255, g))
            o = (y * W + x) * 3
            img[o] = v
            img[o + 1] = v
            img[o + 2] = min(255, v + 6)
    return img


def chrome(typ: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + typ + data
            + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))


def text_chunk(keyword: str, text: str) -> bytes:
    return chrome(b"tEXt", keyword.encode("latin-1") + b"\x00"
                  + text.encode("latin-1"))


def write_png(img: bytearray, path: pathlib.Path) -> None:
    raw = bytearray()
    for y in range(H):
        raw.append(0)                       # filter type 0 (None)
        raw += img[y * W * 3:(y + 1) * W * 3]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    out = (b"\x89PNG\r\n\x1a\n" + chrome(b"IHDR", ihdr)
           + text_chunk("Comment", COMMENT)
           + text_chunk("FieldNote", FIELD_NOTE)
           + chrome(b"IDAT", zlib.compress(bytes(raw), 9))
           + chrome(b"IEND", b""))
    path.write_bytes(out)


def riff_chunk(cid: bytes, payload: bytes) -> bytes:
    """A RIFF chunk with its word-alignment pad byte (strictly valid sizes)."""
    body = cid + struct.pack("<I", len(payload)) + payload
    if len(payload) % 2:
        body += b"\x00"
    return body


def write_wav(path: pathlib.Path) -> None:
    fmt = struct.pack("<HHIIHH", 1, 1, SAMPLE_RATE, SAMPLE_RATE * 2, 2, 16)
    msg = SAMPLE_MSG + b"\x00" * (SAMPLE_COUNT // 8 - len(SAMPLE_MSG))
    bits = list(bits_msb(msg))
    samples = []
    for i in range(SAMPLE_COUNT):
        v = int(3000.0 * math.sin(i / 37.0)) + 500
        v = (v & ~1) | bits[i]              # low bit carries the decoy pattern
        samples.append(v)
    data = b"".join(struct.pack("<h", s) for s in samples)
    info = riff_chunk(b"INAM", TAPE_TITLE.encode("ascii") + b"\x00")
    info += riff_chunk(b"ICMT", DICT)
    body = (b"WAVE" + riff_chunk(b"fmt ", fmt) + riff_chunk(b"data", data)
            + riff_chunk(b"LIST", b"INFO" + info))
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)


def _rows(data, indent="    "):
    out = []
    for i in range(0, len(data), 8):
        out.append(indent + ", ".join("0x%02x" % b for b in data[i:i + 8]) + ",")
    return "\n".join(out)


def write_blob_header(sheet_sha: bytes, tape_sha: bytes,
                      path: pathlib.Path) -> None:
    """GENERATED constants the shipped binary may hold.

    None of these is a means of derivation: the expected reading is held only
    as a SHA-256 digest (the reading itself is never in any binary), the
    carrier fingerprints are derivable from the shipped carriers by anyone,
    and the spent-press record is a decoy advertisement.
    """
    digest = hashlib.sha256(PAYLOAD).digest()
    spent = hashlib.sha256(SPENT_PRESS_SEED).digest()
    out = [
        "/* stage2_blob.h -- GENERATED by gen_carriers.py; do not edit by hand.",
        " * Constants recorded in logs/PHASE_3_LOG.md (internal).",
        " */",
        "#ifndef CARTO_STAGE2_BLOB_H",
        "#define CARTO_STAGE2_BLOB_H",
        "",
        "/* expected reading: %d bytes, held ONLY as a digest: %s */"
        % (len(PAYLOAD), digest.hex()),
        "#define CARTO_S2_EXPECTED_LEN %du" % len(PAYLOAD),
        "static const unsigned char kStage2ExpectedDigest[32] = {",
        _rows(digest),
        "};",
        "",
        "/* carrier fingerprints (SHA-256 of the shipped files) */",
        "static const unsigned char kStage2SheetSha256[32] = {",
        _rows(sheet_sha),
        "};",
        "static const unsigned char kStage2TapeSha256[32] = {",
        _rows(tape_sha),
        "};",
        "",
        "/* decoy advertisement kept live by a never-taken branch:",
        " * %s */" % spent.hex(),
        "static const unsigned char kStage2SpentPress[32] = {",
        _rows(spent),
        "};",
        "static const char kStage2SpentPressNote[] =",
        '    "%s";' % SPENT_PRESS_NOTE,
        "",
        "#endif /* CARTO_STAGE2_BLOB_H */",
    ]
    path.write_text("\n".join(out) + "\n", newline="\n")


def main() -> None:
    for name, value in (("payload", PAYLOAD), ("decoy flag", DECOY_FLAG)):
        if not re.fullmatch(r"CARTO\{[a-z0-9_]{8,64}\}", value.decode()):
            raise SystemExit("%s violates the canonical flag format (D11)" % name)
    registered = '{ 2, "%s"' % DECOY_FLAG.decode()
    if registered not in POLICY.read_text():
        raise SystemExit("stage-2 decoy not registered in src/state/policy.h")

    r6, r7, stride, start = derive(REAL_KEY)
    img = base_sheet()

    # ---- decoy layer: naive whole-image LSB read of the opening marks -------
    cap = DECOY_MARKS * 3 // 8
    stream = (DECOY_FLAG + b"\x00" * cap)[:cap]
    for i, bit in enumerate(bits_msb(stream)):
        off = (i // 3) * 3 + (i % 3)
        img[off] = (img[off] & 0xFE) | bit

    # ---- real layer: blue-channel LSB, one mark per stride -----------------
    co = zlib.compressobj(9, zlib.DEFLATED, 15, 8, zlib.Z_DEFAULT_STRATEGY, DICT)
    zblob = co.compress(PAYLOAD) + co.flush()
    framed = struct.pack("<H", len(zblob)) + zblob
    rbits = list(bits_msb(framed))
    last = start + (len(rbits) - 1) * stride
    if last >= W * H:
        raise SystemExit("real layer does not fit on the sheet")

    # ---- embed the real layer, then self-check both layers in-memory -----
    for k, bit in enumerate(rbits):
        off = (start + k * stride) * 3 + 2
        img[off] = (img[off] & 0xFE) | bit

    chk = [img[(i // 3) * 3 + (i % 3)] & 1 for i in range(cap * 8)]
    if pack_msb(chk) != stream:
        raise SystemExit("decoy layer self-check failed")
    rback = [img[(start + k * stride) * 3 + 2] & 1 for k in range(len(rbits))]
    got = pack_msb(rback)
    n = struct.unpack("<H", got[:2])[0]
    dec = zlib.decompressobj(15, DICT)
    if dec.decompress(got[2:2 + n]) + dec.flush() != PAYLOAD:
        raise SystemExit("real layer self-check failed")

    PKG.mkdir(parents=True, exist_ok=True)
    write_png(img, PKG / "survey_frame.png")
    write_wav(PKG / "survey_tape.wav")

    sheet = PKG / "survey_frame.png"
    tape = PKG / "survey_tape.wav"
    sheet_sha = hashlib.sha256(sheet.read_bytes()).digest()
    tape_sha = hashlib.sha256(tape.read_bytes()).digest()
    digest = hashlib.sha256(PAYLOAD).digest()
    write_blob_header(sheet_sha, tape_sha, HERE / "stage2_blob.h")

    token = "CARTO{%s}" % digest.hex()[:32]
    print("stage2 carriers written")
    print("  sheet            = %s (%d bytes, sha256 %s)"
          % (sheet, sheet.stat().st_size, sheet_sha.hex()))
    print("  tape             = %s (%d bytes, sha256 %s)"
          % (tape, tape.stat().st_size, tape_sha.hex()))
    print("  payload          = %s (%d bytes)" % (PAYLOAD.decode(), len(PAYLOAD)))
    print("  payload sha256   = %s" % digest.hex())
    print("  checkpoint token = %s" % token)
    print("  decoy flag       = %s" % DECOY_FLAG.decode())
    print("  stage1 key words : R6=0x%016x R7=0x%016x" % (r6, r7))
    print("  stride           = %d  (3 + (R6 %% 61))" % stride)
    print("  start mark       = %d  (512 + (R7 %% 9000))" % start)
    print("  real capacity    = %d bits (%d marks used)"
          % ((W * H - start) // stride, len(rbits)))
    print("  zlib blob        = %d bytes; framed (LE16 len) = %d bytes"
          % (len(zblob), len(framed)))
    print("  dict (press)     = %d bytes: %s" % (len(DICT), DICT.hex()))
    print("  tape icmt offset = %d"
          % (tape.read_bytes().find(b"ICMT") + 8))


if __name__ == "__main__":
    main()