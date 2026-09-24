#!/usr/bin/env python3
"""Write organizer-private/TRAP_CATALOGUE.md (spec 5).

Grows phase by phase; covers the canary, the capsule wrong-phrase lanes,
the flood decoy folios, the decoy plates (P3/P4) and the loom decoy
cartridges + diagnostic lane (P5).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import mint
import loom_decoys

out = []
out.append("# PRAMBH v3 - TRAP CATALOGUE (organizer-private)\n")
out.append("Every decoy/bait value, where it lives, and what it costs.\n")

out.append("\n## Canary\n")
out.append("- CANARY-1: `%s` - printed in HUMAN_OPERATOR_NOTICE.txt, on every "
         "tool usage screen, and in PNG Notice chunks. Planted to trace "
         "AI-solver writeups. Never accepted anywhere; not the final "
         "title's shape.\n" % mint.canary_token())

out.append("\n## Capsule wrong-phrase lanes (Stage 0 -> Mirror Room)\n")
out.append("Real launch phrase: `%s` (ships in LAUNCH.txt, ARCHIVE mode).\n"
           % mint.launch_phrase())
out.append("Real load vector: `%s`\n" % mint.capsule_content().hex())
for i, p in enumerate(mint.decoy_capsule_phrases(), 1):
    dv = mint.capsule_open(p)
    out.append("- D-CAP-%d: phrase `%s` -> load vector `%s` -> loom walks "
               "it, output mismatches the loom verifier, routes to the "
               "Mirror Room campaign (P5/P7).\n" % (i, p, dv.hex()))
out.append("- D-CAP-U: any other phrase yields an unregistered but "
           "format-valid load vector; it fails the loom verifier and "
           "routes to the Mirror Room like the designed lanes.\n")

out.append("\n## Flood corpus decoy folios (P4)\n")
out.append("Needle folios (stitched originals): %s\n"
           % ", ".join("folio_%03d" % f for f in mint.needle_folios()))
for i, f in enumerate(mint.decoy_folios()):
    out.append("- D-FLOOD-%d: folio_%03d - format-valid decoy, contradicts "
               "needle #%d; feeds wrong loom model / wrong hall number / "
               "wrong plate method to skimmers.\n" % (i + 1, f, i))
out.append("- D-FLOOD-L: every flood lane (any token, 8 pages) is plausible "
           "generated chaff; wrong tokens are indistinguishable in form.\n")

out.append("\n## Decoy survey plates (P4)\n")
for k, c in enumerate(mint.decoy_plate_codes()):
    out.append("- D-PLATE-%d: plates/decoy_plate_%d.png, code `%s` - "
               "format-valid eye-plate decoy; the stage-4 validator must "
               "treat it as an ordinary wrong answer.\n" % (k + 1, k, c))

# ---- Loom decoy cartridges + diagnostic lane (P5, spec 4.4) ------------
out.append("\n## Loom decoy cartridges + the diagnostic lane (P5 - spec 4.4)\n")
out.append("Registry source: `organizer-private/runs/p5_decoy_tokens.txt` "
           "(harvested once against the production parameters; never "
           "recomputed).  All four lanes print in the same teleprinter voice "
           "as the real cartridge, lodge a claim of the same shape, and exit "
           "clean; nothing in the package labels them.\n")

_params = json.load(open(os.path.join(ROOT, "src", "chain", "chain_params.json")))
_dT = _params["budgets"]["decoy_rom"]["T"]
try:
    _proj = json.load(open(os.path.join(ROOT, "organizer-private", "runs",
                                        "p5_projection.json")))
except (IOError, ValueError):
    _proj = None


def _costs(T):
    if not _proj:
        return ("wasted cost: PROJECTED - see runs/p5_projection.txt "
                "(reduced-T wall-clock projection)")
    nat = T * _proj["native_step_ns"] / 1e9
    emu = T * _proj["emu_step_ns"] / 1e9
    return ("wasted cost (PROJECTED - audit must confirm with the full REAL "
            "run): %.0f s (%.0f min) under the shipped emulator, %.0f s "
            "(%.0f min) for a native re-implementation"
            % (emu, emu / 60.0, nat, nat / 60.0))


for _rid, _rom, _key, _out, _token, _rc in loom_decoys.rows():
    _lane = loom_decoys.LANE_NAME.get(_rid, "?")
    if _rom:
        _k = int(_rid.rsplit("-", 1)[1]) - 1
        _trig = ("running the cartridge (`./loom run %s` / `./loom claim "
                 "%s`) or any all-ROM sweep of the instrument collection"
                 % (_rom, _rom))
        _ddl = ("the token is accepted nowhere - no chamber, no eye-plate, no "
                "validator, no server record - and it contradicts a needle "
                "folio 1:1 (D-FLOOD-1..5)")
        _rec = ("the needle folio names the one program cartridge (the survey "
                "stitch cartridge) and the datasheet's valley-vs-coast tell "
                "separates MERU from MERC")
        _cost = _costs(_dT)
        _head = "- %s (%s), `%s`\n" % (_rid, _lane, _rom)
        _keys = ("  - cartridge pan (mint-derived, CART window): `%s`\n"
                 "  - chain seed (harvested): `%s`\n"
                 % (loom_decoys.cart_pan(_k), _key))
    else:
        _trig = ("a ptrace-based tracer or debugger (gdb, strace, ltrace) - "
                 "TracerPid in /proc/self/status, with a PTRACE_TRACEME/EPERM "
                 "fallback")
        _ddl = ("the calibration token is accepted nowhere; the diagnostic "
                "cartridge lodges no chain claim and touches no state, so a "
                "solver who trusts it holds a plausible dead end and no error")
        _rec = ("the lane's own wording ('not a survey record') plus the "
                "missing claim: the real cartridge lodges one")
        _cost = "wasted cost: 0 (one SHA mixer pass, no chain)"
        _head = "- %s (%s), embedded cartridge\n" % (_rid, _lane)
        _keys = "  - cartridge pan (mint-derived, .rodata): `%s`\n" % _key
    out.append(_head)
    out.append(_keys)
    out.append("  - token: `%s`\n" % _token)
    out.append("  - trigger: %s\n" % _trig)
    out.append("  - dead end: %s\n" % _ddl)
    out.append("  - recovery (documented observation): %s\n" % _rec)
    out.append("  - fairness: same build recipe, same size class and same "
               "output framing as the real cartridge; registered here before "
               "the package was built\n")
    out.append("  - %s\n" % _cost)


# ---- Mirror Room / Duplicate Survey (P7, spec 4.6) ---------------------
out.append("\n## Mirror Room - the Duplicate Survey (P7 - spec 4.6)\n")
_mc = os.path.join(ROOT, "organizer-private", "runs", "mirror_chain.txt")
_mvals = {}
if os.path.exists(_mc):
    for _line in open(_mc):
        if _line.startswith("stage A out"):
            _mvals["a"] = _line.split("=")[1].split()[0].strip()
        elif _line.startswith("stage B out"):
            _mvals["b"] = _line.split("=")[1].split()[0].strip()
        elif _line.startswith("dead-end title"):
            _mvals["title"] = _line.split("=")[1].strip()
out.append("A complete fake campaign: its own marker, its own two-stage walk,")
out.append("its own fiction dated 1981, and its own desk that files exactly one")
out.append("title and says nothing else.  Reachable from wrong capsule phrases")
out.append("(D-CAP-*), the decoy cartridges (D-ROM-*), and four of the seven decoy")
out.append("chambers; it is fully solvable to its dead end by design.\n")
out.append("- D-MIRROR-MARK: `%s` - the campaign's milestone mark.  Registered "
           "decoy; the real tools never acknowledge it.\n" % mint.mirror_milestone_token())
if _mvals:
    out.append("- D-MIRROR-STAGE-A: stage A output `%s` (token `PRAMBH{%s}`) - "
               "the campaign's first stitch.\n" % (_mvals["a"], _mvals["a"][:16]))
    out.append("- D-MIRROR-STAGE-B: stage B output `%s` (token `PRAMBH{%s}`) - "
               "chained from stage A.\n" % (_mvals["b"], _mvals["b"][:16]))
    out.append("- D-MIRROR-TITLE: `%s` - the ONE title `mirror_validate` accepts. "
               "Registered decoy; the real validator refuses it byte-identically "
               "to any other wrong answer.\n" % _mvals.get("title", ""))
out.append("  - trigger: a wrong launch phrase, a decoy cartridge, or a decoy "
           "chamber's pointer ('the duplicate survey is filed at the valley "
           "depot').\n")
out.append("  - dead end: `mirror_validate` prints 'the duplicate survey is "
           "filed.' and nothing else; no real tool ever accepts a mirror "
           "token.\n")
out.append("  - recovery (documented observation): the Duplicate Survey is "
           "dated 1981 while the valley-issue machine is 1983 (its own "
           "datasheet, document 83-MS-117); the mirror corpus cites plate ids "
           "that do not exist in plates/; mirror tools never touch the real "
           "survey record.\n")
out.append("  - fairness: the whole campaign is internally consistent and "
           "solvable; the tells are discoverable, never labelled.\n")
out.append("  - wasted cost (PROJECTED): two mirror walks of %d s each at the "
           "mirror budget, plus the reading and the filing.\n"
           % _params["budgets"]["mirror"]["honest_target_seconds"])
out.append("  - NOTE (deviation, recorded): spec 4.6 says the Duplicate Survey's "
           "dates contradict the epoch printed by `milestone`; `milestone` "
           "prints no date, so the contradiction is carried against the "
           "datasheet's 1983 valley issue instead.  Raised for the audit.\n")


path = os.path.join(ROOT, "organizer-private", "TRAP_CATALOGUE.md")
with open(path, "w") as f:
    f.write("\n".join(out))
print("wrote", path)
