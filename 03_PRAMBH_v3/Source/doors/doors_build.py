#!/usr/bin/env python3
"""Build doors.bin and riddle.bin (spec 4.5) - organizer-side.

doors.bin: eight fixed-size records [seed(32) || ciphertext(2048)], no
magic, no checksum, no header - raw XOR streams whose size and shape are
identical, so nothing tells the doors apart.

  K_i        = SHA-256("prambh:door:v1" || seed_i || LE64(i) || phrase_i)
  door_i     = chamber_i XOR SHA256ctr(K_i)

riddle.bin: the survey verse XOR SHA256ctr(K_loom), where K_loom is
chain #1's output (the loom claim).  Without the chain the verse is
unavailable; with it the solver reads the verse and speaks its answer.

usage: doors_build.py <pkgdir> [--claim-hex HEX]
"""
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "gen"))
sys.path.insert(0, HERE)
import mint  # noqa: E402
import chambers_gen  # noqa: E402
import verse_gen  # noqa: E402

CHAMBER_MAX = chambers_gen.CHAMBER_MAX
RIDDLE_MAX = 2048
RUNS = os.path.join(ROOT, "organizer-private", "runs")


def sha256ctr(key, nbytes):
    out = bytearray()
    ctr = 0
    while len(out) < nbytes:
        out += hashlib.sha256(key + struct.pack("<Q", ctr)).digest()
        ctr += 1
    return bytes(out[:nbytes])


def xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def door_key(seed, i, phrase):
    return hashlib.sha256(b"prambh:door:v1" + seed + struct.pack("<Q", i)
                          + phrase.encode()).digest()


def claim_from_runs(explicit):
    if explicit:
        return explicit.strip()
    for name in ("chain1_walk.txt", "p5_chain1_raw.txt"):
        path = os.path.join(RUNS, name)
        if not os.path.exists(path):
            continue
        for line in open(path):
            if line.startswith("out="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("doors_build: no chain #1 output found - run "
                     "src/gen/chain_jobs.py loom1 (or pass --claim-hex)")


def build(pkgdir, claim_hex):
    claim = bytes.fromhex(claim_hex)
    if len(claim) != 32:
        raise SystemExit("doors_build: claim must be 32 bytes")
    texts = chambers_gen.chambers()
    blob = bytearray()
    for i, text in enumerate(texts):
        seed = mint.door_seed(i)
        plain = text.encode() + bytes(CHAMBER_MAX - len(text))
        assert len(plain) == CHAMBER_MAX and b"\x00" not in text.encode()
        blob += seed + xor(plain, sha256ctr(door_key(seed, i, mint.door_phrase(i)),
                                            CHAMBER_MAX))
    outdir = os.path.join(pkgdir, "stage3_doors")
    os.makedirs(outdir, exist_ok=True)
    doors_path = os.path.join(outdir, "doors.bin")
    with open(doors_path, "wb") as f:
        f.write(blob)

    verse = verse_gen.verse_text().encode()
    riddle_plain = verse + bytes(RIDDLE_MAX - len(verse))
    riddle_path = os.path.join(outdir, "riddle.bin")
    with open(riddle_path, "wb") as f:
        f.write(xor(riddle_plain, sha256ctr(claim, RIDDLE_MAX)))

    rep = ["P6 - HALL OF DOORS BUILD (spec 4.5)",
           "chambers: %d, record size %d (seed %d + cipher %d)"
           % (len(texts), 32 + CHAMBER_MAX, 32, CHAMBER_MAX),
           "doors.bin: %d bytes  sha256=%s"
           % (len(blob), hashlib.sha256(bytes(blob)).hexdigest()),
           "riddle.bin: %d bytes  sha256=%s"
           % (RIDDLE_MAX, hashlib.sha256(open(riddle_path, "rb").read()).hexdigest()),
           "chain #1 claim (K_loom) = %s" % claim_hex,
           "loom ink = %s   loom checkpoint = PRAMBH{%s}"
           % (claim[:8].hex(), claim[8:16].hex()),
           "door ink (real chamber) = %s" % mint.door_ink(),
           "real door index = %d, hall %d"
           % (mint.real_door_index(), mint.real_door_number()),
           "candidate phrases:",
           ]
    for k in range(8):
        rep.append("  %d %-52s %s%s" % (k, verse_gen.LABELS[k], mint.door_phrase(k),
                                        "  <== REAL" if k == mint.real_door_index() else ""))
    repname = "p6_doors_build.txt"
    if os.path.basename(pkgdir.rstrip("/")) not in ("prambh",):
        repname = "p6_doors_build_%s.txt" % os.path.basename(pkgdir.rstrip("/"))
    with open(os.path.join(RUNS, repname), "w") as f:
        f.write("\n".join(rep) + "\n")
    print("\n".join(rep))
    return 0


def main(argv):
    if len(argv) < 2:
        sys.stderr.write(__doc__)
        return 2
    pkgdir = argv[1]
    explicit = None
    if "--claim-hex" in argv:
        explicit = argv[argv.index("--claim-hex") + 1]
    return build(pkgdir, claim_from_runs(explicit))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
