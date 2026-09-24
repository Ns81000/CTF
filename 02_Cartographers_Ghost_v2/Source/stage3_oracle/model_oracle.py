#!/usr/bin/env python3
"""model_oracle.py -- an independent model of the plate, and the attack.

  model_oracle.py answer <figure-hex> [--key-hex K]
  model_oracle.py attack <dataset-file>

The model is written from the round description alone and shares nothing with
the C tool.  The attack is the one the planted tables were built for: for each
key byte the planted entries say exactly when a difference of one bit in the
figure has to come back as a difference of one bit, so a wrong byte is caught
by the pairs where it predicts a completion that never happens.
"""
import json
import os
import sys
from itertools import product

HERE = os.path.dirname(os.path.abspath(__file__))


def gfun(y, t):
    f = (t[0][y & 0xFF] ^ t[1][(y >> 8) & 0xFF] ^ t[2][(y >> 16) & 0xFF] ^
         t[3][(y >> 24) & 0xFF])
    w = (y ^ (f * 0x01010101)) & 0xFFFFFFFF
    return (t[0][w & 0xFF] | (t[1][(w >> 8) & 0xFF] << 8) |
            (t[2][(w >> 16) & 0xFF] << 16) | (t[3][(w >> 24) & 0xFF] << 24))


def fold_of(y, t):
    return (t[0][y & 0xFF] ^ t[1][(y >> 8) & 0xFF] ^ t[2][(y >> 16) & 0xFF] ^
            t[3][(y >> 24) & 0xFF]) & 0xFF


def cipher(l, r, kA, kB, ta, tb):
    for round_no in range(5):
        if round_no & 1:
            t = (l ^ gfun((r ^ kB) & 0xFFFFFFFF, tb)) & 0xFFFFFFFF
        else:
            t = (l ^ gfun((r ^ kA) & 0xFFFFFFFF, ta)) & 0xFFFFFFFF
        l, r = r, t
    return l, r


def answer(figure_hex, kA, kB, tab):
    fig = bytes.fromhex(figure_hex)
    l0 = int.from_bytes(fig[0:4], "little")
    r0 = int.from_bytes(fig[4:8], "little")
    cipher(l0, r0, kA, kB, tab["A"], tab["B"])
    return fold_of(r0 ^ kA, tab["A"]) ^ fold_of(l0 ^ kB, tab["B"])


def planted(t, bit):
    """The values W whose partner differs by exactly one bit's worth."""
    return set(w for w in range(256) if (t[w] ^ t[w ^ bit]) == bit)


def collect_pairs(rows, which, j, bit):
    """Pair up answers whose figures differ only by `bit` in byte j of one
    half; the other half stays put, so its term cancels in the difference."""
    by_fig = {}
    for fig_hex, ans in rows:
        by_fig[fig_hex] = ans
    out = []
    seen = set()
    for fig_hex, ans in rows:
        fig = bytes.fromhex(fig_hex)
        if which == "R":
            half = int.from_bytes(fig[4:8], "little")
            partner = half ^ (bit << (8 * j))
            pfig = (fig[0:4] + partner.to_bytes(4, "little")).hex()
        else:
            half = int.from_bytes(fig[0:4], "little")
            partner = half ^ (bit << (8 * j))
            pfig = (partner.to_bytes(4, "little") + fig[4:8]).hex()
        if pfig in by_fig:
            pair_key = tuple(sorted([fig_hex, pfig]))
            if pair_key not in seen:
                seen.add(pair_key)
                out.append(((half >> (8 * j)) & 0xFF, ans ^ by_fig[pfig]))
    return out


def recover_byte_candidates(pairs, table, bit):
    """Candidates that satisfy the differential transition for all pairs."""
    candidates = []
    for cand in range(256):
        if all(delta == (table[vin ^ cand] ^ table[(vin ^ cand) ^ bit])
               for vin, delta in pairs):
            candidates.append(cand)
    return candidates


def run_attack(rows, tab):
    ta, tb = tab["A"], tab["B"]
    kA_cands, kB_cands = [], []
    for j in range(4):
        bit = 1 << tab["bits"]["A"][j]
        pairs = collect_pairs(rows, "R", j, bit)
        if len(pairs) < 16:
            return None, None, ["too few pairs for kA byte %d" % j]
        cands = recover_byte_candidates(pairs, ta[j], bit)
        if not cands:
            return None, None, ["kA byte %d leaves completions unexplained" % j]
        kA_cands.append(cands)

        bit = 1 << tab["bits"]["B"][j]
        pairs = collect_pairs(rows, "L", j, bit)
        if len(pairs) < 16:
            return None, None, ["too few pairs for kB byte %d" % j]
        cands = recover_byte_candidates(pairs, tb[j], bit)
        if not cands:
            return None, None, ["kB byte %d leaves completions unexplained" % j]
        kB_cands.append(cands)

    sample = rows[:min(20, len(rows))]
    valid_keys = []
    for ka_combo in product(*kA_cands):
        kA_t = int.from_bytes(bytes(ka_combo), "little")
        for kb_combo in product(*kB_cands):
            kB_t = int.from_bytes(bytes(kb_combo), "little")
            if all(answer(f, kA_t, kB_t, tab) == a for f, a in sample):
                valid_keys.append((kA_t, kB_t))

    if len(valid_keys) == 1:
        return valid_keys[0][0], valid_keys[0][1], []
    if len(valid_keys) > 1:
        for f, a in rows[20:]:
            valid_keys = [(ka, kb) for ka, kb in valid_keys if answer(f, ka, kb, tab) == a]
            if len(valid_keys) <= 1:
                break
        if len(valid_keys) == 1:
            return valid_keys[0][0], valid_keys[0][1], []
        return None, None, ["multiple key candidates survived verification"]

    return None, None, ["no candidate survived full cipher verification"]


def load_tables():
    with open(os.path.join(HERE, "stage3_tables.json")) as fh:
        raw = json.load(fh)
    return raw, {"A": [raw["tables"][j] for j in range(4)],
                 "B": [raw["tables"][4 + j] for j in range(4)],
                 "bits": raw["bits"]}


def read_rows(path):
    rows = []
    with open(path) as fh:
        for line in fh:
            parts = line.split()
            if len(parts) >= 2 and len(parts[0]) == 16:
                rows.append((parts[0].lower(), int(parts[1], 16)))
    return rows


def main():
    raw, tab = load_tables()
    if len(sys.argv) > 2 and sys.argv[1] == "answer":
        key = raw["k_real"]
        if "--key-hex" in sys.argv:
            key = sys.argv[sys.argv.index("--key-hex") + 1]
        k = bytes.fromhex(key)
        kA = int.from_bytes(k[0:4], "little")
        kB = int.from_bytes(k[4:8], "little")
        print("%02x" % answer(sys.argv[2], kA, kB, tab))
        return 0
    if len(sys.argv) > 2 and sys.argv[1] == "attack":
        rows = read_rows(sys.argv[2])
        kA, kB, notes = run_attack(rows, tab)
        if kA is None:
            print("NO-CONSENSUS: %s (from %d answers)"
                  % ("; ".join(notes), len(rows)))
            return 3
        ink = (kA.to_bytes(4, "little") + kB.to_bytes(4, "little")).hex()
        print("kA=%08x kB=%08x ink=%s" % (kA, kB, ink))
        print("MATCH" if ink == raw["k_real"][:16] else "MISMATCH")
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "static":
        # the derivation a static reader reaches: the cold key, never the ink
        print("cold %s" % raw["k_cold"][:16])
        print("real %s" % raw["k_real"][:16])
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
