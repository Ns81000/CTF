#!/usr/bin/env python3
"""Write organizer-private/KEYS_PRAMBH.md: seed -> value -> location.

Grows phase by phase; currently the Stage-0 / capsule rows (P3).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import mint
import loom_decoys

LOOM_DECOYS = loom_decoys.rows()

rows = [
    ("label / seed", "value", "location"),
    ("---", "---", "---"),
    ('SHA256("prambh:archive:root:v3")', mint.ROOT.hex(),
     "derivation root (public, deterministic)"),
    ('SHA256("prambh:stage0:token:v1")', mint.stage0_token(),
     "stage0_milestone/milestone (.rodata), printed every run"),
    ('SHA256("prambh:canary:token:v1")', mint.canary_token(),
     "HUMAN_OPERATOR_NOTICE.txt, usage screens, PNG Notice chunks"),
    ('SHA256("prambh:launch:phrase:v1") -> 6 words', mint.launch_phrase(),
     "LAUNCH.txt (package root, ARCHIVE mode)"),
    ('SHA256("prambh:capsule:content:v1")', mint.capsule_content().hex(),
     "nowhere in the clear; = capsule.bin XOR SHA256ctr(SHA256(phrase))"),
    ("capsule.bin", mint.capsule_bin().hex(),
     "capsule.bin (package root)"),
    ('SHA256("prambh:loom:seed:v1" || capsule_content)',
     mint.loom_seed_material(mint.capsule_content()).hex(),
     "nowhere; derived by the loom from the opened capsule (chain #1 seed)"),
     ('SHA256("prambh:loom:model:v1")', mint.loom_model(),
      "needle folio %03d only (flood corpus)" % mint.needle_folios()[1]),
     ('SHA256("prambh:doors:numbers:v1") -> 8 hall numbers',
      ", ".join(str(n) for n in mint.door_numbers()),
      "door folios (P6); needle/decoy folios name one each"),
     ('SHA256("prambh:doors:real:v1") -> real hall',
      "%d (index %d of 8)" % (mint.real_door_number(), mint.real_door_index()),
      "needle folio %03d; the real chamber (P6)" % mint.needle_folios()[2]),
     ("flood needle folios",
      ", ".join("folio_%03d" % f for f in mint.needle_folios()),
      "field-notes/; order: capsule, loom, hall, mirror, plates"),
     ("flood decoy folios",
      ", ".join("folio_%03d" % f for f in mint.decoy_folios()),
      "field-notes/; contradict needles 1:1"),
     ("decoy plate codes",
      ", ".join(mint.decoy_plate_codes()),
      "plates/decoy_plate_0..5.png (rendered pixels)"),

]
# Loom decoy lanes (P5): the production values harvested in
# runs/p5_decoy_tokens.txt, registered here (spec 4.4 / 4.11).
for _k, (_rid, _rom, _key, _out, _token, _rc) in enumerate(LOOM_DECOYS):
    if _rom:
        rows.append(('SHA256("prambh:loom:decoy:v1"||LE32(%d)) -> cartridge pan'
                     % _k, loom_decoys.cart_pan(_k),
                     "%s CART window, written by gen_rom.py" % _rom))
        rows.append(('%s chain seed = SHA256("prambh:loom:seed:v1"||pan)'
                     % _rid, _key,
                     "walked by %s (harvested, runs/p5_decoy_tokens.txt)"
                     % _rom))
        rows.append(("%s field token (chain engine, production T)" % _rid,
                     _token,
                     "printed by %s; registered decoy, accepted nowhere" % _rom))
    else:
        rows.append(('SHA256("prambh:loom:debug:v1") -> diagnostic pan',
                     _key,
                     "diagnostic cartridge .rodata (the anti-debug lane)"))
        rows.append(("%s calibration token" % _rid, _token,
                     "printed by the diagnostic cartridge under a tracer; "
                     "registered decoy (independently re-derived in the P5 "
                     "suite from its pan)"))


# Mirror Room (P7): the fake campaign's registered values.
_MIR = mint.mirror_values()
rows.append(("zip seal words (SHA256(\"prambh:release:zip:v1\") "
             "-> 4 words)", mint.zip_passphrase(),
             "password for the distributed prambh.zip.enc; the room "
             "description hides it as the depot seal sentence"))
rows.append(('SHA256("prambh:mirror:token:v1") -> survey mark',
             mint.mirror_milestone_token(),
             "printed by mirror/mirror_milestone; registered decoy"))
if _MIR["a"]:
    rows.append(("mirror stage A output (own walk, 2-stage)", _MIR["a"],
                 "mirror_milestone walk; token PRAMBH{%s}" % _MIR["a"][:16]))
    rows.append(("mirror stage B output (chained)", _MIR["b"],
                 "mirror_milestone seal; token PRAMBH{%s}" % _MIR["b"][:16]))
    rows.append(("mirror dead-end title", _MIR["title"],
                 "the ONE title mirror_validate accepts (registered decoy)"))
rows.append(("real eye ink", mint.eyes_ink(), "three plates, normative order"))
rows.append(("real eye codes", ", ".join(mint.eyes_code(i) for i in range(3)),
             "plates/depth.png, hue.png, sheet_a+sheet_b.png"))
rows.append(("decoy eye codes", ", ".join(mint.decoy_eyes_code(k) for k in
                                          ("depth", "hue", "moire")),
             "carried INSIDE the same plates (second plane, luminance, "
             "reciprocal bearing)"))
rows.append(("door ink", mint.door_ink(), "the real chamber's plate fragment"))
rows.append(("real door phrase (the verse answer)", mint.real_phrase(),
             "read from riddle.bin with K_loom only"))
rows.append(("chain #2 load vector (real chamber handover)",
             mint.chain2_vector().hex(), "printed inside the real chamber"))
rows.append(("real chamber hall", "%d (index %d)" % (mint.real_door_number(),
                                                     mint.real_door_index()),
             "decoy chambers cite the other seven halls"))

path = os.path.join(ROOT, "organizer-private", "KEYS_PRAMBH.md")
with open(path, "w") as f:
    f.write("# PRAMBH v3 - KEYS (organizer-private)\n\n")
    f.write("Full seed -> value -> location table (spec 5).\n\n")
    for r in rows:
        f.write("| " + " | ".join(r) + " |\n")
print("wrote", path)
