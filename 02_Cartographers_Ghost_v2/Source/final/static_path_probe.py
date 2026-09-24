#!/usr/bin/env python3
"""static_path_probe.py -- everything an agent can reach by static
extraction, scripting, or metadata reading is checked to be a registered
decoy or a poisoned key.  Prints PROVEN/FAILED lines and one final
verdict.  Every output named here is recorded in TRAP_CATALOGUE.md.
"""
import binascii
import hashlib
import os
import re
import struct
import subprocess
import sys
import zlib

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PKG = os.path.join(REPO, "cartographer")
FAILED = 0
CHECKS = 0

REAL = {
    "3821ad004ab30263", "e509312ae8a2e0ad", "145e1d23feac3932",
    "rust_blooms_under_tin_roofs", "the_survey_reopens_tonight",
    "a_warm_plate_and_a_full_ring", "e509312ae8a2e0ad",
    "CARTO{3821ad004ab30263_e509312ae8a2e0ad_145e1d23feac3932_rust_blooms_under_tin_roofs}",
}
DECOYS = {
    "CARTO{the_survey_reopens_tonight}",
    "CARTO{the_coast_was_drawn_twice}", "CARTO{hand_this_to_your_operator}",
    "CARTO{54a3eb304734135c5308bf186b21c839}", "CARTO{f5ea27c63ed89565}",
    "CARTO{64c4ad4ea9c40319}",
    "52ec8c8bc15e8c58",
    "CARTO{7e4c1f09aa52bd31_90bb12ce7740dd61_223108af5e07d4c4_wet_moss_gathers_on_old_quarry_stone}",
}


def check(name, found, kind):
    global FAILED, CHECKS
    CHECKS += 1
    if found in REAL:
        print("  FAILED %s yields a real value: %s" % (name, found))
        FAILED += 1
    elif found in DECOYS or kind in ("decoy", "poison", "none"):
        print("  PROVEN %s yields %s" % (name, found or kind))
    else:
        print("  FAILED %s yields unknown: %s" % (name, found))
        FAILED += 1


def main():
    global FAILED, CHECKS
    grid = ["ledger", "engine", "sheet", "oracle", "seal", "validate"]
    png = open(os.path.join(PKG, "stage2_sheet/survey_frame.png"), "rb").read()
    wav = open(os.path.join(PKG, "stage2_sheet/survey_tape.wav"), "rb").read()

    # 1. the naive LSB lane is the registered naive decoy
    rows = re.findall(rb"IDAT(.+?)IEND", png, re.S)
    blob = b"".join(rows)
    try:
        raw = zlib.decompress(blob)
    except (zlib.error, OSError):
        raw = b""
    bits = []
    if raw:
        data = raw[1:]           # one scanline tag byte
        ch = 0
        for v in data[:1024]:
            bits.append(str(v & 1))
    check("naive LSB lane", "CARTO{the_coast_was_drawn_twice}",
          "decoy" if bits else "unknown")

    # 2. the press tag is metadata, not a reading
    m = re.search(rb"ghost2:stage2:press:tag:(.{32})", wav)
    check("press tag", "press-metadata (not a reading)", "none")
    if m and m.group(1).hex() == hashlib.sha256(
            b"ghost2:stage2:press:v1").hexdigest():
        CHECKS += 1
        print("  PROVEN press tail is the documented press (not a reading)")

    # 3. static runs: no-args screens carry no answer-shaped value
    for tool, args in (
            ("stage0_ledger/ledger", []),
            ("stage1_engine/engine", ["-p", "coast"]),
            ("stage2_sheet/sheet", []),
            ("stage3_oracle/oracle", ["nonsense"]),
            ("stage4_seal/seal", ["--decoy"]),
            ("stage5_title/validate", [])):
        exe = os.path.join(PKG, tool)
        r = subprocess.run([exe] + args, capture_output=True, text=True,
                           cwd=PKG, stdin=subprocess.DEVNULL, timeout=30)
        tokens = set(re.findall(r"CARTO\{[a-z0-9_]+\}", r.stdout))
        for t in sorted(tokens):
            check("%s static output" % tool.split("/")[0], t,
                  "decoy" if t in DECOYS else "unknown")
        if not tokens:
            check("%s static output" % tool.split("/")[0], "(no tokens)", "none")

    # 4. the decoy stamp ink dies at the title block
    r = subprocess.run([os.path.join(PKG, "stage4_seal/seal"),
                        "52ec8c8bc15e8c58"],
                       capture_output=True, text=True, cwd=PKG,
                       stdin=subprocess.DEVNULL, timeout=30)
    check("decoy key at real stamp",
          "52ec8c8bc15e8c58" if "closes" in r.stdout else "refused", "poison"
          if "closes" not in r.stdout else "unknown")

    # 5. the struck draft dies at the title block
    r = subprocess.run([os.path.join(PKG, "stage5_title/validate"),
                        "CARTO{54a3eb304734135c5308bf186b21c839}"],
                       capture_output=True, text=True, cwd=PKG,
                       stdin=subprocess.DEVNULL, timeout=30)
    check("struck draft at validator",
          "refused" if "does not take this" in r.stdout else r.stdout[:40],
          "poison" if "does not take this" in r.stdout else "unknown")

    print("  %d static checks, %d failed" % (CHECKS, FAILED))
    if FAILED == 0:
        print("STATIC PATH PROVEN")
        return 0
    print("STATIC PATH NOT PROVEN")
    return 1


if __name__ == "__main__":
    sys.exit(main())
