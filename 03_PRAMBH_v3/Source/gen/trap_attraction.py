#!/usr/bin/env python3
"""Trap-attraction pass (Appendix C.3) -> organizer-private/TRAP_ATTRACTION.md.

Written BEFORE minting: the misreadings an AI agent or a human will most
likely make of the verse and the plates, each mapped to a decoy chamber or
a mirror thread, plus the cross-corroboration matrix that makes a wrong
turn feel progressively MORE confirmed.

usage: trap_attraction.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src", "doors"))
import mint  # noqa: E402
import verse_gen  # noqa: E402

ROMS = ["tide_merc6", "star_merc3", "grav_merc9"]


def rows():
    out = []
    for k in range(1, 8):
        out.append(("- **M%d** - %s" % (k, verse_gen.LABELS[k]),
                    ["  - who: an AI agent reading the verse as a slot table, or "
                     "a human taking the most salient marker word",
                     "  - yields: `%s`" % mint.door_phrase(k),
                     "  - destination: decoy chamber %d (hall %d)"
                     % (k, mint.door_numbers()[k]),
                     "  - corroboration: its own 12-min chain walk, its "
                     "registered field token, folio_%03d, plate %s, cartridge "
                     "%s, and the Duplicate Survey it files into"
                     % (mint.decoy_folios()[k % len(mint.decoy_folios())],
                        mint.decoy_plate_codes()[k % 6],
                        ROMS[k % 3]),
                     "  - why it feels confirmed: the chamber answers at once and "
                     "agrees with the folio it names, so the reading looks right "
                     "and the hall looks real",
                     "  - escape (fairness): the needle folio states the reading "
                     "rule, and no decoy chamber can hand over a loom ink or a "
                     "next load vector"]))
    out.append(("- **M8** - read the depth plate's SECOND depth plane as the code",
                ["  - who: an autocorrelation/repeat-period pipeline, or a human "
                 "resolving the wrong plane first",
                 "  - yields: `%s` (registered decoy)" % mint.decoy_eyes_code("depth"),
                 "  - destination: the Duplicate Survey's plate lineage",
                 "  - why it feels confirmed: the plane resolves cleanly and the "
                 "code is a well-formed glyph code",
                 "  - escape: the viewing notes say which plane is cut for the "
                 "survey"]))
    out.append(("- **M9** - separate the hue plate by luminance and read that "
                "channel",
                ["  - who: ImageMagick channel separations, any RGB/luma "
                 "segmentation",
                 "  - yields: `%s` (registered decoy)" % mint.decoy_eyes_code("hue"),
                 "  - destination: the Duplicate Survey's plate lineage",
                 "  - escape: the plate's stated illuminant note in the notes"]))
    out.append(("- **M10** - rotate the line screens at the reciprocal bearing",
                ["  - who: a rotation search stopping at the first or strongest "
                 "maximum",
                 "  - yields: `%s` (registered decoy)" % mint.decoy_eyes_code("moire"),
                 "  - destination: the depot's own marked bearing in the mirror "
                 "fiction",
                 "  - escape: the notes give the survey bearing, not its "
                 "reciprocal"]))
    return out



def main():
    doc = ["# PRAMBH v3 - TRAP ATTRACTION PASS (organizer-private)", "",
           "Written before minting (Appendix C.3).  The dominant misreadings:",
           "seven readings of the door verse (one decoy chamber each) and the",
           "three plate misreadings.  Every one lands in a decoy chamber or a",
           "mirror thread, and they cross-corroborate each other.", "",
           "Rule the design exploits: the further a wrong reading is followed,",
           "the MORE confirmation it collects - every trap points at the",
           "Duplicate Survey and at the other traps, not at the real record.", "",
           "## Misreadings", ""]
    for head, body in rows():
        doc.append(head)
        doc.extend(body)
        doc.append("")
    doc += ["## Cross-corroboration matrix", "",
            "| trap | points at | agrees with |", "| --- | --- | --- |"]
    for k in range(1, 8):
        doc.append("| M%d (chamber %d) | Duplicate Survey, folio_%03d, plate %s | "
                   "the other decoy chambers, the decoy cartridges |"
                   % (k, k, mint.decoy_folios()[k % len(mint.decoy_folios())],
                      mint.decoy_plate_codes()[k % 6]))
    doc.append("| D-ROM-1..3 | decoy models MERC-6/3/9 | folios 1:1, mirror room |")
    doc.append("| mirror campaign | the Duplicate Survey, its own 2-stage chain | "
               "every decoy chamber files into it |")
    doc.append("| M8/M9/M10 | the mirror room's plate lineage | each other |")
    doc += ["", "## Fairness (spec 4.6/4.11)", "",
            "Escapable by documented observation, never by luck:",
            "1. only the real chamber hands over the domain ink and the next",
            "   load vector;",
            "2. the needle folio states the verse's reading rule in words;",
            "3. the Duplicate Survey's dates contradict the zero-milestone epoch;",
            "4. the mirror corpus cites plate ids absent from plates/;",
            "5. the real tools never acknowledge a mirror token.", "",
            "Intended asymmetry: an agent chasing corroboration sees more",
            "agreement the deeper it follows, while a human comparing two",
            "folios sees the contradiction.", "",
            "real eye ink: %s" % mint.eyes_ink(),
            "registered decoy codes: depth=%s hue=%s moire=%s"
            % (mint.decoy_eyes_code("depth"), mint.decoy_eyes_code("hue"),
               mint.decoy_eyes_code("moire")),
            "door readings: %s" % ", ".join("%d=%s" % (k, mint.door_phrase(k))
                                            for k in range(8)),
            ""]
    path = os.path.join(ROOT, "organizer-private", "TRAP_ATTRACTION.md")
    with open(path, "w") as f:
        f.write("\n".join(doc) + "\n")
    print("wrote %s (%d lines)" % (path, len(doc)))
    for k in range(8):
        print("reading %d -> %s" % (k, mint.door_phrase(k)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
