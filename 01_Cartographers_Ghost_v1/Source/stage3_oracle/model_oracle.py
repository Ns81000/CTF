#!/usr/bin/env python3
"""model_oracle.py -- independent python implementation of the Stage 3
cipher oracle. INTERNAL (not shipped).

Mirrors oracle.c bit-exactly (cross-checked by the suite on live oracle
output) and carries the differential attack used to prove that the planted
round-function bias is exploitable at the recorded sample size (D47/D52).

    python3 model_oracle.py --selftest
    python3 model_oracle.py --keys '<reading>'
    python3 model_oracle.py --enc '<reading>' <16-hex-figure>
    python3 model_oracle.py --stats
    python3 model_oracle.py --attack-json <pairs.json> [--expect <kAhex:kBhex>]

The attack consumes pair records {"p": int, "c0": int, "c1": int, "d": int}
(d = p0 ^ p1, the block difference) and recovers the two 32-bit subkeys by
per-byte intersection over the characteristic hits.
"""

import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
LAYOUT = json.loads((HERE / "oracle_layout.json").read_text())

M32 = 0xFFFFFFFF
M64 = 0xFFFFFFFFFFFFFFFF
WINDOWS = LAYOUT["windows"]
T = {z: [LAYOUT["tables"][z][str(j)] for j in range(WINDOWS)] for z in "AB"}
ACCEPT = {z: [set(LAYOUT["accepts"][z][str(j)]) for j in range(WINDOWS)]
          for z in "AB"}
DELTA = {z: [LAYOUT["planted_delta"][z][j] for j in range(WINDOWS)]
         for z in "AB"}
SEED_REAL = bytes.fromhex(LAYOUT["kdf_seed_real"])
SEED_POISON = bytes.fromhex(LAYOUT["kdf_seed_poison"])


def rotl(x, n):
    x &= M32
    return ((x << n) | (x >> (32 - n))) & M32


def mix_a(x):
    x ^= x >> 16
    x = (x * 0x85EBCA6B) & M32
    x ^= x >> 13
    x = (x * 0xC2B2AE35) & M32
    x ^= x >> 16
    return rotl(x, 7)


def mix_b(x):
    x = rotl(x, 17)
    x ^= x >> 15
    x = (x * 0x2545F491) & M32
    x ^= x >> 14
    x = (x * 0x9E3779B1) & M32
    x ^= x >> 16
    return x


MIXFN = {"A": mix_a, "B": mix_b}


def fold(z, y):
    f = 0
    for j in range(WINDOWS):
        f ^= T[z][j][(y >> (8 * j)) & 0xFF] << (8 * j)
    return f & M32


def g(z, y):
    return MIXFN[z]((y ^ fold(z, y)) & M32)


def encrypt(kA, kB, p):
    l, r = (p >> 32) & M32, p & M32
    for rnd in range(4):
        if rnd % 2 == 0:
            t = g("A", (r ^ kA) & M32)
        else:
            t = g("B", (r ^ kB) & M32)
        l, r = r, (l ^ t) & M32
    return ((l << 32) | r) & M64


def kdf_real(reading: bytes):
    d = hashlib.sha256(SEED_REAL + reading).digest()
    return (int.from_bytes(d[0:4], "big"),
            int.from_bytes(d[4:8], "big"), d)


def kdf_poison(real_digest: bytes):
    d = hashlib.sha256(SEED_POISON + real_digest).digest()
    return (int.from_bytes(d[0:4], "big"),
            int.from_bytes(d[4:8], "big"), d)


# ------------------------------------------------------------ the attack ---
def _byte(y, j):
    return (y >> (8 * j)) & 0xFF


TOLERANCE = 3          # hits allowed to contradict the winning byte
MIN_SCORE = 4          # a byte must be backed by at least this many hits


def _recover_byte(hit_sets, dw):
    """Score-based per-byte recovery with the pairing-symmetry caveat.

    A zero-differential plant is inherently symmetric: if W is accepted
    then so is W ^ dw, so every honest hit set contains BOTH the true
    byte and its dw-twin.  Returns (cands, state): cands is the single
    winning byte, or its 2-member twin pair; state in
    {"ok", "pair", "insufficient", "ambiguous"}."""
    score = {}
    for s in hit_sets:
        for c in s:
            score[c] = score.get(c, 0) + 1
    if not score:
        return None, "insufficient"
    best = max(score.values())
    winners = [c for c, v in score.items() if v == best]
    if best < MIN_SCORE:
        return None, "insufficient"
    if best < len(hit_sets) - TOLERANCE:
        return None, "insufficient"
    if len(winners) == 1:
        return winners, "ok"
    if (len(winners) == 2 and (winners[0] ^ winners[1]) == dw):
        return winners, "pair"
    return winners, "ambiguous"


def _finish(pairs, kA_cands, kB_cands):
    """Resolve the pairing-symmetric twin ambiguity offline: try every
    twin combination against the collected pairs (no queries spent)."""
    survivors = []
    for a0 in (kA_cands[0] or [0]):
        for a1 in (kA_cands[1] or [0]):
            for a2 in (kA_cands[2] or [0]):
                for a3 in (kA_cands[3] or [0]):
                    kA = a0 | (a1 << 8) | (a2 << 16) | (a3 << 24)
                    for b0 in (kB_cands[0] or [0]):
                        for b1 in (kB_cands[1] or [0]):
                            for b2 in (kB_cands[2] or [0]):
                                for b3 in (kB_cands[3] or [0]):
                                    kB = (b0 | (b1 << 8) | (b2 << 16)
                                          | (b3 << 24))
                                    ok = True
                                    for rec in pairs:
                                        if encrypt(kA, kB,
                                                   rec["p"]) != rec["c0"]:
                                            ok = False
                                            break
                                    if ok:
                                        survivors.append((kA, kB))
    return survivors


def attack(pairs):
    """Differential attack (D52).  Returns (kA, kB, report) on success or
    (None, None, report) when the data fails to converge (the deterministic
    falsification signal for mixed datasets)."""
    report = {"hits_a": {}, "hits_b": {}, "cands": {}, "state": [],
              "finish": 0, "empty": [], "ambiguous": []}
    a_cands = [None] * 4
    b_cands = [None] * 4

    # Phase A: round-1 hits pin kA byte j up to its dw-twin.
    for j in range(WINDOWS):
        dw = 1 << LAYOUT["planted_bit"]["A"][j]
        sets = []
        for rec in pairs:
            d = rec["d"]
            if d != DELTA["A"][j]:
                continue
            if (rec["c0"] ^ rec["c1"]) != d:
                continue
            r0 = rec["p"] & M32
            sets.append({_byte(r0, j) ^ w for w in ACCEPT["A"][j]})
        report["hits_a"][j] = len(sets)
        c, st = _recover_byte(sets, dw)
        report["cands"]["A%d" % j] = c
        if st in ("ok", "pair"):
            a_cands[j] = c
        else:
            report["state"].append("A%d:%s" % (j, st))
            if st == "ambiguous":
                report["ambiguous"].append("A%d" % j)
            else:
                report["empty"].append("A%d" % j)

    if all(c is not None for c in a_cands):
        # Phase B: round-2 hits pin kB byte j; the hit input
        # x = R1 = L0 ^ g_A(R0 ^ kA) needs kA, which phase A narrowed to
        # at most 16 twins -- try each (all must agree for the attack to
        # proceed; disagreement means mixed/contaminated data).
        kA_tries = [a0 | (a1 << 8) | (a2 << 16) | (a3 << 24)
                    for a0 in a_cands[0] for a1 in a_cands[1]
                    for a2 in a_cands[2] for a3 in a_cands[3]]
        agree = None
        for kA_try in kA_tries:
            b_all = [None] * 4
            ok = True
            for j in range(WINDOWS):
                dw = 1 << LAYOUT["planted_bit"]["B"][j]
                sets = []
                for rec in pairs:
                    d = rec["d"]
                    if d != (DELTA["B"][j] << 32):
                        continue
                    if (rec["c0"] ^ rec["c1"]) != d:
                        continue
                    p0 = rec["p"]
                    r0 = p0 & M32
                    x = ((p0 >> 32) ^ g("A", (r0 ^ kA_try) & M32)) & M32
                    sets.append({_byte(x, j) ^ w for w in ACCEPT["B"][j]})
                report["hits_b"][j] = len(sets)
                c, st = _recover_byte(sets, dw)
                report["cands"]["B%d" % j] = c
                if st not in ("ok", "pair"):
                    ok = False
                    report["state"].append("B%d:%s@kA=%08x" % (j, st, kA_try))
                    break
                b_all[j] = c
            if not ok:
                continue
            for combo in [b for b0 in b_all[0] for b1 in b_all[1]
                          for b2 in b_all[2] for b3 in b_all[3]
                          for b in [(b0 | (b1 << 8) | (b2 << 16)
                                    | (b3 << 24))]]:
                kB_try = combo
                if all(encrypt(kA_try, kB_try, rec["p"]) == rec["c0"]
                       for rec in pairs):
                    agree = (kA_try, kB_try)
                    break
            if agree:
                break
        if agree:
            report["finish"] = len(_finish(pairs, a_cands, b_cands))
            return agree[0], agree[1], report
        return None, None, report
    return None, None, report


# ------------------------------------------------------------ self checks --
def selftest():
    ok = True
    for z in "AB":
        for j in range(WINDOWS):
            dw = 1 << LAYOUT["planted_bit"][z][j]
            acc = {w for w in range(256)
                   if (T[z][j][w] ^ T[z][j][w ^ dw]) == dw}
            if acc != ACCEPT[z][j]:
                print("FAIL: accept set mismatch %s%d" % (z, j))
                ok = False
            if len(acc) != 64:
                print("FAIL: accept size %s%d = %d" % (z, j, len(acc)))
                ok = False
    seen_a, seen_b = set(), set()
    for x in range(1 << 16):
        va, vb = mix_a(x), mix_b(x)
        if va in seen_a or vb in seen_b:
            print("FAIL: mix collision on probe range")
            ok = False
            break
        seen_a.add(va)
        seen_b.add(vb)
    kA, kB, _ = kdf_real(b"CARTO{no_figure_sits_in_every_pixel}")
    if (kA, kB) != (0x73070925, 0xA159F9E2):
        print("FAIL: demo kdf drifted: %08x %08x" % (kA, kB))
        ok = False
    if ok:
        print("SELFTEST OK (accept sets, mix injectivity, kdf anchor)")


def stats():
    import random
    rnd = random.Random(0xCA4705E2)
    kA = rnd.getrandbits(32)
    kB = rnd.getrandbits(32)
    n = 30000
    d = DELTA["A"][0]
    hits = 0
    for _ in range(n):
        p = rnd.getrandbits(64)
        if (encrypt(kA, kB, p) ^ encrypt(kA, kB, p ^ d)) == d:
            hits += 1
    mean, sig = n / 16.0, (n / 16.0 * (1 - 1 / 16.0)) ** 0.5
    print("planted delta %08x: %d completions in %d pairs "
          "(want %.0f +- %.0f)" % (d, hits, n, mean, 4 * sig))
    if abs(hits - mean) > 4 * sig:
        print("FAIL: completion rate off")
        return 1
    d2 = 0x2                    # same window, non-planted bit
    misses = sum(1 for _ in range(20000)
                 if (encrypt(kA, kB, (p0 := rnd.getrandbits(64)))
                     ^ encrypt(kA, kB, p0 ^ d2)) == d2)
    print("non-planted delta %08x: %d completions in 20000 pairs "
          "(want ~0)" % (d2, misses))
    if misses > 4:
        print("FAIL: non-planted bias too visible")
        return 1
    print("STATS OK")
    return 0


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        selftest()
        return 0
    if "--stats" in args:
        return stats()
    if "--keys" in args:
        reading = args[args.index("--keys") + 1].encode()
        kA, kB, _ = kdf_real(reading)
        print("kA=%08x kB=%08x" % (kA, kB))
        return 0
    if "--enc" in args:
        i = args.index("--enc")
        reading = args[i + 1].encode()
        fig = int(args[i + 2], 16)
        kA, kB, _ = kdf_real(reading)
        print("%016x" % encrypt(kA, kB, fig))
        return 0
    if "--poison-enc" in args:
        i = args.index("--poison-enc")
        reading = args[i + 1].encode()
        fig = int(args[i + 2], 16)
        _, _, d = kdf_real(reading)
        kA, kB, _ = kdf_poison(d)
        print("%016x" % encrypt(kA, kB, fig))
        return 0
    if "--attack-json" in args:
        i = args.index("--attack-json")
        blob = json.loads(pathlib.Path(args[i + 1]).read_text())
        kA, kB, rep = attack(blob["pairs"])
        if kA is None:
            print("EMPTY-INTERSECTION")
        elif rep["ambiguous"]:
            print("AMBIGUOUS %s" % ",".join(rep["ambiguous"]))
        else:
            print("KEY=%08x%08x" % (kA, kB))
            if "expect" in blob:
                want = blob["expect"]
                got = "%08x%08x" % (kA, kB)
                print("VERIFIED" if got == want else "MISMATCH want=%s" % want)
        print("report: %s" % rep)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())

