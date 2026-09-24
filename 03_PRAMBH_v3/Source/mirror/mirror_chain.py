#!/usr/bin/env python3
"""Mirror campaign two-stage chain (spec 4.6) - organizer-side.

Stage A walks the Duplicate Survey's opening chain; stage B is chained
from stage A's output.  Both use the shared engine (src/chain) at the
mirror budget so the whole fake campaign stays cheap to solve, and the
dead-end title mirror_validate accepts is derived from stage B.

usage: mirror_chain.py            (writes organizer-private/runs/mirror_chain.txt)
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "gen"))
import mint  # noqa: E402

CHAIN = os.path.join(ROOT, "src", "chain", "prambh_chain")
PARAMS = json.load(open(os.path.join(ROOT, "src", "chain", "chain_params.json")))
S = PARAMS["table_bytes"]
T = PARAMS["budgets"]["mirror"]["T"]


def walk(seed_hex):
    t0 = time.time()
    p = subprocess.run([CHAIN, "walk", "--seed-hex", seed_hex, "--s", str(S),
                        "--t", str(T)], capture_output=True, text=True)
    if p.returncode != 0 or len(p.stdout.strip()) != 64:
        raise SystemExit("mirror_chain: walk failed: " + p.stderr[:200])
    return p.stdout.strip(), time.time() - t0


def main():
    seed_a = mint.mirror_stage_a_seed()
    out_a, sec_a = walk(seed_a.hex())
    seed_b = mint.mirror_stage_b_seed(bytes.fromhex(out_a))
    out_b, sec_b = walk(seed_b.hex())
    title = mint.mirror_dead_end_title(bytes.fromhex(out_b))
    lines = [
        "P7 MIRROR CAMPAIGN - two-stage chain (spec 4.6)",
        "engine: %s (S=%d, T=%d each stage)" % (CHAIN, S, T),
        "stage A seed = SHA256(\"prambh:mirror:stage-a:v1\") = %s" % seed_a.hex(),
        "stage A out  = %s  (elapsed %.1f s)" % (out_a, sec_a),
        "stage A token = PRAMBH{%s}" % out_a[0:16],
        "stage B seed = SHA256(\"prambh:mirror:stage-b:v1\" || stage A out) = %s"
        % seed_b.hex(),
        "stage B out  = %s  (elapsed %.1f s)" % (out_b, sec_b),
        "stage B token = PRAMBH{%s}" % out_b[0:16],
        "dead-end title accepted by mirror_validate = %s" % title,
        "NOTE: measured with the real engine at the mirror budget; the audit",
        "re-times these two walks under its own machine conditions.",
    ]
    out = os.path.join(ROOT, "organizer-private", "runs", "mirror_chain.txt")
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
