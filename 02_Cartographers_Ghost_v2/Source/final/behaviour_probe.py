#!/usr/bin/env python3
"""behaviour_probe.py -- fast, piped and uniform paths are gated or
poisoned.  Runs the sitting a script would run and records, for every
regime, that the answer it yields is wrong-by-design.  Prints
PROVEN/FAILED lines and one final verdict.
"""
import os
import re
import subprocess
import sys
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PKG = os.path.join(REPO, "cartographer")
WORK = "/tmp/carto_probe"
FAILED = 0
CHECKS = 0

READING = "CARTO{rust_blooms_under_tin_roofs}"
INK = "145e1d23feac3932"
TITLE = ("CARTO{3821ad004ab30263_e509312ae8a2e0ad_"
         "145e1d23feac3932_rust_blooms_under_tin_roofs}")
REAL = {"3821ad004ab30263", "e509312ae8a2e0ad", "145e1d23feac3932",
        "rust_blooms_under_tin_roofs", TITLE}


def check(name, ok):
    global FAILED, CHECKS
    CHECKS += 1
    if ok:
        print("  PROVEN %s" % name)
    else:
        print("  FAILED %s" % name)
        FAILED += 1


def run(args, tty=False, stdin=None):
    kw = dict(cwd=WORK, capture_output=True, text=True, timeout=30)
    if tty:
        return subprocess.run(["script", "-qec", " ".join(args),
                               "/dev/null"], stdin=subprocess.DEVNULL,
                              **kw)
    return subprocess.run(args, stdin=subprocess.DEVNULL, **kw)


def main():
    import shutil
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    subprocess.run(["cp", "-a", PKG + "/.", WORK], check=True)

    # 1. piped asks never warm the plate
    outs = set()
    for i in range(6):
        r = run(["./stage3_oracle/oracle", "-r", READING,
                 "0f1e2d3c4b5a697%d" % i])
        outs.add(r.stdout.strip().splitlines()[-1] if r.stdout else "")
    check("piped asks all get the pipe verse",
          all("pipe" in o for o in outs))
    check("piped answers carry no ink",
          not any(v in "".join(outs) for v in REAL))

    # 2. burst asks never warm the plate; a metronome asks never either.
    #    any cold/poison verse is a pass (young record, hot ring, smooth
    #    spacing all refuse differently); a pass never carries real ink
    r = run(["./stage3_oracle/oracle", "-r", READING,
             "0f1e2d3c4b5a6100"], tty=True)
    check("fast repeated asks are poisoned, never warm",
          any(v in r.stdout for v in
              ("run hot", "still cold", "still warming", "gone smooth",
               "too recently", "gives nothing"))
          and not any(v in r.stdout for v in REAL))

    # 3. the tally never comes off a scripted record
    r = run(["./stage3_oracle/oracle", "-t", "-r", READING])
    check("scripted tally is never set", "witness:" not in r.stdout)

    # 4. a piped right title is refused, and identically
    r1 = run(["./stage5_title/validate", TITLE])
    r2 = run(["./stage5_title/validate", "CARTO{the_coast_was_drawn_twice}"])
    check("piped right title refused", "does not take this" in r1.stdout)
    check("piped refusals identical", r1.stdout == r2.stdout)

    # 5. the sheet never reads for a pipe
    r = run(["./stage2_sheet/sheet", "-r"])
    check("piped sheet reveal refused",
          "not a pipe" in r.stdout or "hand" in r.stdout)

    # 6. a rate hammer heals nothing: one careful ask still answers cold
    for i in range(40):
        run(["./stage3_oracle/oracle", "-r", READING,
             "%016x" % (0x5000 + i)])
    r = run(["./stage3_oracle/oracle", "-t", "-r", READING])
    check("the plate stays cold after a hammer", "witness:" not in r.stdout)

    # 7. deleting the record resets the tower silently
    if os.path.exists(os.path.join(WORK, ".cartographer_state")):
        os.unlink(os.path.join(WORK, ".cartographer_state"))
    r = run(["./stage0_ledger/ledger"])
    check("the ledger opens on a fresh record", r.returncode == 0
          and "the_survey_reopens_tonight" in r.stdout)

    print("  %d behaviour checks, %d failed" % (CHECKS, FAILED))
    shutil.rmtree(WORK, ignore_errors=True)
    if FAILED == 0:
        print("BEHAVIOUR PROVEN")
        return 0
    print("BEHAVIOUR NOT PROVEN")
    return 1


if __name__ == "__main__":
    sys.exit(main())
