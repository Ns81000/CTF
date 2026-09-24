#!/usr/bin/env python3
"""P4 corpus verification: format uniformity, needle/decoy
indistinguishability, and leak scan. Prints PASS/FAIL lines."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "gen"))
import mint

FAILS = 0


def check(ok, name):
    global FAILS
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        FAILS += 1


HDR = re.compile(r"^MERU FIELD SURVEY - folio \d{3}-\d{2} / stitch [0-9a-f]{8}$")
MEAS = re.compile(r"^= \d{1,2}\.\d{2} m$")
NUM = re.compile(r"^\d+$")


def main(cdir):
    vocab = set(mint.WORDS) | {"stitched", "original:"}
    folios = sorted(os.listdir(cdir))
    check(len(folios) == mint.CORPUS_FOLIOS, "py: folio count %d" % len(folios))

    pages = {}
    stitches = set()
    ok_hdr = ok_lines = True
    for fn in folios:
        lines = open(os.path.join(cdir, fn)).read().splitlines()
        pages[fn] = lines
        if not HDR.match(lines[0]):
            ok_hdr = False
        if len(lines) != mint.FOLIO_BODY_LINES + 1:
            ok_lines = False
        stitches.add(lines[0].rsplit(" ", 1)[1])
    check(ok_hdr, "py: every folio header format identical")
    check(ok_lines, "py: every folio exactly %d lines" % (mint.FOLIO_BODY_LINES + 1))
    check(len(stitches) == len(folios), "py: stitch tokens unique")

    blob = "\n".join("\n".join(v) for v in pages.values())
    check(not re.search(r"[0-9a-f]{16,}", blob.replace("stitch ", "")),
          "py: no long hex strings in corpus")
    check("PRAMBH{" not in blob, "py: no CTF tokens in corpus")
    check(mint.capsule_content().hex() not in blob, "py: no capsule content")
    check(mint.launch_phrase() not in blob, "py: no launch phrase")

    lm, dm = mint.loom_model(), mint.decoy_loom_model(mint.loom_model())
    check(blob.count(lm) == 1, "py: real loom model only in needle folio")
    check(blob.count(dm) == 1, "py: decoy loom model only in decoy folio")

    nf = ["folio_%03d.txt" % f for f in mint.needle_folios()]
    df = ["folio_%03d.txt" % f for f in mint.decoy_folios()]

    def rare_count(lines):
        n = 0
        for line in lines[1:]:
            for tok in line.split():
                if tok in vocab or NUM.match(tok) or MEAS.match(tok):
                    continue
                n += 1
        return n

    def mean_len(lines):
        return sum(len(x) for x in lines) / len(lines)

    nr = [rare_count(pages[f]) for f in nf]
    dr = [rare_count(pages[f]) for f in df]
    check(max(nr) >= min(dr) and max(dr) >= min(nr),
          "py: needle/decoy rare-token ranges overlap (n=%s d=%s)" % (nr, dr))
    check(abs(sum(nr) / len(nr) - sum(dr) / len(dr)) <= 4,
          "py: needle/decoy rare-token means within 4")
    nl = [mean_len(pages[f]) for f in nf]
    dl = [mean_len(pages[f]) for f in df]
    check(abs(sum(nl) / 5 - sum(dl) / 5) / (sum(nl) / 5) <= 0.15,
          "py: needle/decoy mean line length within 15%%")

    check(all("stitched from the surveyor's original:" in "\n".join(pages[f])
              for f in nf), "py: needle splice markers present")
    check(all("recovered from a secondary copy:" in "\n".join(pages[f])
              for f in df), "py: decoy splice markers present")
    check("hall %d" % mint.real_door_number() in "\n".join(pages[nf[2]]),
          "py: needle N3 names the real hall number")
    check("red channel" in "\n".join(pages[nf[4]]),
          "py: needle N5 plate method present")

    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main(sys.argv[1])
