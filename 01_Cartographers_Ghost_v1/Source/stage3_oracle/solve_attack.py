#!/usr/bin/env python3
"""solve_attack.py -- drives the Stage 3 differential attack (D52). INTERNAL.

Modes:
  --model           attack a seeded random in-process key (proves the
                    recorded sample size recovers the full 64-bit key)
  --model-true      attack the true reading-derived key (end-to-end)
  --bin --pairs N   collect N pairs from the REAL oracle binary (run from
                    the package root) with human-ish pacing, cross-check
                    the answers against the model
  --fast-demo N     N identical scripted-fast queries against the real
                    binary to expose the poison (clean tail -> poisoned,
                    self-consistent, well-formed)

Pacing for --bin / --fast-demo alternates two sleeps (default 0.4 s and
3.6 s): inter-arrival stddev = (b - a) / 2 = 1.6 s > CARTO_STDDEV_LOW_MS,
so a paced collection stays clean while a tight loop poisons (D48).
"""

import hashlib
import pathlib
import random
import re
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import model_oracle as M                      # noqa: E402

PKG = HERE.parent.parent / "cartographer"
ORACLE = PKG / "stage3_oracle" / "oracle"
READING = "CARTO{no_figure_sits_in_every_pixel}"
M64 = M.M64

ANSWER_RE = re.compile(r"the oracle answers:\s*\n\s*([0-9a-f]{16})")


def spaced_p(rnd):
    return rnd.getrandbits(64)


def gen_pairs(key, per_window, seed=0xCA4705E3):
    """Model-side collection: (z,j) experiments in generator order."""
    rnd = random.Random(seed)
    kA, kB = key
    pairs = []
    for z in ("A", "B"):
        for j in range(4):
            d = M.DELTA[z][j] << (0 if z == "A" else 32)
            for _ in range(per_window):
                p = spaced_p(rnd)
                c0 = M.encrypt(kA, kB, p)
                c1 = M.encrypt(kA, kB, (p ^ d) & M64)
                pairs.append({"p": p, "c0": c0, "c1": c1, "d": d})
    return pairs


def run_model(per_window, use_true_key):
    if use_true_key:
        kA, kB, _ = M.kdf_real(READING.encode())
        expect = "%08x%08x" % (kA, kB)
        key = (kA, kB)
    else:
        rnd = random.Random(0x5EEDC1A0)
        key = (rnd.getrandbits(32), rnd.getrandbits(32))
        expect = "%08x%08x" % key
    pairs = gen_pairs(key, per_window)
    kAx, kBx, rep = M.attack(pairs)
    print("model key   : %s" % expect)
    print("pairs used  : %d (%d per experiment)" % (len(pairs), per_window))
    print("hits A      : %s" % [rep["hits_a"][j] for j in range(4)])
    if kAx is None:
        print("NO-CONSENSUS")
        print("report      : %s" % rep)
        return 1
    print("recovered   : %08x%08x" % (kAx, kBx))
    print("hits B      : %s" % [rep["hits_b"][j] for j in range(4)])
    print("cands       : %s" % rep["cands"])
    if "%08x%08x" % (kAx, kBx) == expect:
        print("VERIFIED")
        return 0
    print("MISMATCH")
    return 1

def mixed_model():
    """Mixed clean+poisoned dataset -> deterministic empty intersection."""
    kA, kB, _ = M.kdf_real(READING.encode())
    digest = hashlib.sha256(M.SEED_REAL + READING.encode()).digest()
    pkA, pkB, _ = M.kdf_poison(digest)
    clean = gen_pairs((kA, kB), 6, seed=0x11)
    poison = gen_pairs((pkA, pkB), 6, seed=0x22)
    got = M.attack(clean + poison)[0]
    print("mixed dataset: %d clean + %d poisoned pairs"
          % (len(clean), len(poison)))
    if got is None:
        print("NO-CONSENSUS (mixed data falsifies deterministically)")
        return 0
    print("UNEXPECTED-KEY %08x%08x -- mixed data should not converge" % got)
    return 1


def poison_model_converges():
    """A fully poisoned dataset is self-consistent: the SAME attack yields
    the POISON key (no coin flip; falsifiable by comparison)."""
    kA, kB, _ = M.kdf_real(READING.encode())
    digest = hashlib.sha256(M.SEED_REAL + READING.encode()).digest()
    pkA, pkB, _ = M.kdf_poison(digest)
    pairs = gen_pairs((pkA, pkB), 400, seed=0x33)
    got = M.attack(pairs)
    kAx, kBx = got[0], got[1]
    want = "%08x%08x" % (pkA, pkB)
    print("poisoned dataset -> %s" %
          ("KEY=%08x%08x" % (kAx, kBx) if kAx else "NO-CONSENSUS"))
    if kAx and "%08x%08x" % (kAx, kBx) == want:
        print("POISON-KEY-RECOVERED (self-consistent wrong dataset)")
        return 0
    return 1


def query_oracle(reading, fig_hex, cwd):
    r = subprocess.run([str(ORACLE), "-r", reading, fig_hex],
                       capture_output=True, text=True, cwd=str(cwd))
    m = ANSWER_RE.search(r.stdout)
    if r.returncode != 0 or r.stderr or m is None:
        raise SystemExit("oracle run failed rc=%d stderr=%r out=%r"
                         % (r.returncode, r.stderr, r.stdout[:200]))
    return m.group(1)


def collect_bin(n, pace, seed=0x5157):
    """Collect pair records from the real binary with alternating pacing.
    Uses the phase-A window-0 experiment: (P, P ^ delta)."""
    rnd = random.Random(seed)
    delta = M.DELTA["A"][0]
    answers = []
    for i in range(n):
        if i % 2 == 0:
            p0 = spaced_p(rnd)
            fig0 = "%016x" % p0
            fig1 = "%016x" % ((p0 ^ delta) & M64)
        fig = fig0 if (i % 2 == 0) else fig1
        ans = query_oracle(READING, fig, PKG)
        answers.append((fig, ans))
        time.sleep(pace[i % 2])
    records = []
    for i in range(0, n - 1, 2):
        f0, a0 = answers[i]
        f1, a1 = answers[i + 1]
        p = int(f0, 16)
        records.append({"p": p, "c0": int(a0, 16),
                        "c1": int(a1, 16), "d": p ^ int(f1, 16)})
    return records

def bin_crosscheck(n, pace):
    """Small real-binary batch: answers must match the model bit-exactly."""
    records = collect_bin(n, pace)
    if not records:
        print("no pairs collected")
        return 1
    bad = 0
    kA, kB, _ = M.kdf_real(READING.encode())
    for rec in records:
        got0 = M.encrypt(kA, kB, rec["p"])
        got1 = M.encrypt(kA, kB, (rec["p"] ^ rec["d"]) & M64)
        if ("%016x" % got0 != "%016x" % rec["c0"]
                or "%016x" % got1 != "%016x" % rec["c1"]):
            bad += 1
    print("real-vs-model: %d/%d pair answers matched" % (len(records) - bad,
                                                         len(records)))
    print("CROSSCHECK-" + ("OK" if bad == 0 else "FAIL"))
    return 0 if bad == 0 else 1


def fast_demo(n):
    """Scripted-fast identical queries: poison must appear, self-consistent."""
    fig = "0123456789abcdef"
    answers = []
    for _ in range(n):
        answers.append(query_oracle(READING, fig, PKG))
        time.sleep(0.05)
    uniq = []
    for a in answers:
        if a not in uniq:
            uniq.append(a)
    print("fast-demo answers in order: %s" % " ".join(answers))
    print("distinct answers: %d %s" % (len(uniq), uniq))
    if len(uniq) == 1:
        print("SINGLE-ANSWER (ring already uniform or human-paced)")
        return 0
    if len(uniq) == 2:
        print("CLEAN=%s POISON=%s" % (uniq[0], uniq[1]))
        print("POISON-DIFFERS-FROM-CLEAN")
        print("SELF-CONSISTENT-POISON")
        return 0
    print("MORE-THAN-TWO-ANSWERS (unexpected)")
    return 1


def main():
    args = sys.argv[1:]

    def opt(name, default):
        return int(args[args.index(name) + 1]) if name in args else default

    if "--model" in args:
        return run_model(opt("--pairs-per-window", 400), False)
    if "--model-true" in args:
        return run_model(opt("--pairs-per-window", 400), True)
    if "--mixed" in args:
        return mixed_model()
    if "--poison-converges" in args:
        return poison_model_converges()
    if "--bin" in args:
        n = opt("--pairs", 8)
        pace = (0.4, 3.6)
        if "--pace" in args:
            a, b = args[args.index("--pace") + 1].split(",")
            pace = (float(a), float(b))
        return bin_crosscheck(n, pace)
    if "--fast-demo" in args:
        return fast_demo(opt("--pairs", 12))
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())

