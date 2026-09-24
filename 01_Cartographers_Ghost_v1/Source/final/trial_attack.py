#!/usr/bin/env python3
"""trial_attack.py -- Phase FINAL-2 section 1: N_REQUIRED reliability trials.

INTERNAL (never shipped).  Answers one question with evidence instead of a
single lucky run: at how small a per-window sample size does the Stage-3
differential attack still recover the master key EVERY time?

Two data sources, both addressing the same attack (model_oracle.attack):

  --mode real   Collect the pairs from the REAL oracle binary, one isolated
                package directory per trial (so the interaction ring of one
                trial can never contaminate another), with a FRESH random
                seed per trial.  Run against the scaled test build so a trial
                costs seconds instead of ~an hour; the pacing is divided by
                the same scale, which keeps the ring stddev above the scaled
                poison floor -- the sampled ciphertexts are therefore the
                clean-key ones, exactly like a real solve.
  --mode model  Generate the pairs with the python model (proven bit-exact
                against the binary by src/stage3_oracle/test_stage3.sh) and
                run the identical attack.  Cheap enough for hundreds of
                trials per candidate, which is what turns "5/5 succeeded"
                into a measurable failure RATE.

    python3 src/final/trial_attack.py --mode real  --candidates 160,200,240,280,320
    python3 src/final/trial_attack.py --mode model --candidates 120,160,200,240,280 --trials 200

Every trial prints one JSON line: {mode, n, trial, seed, ok, kA, kB, hits_a,
hits_b, state, seconds}.  The parent aggregates and prints the table.
"""

import argparse
import json
import os
import pathlib
import random
import shutil
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent                       # /home/manish/cartographer-build
PKG_SRC = ROOT / "cartographer"
TRIAL_ROOT = pathlib.Path(os.environ.get("CARTO_TRIAL_ROOT", "/tmp/carto_trials"))
READING = "CARTO{no_figure_sits_in_every_pixel}"
EXPECT_KEY = "73070925a159f9e2"
TSCALE = int(os.environ.get("CARTO_FINAL_TSCALE", "60") or "60")
BASE_PACE = [float(x) for x in os.environ.get("CARTO_FINAL_PACE",
                                              "0.15,1.85").split(",")]



# ------------------------------------------------------------- one trial ----

def fresh_seed():
    return int.from_bytes(os.urandom(4), "little")


def isolate_pkg(dest):
    """A per-trial package root: only what the oracle path needs, so the
    state file, the ring and the decoy bits stay private to this trial."""
    dest = pathlib.Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "stage3_oracle").mkdir(parents=True)
    (dest / "stage2_stego").mkdir(parents=True)
    shutil.copy2(PKG_SRC / "stage3_oracle" / "oracle",
                 dest / "stage3_oracle" / "oracle")
    for c in ("survey_frame.png", "survey_tape.wav"):
        shutil.copy2(PKG_SRC / "stage2_stego" / c, dest / "stage2_stego" / c)
    return dest


def model_pairs(per_window, seed):
    """Fresh random figures, same 8 experiments, model ciphertexts."""
    import model_oracle as M
    kA, kB, _ = M.kdf_real(READING.encode())
    rnd = random.Random(seed)
    pairs = []
    for z in ("A", "B"):
        for j in range(4):
            d = M.DELTA[z][j] << (0 if z == "A" else 32)
            for _ in range(per_window):
                p = rnd.getrandbits(64)
                pairs.append({"p": p,
                              "c0": M.encrypt(kA, kB, p),
                              "c1": M.encrypt(kA, kB, (p ^ d) & M.M64),
                              "d": d})
    return pairs, kA, kB


def collect_real(per_window, seed, pkg):
    """Real-binary collection in an isolated package root.

    CARTO_TEST_TIME_SCALE is exported to the oracle subprocesses: the test
    build scales the poison FLOOR by exactly the same factor as the pacing,
    so a scaled run samples the clean-key ciphertexts just like a real one.
    (Forgetting it is not a subtle failure -- the oracle silently answers
    under the poison key from the 5th query on, which is why every trial in
    this harness re-verifies its data against the real key.)"""
    os.environ["CARTO_PKG"] = str(pkg)
    os.environ["CARTO_TEST_TIME_SCALE"] = str(TSCALE)
    sys.path.insert(0, str(HERE))
    import cartosolve as C
    pace = (BASE_PACE[0] / TSCALE, BASE_PACE[1] / TSCALE)
    records = C.collect_pairs(READING, per_window, pace, None, tag="t",
                              seed=seed, progress_every=0)
    sd, _ = C.ring_stddev()
    return records, sd


def data_consistency(records, kA, kB, sample=200):
    """How much of the collected data is actually the clean key's?

    A poisoned or contaminated dataset is a harness defect, not a weak
    attack, so every trial records this."""
    import model_oracle as M
    _, _, digest = M.kdf_real(READING.encode())
    pkA, pkB, _ = M.kdf_poison(digest)
    step = max(1, len(records) // sample)
    real = poi = 0
    for rec in records[::step]:
        if M.encrypt(kA, kB, rec["p"]) == rec["c0"]:
            real += 1
        if M.encrypt(pkA, pkB, rec["p"]) == rec["c0"]:
            poi += 1
    return real, poi



def one_trial(mode, per_window, trial, seed):
    sys.path.insert(0, str(ROOT / "src" / "stage3_oracle"))
    t0 = time.time()
    rec = {"mode": mode, "n": per_window, "trial": trial, "seed": seed}
    if mode == "model":
        pairs, kA, kB = model_pairs(per_window, seed)
        sd = None
    else:
        pkg = isolate_pkg(TRIAL_ROOT / ("n%d_t%d" % (per_window, trial)))
        pairs, sd = collect_real(per_window, seed, pkg)
        import model_oracle as M
        kA, kB, _ = M.kdf_real(READING.encode())

    import model_oracle as M
    gA, gB, rep = M.attack(pairs)
    rec["ok"] = bool(gA == kA and gB == kB)
    if mode == "real":
        rec["clean"], rec["poison"] = data_consistency(pairs, kA, kB)
        if rec["poison"]:
            raise SystemExit("collected data is under the POISON key "
                             "(%d/%d sampled) -- harness defect" % (rec["poison"], rec["clean"] + rec["poison"]))
        if not rec["clean"]:
            raise SystemExit("collected data matches neither key -- harness defect")
    rec["kA"] = None if gA is None else "%08x" % gA
    rec["kB"] = None if gB is None else "%08x" % gB
    rec["hits_a"] = rep["hits_a"]
    rec["hits_b"] = rep["hits_b"]
    rec["state"] = rep["state"]
    rec["ring_sd_ms"] = sd
    rec["seconds"] = round(time.time() - t0, 2)

    ha = [rep["hits_a"].get(k, 0) for k in sorted(rep["hits_a"])]
    hb = [rep["hits_b"].get(k, 0) for k in sorted(rep["hits_b"])]
    rec["min_hits_a"] = min(ha) if ha else None
    rec["min_hits_b"] = min(hb) if hb else None
    return rec


# --------------------------------------------------------------- the runs ---

def run_parallel(mode, cands, trials, jobs, out_path, quiet_ok=True):
    procs = []
    results = []
    queue = [(n, t) for n in cands for t in range(trials)]
    seeds = {k: fresh_seed() for k in queue}
    fh = open(out_path, "w", buffering=1)

    def launch(n, t):
        cmd = [sys.executable, str(pathlib.Path(__file__).resolve()),
               "--one-trial", mode, str(n), str(seeds[(n, t)])]
        procs.append((subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True),
                      n, t))

    while queue or procs:
        while queue and len(procs) < jobs:
            launch(*queue.pop(0))
        time.sleep(0.2)
        for item in list(procs):
            p, n, t = item
            if p.poll() is None:
                continue
            procs.remove(item)
            out, err = p.communicate()
            line = [l for l in out.splitlines() if l.startswith("{")]
            if p.returncode != 0 or not line:
                rec = {"mode": mode, "n": n, "trial": t, "ok": False,
                       "error": (err or out)[-500:], "seconds": 0}
            else:
                rec = json.loads(line[-1])
            results.append(rec)
            fh.write(json.dumps(rec) + "\n")
            if not rec.get("ok") or not quiet_ok:
                print("[%s] n=%-4d trial=%-3d min_hits_a=%s min_hits_b=%s %s"
                      % ("OK " if rec.get("ok") else "FAIL", n, t,
                         rec.get("min_hits_a"), rec.get("min_hits_b"),
                         "" if rec.get("ok") else json.dumps(rec)[:400]),
                      flush=True)
    fh.close()
    return results


def report(results):
    print("\n==== reliability summary ====")
    cands = sorted({r["n"] for r in results})
    print("%-6s %-7s %-7s %-10s %-16s %s"
          % ("N", "trials", "ok", "fail_rate", "worst min_hits", "notes"))
    for n in cands:
        rs = [r for r in results if r["n"] == n]
        ok = sum(1 for r in rs if r.get("ok"))
        mins = [min([r[k] for k in ("min_hits_a", "min_hits_b")
                     if r.get(k) is not None] or [0]) for r in rs]
        secs = [r.get("seconds", 0) for r in rs]
        print("%-6d %-7d %-7d %-10s %-16s %s"
              % (n, len(rs), ok, "%.3f" % ((len(rs) - ok) / len(rs)),
                 min(mins) if mins else "n/a",
                 "avg %.1fs/trial" % (sum(secs) / len(secs))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["real", "model"], default="real")
    ap.add_argument("--candidates", default="160,200,240,280,320")
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--out", default=None)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--one-trial", nargs=3, metavar=("MODE", "N", "SEED"))
    args = ap.parse_args()

    if args.one_trial:
        mode, n, seed = args.one_trial
        print(json.dumps(one_trial(mode, int(n), int(seed) % 100000000, int(seed))))
        return 0

    if args.mode == "real":
        b = PKG_SRC / "stage3_oracle" / "oracle"
        if b"CARTO_TEST_TIME_SCALE" not in subprocess.run(
                ["strings", str(b)], capture_output=True).stdout:
            raise SystemExit("real-mode trials need the SCALED TEST BUILD "
                             "(src/final/build_testbuild.sh)")

    cands = [int(x) for x in args.candidates.split(",")]
    out = args.out or str(ROOT / "logs" / "runs" /
                          ("pf2_trials_%s.jsonl" % args.mode))
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    print("mode=%s candidates=%s trials=%d jobs=%d out=%s"
          % (args.mode, cands, args.trials, args.jobs, out), flush=True)
    res = run_parallel(args.mode, cands, args.trials, args.jobs, out,
                       quiet_ok=not args.verbose)
    report(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())

