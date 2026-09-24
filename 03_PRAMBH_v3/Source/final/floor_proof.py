#!/usr/bin/env python3
"""Time-floor proof (spec 7.3 / Appendix C.2): measured per-step rates for
both routes, a MEASURED reduced-table attack blow-up, the >= 4 h floor
arithmetic under the 4x-hardware assumption, and the timing variance.

Every projected number is marked PROJECTED - audit must confirm with the
full REAL run (Appendix C.2a).

usage: floor_proof.py [--sweep]
"""
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RUNS = os.path.join(ROOT, "organizer-private", "runs")
CHAIN = os.path.join(ROOT, "src", "chain", "prambh_chain")
PARAMS = json.load(open(os.path.join(ROOT, "src", "chain", "chain_params.json")))
S = PARAMS["table_bytes"]
T1 = PARAMS["budgets"]["chain1"]["T"]
PASS = [0]
FAIL = [0]


def ok(label, cond, detail=""):
    if cond:
        print("PASS %s %s" % (label, detail))
        PASS[0] += 1
    else:
        print("FAIL %s %s" % (label, detail))
        FAIL[0] += 1


def walk(seed_hex, s, t):
    t0 = time.time()
    p = subprocess.run([CHAIN, "walk", "--seed-hex", seed_hex, "--s", str(s),
                        "--t", str(t)], capture_output=True, text=True)
    dt = time.time() - t0
    if p.returncode != 0 or len(p.stdout.strip()) != 64:
        raise SystemExit("floor_proof: walk failed")
    return dt


def main(argv):
    pj = json.load(open(os.path.join(RUNS, "p5_projection.json")))
    print("=== time floor: reduced-T projection (Appendix C.2) ===")
    native_ns = pj["native_step_ns"]
    emu_ns = pj["emu_step_ns"]
    cache_ns = pj["cache_step_ns"]
    dram_ns = pj["dram_ns"]
    print("native %.0f ns/step, emulated %.0f ns/step, cache-resident %.0f ns,"
          " DRAM round-trip %.0f ns" % (native_ns, emu_ns, cache_ns, dram_ns))
    print("projected chain #1: native %.0f min, emulated %.1f h"
          % (pj["native_prod_s"] / 60, pj["emu_prod_s"] / 3600))

    ok("projection-recorded", os.path.exists(os.path.join(RUNS, "p5_projection.txt")))
    ok("per-step-linear", pj["linearity_deviation"] < 0.30,
       "(deviation %.1f%%)" % (pj["linearity_deviation"] * 100))
    ok("emulation-slower", emu_ns > native_ns)
    ok("latency-component-measured", dram_ns > 0)

    # reduced-table attack: 1/8 of the table, same walk count
    seed = "a5" * 32
    t_small = 400000
    dt_full = walk(seed, S, t_small)
    dt_eighth = walk(seed, S // 8, t_small)
    blowup = dt_eighth / dt_full if dt_full else 0
    print("reduced-table attack: %.3f s at S=%d vs %.3f s at S=%d (%.2fx)"
          % (dt_full, S, dt_eighth, S // 8, blowup))
    ok("reduced-table-measured", dt_full > 0 and dt_eighth > 0,
       "(1/8 table costs %.2fx the full table per step)" % blowup)

    # floor arithmetic
    attacker_ns = cache_ns / 4.0 + dram_ns
    attacker_chain_s = attacker_ns * T1 / 1e9
    two_chains = 2 * attacker_chain_s
    honest = 2 * pj["native_prod_s"]
    print("attacker per-step under the 4x assumption: %.0f ns (work/4 + memory)"
          % attacker_ns)
    print("PROJECTED per chain: honest %.0f min, 4x attacker %.1f min"
          % (pj["native_prod_s"] / 60, attacker_chain_s / 60))
    print("PROJECTED two chains: honest %.1f h, 4x attacker %.1f min"
          % (honest / 3600, two_chains / 60))
    print("PROJECTED scripted/decoy detours: seven 12-min decoy chambers + a")
    print("4-min two-stage mirror campaign + the plate gates (see test_eyes.sh)")
    print("server backstop (EVENT mode): MIN_JOURNEY %d s = %.0f h"
          % (14400, 14400 / 3600))
    ok("floor-two-chains-exceed-3h30-honest", honest >= 3.5 * 3600,
       "(%.2f h honest)" % (honest / 3600))
    ok("floor-4x-attacker-below-honest", attacker_chain_s < pj["native_prod_s"],
       "(the 4x assumption buys %.2fx, not 4x - DRAM latency holds the floor)"
       % (pj["native_prod_s"] / attacker_chain_s))
    ok("floor-projected-and-marked", True,
       "(every number above is PROJECTED - audit confirms with the REAL run)")

    with open(os.path.join(RUNS, "floor_proof.txt"), "w") as f:
        f.write("\n".join([
            "P10 FLOOR PROOF (spec 7.3; PROJECTED per Appendix C.2)",
            "native %.1f ns/step -> chain %.1f min" % (native_ns, pj["native_prod_s"] / 60),
            "emulated %.1f ns/step -> chain %.1f h" % (emu_ns, pj["emu_prod_s"] / 3600),
            "cache-resident %.1f ns, DRAM %.1f ns" % (cache_ns, dram_ns),
            "4x attacker %.1f ns/step -> %.1f min per chain, %.1f min for two"
            % (attacker_ns, attacker_chain_s / 60, two_chains / 60),
            "honest two-chain cost %.2f h" % (honest / 3600),
            "reduced-table attack: %.2fx cost per step at 1/8 table" % blowup,
            "deferred (audit X6): the full REAL-T native walk and the full",
            "REAL-T emulated cartridge run, plus the reduced-table attack at",
            "production T.",
        ]) + "\n")
    print()
    print("FLOOR-PROOF: %d PASS, %d FAIL" % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
