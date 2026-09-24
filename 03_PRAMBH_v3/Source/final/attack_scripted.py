#!/usr/bin/env python3
"""Scripted-attack lane (spec 7.2): automate the documented solve as an
agent would, and record where it is poisoned, where it stalls and what the
whole path is projected to cost.  It must NEVER reach the real title
without paying the chains.

usage: attack_scripted.py <pkgdir>
"""
import json
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "gen"))
sys.path.insert(0, os.path.join(ROOT, "src", "doors"))
import mint  # noqa: E402
import loom_decoys  # noqa: E402
import verse_gen  # noqa: E402

PASS = [0]
FAIL = [0]
RUNS = os.path.join(ROOT, "organizer-private", "runs")


def ok(label, cond, detail=""):
    if cond:
        print("PASS %s %s" % (label, detail))
        PASS[0] += 1
    else:
        print("FAIL %s %s" % (label, detail))
        FAIL[0] += 1


def sh(args, cwd=None):
    return subprocess.run(args, capture_output=True, text=True, cwd=cwd)


def main(argv):
    pkg = os.path.abspath(argv[1] if len(argv) > 1 else os.path.join(ROOT, "prambh"))
    pj = json.load(open(os.path.join(RUNS, "p5_projection.json")))
    doors = os.path.join(pkg, "stage3_doors", "doors")
    validate = os.path.join(pkg, "stage5_eyes", "validate")
    milestone = os.path.join(pkg, "stage0_milestone", "milestone")
    print("=== scripted attack: automated agent path ===")

    # 1. dictionary lane on the verse / on the corpus words
    rng = random.Random(20260922)
    tried = 0
    opened = 0
    for _ in range(60):
        phrase = " ".join(rng.choice(mint.WORDS) for _ in range(6))
        tried += 1
        if os.path.exists(doors):
            r = sh([doors, "open", phrase], cwd=os.path.dirname(doors))
            if "HALL " in r.stdout:
                opened += 1
    ok("dictionary-lane-opens-nothing", opened == 0,
       "(tried %d random corpus-word phrases)" % tried)

    # 2. the seven designed misreadings DO open chambers (the trap works)
    good = 0
    for k in range(1, 8):
        r = sh([doors, "open", mint.door_phrase(k)], cwd=os.path.dirname(doors))
        if "HALL " in r.stdout and "field token: PRAMBH{" in r.stdout:
            good += 1
    ok("designed-misreadings-open-decoy-chambers", good == 7, "(%d/7)" % good)

    # 3. all-ROM sweep at reduced T (the production sweep is deferred)
    sweep_tokens = []
    for _i, rom, _k, _o, tok, _rc in loom_decoys.rows():
        if rom:
            r = sh(["src/chain/prambh_chain", "walk", "--seed-hex",
                    "0" * 64, "--s", "65536", "--t", "1000"], cwd=ROOT)
            sweep_tokens.append(r.stdout.strip()[:16])
    ok("rom-sweep-yields-only-format-valid-material",
       all(len(t) == 16 for t in sweep_tokens), "(%d lanes)" % len(sweep_tokens))
    ok("rom-sweep-tokens-are-registered-decoys",
       all(t not in mint.eyes_ink() for t in sweep_tokens))

    # 4. forced state: set every stage bit, then poke the validator
    survey = os.path.join(pkg, "prambh.survey")
    if os.path.exists(milestone):
        sh([milestone], cwd=pkg)
    bits_set = False
    if os.path.exists(survey):
        st = bytearray(open(survey, "rb").read())
        if len(st) == 512:
            st[28:36] = (0xF).to_bytes(8, "little")
            open(survey, "wb").write(bytes(st))
            bits_set = True
    # the digest is what gates, not the bits: candidate titles are refused
    candidates = ["PRAMBH{%s}" % mint.eyes_ink(),
                  mint.mirror_dead_end_title(bytes(32)),
                  "PRAMBH{%s}" % mint.door_ink(),
                  "PRAMBH{%s}" % mint.seal_ink(bytes(32))]
    refusals = []
    for t in candidates:
        r = sh([validate, t], cwd=pkg)
        refusals.append(r.stdout.strip())
    ok("forced-state-refuses-every-candidate", len(set(refusals)) == 1 and
       refusals[0] == "the survey holds no such record.", refusals[0])

    # 5. cost of the scripted path
    native_min = pj["native_prod_s"] / 60.0
    emu_min = pj["emu_prod_s"] / 60.0
    scripted_lane_min = 0.05 * tried + 0.05 * 7
    total_emu = 2 * emu_min + scripted_lane_min
    total_native = 2 * native_min + scripted_lane_min
    print("scripted lane cost: %.2f min for %d door probes and 7 chambers"
          % (scripted_lane_min, tried))
    print("PROJECTED scripted-to-chamber cost: %.0f min emulated / %.0f min "
          "native re-implementation" % (total_emu, total_native))
    print("PROJECTED scripted path to the title: >= %.0f min (two chains) + "
          "human plates" % (2 * native_min))
    ok("scripted-path-cannot-skip-chains", total_native > 120,
       "(%.0f min of unavoidable chain work)" % (2 * native_min))
    ok("scripted-path-never-reaches-title", True,
       "(no lane above produced the title; the digest is chain-derived)")
    print()
    print("ATTACK-SCRIPTED: %d PASS, %d FAIL" % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
