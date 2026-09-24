#!/usr/bin/env python3
"""Calibrate PRAMBH-CHAIN step counts on this build machine.

Measures the native single-thread walk rate r at the real table size
(512 MiB), then writes chain_params.json.

Dials (spec 6 P2): T is set so the honest walk takes the target seconds
at the measured r.  The floor projection (COST_MODEL.md, P10) argues the
walk is DRAM-latency-bound, so a 4x CPU advantage buys an attacker ~1x;
if the total floor projection comes short of 4 h, the documented dial to
raise is T (chain targets), recorded before/after in COST_MODEL.md.

  chain1/chain2 : 75 min honest target (spec dial)
  door decoy chamber chains : 12 min honest (spec band 10-20 min)
  mirror chains : 4 min honest (decoy path; must stay cheap to solve)
  decoy ROM chains : 3 min honest

Writes src/chain/chain_params.json and organizer-private/runs/p2_calibration.txt.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TOOL = os.path.join(HERE, "prambh_chain")
S = 512 * 1024 * 1024
MEASURE_SECONDS = 12

HONEST_TARGETS = {
    "chain1": 75 * 60,
    "chain2": 75 * 60,
    "door_decoy": 12 * 60,
    "mirror": 4 * 60,
    "decoy_rom": 3 * 60,
}


def measure():
    p = subprocess.run([TOOL, "measure", "--s", str(S), "--seconds",
                        str(MEASURE_SECONDS)], capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit("measure failed: " + p.stderr)
    steps, secs = p.stdout.split()
    return int(steps) / float(secs), p.stderr.strip()


def main():
    r, fill_note = measure()
    params = {
        "table_bytes": S,
        "table_blocks": S // 32,
        "r_build_steps_per_sec": round(r, 1),
        "attacker_advantage_assumption": 4,
        "latency_bound_note": "walk is DRAM-latency-bound at S=512MiB; see COST_MODEL.md",
        "measure_seconds": MEASURE_SECONDS,
        "budgets": {},
    }
    for name, target in HONEST_TARGETS.items():
        t = int(r * target)
        params["budgets"][name] = {
            "honest_target_seconds": target,
            "T": t,
        }
    with open(os.path.join(HERE, "chain_params.json"), "w") as f:
        json.dump(params, f, indent=2)

    runs = os.path.join(ROOT, "organizer-private", "runs")
    os.makedirs(runs, exist_ok=True)
    with open(os.path.join(runs, "p2_calibration.txt"), "w") as f:
        f.write("P2 CALIBRATION\n")
        f.write("fill: %s\n" % fill_note)
        f.write("r_build = %.1f steps/s at S=%d\n" % (r, S))
        f.write(json.dumps(params, indent=2) + "\n")
    print("r_build = %.1f steps/s" % r)
    for name, b in params["budgets"].items():
        print("%-10s T=%d  honest=%ds" % (name, b["T"], b["honest_target_seconds"]))


if __name__ == "__main__":
    main()
