#!/usr/bin/env python3
"""pf2_report.py -- aggregate the Phase FINAL-2 reliability trial JSONL files.

    python3 src/final/pf2_report.py logs/runs/pf2_trials_model.jsonl [...]
"""

import collections
import json
import pathlib
import sys


def load(path):
    recs = []
    for line in pathlib.Path(path).read_text().splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            recs.append(json.loads(line))
        except ValueError:
            pass
    return recs


def summarize(path, recs, mode):
    print("== %s (%d records) ==" % (path, len(recs)))
    print("%-5s %-7s %-7s %-10s %-11s %-11s %s"
          % ("N", "trials", "ok", "fail_rate", "mean_secs", "worst_hits",
             "harness_errors"))
    by_n = collections.OrderedDict()
    for r in recs:
        by_n.setdefault(r["n"], []).append(r)
    for n in sorted(by_n):
        rs = by_n[n]
        ok = sum(1 for r in rs if r.get("ok"))
        err = [r for r in rs if r.get("error")]
        secs = [r.get("seconds", 0.0) for r in rs]
        mins = [min([r.get(k) for k in ("min_hits_a", "min_hits_b")
                     if r.get(k) is not None] or [0]) for r in rs]
        print("%-5d %-7d %-7d %-10.4f %-11.2f %-11s %d"
              % (n, len(rs), ok, (len(rs) - ok) / float(len(rs)),
                 sum(secs) / len(secs), min(mins) if mins else "n/a",
                 len(err)))
        if err:
            print("      first harness error: %s"
                  % err[0]["error"][:220].replace("\n", " | "))
        fails = [r for r in rs if not r.get("ok") and not r.get("error")]
        if fails:
            shapes = collections.Counter()
            for r in fails:
                st = ",".join(s.split(":")[0] for s in r.get("state", []))
                shapes[st] += 1
            print("      %d real failures, shapes: %s"
                  % (len(fails), shapes.most_common(4)))
        cl = [r["clean"] for r in rs if r.get("clean") is not None]
        po = [r["poison"] for r in rs if r.get("poison") is not None]
        if cl:
            print("      data check: all trials clean (min %d/%d sampled "
                  "pairs under the real key, max %d under the poison key)"
                  % (min(cl), 200, max(po)))
    return 0


def main():
    for path in sys.argv[1:]:
        recs = load(path)
        mode = recs[0]["mode"] if recs else "?"
        summarize(path, recs, mode)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
