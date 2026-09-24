#!/usr/bin/env python3
"""The scripted path: fast, piped, uniform -- everything a sitting is not.

Drives the shipped oracle binary with a script's timing (no pty, fast
uniform asks, duplicated figures).  Confirms every behaviour the dials
promise: the plate answers cold/poisoned, the tally never comes, and
nothing in the output is ever an ink.
"""
import os
import re
import shutil
import subprocess
import sys
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PKG = os.path.join(REPO, "cartographer")
WORK = "/tmp/carto_poison"
READING = "CARTO{rust_blooms_under_tin_roofs}"

# values that must never appear on a scripted path
POISON = ["3821ad004ab30263", "e509312ae8a2e0ad", "145e1d23feac3932",
          "rust_blooms_under_tin_roofs", "a_warm_plate_and_a_full_ring",
          "01d94d492a46ce3d", "CARTO_TEST_TIME_SCALE"]


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    subprocess.run(["cp", "-a", PKG + "/.", WORK], check=True)

    fig = "a1b2c3d4e5f60718"
    # fast piped uniform asks -- the sitting that is not a sitting
    for i in range(24):
        r = subprocess.run(["./stage3_oracle/oracle", "-r", READING, fig],
                           cwd=WORK, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=30)
        assert r.returncode == 0, "oracle errored on the scripted path"
        assert r.stderr == "", "oracle spoke on stderr"
    out1 = r.stdout
    # the same figure again comes back from the same plate
    r = subprocess.run(["./stage3_oracle/oracle", "-r", READING, fig],
                       cwd=WORK, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=30)
    out2 = r.stdout
    # the tally: cold plates do not set it
    r = subprocess.run(["./stage3_oracle/oracle", "-t", "-r", READING],
                       cwd=WORK, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=30)
    tally = r.stdout
    # the title block on this record: refused, identically
    title = ("CARTO{3821ad004ab30263_e509312ae8a2e0ad_"
             "145e1d23feac3932_rust_blooms_under_tin_roofs}")
    r = subprocess.run(["./stage5_title/validate", title],
                       cwd=WORK, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=30)
    refuse = r.stdout

    print("SCRIPTED PATH COMPLETE")
    print("tally answer: %s" % " ".join(tally.split()))
    print("title answer: %s" % " ".join(refuse.split()))
    leaks = 0
    for bad in POISON:
        for name, blob in (("ask", out1 + out2), ("tally", tally),
                           ("title", refuse)):
            if bad in blob:
                leaks += 1
                print("LEAK %s in %s" % (bad, name))
    assert leaks == 0, "scripted path leaked %d values" % leaks
    assert "warm plate" not in tally and "witness:" not in tally, \
        "a cold plate set the tally"
    assert "does not take this" in refuse, "the block took a piped title"
    print("no real value reached the scripted path")
    return 0


if __name__ == "__main__":
    sys.exit(main())
