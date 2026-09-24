#!/usr/bin/env python3
"""Fill the COST_MODEL template with the measured numbers from the runs."""
import os
import re

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUNS = os.path.join(REPO, "organizer-private", "runs")


def grab(path, pat, default="?"):
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return default
    m = re.search(pat, text)
    return m.group(1).strip() if m else default


def main():
    clean = grab(os.path.join(RUNS, "clean_path.txt"), r"TIME TOTAL\s+([\d.]+) s")
    seal = open(os.path.join(RUNS, "stage4_seal.log"),
                encoding="utf-8", errors="replace").read()
    work = re.search(r"work=(\d+)", seal)
    wall = re.search(r"wall=([\d.]+)s", seal)
    work_n = work.group(1) if work else "?"
    wall_n = wall.group(1) if wall else "?"
    bait = grab(os.path.join(RUNS, "final.log"), r"bait layer is (\d+) lines")

    tpl = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "COST_MODEL_TEMPLATE.md")
    text = open(tpl, encoding="utf-8").read()
    text = text.replace("PAIRS_N", "750")
    text = text.replace("mitm seconds", wall_n + " s")
    text = text.replace("evals evaluations", work_n + " evaluations")
    text = text.replace("LINES_BAIT", bait)
    out = os.path.join(REPO, "organizer-private", "COST_MODEL.md")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("wrote %s" % out)
    print("clean total (scaled): %s s; mitm: %s evals in %s s; bait: %s lines"
          % (clean, work_n, wall_n, bait))


if __name__ == "__main__":
    main()
