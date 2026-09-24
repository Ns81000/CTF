#!/usr/bin/env python3
"""gen_oracle_constants.py -- Stage 3 (Phase 4) constant generator. INTERNAL.

Builds, deterministically and with in-memory self-checks:
  - the two masked KDF seeds (real / poison) that oracle_blob.h carries
  - the two round functions' fold tables T[Z][j][256] with planted
    2^-2 collision sets (the deliberate round-function bias)
  - oracle_layout.json: machine-readable mirror for the python model,
    the attack solver and the test suite (INTERNAL, not shipped)

Everything is derived from fixed seed strings via SHA-256; the script is
idempotent and byte-reproducible. Nothing is written until every self-check
passes. Recorded design: logs/PHASE_4_LOG.md (D46-D52).
"""

import hashlib
import json
import pathlib
import struct

HERE = pathlib.Path(__file__).resolve().parent

# ---------------------------------------------------------------- seeds ---
# Derivation seeds (NEVER compiled into any binary; asserted absent).
KDF_SEED_REAL = b"cartographer-ghost:stage3:cipher-key:v1"
KDF_SEED_POISON = b"cartographer-ghost:stage3:poison-key:v1"
# Mask seeds (DO ship as strings, like the Phase-0 "cartographer-mask-v1"
# convention: a mask alone reveals nothing).
# Mask seeds removed in Phase FIX -- masks derived from fold tables
# Fold-table seed (generator + this log only).
FOLD_SEED = b"cartographer-ghost:stage3:fold-tables:v1"


def sha(b):
    return hashlib.sha256(b).digest()


def _drng_blocks(seed, label):
    ctr = 0
    while True:
        yield sha(seed + label + struct.pack("<I", ctr))
        ctr += 1


class Rng:
    """Deterministic byte DRNG (counter mode over SHA-256)."""

    def __init__(self, seed, label=b""):
        self._gen = _drng_blocks(seed, label)
        self._buf = b""

    def bytes(self, n):
        while len(self._buf) < n:
            self._buf += next(self._gen)
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def below(self, m):
        return int.from_bytes(self.bytes(4), "little") % m


def rotl32(x, n):
    x &= 0xFFFFFFFF
    return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF


# --------------------------------------------------------- mix constants ---
# M_Z: strong 32-bit Bijections (xorshift / odd-multiply / rotate steps).
# Mirrored EXACTLY in oracle.c and model_oracle.py; cross-checked by the
# suite's bit-exact vector comparison.
def mix_a(x):
    x ^= x >> 16
    x = (x * 0x85EBCA6B) & 0xFFFFFFFF
    x ^= x >> 13
    x = (x * 0xC2B2AE35) & 0xFFFFFFFF
    x ^= x >> 16
    return rotl32(x, 7)


def mix_b(x):
    x = rotl32(x, 17)
    x ^= x >> 15
    x = (x * 0x2545F491) & 0xFFFFFFFF
    x ^= x >> 14
    x = (x * 0x9E3779B1) & 0xFFFFFFFF
    x ^= x >> 16
    return x


MIXFN = {"A": mix_a, "B": mix_b}

# ------------------------------------------------------------- folding ----
# c_Z(y) = y ^ fold_Z(y);  fold_Z(y) = sum_j T[Z][j][W_j(y)] << 8j
# with W_j(y) = (y >> 8j) & 0xFF.  A difference confined to byte j
# cancels the fold iff T[Z][j][W] ^ T[Z][j][W^dw] == dw (dw = the byte
# difference), which happens for exactly 64 of 256 values of W -- the
# planted 2^-2 collision set.  For all other bytes the fold difference is
# nonzero, so M_Z (a bijection) hides the event at ~2^-32.
WINDOWS = 4


def planted_bit(z, j):
    # distinct planted bit per (round-function, window): A -> 0,9,18,27;
    # B -> 4,13,22,31 (block-bit positions after <<8j).
    return j if z == "A" else (j + 4) % 8


def planted_delta(z, j):
    return 1 << (8 * j + planted_bit(z, j))


def make_table(z, j):
    """Returns (table, dw, accept_sorted) with EXACTLY 64 accept values."""
    dw = 1 << planted_bit(z, j)
    rng = Rng(sha(FOLD_SEED), b"fold:%s:%d" % (z.encode(), j))
    t = list(range(256))
    for i in range(255, 0, -1):                    # seeded permutation base
        k = rng.below(i + 1)
        t[i], t[k] = t[k], t[i]
    order = list(range(256))                       # deterministic root order
    for i in range(255, 0, -1):
        k = rng.below(i + 1)
        order[i], order[k] = order[k], order[i]
    roots = [r for r in order if (r & dw) == 0][:32]
    accept = set()
    for r in roots:
        o = r ^ dw
        d0 = t[r] ^ t[o]
        zr = rng.below(256)
        t[r] ^= zr
        t[o] ^= zr ^ d0 ^ dw
        accept.add(r)
        accept.add(o)
    # Fix-ups: any ACCIDENTAL extra pair (both members outside the planted
    # set) is perturbed deterministically until the accept set is exact.
    # Perturbing one member of a non-planted pair cannot disturb planted
    # pairs (they never share both members).
    for _round in range(256):
        extra = sorted(w for w in range(256)
                       if w not in accept and (t[w] ^ t[w ^ dw]) == dw)
        if not extra:
            break
        w = extra[0]
        for k in range(1, 256):
            cand = (t[w] + k) & 0xFF
            if (cand ^ t[w ^ dw]) != dw:
                t[w] = cand
                break
        else:
            raise SystemExit("fix-up exhausted for %s%d" % (z, j))
    else:
        raise SystemExit("fix-up did not converge for %s%d" % (z, j))
    got = {w for w in range(256) if (t[w] ^ t[w ^ dw]) == dw}
    if got != accept:
        raise SystemExit("accept mismatch for %s%d: %d vs 64"
                         % (z, j, len(got)))
    return t, dw, sorted(accept)


# ------------------------------------------------------ the cipher (ref) ---
# Mirrored EXACTLY in oracle.c and model_oracle.py.
TABLES = {}          # TABLES[z][j] -> list of 256 ints
ACCEPTS = {}         # ACCEPTS[z][j] -> sorted list of 64 ints


def fold(z, y):
    f = 0
    for j in range(WINDOWS):
        f ^= TABLES[z][j][(y >> (8 * j)) & 0xFF] << (8 * j)
    return f & 0xFFFFFFFF


def g(z, y):
    return MIXFN[z]((y ^ fold(z, y)) & 0xFFFFFFFF)


def encrypt(kA, kB, p):
    l = (p >> 32) & 0xFFFFFFFF
    r = p & 0xFFFFFFFF
    for rnd in range(4):
        if rnd % 2 == 0:
            t = g("A", (r ^ kA) & 0xFFFFFFFF)
        else:
            t = g("B", (r ^ kB) & 0xFFFFFFFF)
        l, r = r, (l ^ t) & 0xFFFFFFFF
    return ((l << 32) | r) & 0xFFFFFFFFFFFFFFFF


def kdf(seed, reading):
    d = sha(seed + reading)
    return (int.from_bytes(d[0:4], "big"),
            int.from_bytes(d[4:8], "big"), d)


# ------------------------------------------------------------ self-checks ---
def xorshift_key(seed, label):
    r = Rng(seed, label)
    return (int.from_bytes(r.bytes(4), "big"),
            int.from_bytes(r.bytes(4), "big"))


def check_cipher_bias():
    """Empirical characteristic check on the reference implementation."""
    simseed = sha(FOLD_SEED + b"simcheck")
    rng = Rng(simseed, b"sim")
    kA, kB = xorshift_key(simseed, b"simkey")
    n = 30000
    for z, side in (("A", 0), ("B", 32)):
        for j in range(WINDOWS):
            d = planted_delta(z, j) << side
            hits = 0
            for _ in range(n):
                p = int.from_bytes(rng.bytes(8), "big") & 0xFFFFFFFFFFFFFFFF
                c0 = encrypt(kA, kB, p)
                c1 = encrypt(kA, kB, p ^ d)
                if (c0 ^ c1) == d:
                    hits += 1
            mean = n / 16.0
            sig = (mean * (1 - 1 / 16.0)) ** 0.5
            if abs(hits - mean) > 4 * sig:
                raise SystemExit("bias check failed: %s side %d win %d: "
                                 "%d hits, want %.0f +- %.0f"
                                 % (z, side, j, hits, mean, 4 * sig))
    # r1-predicate equivalence for one (z,j): hits iff W(R^k) in ACCEPT
    z, j = "A", 0
    acc = set(ACCEPTS[z][j])
    rng2 = Rng(simseed, b"pred")
    for _ in range(4000):
        r0 = int.from_bytes(rng2.bytes(4), "big")
        kA, kB = xorshift_key(sha(FOLD_SEED + b"pk"), b"pk")
        y0 = (r0 ^ kA) & 0xFFFFFFFF
        d = planted_delta(z, j)
        hit = g(z, y0) == g(z, y0 ^ d)
        want = ((y0 >> (8 * j)) & 0xFF) in acc
        if hit != want:
            raise SystemExit("predicate mismatch at r0=%08x kA=%08x" % (r0, kA))


def check_accidentals():
    """Other same-window differences must stay rare (tripwire, not exact)."""
    for z in ("A", "B"):
        for j in range(WINDOWS):
            t = TABLES[z][j]
            for b in range(8):
                dw = 1 << b
                cnt = sum(1 for w in range(256)
                          if (t[w] ^ t[w ^ dw]) == dw)
                if b == planted_bit(z, j):
                    if cnt != 64:
                        raise SystemExit("planted count %d != 64" % cnt)
                elif cnt >= 24:
                    raise SystemExit("accidental bias too large: "
                                     "%s%d bit %d -> %d" % (z, j, b, cnt))


def check_mix_bijection():
    for z in ("A", "B"):
        fn = MIXFN[z]
        seen = set()
        for x in range(0, 1 << 20):
            seen.add(fn(x))
        if len(seen) != (1 << 20):
            raise SystemExit("mix %s not injective on probe range" % z)


# ------------------------------------------------------------- emission ---
HDR = """/* oracle_blob.h -- GENERATED by gen_oracle_constants.py (Phase 4).
 * INTERNAL CONSTANTS for the Stage 3 cipher oracle.  Regenerate with:
 *   cd src/stage3_oracle && python3 gen_oracle_constants.py
 * Byte-reproducible; do not edit by hand.  Design record:
 * logs/PHASE_4_LOG.md (D46-D52).  The KDF derivation seeds are NOT here --
 * only their masked forms (XOR with a SHA-256-derived mask); the mask seed
 * strings appear by the Phase-0 D4 convention (a mask alone reveals
 * nothing).  The fold tables are the cipher's own public data.
 */
#ifndef CARTO_ORACLE_BLOB_H
#define CARTO_ORACLE_BLOB_H

#include <stdint.h>
"""

def hex_rows(name, data, per_row=16, ctype="static const uint8_t"):
    lines = ["%s %s[%d] = {" % (ctype, name, len(data))]
    for i in range(0, len(data), per_row):
        chunk = data[i:i + per_row]
        lines.append("    " + ", ".join("0x%02x" % b for b in chunk) + ",")
    lines.append("};")
    return "\n".join(lines)


def build_blob_bytes():
    seed_real = sha(KDF_SEED_REAL)
    seed_poison = sha(KDF_SEED_POISON)
    t_A = b"".join(bytes(TABLES["A"][j]) for j in range(WINDOWS))
    t_B = b"".join(bytes(TABLES["B"][j]) for j in range(WINDOWS))
    mask_real = sha(t_A + t_B)
    mask_poison = sha(t_B + t_A)
    masked_real = bytes(a ^ b for a, b in zip(seed_real, mask_real))
    masked_poison = bytes(a ^ b for a, b in zip(seed_poison, mask_poison))
    out = [HDR]
    out.append("\n/* KDF seeds, masked: unmasked by table folding (no plaintext labels). */\n")
    out.append(hex_rows("kMaskedSeedReal", masked_real) + "\n\n")
    out.append(hex_rows("kMaskedSeedPoison", masked_poison) + "\n\n")
    for z in ("A", "B"):
        out.append("/* Round function %s: fold tables, one 256-byte table per\n"
                   " * window byte j of the 32-bit F-input (bits 8j..8j+7). */\n" % z)
        for j in range(WINDOWS):
            out.append(hex_rows("kFold%c%d" % (z, j), TABLES[z][j]) + "\n\n")
    # NOTE: the ACCEPT sets are NOT shipped: the oracle never needs them at
    # runtime; they live in oracle_layout.json (internal) and are derivable
    # from the shipped tables by anyone who reverses the round function.
    out.append("#endif /* CARTO_ORACLE_BLOB_H */\n")
    return "".join(out)


def main():
    for z in ("A", "B"):
        TABLES[z] = {}
        ACCEPTS[z] = {}
        for j in range(WINDOWS):
            t, dw, acc = make_table(z, j)
            TABLES[z][j] = t
            ACCEPTS[z][j] = acc
    check_mix_bijection()
    check_accidentals()
    check_cipher_bias()

    seed_real = sha(KDF_SEED_REAL)
    seed_poison = sha(KDF_SEED_POISON)
    layout = {
        "version": 1,
        "windows": WINDOWS,
        "tables": {z: {str(j): TABLES[z][j] for j in range(WINDOWS)}
                   for z in ("A", "B")},
        "accepts": {z: {str(j): ACCEPTS[z][j] for j in range(WINDOWS)}
                    for z in ("A", "B")},
        "planted_bit": {z: [planted_bit(z, j) for j in range(WINDOWS)]
                        for z in ("A", "B")},
        "planted_delta": {z: [planted_delta(z, j) for j in range(WINDOWS)]
                          for z in ("A", "B")},
        "mix": {"A": "x^=x>>16;x=(x*0x85EBCA6B);x^=x>>13;x=(x*0xC2B2AE35);"
                     "x^=x>>16;rotl(x,7)",
                "B": "rotl(x,17);x^=x>>15;x=(x*0x2545F491);x^=x>>14;"
                     "x=(x*0x9E3779B1);x^=x>>16"},
        "kdf_seed_real": seed_real.hex(),
        "kdf_seed_poison": seed_poison.hex(),
        "cipher": "64-bit block, 4 rounds, alternating F_A/F_B, no final swap",
    }
    (HERE / "oracle_layout.json").write_text(json.dumps(layout, indent=1))
    (HERE / "oracle_blob.h").write_text(build_blob_bytes())

    # KDF worked examples for the log / suite (real reading is internal).
    demo = b"CARTO{no_figure_sits_in_every_pixel}"
    kA, kB, d = kdf(seed_real, demo)
    pA, pB, pd = kdf(seed_poison, d)
    print("tables built; self-checks passed")
    print("planted deltas A: %s" % [hex(x) for x in layout["planted_delta"]["A"]])
    print("planted deltas B: %s" % [hex(x) for x in layout["planted_delta"]["B"]])
    print("demo reading kdf: kA=%08x kB=%08x" % (kA, kB))
    print("demo poison keys: kA=%08x kB=%08x" % (pA, pB))
    print("oracle_blob.h + oracle_layout.json written")


if __name__ == "__main__":
    main()


