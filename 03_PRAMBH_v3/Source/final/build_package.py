#!/usr/bin/env python3
"""Assemble the player package (spec 4.x) - organizer-side.

  <pkg>/README_FOR_SOLVER.txt      how to unpack and start (no mechanism
                                   words, no stage counts, no lengths)
  <pkg>/HUMAN_OPERATOR_NOTICE.txt  the operator notice + canary
  <pkg>/LAUNCH.txt                 the launch sheet (ARCHIVE mode only)
  <pkg>/capsule.bin                the launch capsule
  <pkg>/stage0_milestone/milestone
  <pkg>/stage1_flood/flood
  <pkg>/archive/                   the flood corpus (generated)
  <pkg>/field-notes/               the needle folios + the loom datasheet
  <pkg>/plates/                    carrier plate, decoy plates, eye plates
  <pkg>/stage2_loom/loom, loom.rom, roms/*.rom
  <pkg>/stage3_doors/doors, doors.bin, riddle.bin
  <pkg>/mirror/                    the Duplicate Survey (tools + fiction)
  <pkg>/stage5_eyes/eyes, validate, eyes_notes.bin

Chain-derived files are taken from organizer-private/runs/ (harvested).

usage: build_package.py <pkgdir>
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "gen"))
import mint  # noqa: E402

RUNS = os.path.join(ROOT, "organizer-private", "runs")
CC = "musl-gcc"
CF = ["-O2", "-static", "-s", "-Wall", "-Wextra", "-std=gnu11", "-D_GNU_SOURCE"]
READ_ME = """PRAMBH - the first survey
=======================

This station is a set of field instruments and the surveyor's notes.
Nothing here talks to a network; nothing needs installing.

  ./stage0_milestone/milestone      start here
  ./field-notes/                    the first surveyor's notes
  ./archive/                        the survey's paper record
  ./plates/                         the plates the depot shipped

Run the instruments from this folder; they keep their working record
here.  Read every sheet before you decide it is quiet.
"""


def run(args, env=None):
    p = subprocess.run(args, capture_output=True, text=True, env=env,
                       cwd=ROOT)
    if p.returncode != 0:
        raise SystemExit("build_package: %s failed rc=%d\n%s"
                         % (" ".join(args), p.returncode, p.stderr[-800:]))
    return p


def compile_tool(pkg, outdir, binary, sources, extra=()):
    d = os.path.join(pkg, outdir)
    os.makedirs(d, exist_ok=True)
    run([CC] + CF + ["-o", os.path.join(d, binary)] + sources + list(extra))


def main(argv):
    if len(argv) != 2:
        sys.stderr.write(__doc__)
        return 2
    pkg = os.path.abspath(argv[1])
    for sub in ("stage0_milestone", "stage1_flood", "stage2_loom", "stage3_doors",
                "stage5_eyes", "mirror", "archive", "field-notes", "plates"):
        os.makedirs(os.path.join(pkg, sub), exist_ok=True)

    # --- generators ---------------------------------------------------
    run([sys.executable, "src/flood/corpus_gen.py", os.path.join(pkg, "archive")])
    run([sys.executable, "src/plates/plate_gen.py", os.path.join(pkg, "plates")])
    run([sys.executable, "src/eyes/plate_gen.py", pkg])
    run([sys.executable, "src/loom/gen_rom.py", os.path.join(pkg, "stage2_loom")])
    run([sys.executable, "src/loom/gen_datasheet.py",
         os.path.join(pkg, "field-notes", "meru1_datasheet.txt")])
    run([sys.executable, "src/doors/gen_consts.py"])
    run([sys.executable, "src/gen/gen_canary.py"])
    run([sys.executable, "src/plates/carrier_gen.py", os.path.join(pkg, "plates")])
    # chain-derived artefacts (harvested from organizer-private/runs/).
    # Each one is skipped with a warning when its chain walk has not been
    # harvested yet, so the package can be assembled in two passes.
    for script, need in (("src/doors/doors_build.py", "chain1"),
                         ("src/eyes/gen_eyes.py", "chain2"),
                         ("src/mirror/gen_mirror.py", "mirror")):
        try:
            run([sys.executable, script, pkg])
        except SystemExit as e:
            print("NOTE %s skipped (%s chain not harvested yet): %s"
                  % (script, need, str(e).splitlines()[0][:120]))

    # --- text artefacts ----------------------------------------------
    with open(os.path.join(pkg, "README_FOR_SOLVER.txt"), "w") as f:
        f.write(READ_ME)
    with open(os.path.join(pkg, "HUMAN_OPERATOR_NOTICE.txt"), "w") as f:
        f.write("PRAMBH - operator notice\n\n"
                "PRAMBH is a survey, not a service. Its instruments record but "
                "never confirm:\nno output here will tell you whether anything "
                "worked, and nothing will\nobject when it did not. The only "
                "proof of the whole journey is the final\ntitle. Take notes. "
                "Trust timestamps, not moods.\n\n"
                "station canary: %s\n" % mint.canary_token())
    with open(os.path.join(pkg, "LAUNCH.txt"), "w") as f:
        f.write(mint.launch_phrase() + "\n")
    with open(os.path.join(pkg, "capsule.bin"), "wb") as f:
        f.write(mint.capsule_bin())

    # --- field-notes: the needle folios, copied out of the corpus -----
    for folio in mint.needle_folios():
        src = os.path.join(pkg, "archive", "folio_%03d.txt" % folio)
        shutil.copyfile(src, os.path.join(pkg, "field-notes",
                                          "folio_%03d.txt" % folio))

    # --- tools --------------------------------------------------------
    core = ["src/core/carto_sha256.c", "src/core/sha256ctr.c"]
    st = "src/state/state.c"
    chn = "src/chain/chain.c"
    compile_tool(pkg, "stage0_milestone", "milestone", ["src/stage0/milestone.c"],
                 core + [st])
    compile_tool(pkg, "stage1_flood", "flood", ["src/flood/flood.c"], core)
    compile_tool(pkg, "stage2_loom", "loom",
                 ["src/loom/loom.c", "src/loom/meru1.c", chn], core)
    compile_tool(pkg, "stage3_doors", "doors", ["src/doors/doors.c"],
                 core + [st])
    compile_tool(pkg, "mirror", "mirror_milestone",
                 ["src/mirror/mirror_milestone.c", chn], core)
    compile_tool(pkg, "mirror", "mirror_validate",
                 ["src/mirror/mirror_validate.c"], core)
    compile_tool(pkg, "stage5_eyes", "eyes", ["src/eyes/eyes.c", chn],
                 core + [st])
    compile_tool(pkg, "stage5_eyes", "validate", ["src/eyes/validate.c"],
                 core + [st])
    print("package built at %s" % pkg)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
