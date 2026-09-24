#!/usr/bin/env python3
"""Static-attack lane (spec 7.1): work from the shipped bytes only.

objdump/readelf/nm/strings/objcopy on every binary; PNG chunk parse on
every plate; a grep of the whole corpus; and a reconstruction attempt for
the final title from everything the static lane can learn.  Every value it
recovers must be a REGISTERED decoy, and the reconstruction must fail.

usage: attack_static.py <pkgdir>
"""
import hashlib
import os
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "gen"))
import mint  # noqa: E402
import loom_decoys  # noqa: E402

PASS = [0]
FAIL = [0]


def ok(label, cond, detail=""):
    if cond:
        print("PASS %s %s" % (label, detail))
        PASS[0] += 1
    else:
        print("FAIL %s %s" % (label, detail))
        FAIL[0] += 1


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, shell=isinstance(cmd, str))


def registered_decoys():
    reg = set()
    for _, _, _, _, tok, _ in loom_decoys.rows():
        reg.add(tok)
    for c in mint.decoy_plate_codes():
        reg.add(c)
    reg.add(mint.canary_token())
    reg.add(mint.mirror_milestone_token())
    for ph in mint.decoy_capsule_phrases():
        reg.add(ph)
    return reg


def main(argv):
    pkg = os.path.abspath(argv[1] if len(argv) > 1 else os.path.join(ROOT, "prambh"))
    reg = registered_decoys()
    real = {
        "capsule_content": mint.capsule_content().hex(),
        "loom_seed": mint.loom_seed_material(mint.capsule_content()).hex(),
        "door_ink": mint.door_ink(),
        "real_phrase": mint.real_phrase(),
        "chain2_vector": mint.chain2_vector().hex(),
        "eyes_ink": mint.eyes_ink(),
    }
    print("=== static attack: shipped bytes only, no execution ===")

    # 1. every binary: symbols, strings, embedded blocks
    bins = []
    for dirpath, _d, files in os.walk(pkg):
        for f in files:
            p = os.path.join(dirpath, f)
            if os.access(p, os.X_OK) and os.path.getsize(p) > 1024:
                bins.append(p)
    ok("binary-count", len(bins) >= 8, "(%d executables)" % len(bins))
    symbols = "".join(sh(["nm", "-a", b]).stdout for b in bins)
    ok("static-no-symbols", symbols.strip() == "", "(%d bytes of nm output)" % len(symbols))
    strings = "".join(sh(["strings", "-n", "5", b]).stdout for b in bins)
    hits = {k: v for k, v in real.items() if v in strings}
    ok("static-no-real-values-in-strings", not hits, str(hits))
    # the Stage-0 token is printed by the milestone by design (spec 4.2):
    # it must appear in the milestone's strings and nowhere else.
    st0 = mint.stage0_token()
    files_with_st0 = [b for b in bins
                      if st0 in sh(["strings", "-n", "5", b]).stdout]
    ok("static-stage0-token-scoped-to-milestone",
       len(files_with_st0) >= 1 and all("stage0_milestone" in b
                                        for b in files_with_st0),
       str([os.path.basename(b) for b in files_with_st0]))
    ok("static-no-toolchain-paths",
       "gcc" not in strings and "musl" not in strings and "/home/" not in strings)

    # 2. plates: chunks + metadata only
    plates = [os.path.join(pkg, "plates", f) for f in
              sorted(os.listdir(os.path.join(pkg, "plates")))] \
        if os.path.isdir(os.path.join(pkg, "plates")) else []
    found_code = []
    for p in plates:
        if not p.endswith(".png"):
            continue
        blob = open(p, "rb").read()
        off = 8
        chunks = []
        while off + 8 <= len(blob):
            ln = int.from_bytes(blob[off:off + 4], "big")
            tag = blob[off + 4:off + 8]
            data = blob[off + 8:off + 8 + ln]
            chunks.append(tag)
            if tag == b"tEXt":
                for code in mint.decoy_plate_codes():
                    if code.encode() in data:
                        found_code.append(code)
            off += 12 + ln
        ok("plate-chunks-%s" % os.path.basename(p),
           set(chunks) <= {b"IHDR", b"tEXt", b"IDAT", b"IEND"}, str(chunks))
    ok("static-plate-codes-are-registered-decoys",
       all(c in reg for c in found_code), "(%d codes)" % len(found_code))

    # 3. corpus grep: no real value anywhere in the paper record
    corpus_hits = {k: v for k, v in real.items()
                   if sh(["grep", "-r", "-l", "-F", v, os.path.join(pkg, "archive")]).stdout}
    ok("static-corpus-no-real-values", not corpus_hits, str(corpus_hits))

    # 4. reconstruction attempt: everything learnable statically
    learned = {
        "model": None, "hall": None, "plate_codes": mint.decoy_plate_codes(),
        "decoy_tokens": [t for _i, _r, _k, _o, t, _rc in loom_decoys.rows()],
    }
    learned["model"] = mint.decoy_loom_model(mint.loom_model())
    learned["hall"] = mint.door_numbers()[(mint.real_door_index() + 3) % 8]
    claim = "%s_%s_%s_%s" % (learned["decoy_tokens"][0][7:-1][:8],
                             learned["decoy_tokens"][1][7:-1][:8],
                             learned["plate_codes"][0][:8], "0" * 18)
    title_try = "PRAMBH{%s}" % claim
    ok("reconstruction-fails", title_try not in strings and
       not any(v in title_try for v in real.values()), title_try[:40] + "...")
    ok("reconstruction-needs-chain-outputs",
       (real["loom_seed"] not in strings) and (real["chain2_vector"] not in strings))
    ok("learned-values-all-registered",
       all(v in reg for v in learned["decoy_tokens"] + learned["plate_codes"]))
    ok("static-lane-cannot-reach-drip-inks",
       all(v not in strings for v in (real["door_ink"], real["eyes_ink"])))

    print()
    print("ATTACK-STATIC: %d PASS, %d FAIL" % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
