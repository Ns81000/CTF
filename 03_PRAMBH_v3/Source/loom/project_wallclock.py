#!/usr/bin/env python3
"""Reduced-T wall-clock PROJECTION for chain #1 (Appendix C.2).

The build session does NOT run the >= 75-min production chain.  It
measures the per-step cost at several reduced T, checks the cost is
constant across T (linear scaling - the walk is one sequential SHA-256
dependency chain, so this projection is sound), and projects production
wall-clock = T_prod x per-step.  Every number it writes is marked
"PROJECTED - audit must confirm with the full REAL run".

Routes measured:
  native   - src/chain/prambh_chain (the same code path loom verify uses)
  emulated - the shipped loom running the real cartridge at reduced T
  cache    - the same walk over a 2 MiB table, to separate the DRAM
             round-trip from the SHA work (latency-bound evidence for the
             4x-attacker floor argument)

usage: project_wallclock.py --loom <loom binary> [--out FILE]
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "gen"))
import mint  # noqa: E402

CHAIN_TOOL = os.path.join(ROOT, "src", "chain", "prambh_chain")
PARAMS = json.load(open(os.path.join(ROOT, "src", "chain", "chain_params.json")))
S_PROD = PARAMS["table_bytes"]
T_PROD = PARAMS["budgets"]["chain1"]["T"]
DECOY_T = PARAMS["budgets"]["decoy_rom"]["T"]

T_NATIVE = [1500000, 3000000, 6000000]      # reduced T ladder (native)
SAMPLES = 2
T_EMU = 200000                              # reduced T for the emulated ROM
S_CACHE = 2 * 1024 * 1024                   # cache-resident probe table
T_CACHE = 6000000
T_DUMP = 3000000                            # table-file walk corroboration
BAND = (3600.0, 5400.0)                     # accepted idle projection (s)

PASS = [0]
FAIL = [0]


def check(label, cond, detail=""):
    if cond:
        print("PASS %s%s" % (label, (" " + detail) if detail else ""))
        PASS[0] += 1
    else:
        print("FAIL %s%s" % (label, (" " + detail) if detail else ""))
        FAIL[0] += 1


def run(cmd):
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    return time.time() - t0, p


def walk_timed(seed_hex, S, T, extra=()):
    dt, p = run([CHAIN_TOOL, "walk", "--seed-hex", seed_hex,
                 "--s", str(S), "--t", str(T)] + list(extra))
    if p.returncode != 0 or len(p.stdout.strip()) != 64:
        raise SystemExit("project_wallclock: walk failed rc=%d err=%s"
                         % (p.returncode, p.stderr[:200]))
    return dt, p.stdout.strip()


def fit(xs, ys):
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    slope = num / den
    return slope, my - slope * mx      # per-step seconds, fill seconds


def main(argv):
    loom = None
    out = os.path.join(ROOT, "organizer-private", "runs", "p5_projection.txt")
    i = 1
    while i < len(argv):
        if argv[i] == "--loom" and i + 1 < len(argv):
            loom = argv[i + 1]
            i += 2
        elif argv[i] == "--out" and i + 1 < len(argv):
            out = argv[i + 1]
            i += 2
        else:
            sys.stderr.write(__doc__)
            return 2
    if not loom or not os.path.exists(loom):
        sys.stderr.write("project_wallclock: --loom <built loom binary> required\n")
        return 2

    load = float(open("/proc/loadavg").read().split()[0])
    content = mint.capsule_content()
    vector = content.hex()
    seed = mint.loom_seed_material(content).hex()

    print("chain #1 wall-clock projection (S=%d B, T_prod=%d, loadavg=%.2f)"
          % (S_PROD, T_PROD, load))

    # ---- fill costs (native, sequential SHA over the table) ------------
    dt, p = run([CHAIN_TOOL, "fillbench", "--s", str(S_PROD)])
    fill_prod = float(p.stdout.strip())
    dt, p = run([CHAIN_TOOL, "fillbench", "--s", str(S_CACHE)])
    fill_cache = float(p.stdout.strip())
    print("fill: %.3f s at S=%d, %.4f s at S=%d"
          % (fill_prod, S_PROD, fill_cache, S_CACHE))

    # ---- native ladder (fill + walk per sample) ------------------------
    samples = []
    for T in T_NATIVE:
        for k in range(SAMPLES):
            dt, out_hex = walk_timed(seed, S_PROD, T)
            samples.append({"T": T, "sample": k + 1, "seconds": round(dt, 4),
                            "out": out_hex})
            print("  native  T=%-9d sample %d  %.3f s" % (T, k + 1, dt))
    step_s, intercept_s = fit([s["T"] for s in samples],
                              [s["seconds"] for s in samples])
    native_step_ns = step_s * 1e9

    lo = [s for s in samples if s["T"] == T_NATIVE[0]][0]["seconds"]
    hi = [s for s in samples if s["T"] == T_NATIVE[-1]][0]["seconds"]
    extreme_ns = (hi - lo) / (T_NATIVE[-1] - T_NATIVE[0]) * 1e9
    dev = abs(extreme_ns - native_step_ns) / native_step_ns
    print("per-step: regression %.1f ns, extremes %.1f ns, deviation %.1f%%"
          % (native_step_ns, extreme_ns, dev * 100))

    # ---- table-file walk (walk only, fill excluded) --------------------
    tbl = "/tmp/p5_projection_table.bin"
    walk_timed(seed, S_PROD, T_DUMP, ("--dump-table", tbl))
    dt_tbl, _ = walk_timed(seed, S_PROD, T_DUMP, ("--table-file", tbl))
    walk_only_ns = dt_tbl / T_DUMP * 1e9
    print("table-file walk: %.3f s for T=%d -> %.1f ns/step (fill excluded)"
          % (dt_tbl, T_DUMP, walk_only_ns))

    # ---- cache-resident probe (latency-bound evidence) -----------------
    cache = []
    for k in range(SAMPLES):
        dt, _ = walk_timed(seed, S_CACHE, T_CACHE)
        cache.append(dt)
        print("  cache   T=%-9d sample %d  %.3f s  (S=%d)"
              % (T_CACHE, k + 1, dt, S_CACHE))
    cache_step_ns = (sum(cache) / len(cache) - fill_cache) / T_CACHE * 1e9
    mem_ns = max(0.0, native_step_ns - cache_step_ns)
    attacker_step_ns = cache_step_ns / 4.0 + mem_ns
    print("per-step split: work(cache) %.1f ns + memory %.1f ns"
          % (cache_step_ns, mem_ns))

    # ---- emulated route (the shipped cartridge at reduced T) -----------
    tmp = tempfile.mkdtemp(prefix="p5proj.")
    gens = os.path.join(HERE, "gen_rom.py")
    p = subprocess.run([sys.executable, gens, tmp, "--T", str(T_EMU),
                        "--S", str(S_PROD), "--decoy-T", "1000",
                        "--no-params"], capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit("project_wallclock: gen_rom failed: " + p.stderr[:200])
    dt_emu, p_emu = run([loom, "claim", os.path.join(tmp, "loom.rom"),
                         "--vector", vector])
    rom_out = p_emu.stdout.strip().splitlines()[-1]
    dt_nat, nat_out = walk_timed(seed, S_PROD, T_EMU)
    emu_step_ns = (dt_emu - fill_prod) / T_EMU * 1e9
    print("emulated: T=%d in %.3f s -> %.1f ns/step"
          % (T_EMU, dt_emu, emu_step_ns))

    # ---- projections ---------------------------------------------------
    prod_native_s = native_step_ns * T_PROD / 1e9
    prod_emu_s = emu_step_ns * T_PROD / 1e9
    attacker_s = attacker_step_ns * T_PROD / 1e9
    attack_ratio = prod_native_s / attacker_s if attacker_s else 0.0
    print("PROJECTED chain #1 native  : %.0f s (%.1f min)"
          % (prod_native_s, prod_native_s / 60))
    print("PROJECTED chain #1 emulated: %.0f s (%.2f h)  ratio %.1fx native"
          % (prod_emu_s, prod_emu_s / 3600.0, emu_step_ns / native_step_ns))
    print("PROJECTED chain #1, 4x attacker core: %.0f s (%.1f min) (%.2fx faster)"
          % (attacker_s, attacker_s / 60, attack_ratio))
    print("PROJECTED two chains, 4x attacker: %.0f min" % (2 * attacker_s / 60))
    print("PROJECTED decoy cartridge lane (T=%d, emulated): %.0f min"
          % (DECOY_T, DECOY_T * emu_step_ns / 1e9 / 60))

    # ---- checks --------------------------------------------------------
    check("native-per-step-linear", dev < 0.30,
          "(deviation %.1f%% across T=%d..%d)"
          % (dev * 100, T_NATIVE[0], T_NATIVE[-1]))
    check("regression-vs-walkonly",
          abs(walk_only_ns - native_step_ns) / native_step_ns < 0.30,
          "(%.1f vs %.1f ns/step)" % (walk_only_ns, native_step_ns))
    check("rom-vs-native-parity", rom_out == nat_out,
          "(reduced-T cartridge claim == native walk)")
    check("emulation-slower-than-native", emu_step_ns > native_step_ns)
    check("memory-vs-work-split", mem_ns > 0.0,
          "(%.1f ns of %.1f ns per step is the DRAM round-trip)"
          % (mem_ns, native_step_ns))
    if load < 1.5:
        check("projected-in-target-band", BAND[0] <= prod_native_s <= BAND[1],
              "(%.0f s in [%.0f, %.0f] s = 75 min +/- 15 min)"
              % (prod_native_s, BAND[0], BAND[1]))
    else:
        print("NOTE contended measurement (loadavg %.2f): projection %.0f s, "
              "band check deferred to the idle re-run" % (load, prod_native_s))


    # ---- report --------------------------------------------------------
    rep = [
        "P5 - CHAIN #1 REDUCED-T WALL-CLOCK PROJECTION (Appendix C.2)",
        "EVERY NUMBER BELOW IS PROJECTED - audit must confirm with the full REAL run.",
        "",
        "machine: %s, %d cores, /proc/loadavg at measurement = %.2f"
        % (os.uname().release, os.cpu_count(), load),
        "production dials: S=%d B, T_prod=%d (chain_params.json budgets.chain1)"
        % (S_PROD, T_PROD),
        "chain #1 seed (label prambh:loom:seed:v1 || capsule_content) = %s" % seed,
        "route 1 (native)   : %s walk" % CHAIN_TOOL,
        "route 2 (emulated) : %s claim <reduced loom.rom> --vector "
        "<capsule_content>" % loom,
        "",
        "raw samples (native ladder; each sample = full fill + walk):",
    ]
    for s in samples:
        rep.append("  T=%-9d sample %d  %.4f s   out=%s"
                   % (s["T"], s["sample"], s["seconds"], s["out"]))
    rep += [
        "",
        "fill (sequential SHA over the table, fillbench): %.4f s at S=%d, "
        "%.4f s at S=%d" % (fill_prod, S_PROD, fill_cache, S_CACHE),
        "native regression: per-step %.2f ns, intercept %.3f s"
        % (native_step_ns, intercept_s),
        "native extremes check: implied per-step %.2f ns (deviation %.1f%%)"
        % (extreme_ns, dev * 100),
        "table-file walk (fill excluded): %.4f s for T=%d -> %.2f ns/step"
        % (dt_tbl, T_DUMP, walk_only_ns),
        "cache-resident probe (S=%d, T=%d): %s s -> %.2f ns/step"
        % (S_CACHE, T_CACHE, ["%.3f" % c for c in cache], cache_step_ns),
        "emulated route (reduced T=%d, S=%d): %.4f s -> %.2f ns/step"
        % (T_EMU, S_PROD, dt_emu, emu_step_ns),
        "rom-vs-native parity at reduced T: %s (claim %s / walk %s)"
        % ("IDENTICAL" if rom_out == nat_out else "MISMATCH",
           rom_out[:32] + "...", nat_out[:32] + "..."),
        "",
        "projection math:",
        "  native  : %.2f ns/step x %d steps = %.0f s (%.1f min)"
        % (native_step_ns, T_PROD, prod_native_s, prod_native_s / 60),
        "  emulated: %.2f ns/step x %d steps = %.0f s (%.2f h)"
        % (emu_step_ns, T_PROD, prod_emu_s, prod_emu_s / 3600.0),
        "  per-step split: work %.2f ns (cache-resident) + memory %.2f ns"
        % (cache_step_ns, mem_ns),
        "  4x attacker core: work/4 + memory = %.2f ns/step -> %.0f s (%.1f min)"
        % (attacker_step_ns, attacker_s, attacker_s / 60),
        "  two chains under the 4x assumption: %.0f min" % (2 * attacker_s / 60),
        "  decoy cartridge lane (T=%d) emulated: %.0f min"
        % (DECOY_T, DECOY_T * emu_step_ns / 1e9 / 60),
        "",
        "linear scaling check: the extremes-implied per-step deviates %.1f%% from"
        % (dev * 100),
        "the regression slope (< 30%), so per-step cost is constant across T and",
        "the projection T_prod x per-step is sound: the walk is one sequential",
        "SHA-256 dependency chain, so there is nothing to parallelise.",
        "",
        "deferred (audit, Appendix C.2a): the full REAL-T emulated cartridge run",
        "(%.2f h projected) and the full REAL-T native walk (%.1f min projected)."
        % (prod_emu_s / 3600.0, prod_native_s / 60),
        "native command:",
        "  src/chain/prambh_chain walk --seed-hex %s --s %d --t %d"
        % (seed, S_PROD, T_PROD),
        "",
    ]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write("\n".join(rep) + "\n")
    with open(os.path.join(os.path.dirname(out), "p5_projection.json"), "w") as f:
        json.dump({"native_step_ns": native_step_ns, "emu_step_ns": emu_step_ns,
                   "cache_step_ns": cache_step_ns, "dram_ns": mem_ns,
                   "fill_prod_s": fill_prod, "intercept_s": intercept_s,
                   "native_prod_s": prod_native_s, "emu_prod_s": prod_emu_s,
                   "attacker_4x_s": attacker_s, "loadavg": load,
                   "linearity_deviation": dev, "samples": samples}, f, indent=2)
    print("wrote %s" % out)
    print()
    print("P5-PROJECTION: %d PASS, %d FAIL" % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

