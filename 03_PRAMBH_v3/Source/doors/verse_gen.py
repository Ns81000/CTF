#!/usr/bin/env python3
"""Hall of Doors verse generator (spec 4.5) - organizer-side.

Builds the survey verse from the eight designed phrases so that EIGHT
different readings of the same six lines each yield exactly one designed
phrase: the real answer (reading 0) plus the seven designed misreadings
(one decoy chamber each, in trap-catalogue order).

Each line is cut from one skeleton, and every skeleton word the readings
care about sits directly behind its own marker word:

  <opening> by the <a0> at the <a1>, <filler> past the <a2> near <a3>,
  under <a4> through <a5> toward <a6>, the <a7>.

    reading 0 (REAL)  the word each mark settles with = the line-final word
    reading 1         the word after "past"
    reading 2         the word after "by"
    reading 3         the word after "at"
    reading 4         the word after "near"
    reading 5         the word after "under"
    reading 6         the word after "through"
    reading 7         the word after "toward"

Deterministic: same mint -> same verse.  main() prints the verse, the
reading table and a self-check that every reading reproduces its phrase.

usage: verse_gen.py [--json]
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "gen"))
import mint  # noqa: E402

# reading k -> (marker word, human label); reading 0 is the real one.
MARKERS = [None, "past", "by", "at", "near", "under", "through", "toward"]
LABELS = ["the word each mark settles with (line-final)",
          "the word after 'past'",
          "the word after 'by'",
          "the word after 'at'",
          "the word after 'near'",
          "the word after 'under'",
          "the word after 'through'",
          "the word after 'toward'"]
# reading k -> skeleton slot (a permutation of 0..7)
SLOT_OF = [7, 2, 0, 1, 3, 4, 5, 6]

OPENINGS = [
    "", "", "with the lamp low, ", "spool dry and carriage true, ",
    "after the second cut, ", "", "with the drums quiet, ",
    "in the valley issue, ",
]
FILLERS = [
    "", "", "the bed level, ", "the needle steady, ", "the drum turning, ",
    "no slack in the wire, ", "the tally kept, ", "the sheet squared, ",
]
FRAME = [
    "FIRST SURVEY - hall door verse, cut from the hall folio.",
    "six marks were cut below; read them down, in the order cut.",
    "speak the word each mark comes to rest on - the last word cut into",
    "that line - and the six so taken are the door's own word.",
]

ACCESSORS = [m for m in MARKERS if m]
VERSE_LABEL = "prambh:doors:verse:v1"
LINES = 6


def _stream():
    return mint.sha256ctr(mint.seed(VERSE_LABEL), 64)


def line_slots(i):
    """The eight skeleton words of line i, one per slot (see SLOT_OF)."""
    slots = [None] * 8
    for k, phrase in enumerate(mint.door_phrases()):
        slots[SLOT_OF[k]] = phrase[i]
    if None in slots:
        raise SystemExit("verse_gen: slot map is not a permutation")
    return slots


def build_line(i, stream):
    a = line_slots(i)
    opening = OPENINGS[stream[i] % len(OPENINGS)]
    filler = FILLERS[stream[8 + i] % len(FILLERS)]
    body = ("by %s at %s, %spast %s near %s, under %s through %s toward %s, "
            "the %s." % (a[0], a[1], filler, a[2], a[3], a[4], a[5], a[6], a[7]))
    text = opening + body
    return text[0].upper() + text[1:]


def verse_lines():
    stream = _stream()
    return [build_line(i, stream) for i in range(LINES)]


def read_phrase(lines, k):
    """Apply designed reading k to the verse lines -> its six words.

    Reading k>0 takes the word that follows marker k exactly once per
    line (the field-note skeleton fixes that position); reading 0 takes
    the line-final word.
    """
    out = []
    for line in lines:
        toks = [t.lower() for t in re.findall(r"[A-Za-z']+", line)]
        if k == 0:
            out.append(toks[-1])
        else:
            out.append(toks[toks.index(MARKERS[k]) + 1])
    return out


def verse_text():
    return "\n".join(FRAME + verse_lines()) + "\n"


def check():
    """Structural self-check: markers unique per line, every reading
    reproduces its designed phrase, and no accessor word hides in the
    prose."""
    lines = verse_lines()
    for i, line in enumerate(lines):
        toks = [t.lower() for t in re.findall(r"[A-Za-z']+", line)]
        for m in ACCESSORS:
            if toks.count(m) != 1:
                return "line %d: marker %r appears %d times" % (i, m, toks.count(m))
        if len(toks) < 8:
            return "line %d: too few words" % i
    for k in range(8):
        got = read_phrase(lines, k)
        want = mint.door_phrases()[k]
        if got != want:
            return "reading %d mismatch: %r != %r" % (k, got, want)
    return None


def main(argv):
    lines = verse_lines()
    if "--json" in argv:
        print(json.dumps({"frame": FRAME, "lines": lines,
                          "readings": [{"k": k, "label": LABELS[k],
                                        "phrase": " ".join(read_phrase(lines, k)),
                                        "real": k == mint.real_door_index()}
                                       for k in range(8)]}, indent=2))
        return 0
    err = check()
    print("HALL OF DOORS VERSE (mint-derived, deterministic)")
    print("=" * 62)
    print(verse_text())
    print("=" * 62)
    for k in range(8):
        print("reading %d (%-42s) -> %s%s"
              % (k, LABELS[k], " ".join(read_phrase(lines, k)),
                 "   <== REAL ANSWER" if k == mint.real_door_index() else ""))
    print("self-check:", "OK" if err is None else "FAILED: " + err)
    return 0 if err is None else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
