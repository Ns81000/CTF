#!/usr/bin/env python3
"""Generate the PRAMBH flood corpus (spec 4.3): <root>/field-notes/.

450 folios, 46 lines each. Needle and decoy folios have their stitched
original spliced in at a minted line offset. Pure stdlib, deterministic.
"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "gen"))
import mint

SPLICE_LABEL = "prambh:flood:splice:v1"


def write_words_header(path):
    with open(path, "w") as f:
        f.write("#ifndef PRAMBH_FLOOD_WORDS_H\n#define PRAMBH_FLOOD_WORDS_H\n\n")
        f.write("#define PRAMBH_N_WORDS %d\n\n" % len(mint.WORDS))
        f.write("static const char *const PRAMBH_WORDS[PRAMBH_N_WORDS] = {\n")
        for w in mint.WORDS:
            f.write('    "%s",\n' % w)
        f.write("};\n\n#endif\n")


def splice_offset(folio, nlines):
    b = mint.seed(SPLICE_LABEL, struct.pack("<I", folio))
    return 1 + b[0] % (mint.FOLIO_BODY_LINES - nlines)


def build_corpus(outdir):
    os.makedirs(outdir, exist_ok=True)
    needles = mint.needle_texts()
    decoys = mint.decoy_texts()
    nf = mint.needle_folios()
    df = mint.decoy_folios()
    for folio in range(mint.CORPUS_FOLIOS):
        lines = mint.corpus_page_lines(folio)
        if folio in nf:
            text = needles[nf.index(folio)]
            off = splice_offset(folio, len(text))
            lines[off:off + len(text)] = text
        elif folio in df:
            text = decoys[df.index(folio)]
            off = splice_offset(folio, len(text))
            lines[off:off + len(text)] = text
        with open(os.path.join(outdir, "folio_%03d.txt" % folio), "w") as f:
            f.write("\n".join(lines) + "\n")


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else None
    write_words_header(os.path.join(ROOT, "flood", "flood_words.h"))
    if outdir:
        build_corpus(outdir)


if __name__ == "__main__":
    main()
