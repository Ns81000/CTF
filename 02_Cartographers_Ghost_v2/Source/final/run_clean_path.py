#!/usr/bin/env python3
"""The honest path on the test builds, driven the way a person would sit.

Uses the test binaries only (time-scale hook compiled in), pty-wrapped,
with a thin record laid first and every tool fed the ink the previous
tool produced.  Ends with the title block taking the assembled title.
Writes per-stage timing lines for COST_MODEL.md.
"""
import os
import random
import re
import shutil
import subprocess
import sys
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PKG = os.path.join(REPO, "cartographer")
WORK = "/tmp/carto_clean_path"
SCALE = "10000"
PAIRS = 24
READING = "CARTO{rust_blooms_under_tin_roofs}"
INK = "145e1d23feac3932"
SEAL_KEY = "3821ad004ab30263"
ORACLE_INK = "e509312ae8a2e0ad"
TITLE = ("CARTO{3821ad004ab30263_e509312ae8a2e0ad_"
         "145e1d23feac3932_rust_blooms_under_tin_roofs}")


def pty(cmd, timeout=600):
    t0 = time.time()
    r = subprocess.run(["script", "-qec", cmd, "/dev/null"],
                       cwd=WORK, capture_output=True, text=True,
                       timeout=timeout, stdin=subprocess.DEVNULL)
    return r.stdout.replace("\r", ""), r.returncode, time.time() - t0


def plain(cmd, timeout=600):
    t0 = time.time()
    r = subprocess.run(cmd, shell=True, cwd=WORK, capture_output=True,
                       text=True, timeout=timeout,
                       stdin=subprocess.DEVNULL)
    return r.stdout, r.returncode, time.time() - t0


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    subprocess.run(["cp", "-a", PKG + "/.", WORK], check=True)
    for f in ("seed3", "oracle_test", "collect.py", "model_oracle.py",
              "stage3_tables.json"):
        src = os.path.join(REPO, "src/stage3_oracle", f)
        if os.path.exists(src):
            shutil.copy(src, WORK)
    # no pre-laid record: the tower is climbed in order, from a fresh
    # record, exactly as a solver would.  the sitting itself generates
    # the volume the dials ask for (>= 6000 interactions, >= 3000
    # distinct figures, the scaled span), through the hook on the
    # test build only.

    timings = {}
    envp = "env CARTO_TEST_TIME_SCALE=%s" % SCALE

    # ---- stage 0: the ledger -------------------------------------------------
    # a person plays with the ledger; every visit is a real terminal
    # interaction on the record, and the stage never moves backwards.
    # the pauses are the sitting: the shipped tools read the real dials.
    t0 = time.time()
    rngp = random.Random(4711)
    for k in range(8):
        out, rc, _ = pty("%s ./stage0_ledger/ledger" % envp)
        assert rc == 0, "ledger failed"
        time.sleep(0.2 + 0.5 * rngp.random())
    assert "CARTO{the_survey_reopens_tonight}" in out, \
        "the ledger did not hand over its token:\n%s" % out[-400:]
    timings["stage0 ledger"] = time.time() - t0

    # ---- stage 1: the engine, both profiles ---------------------------------
    out, rc, wall = pty("%s ./stage1_engine/engine -p coast" % envp)
    assert rc == 0, "engine coast failed:\n%s" % out[-400:]
    assert "bearing" not in out.lower(), \
        "the engine leaked the bearing on the screen (spec says never)"
    timings["stage1 engine coast"] = wall
    time.sleep(0.4)
    out, rc, wall = pty("%s ./stage1_engine/engine -p interior" % envp)
    assert rc == 0, "engine interior failed:\n%s" % out[-400:]
    timings["stage1 engine interior"] = wall

    # ---- stage 2: the sheet (the bearing comes off the record) --------------
    time.sleep(0.3)
    out, rc, wall = pty("%s ./stage2_sheet/sheet -r --plain" % envp)
    assert rc == 0, "sheet reveal failed:\n%s" % out[-400:]
    assert "rust_blooms_under_tin_roofs" in out, \
        "sheet did not reveal the reading:\n%s" % out[-500:]
    timings["stage2 sheet reveal"] = wall

    # ---- stage 3: the oracle --------------------------------------------------
    t0 = time.time()
    # the sitting: pace out the volume dial on ordinary figures first --
    # the plate answers cold until the record shows a real sitting -- and
    # then collect the differential families the attack needs.  the
    # warm-up runs on one held-open terminal so each ask is cheap.
    import pty as _pty
    master, slave = _pty.openpty()

    def on_pty(cmd, timeout=60):
        r = subprocess.run(cmd, shell=True, cwd=WORK, stdin=slave,
                           stdout=slave, stderr=slave, timeout=timeout)
        try:
            os.read(master, 65536)
        except OSError:
            pass
        return r.returncode

    rng = random.Random(20260922)
    asked = 0
    while asked < 6200:
        fig = rng.randrange(0, 1 << 64).to_bytes(8, "little").hex()
        rc = on_pty("%s ./oracle_test -r '%s' -i %s %s"
                    % (envp, READING, INK, fig))
        assert rc == 0, "warm-up ask failed at %d" % asked
        asked += 1
    out, rc, _ = pty("%s ./oracle_test -t -r %s" % (envp, READING))
    assert "CARTO{a_warm_plate_and_a_full_ring}" in out, \
        "the tally did not come after the sitting:\n%s" % out[-400:]

    out, rc, _ = pty("%s python3 collect.py %s/ds --pairs 750 "
                     "--oracle ./oracle_test" % (envp, WORK),
                     timeout=3600)
    assert rc == 0, "collect failed:\n%s" % out[-400:]
    rows = []
    with open(os.path.join(WORK, "ds")) as fh:
        for line in fh:
            p = line.split()
            if len(p) >= 2:
                rows.append((p[0], p[1]))
    assert len(rows) >= 8 * 750, "too few rows: %d" % len(rows)
    aout, arc, _ = plain("python3 model_oracle.py attack %s/ds" % WORK)
    assert arc == 0, "attack model failed:\n%s" % aout[-400:]
    m = re.search(r"ink=([0-9a-f]{16})", aout)
    assert m, "attack model found no ink:\n%s" % aout[-800:]
    assert m.group(1) == ORACLE_INK, \
        "the attack landed on %s, not the real ink" % m.group(1)
    timings["stage3 oracle sitting"] = time.time() - t0

    # ---- stage 4: the seal ---------------------------------------------------
    t0 = time.time()
    got = ""
    for b8 in range(256):
        cand = "%s%02x" % (SEAL_KEY[:14], b8)
        out, rc, _ = pty("./stage4_seal/seal %s" % cand)
        assert rc == 0
        if "the stamp closes" in out:
            got = cand
            break
    assert got == SEAL_KEY, "the closing byte walk failed (%s)" % got
    timings["stage4 seal walk"] = time.time() - t0

    # ---- stage 5: the title --------------------------------------------------
    out, rc, wall = pty("./stage5_title/validate '%s'" % TITLE)
    assert "the block takes the title" in out, \
        "the block refused the title:\n%s" % out[-400:]
    timings["stage5 title"] = wall

    total = sum(timings.values())
    print("CLEAN PATH COMPLETE")
    print("title %s" % TITLE)
    for k in sorted(timings):
        print("TIME %-26s %8.1f s (scaled wall)" % (k, timings[k]))
    print("TIME %-26s %8.1f s (scaled total)" % ("TOTAL", total))
    with open(os.path.join(REPO, "organizer-private", "runs",
                           "clean_path.txt"), "w") as fh:
        fh.write("CLEAN PATH COMPLETE\n")
        for k in sorted(timings):
            fh.write("TIME %-26s %8.1f s (scaled wall)\n" % (k, timings[k]))
        fh.write("TIME %-26s %8.1f s (scaled total)\n" % ("TOTAL", total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
