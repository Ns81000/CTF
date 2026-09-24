#!/usr/bin/env python3
"""EVENT-mode per-player package generator (spec 3) - organizer-side.

  seed = SHA-256(master_secret || "prambh:player:v1" || callsign)

mixes into every derivation of the package (mint.set_player_context), so
the whole package - keys, inks, decoys, door permutation, chambers,
plates, glyph codes, corpus needles, chain seeds - is regenerated per
player.  ARCHIVE mode (no context) is bit-identical to the archived
package; this generator is what EVENT mode adds.

The chain steps are the real ones at production dials; --reduced-t shrinks
them for tests only (the values are then marked reduced and the per-player
production title must be produced by the real run at event start).

usage: player_gen.py --callsign NAME --out DIR [--master-secret-hex HEX]
                     [--reduced-t FACTOR] [--no-chains]
"""
import hashlib
import json
import os
import struct
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import mint  # noqa: E402

PARAMS = json.load(open(os.path.join(ROOT, "src", "chain", "chain_params.json")))
S = PARAMS["table_bytes"]
CHAIN = os.path.join(ROOT, "src", "chain", "prambh_chain")


def walk(seed_hex, t):
    p = subprocess.run([CHAIN, "walk", "--seed-hex", seed_hex, "--s", str(S),
                        "--t", str(t)], capture_output=True, text=True)
    if p.returncode != 0 or len(p.stdout.strip()) != 64:
        raise SystemExit("player_gen: walk failed: " + p.stderr[:200])
    return p.stdout.strip()


def gen(script, args, env):
    p = subprocess.run([sys.executable, os.path.join(ROOT, script)] + args,
                       capture_output=True, text=True, env=env)
    return p


def compile_tool(env, pkg, src, out, extra=()):
    """Compile one player-side tool with the player's in-tree headers."""
    sub = os.path.join(pkg, out[0])
    os.makedirs(sub, exist_ok=True)
    cmd = ["musl-gcc", "-O2", "-static", "-s", "-std=gnu11", "-D_GNU_SOURCE",
           "-o", os.path.join(sub, os.path.basename(out[1]))] + list(extra) \
        + [os.path.join(ROOT, src)]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return p.returncode


def restore_archive_headers(env):
    """Put the ARCHIVE-mode generated headers back after a player build."""
    for script in ("src/stage0/gen_consts.py", "src/doors/gen_consts.py",
                   "src/gen/gen_canary.py"):
        subprocess.run([sys.executable, os.path.join(ROOT, script)],
                       capture_output=True, text=True, env=env)
    # debug_rom.h / params.h carry the minted pan: regenerate them from the
    # ARCHIVE mint into a throwaway dir so the player package's ROMs are
    # never touched by the restore.
    tmp = tempfile.mkdtemp(prefix="archrom.")
    subprocess.run([sys.executable, os.path.join(ROOT, "src/loom/gen_rom.py"),
                    tmp], env=env, capture_output=True, text=True)
    shutil.rmtree(tmp, ignore_errors=True)


def main(argv):
    callsign = None
    out = None
    secret = b"prambh-dev-master-secret"
    factor = 1
    no_chains = False
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--callsign":
            callsign = argv[i + 1]; i += 2
        elif a == "--out":
            out = argv[i + 1]; i += 2
        elif a == "--master-secret-hex":
            secret = bytes.fromhex(argv[i + 1]); i += 2
        elif a == "--reduced-t":
            factor = int(argv[i + 1]); i += 2
        elif a == "--no-chains":
            no_chains = True; i += 1
        else:
            sys.stderr.write(__doc__)
            return 2
    if not callsign or not out:
        sys.stderr.write(__doc__)
        return 2

    ctx = mint.player_seed(secret, callsign)
    pkg = os.path.join(out, "prambh")
    os.makedirs(pkg, exist_ok=True)
    env = dict(os.environ, PRAMBH_PLAYER_HEX=ctx.hex())
    mint.set_player_context(ctx)

    steps = [
        ("src/gen/gen_canary.py", []),
        ("src/stage0/gen_consts.py", []),
        ("src/loom/gen_rom.py", [pkg]),
        ("src/doors/gen_consts.py", []),
        ("src/flood/corpus_gen.py", [pkg]),
        ("src/eyes/plate_gen.py", [pkg]),
    ]
    log = []
    for script, args in steps:
        p = gen(script, args, env)
        log.append("%-28s rc=%d %s" % (script, p.returncode,
                                       p.stdout.strip().splitlines()[-1]
                                       if p.stdout.strip() else ""))
    # per-player chains (chain #1 then chain #2), reduced for tests only
    t1 = max(1000, PARAMS["budgets"]["chain1"]["T"] // factor)
    t2 = max(1000, PARAMS["budgets"]["chain2"]["T"] // factor)
    inst = pkg
    if not no_chains:
        c1 = walk(mint.loom_seed_material(mint.capsule_content()).hex(), t1)
        log.append("chain #1 (%s) %s" % ("PRODUCTION" if factor == 1
                                         else "REDUCED x%d" % factor, c1[:32]))
        p = gen("src/doors/doors_build.py", [pkg, "--claim-hex", c1], env)
        log.append("doors_build rc=%d" % p.returncode)
        c2 = walk(mint.chain2_seed().hex(), t2)
        log.append("chain #2 (%s) %s" % ("PRODUCTION" if factor == 1
                                         else "REDUCED x%d" % factor, c2[:32]))
        p = gen("src/eyes/gen_eyes.py", [pkg], env)
        log.append("gen_eyes rc=%d" % p.returncode)
        title = mint.final_title(bytes.fromhex(c2), bytes.fromhex(c1))
        digest = mint.title_digest(title)
    else:
        title, digest = "", b"" * 32
    # the player's own launch sheet and capsule
    with open(os.path.join(pkg, "LAUNCH.txt"), "w") as f:
        f.write(mint.launch_phrase() + "\n")
    with open(os.path.join(pkg, "capsule.bin"), "wb") as f:
        f.write(mint.capsule_bin())
    log.append("capsule+launch written")

    # the player's own tools, compiled with the player's headers
    core = [os.path.join(ROOT, "src/core/carto_sha256.c"),
            os.path.join(ROOT, "src/core/sha256ctr.c")]
    st = os.path.join(ROOT, "src/state/state.c")
    chn = os.path.join(ROOT, "src/chain/chain.c")
    tools = [
        ("src/stage0/milestone.c", ("stage0_milestone", "milestone"), core + [st]),
        ("src/doors/doors.c", ("stage3_doors", "doors"), core + [st, chn]),
        ("src/eyes/eyes.c", ("stage5_eyes", "eyes"), core + [st, chn]),
        ("src/eyes/validate.c", ("stage5_eyes", "validate"), core + [st]),
    ]
    for src, tdir, extra in tools:
        rc = compile_tool(env, pkg, src, tdir, extra)
        log.append("compile %-22s rc=%d" % (tdir[1], rc))
    restore_archive_headers(dict(os.environ, PRAMBH_PLAYER_HEX=""))

    answers = {
        "callsign": callsign,
        "player_context": ctx.hex(),
        "stage0_token": mint.stage0_token(),
        "final_title": title,
        "title_digest": digest.hex(),
        "launch_phrase": mint.launch_phrase(),
        "reduced": factor != 1,
        "package": pkg,
    }
    with open(os.path.join(out, "answers.json"), "w") as f:
        json.dump(answers, f, indent=2)
    with open(os.path.join(out, "build.log"), "w") as f:
        f.write("\n".join(log) + "\n")
    print(json.dumps({k: answers[k] for k in
                      ("callsign", "player_context", "stage0_token",
                       "final_title", "reduced")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
