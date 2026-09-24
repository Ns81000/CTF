#!/usr/bin/env python3
"""Write the organizer docs from real numbers (spec 5 / 10).

  organizer-private/COST_MODEL.md
  organizer-private/HINTS.md
  organizer-private/TRYHACKME_ROOM_TEXT.md
  organizer-private/SOLVE_PATH_PRIVATE.md

Everything is derived from the mint and the harvested runs, so the docs
cannot drift from the package.  SESSION_1_LOG.md and HANDOFF.md are
written separately (they need the final git state).

usage: docs_gen.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src", "doors"))
import mint  # noqa: E402
import verse_gen  # noqa: E402

RUNS = os.path.join(ROOT, "organizer-private", "runs")
ORG = os.path.join(ROOT, "organizer-private")
PARAMS = json.load(open(os.path.join(ROOT, "src", "chain", "chain_params.json")))


def proj():
    try:
        return json.load(open(os.path.join(RUNS, "p5_projection.json")))
    except (IOError, ValueError):
        return {}


def chain_out(*names):
    for n in names:
        p = os.path.join(RUNS, n)
        if os.path.exists(p):
            for line in open(p):
                if line.startswith("out="):
                    return line.split("=", 1)[1].strip()
    return ""


def write(name, lines):
    with open(os.path.join(ORG, name), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote %s (%d lines)" % (name, len(lines)))


def cost_model():
    pj = proj()
    lines = ["# PRAMBH v3 - COST MODEL (organizer-private, spec 5)", "",
             "Every wall-clock number is PROJECTED from reduced-T measurement",
             "(Appendix C.2); the audit session owns the full REAL runs (X6).",
             "", "## chain dials (src/chain/chain_params.json)", "",
             "| chain | S (bytes) | T (steps) | honest target (s) |",
             "| --- | --- | --- | --- |"]
    for name, b in PARAMS["budgets"].items():
        lines.append("| %s | %d | %d | %d |"
                     % (name, PARAMS["table_bytes"], b["T"],
                        b["honest_target_seconds"]))
    lines += ["",
              "build-machine rate: %.1f steps/s at S=%d (P2 calibration)"
              % (PARAMS["r_build_steps_per_sec"], PARAMS["table_bytes"]), "",
              "## measured per-step cost (reduced T)", "",
              "- native %.1f ns/step = cache-resident %.1f ns + DRAM %.1f ns"
              % (pj.get("native_step_ns", 0), pj.get("cache_step_ns", 0),
                 pj.get("dram_ns", 0)),
              "- emulated cartridge %.1f ns/step (the camouflage route)"
              % pj.get("emu_step_ns", 0),
              "- linearity deviation across T: %.1f%% (cost per step is constant,"
              " so T x per-step projects soundly)"
              % (pj.get("linearity_deviation", 0) * 100), "",
              "## projection math", "",
              "  native chain #1   = %.1f ns x %d = %.0f s (%.1f min)"
              % (pj.get("native_step_ns", 0), PARAMS["budgets"]["chain1"]["T"],
                 pj.get("native_prod_s", 0), pj.get("native_prod_s", 0) / 60),
              "  emulated chain #1 = %.1f ns x %d = %.0f s (%.1f h)"
              % (pj.get("emu_step_ns", 0), PARAMS["budgets"]["chain1"]["T"],
                 pj.get("emu_prod_s", 0), pj.get("emu_prod_s", 0) / 3600),
              "",
              "Honest ARCHIVE path: chain #1 + chain #2 = %.1f h of sequenced work,"
              % (2 * pj.get("native_prod_s", 0) / 3600),
              "plus the seven 12-min decoy chamber walks a wrong reading invites,",
              "plus the plate gates and the paper record.  A 4x faster core buys",
              "about %.1fx rather than 4x, because %.0f of %.0f ns per step is a"
              % ((pj.get("native_prod_s", 0) / pj["attacker_4x_s"])
                 if pj.get("attacker_4x_s") else 0, pj.get("dram_ns", 0),
                 pj.get("native_step_ns", 0)),
              "DRAM round-trip: the walk is one sequential SHA-256 dependency",
              "chain and nothing in it parallelises.  EVENT mode adds the",
              "server's 4 h MIN_JOURNEY gate as a backstop, never as the floor.",
              "",
              "NOT proven in this session (audit, Appendix C.2a): the full REAL-T",
              "native walk, the full REAL-T emulated cartridge run, and the",
              "reduced-table attack at production T.", ""]
    write("COST_MODEL.md", lines)


def solve_path():
    c1 = chain_out("chain1_walk.txt", "p5_chain1_raw.txt")
    c2 = chain_out("chain2_walk.txt")
    title = mint.final_title(bytes.fromhex(c2), bytes.fromhex(c1)) \
        if c2 and c1 else "(chain outputs pending)"
    lines = ["# PRAMBH v3 - SOLVE PATH (organizer-private, spec 5)", "",
             "The honest walk, step by step:", "",
             "1. `stage0_milestone/milestone` prints the scored Stage-0 token and",
             "   points at `field-notes/`.  The needle folios (%s)"
             % ", ".join("folio_%03d" % f for f in mint.needle_folios()),
             "   carry the real information; the decoy folios contradict them 1:1",
             "   (trap catalogue D-FLOOD-1..5).",
             "2. Needle #0: the launch sheet is the full six-word phrase; only the",
             "   full phrase opens the capsule (`milestone open <phrase>`).",
             "3. Needle #1 names the model (%s, valley issue, badge III) and points"
             % mint.loom_model(),
             "   at `field-notes/meru1_datasheet.txt`, whose cartridge section names",
             "   the one program of record.  The carrier plate repeats the model as",
             "   pixels only.",
             "4. `stage2_loom/loom claim loom.rom --vector <capsule vector>` walks",
             "   chain #1; the printed claim IS K_loom.  Its first eight bytes are",
             "   the loom ink, the next eight the checkpoint token.",
             "5. `stage3_doors/doors riddle <K_loom>` opens `riddle.bin` and prints",
             "   the verse.  The verse itself says to take the word each mark comes",
             "   to rest on: the six words are the door word.",
             "6. `doors open <the six words>` prints the real chamber: the hall ink",
             "   (door ink) and the load vector for the seal.",
             "7. `stage5_eyes/eyes seal <load vector>` walks chain #2 (same table,",
             "   same wait) and prints the viewing notes.",
             "8. Read the plates per the notes: depth plate nearest plane = %s,"
             % mint.eyes_code(0),
             "   hue plate in hue not luminance = %s, line screens at the survey"
             % mint.eyes_code(1),
             "   bearing = %s." % mint.eyes_code(2),
             "9. Assemble PRAMBH{seal_ink_loom_ink_door_ink_eyes_ink} and file it",
             "   with `stage5_eyes/validate`.", "",
             "loom ink %s | door ink %s | eyes ink %s | seal ink %s"
             % (c1[:16] if c1 else "-", mint.door_ink(), mint.eyes_ink(),
                mint.seal_ink(bytes.fromhex(c2)) if c2 else "-"),
             "FINAL TITLE: %s" % title, "",
             "Verse (generated by src/doors/verse_gen.py):", ""]
    lines += ["  " + ln for ln in verse_gen.verse_text().splitlines()]
    lines += ["", "The eight designed readings:"]
    for k in range(8):
        lines.append("  %d %-52s %s%s"
                     % (k, verse_gen.LABELS[k], mint.door_phrase(k),
                        "   <== REAL" if k == mint.real_door_index() else ""))
    write("SOLVE_PATH_PRIVATE.md", lines)


def hints():
    write("HINTS.md", [
        "# PRAMBH v3 - graduated hints (organizer-private)", "",
        "H1. Start at the milestone; it names the notes folder.",
        "H2. The notes folder holds five stitched folios and one datasheet.",
        "H3. Only the full six-word sheet opens the capsule.",
        "H4. The datasheet's cartridge section names the one program of record.",
        "H5. The loom's claim is the key the riddle wants.",
        "H6. The verse says how to read itself; read it literally.",
        "H7. The real chamber hands over an ink and a load vector.",
        "H8. The seal wants the same table as the loom, and the same wait.",
        "H9. The viewing notes order the planes; the plates do not.",
        "H10. Assemble the four inks in the order the record names them.",
        "",
        "Hand out one at a time, oldest first.", ""])


def room_text():
    write("TRYHACKME_ROOM_TEXT.md", [
        "# PRAMBH - TryHackMe room text (organizer-private)", "",
        "## ARCHIVE mode", "",
        "PRAMBH - the first survey", "",
        "Before the Ghost's survey there was the First Survey, and its zero",
        "milestone was never found.  The station is a set of period field",
        "instruments, a paper archive and a set of plates.  Nothing here",
        "confirms anything: the instruments record, they never answer.  The only",
        "proof of the journey is the assembled title.", "",
        "Download the package, unpack it and start at the milestone.  Two",
        "answers are scored: the zero milestone mark and the final title.", "",
        "## EVENT mode", "",
        "Register with the organizer to receive your own package; the room",
        "publishes the launch sheet when the event opens.  File checkpoints",
        "with the desk as you go; the proof-of-journey flag is issued when your",
        "own title is filed after the journey floor.", "",
        "### launch sheet (published at event start in EVENT mode)", "",
        "`%s`" % mint.launch_phrase(), ""])


def main():
    cost_model()
    solve_path()
    hints()
    room_text()
    return 0


if __name__ == "__main__":
    sys.exit(main())

    write("COST_MODEL.md", lines)
