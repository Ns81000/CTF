#!/usr/bin/env python3
"""Hall of Doors chamber generator (spec 4.5) - organizer-side.

Builds the eight chamber texts from the mint: the real chamber (the hall
ink + chain #2's handover vector) and seven decoy chambers, each of which
carries its own chain walk (12 min budget), its registered field token
(harvested from organizer-private/runs/door<k>_walk.txt) and the
cross-corroboration web the trap-attraction pass demands (decoy folio,
decoy plate, decoy cartridge, the Duplicate Survey).

usage: chambers_gen.py [--preview FILE]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "gen"))
sys.path.insert(0, HERE)
import json  # noqa: E402
import mint  # noqa: E402
import verse_gen  # noqa: E402

PARAMS = json.load(open(os.path.join(ROOT, "src", "chain", "chain_params.json")))
S = PARAMS["table_bytes"]
TDOOR = PARAMS["budgets"]["door_decoy"]["T"]
CHAMBER_MAX = 2048          # must match doors.c
RUNS = os.path.join(ROOT, "organizer-private", "runs")
MARK = "HALL "


def harvested_token(k):
    """Field token of decoy chamber k, from its walk report (never
    recomputed here)."""
    path = os.path.join(RUNS, "door%d_walk.txt" % k)
    if not os.path.exists(path):
        raise SystemExit("chambers_gen: %s missing - run chain_jobs.py doors "
                         "first (token must be harvested, never guessed)" % path)
    for line in open(path):
        if line.startswith("derived:"):
            return line.split("checkpoint=")[1].split()[0]
    raise SystemExit("chambers_gen: no checkpoint in " + path)


def real_chamber():
    dn = mint.real_door_number()
    body = [
        "%s%d" % (MARK, dn),
        "the survey walks on. hall %d was cut in one pass and its folio is" % dn,
        "complete; the loom has nothing further to settle here.",
        "",
        "what the plate fragment leaves behind is the hall ink, taken as",
        "printed and nothing more: %s" % mint.door_ink(),
        "",
        "the next instrument takes its own load vector from this hall,",
        "exactly as written:",
        "  %s" % mint.chain2_vector().hex(),
        "",
        "carry it to the eye plates. the seal is set at the same table as",
        "the loom's walk, so the wait is the same wait.",
        "",
    ]
    return "\n".join(body)


def decoy_chamber(k):
    """Decoy chamber for misreading k (k = 1..7)."""
    dn = mint.door_numbers()[k]
    tok = harvested_token(k)
    vec = mint.door_decoy_vector(k).hex()
    folio = "folio_%03d" % mint.decoy_folios()[k % len(mint.decoy_folios())]
    plate = mint.decoy_plate_codes()[k % 6]
    rom = ["tide_merc6", "star_merc3", "grav_merc9"][k % 3]
    body = [
        "%s%d" % (MARK, dn),
        "hall %d answers to the word %s - the reading every duplicate" % (dn, verse_gen.LABELS[k].replace("the word after '", "taken after '")),
        "folio in the depot used, and the one this hall was cut against.",
        "",
        "before the hall opens further it asks for its own stitch. run the",
        "loom's walk on the vector printed here, at the standard table:",
        "  ./loom verify --vector %s --T %d --S %d" % (vec, TDOOR, S),
        "  the checkpoint that settles is this hall's field token: %s" % tok,
        "",
        "file it with %s at the valley depot, beside the %s strips" % (folio, rom),
        "and the plate fragment %s the depot sent with them - all three" % plate,
        "carry the same hall number, so the record is consistent.",
        "",
        "the duplicate survey is filed at the valley depot; every hall it",
        "holds answers to the same reading you have already used.",
        "",
    ]
    return "\n".join(body)


def chambers():
    out = [real_chamber()] + [decoy_chamber(k) for k in range(1, 8)]
    for i, text in enumerate(out):
        if not text.startswith(MARK):
            raise SystemExit("chambers_gen: chamber %d lacks the marker" % i)
        if len(text) >= CHAMBER_MAX - 1:
            raise SystemExit("chambers_gen: chamber %d too long (%d)"
                             % (i, len(text)))
    return out


def main(argv):
    texts = chambers()
    preview = os.path.join(RUNS, "chambers_preview.txt")
    if "--preview" in argv:
        preview = argv[argv.index("--preview") + 1]
    lines = ["P6 - HALL OF DOORS CHAMBER PREVIEW (spec 4.5)",
             "real chamber index = %d (hall %d, door ink %s)"
             % (mint.real_door_index(), mint.real_door_number(), mint.door_ink()),
             "decoy chamber chains: S=%d T=%d (12 min budget each)" % (S, TDOOR),
             ""]
    for i, text in enumerate(texts):
        lines.append("---- chamber %d (%s) ----"
                     % (i, "REAL" if i == mint.real_door_index() else "decoy"))
        lines.append(text)
        lines.append("")
    lines.append("candidate phrases (reading k -> phrase):")
    for k in range(8):
        lines.append("  %d %-52s %s%s"
                     % (k, verse_gen.LABELS[k], mint.door_phrase(k),
                        "  <== REAL" if k == mint.real_door_index() else ""))
    with open(preview, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote %s" % preview)
    print("chambers: %d (sizes %s)"
          % (len(texts), [len(t) for t in texts]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
