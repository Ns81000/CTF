# PRAMBH v3 — HANDOFF (audit session worklist, Appendix C.4)

> **STATUS: SESSION 2 AUDIT COMPLETE — GO VERDICT (23 Sept 2026)**
>
> All deferred production chain walks, verification lanes, package integrity checks, and release packaging completed cleanly.
> - Chain #1 native walk: 5447 s (90.7 min) -> loom ink `de918c455c4b1d42`
> - Chain #2 native walk: 5457 s (91.0 min) -> seal ink `43560fb33c8d0924`
> - Final capstone title: `PRAMBH{43560fb33c8d0924_de918c455c4b1d42_66cb77c72ed791a7_Y22RGQ_9NK3HT_9UJYNG}`
> - Release assets verified: `E:\drive-upload\prambh\RELEASE\` (`prambh.zip`, `prambh.zip.enc`, `MANIFEST.sha256`)
> - Full audit sign-off report: `organizer-private/SESSION_2_AUDIT.md`

Written by the build session at the end of its run. Everything the audit
must do, every PROJECTED number with its math, every known nit, and the
final git state. Nothing here is estimated by hand: every figure comes
from `organizer-private/runs/`.

## 1. DEFERRED RUNS — exact commands (Appendix C.2a)

The build session runs reduced-T projections and skips these long runs.
They are the audit's (lane X6):

```bash
# (a) chain #1, full REAL-T native walk (projected ~75 min; this is the
#     value the shipped package was built with):
cd /home/ns8pc/prambh-build
src/chain/prambh_chain walk \
  --seed-hex 4668e434c5ea0e9b249cae68c6ecc81e1ad79afaa4f0aefef0661b72746045c7 \
  --s 536870912 --t 7705630875

# (b) chain #1, full REAL-T EMULATED cartridge run (projected ~23 h on the
#     build machine: the emulsion route is ~19x the native route):
cd prambh/stage2_loom && ./loom claim loom.rom --vector \
  96415166fc01091e7bce5b43d36a5d491cb6591f0471415e5f670535c7856392

# (c) chain #2 (the seal), full REAL-T native walk (~75 min projected):
src/chain/prambh_chain walk \
  --seed-hex $(python3 -c "import sys; sys.path.insert(0,'src/gen'); import mint; print(mint.chain2_seed().hex())") \
  --s 536870912 --t 7705630875

# (d) the honest REAL-paced full solve (hours; Appendix C.2b)
bash src/final/isolated_solve.sh        # structural lane, runs today
#    ...then repeat the documented path at production T with real wall-clock
#    bookkeeping (runs/ has the per-stage commands).

# (e) deep adversarial hunting: mutation testing of the suites, extended
#     fuzzing, race hunts, timing sweeps (audit lanes X1-X5).

# (f) the full suite battery (each suite is real and self-contained):
bash src/final/verify_all.sh

# (g) the release + hygiene lanes:
bash src/final/leak_grep.sh
bash src/final/rebuild_repro.sh
bash src/final/make_release.sh /mnt/e/drive-upload/prambh/RELEASE
# produce the outer encrypted depot package prambh.zip.enc with the briefing words:
openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt \
  -in /mnt/e/drive-upload/prambh/RELEASE/prambh.zip \
  -out /mnt/e/drive-upload/prambh/RELEASE/prambh.zip.enc \
  -pass pass:"gate hearth zinc field"
bash src/final/package_check.sh
python3 src/final/attack_static.py
python3 src/final/attack_scripted.py
python3 src/final/floor_proof.py
```

## 2. PROJECTED numbers and their math (all marked PROJECTED)

Source: `organizer-private/runs/p5_projection.txt` + `p5_projection.json`
(measured at reduced T on the build machine, 12 cores, S = 512 MiB):

```
native per-step     0.58-1.4 us   (regression over T = 1.5M / 3M / 6M steps)
emulated per-step   ~11 us        (shipped loom, reduced-T cartridge)
cache-resident      0.20-0.30 us  (2 MiB table: the SHA work alone)
DRAM round-trip     the difference (native - cache): ~0.3-1.1 us per step
linearity           per-step cost constant across T (deviation < 30%)

chain #1 native   = T_prod x per-step = 7,705,630,875 x ~0.58 us = ~75 min
chain #1 emulated = 7,705,630,875 x ~11 us  = ~23.5 h
4x-attacker core  = work/4 + DRAM      = ~0.15 + ~0.4 us = ~0.55 us/step
                    -> ~70 min per chain, i.e. the 4x assumption buys
                    ~1.1x, not 4x, because the walk is one sequential
                    SHA-256 dependency chain with a DRAM round-trip per
                    step: nothing in it parallelises.
honest two chains = ~2.5 h; + seven 12-min decoy walks a wrong reading
                    invites + the plate gates + the paper record
EVENT backstop    = MIN_JOURNEY 14400 s (4 h) on the checker server
```

Every one of these is **PROJECTED — audit must confirm with the full REAL
run** (§1 above). The measured real walks of this session (chain #1,
chain #2, seven 12-minute decoy chamber walks, two mirror stages) were run
in parallel and are contention-inflated: see `runs/*_walk.txt`.

## 3. Known nits and open questions for the audit

1. **MERU-8 vs MERU-1.** The contract's prose calls the emulator "the
   MERU-1 survey loom" and names `field-notes/meru1_datasheet.txt`, while
   every generated artifact (datasheet title, ROM banners, ISA table,
   minted model needle) says **MERU-8**. The datasheet carries the
   valley-vs-coast tell that resolves the near-miss. Audit: decide whether
   the mismatch is a fairness problem or intended flavour.
2. **Mirror dates.** Spec §4.6 says the Duplicate Survey's dates
   contradict the epoch printed by `milestone`; `milestone` prints no
   date. The contradiction is carried against the datasheet's 1983
   valley issue instead (recorded in TRAP_CATALOGUE.md).
3. **Anti-debug detector (fixed this session).** `/proc/self/TracerPid`
   does not exist on Linux; `loom.c` now parses the field out of
   `/proc/self/status`. gdb/strace lanes are green in `runs/p5_loom.txt`.
4. **Datasheet opcode count (fixed this session).** It said "64
   operations" while `opcodes.py` defines 96 (both ≥ the contract's 60);
   the count is now generated.
5. **Exit-code policy.** Every shipped tool returns 0 for every abuse
   input (usage screens, unreadable files, refusals) so no outcome can be
   told apart by rc (spec §7 lane 6).
6. **labelled `prambh:loom:seed:v1` in the loom binary** is the tool's own
   derivation label (it needs it); the leak lane asserts no *other*
   stage's labels appear inside it.
7. **Tracked binaries.** `src/chain/prambh_chain`, `src/chain/chain_dbg`,
   `src/state/test_state` are organizer-side tools committed deliberately
   (they never ship; `package_check.sh` asserts the package holds none of
   the sources, and `make_release.sh` builds the zip from `prambh/` only).
8. **`.pyc` hygiene.** `__pycache__/` is now git-ignored; the previously
   tracked `.pyc` files were removed in the P5 commit.

## 4. State at hand-off (what is green, what is pending)

| item | state |
| --- | --- |
| P0-P4 suites | green before this session (commits + runs/*.txt) |
| P5 loom suite | written and green except the projection *band* check, which prints a NOTE while the machine is loaded (see section 5) |
| P6 doors suite | written; needs the seven decoy-chamber walk tokens (`runs/door*_walk.txt`) to generate the chamber texts - those walks were still running at hand-off |
| P7 mirror suite | written; the campaign's two-stage chain is harvested (`runs/mirror_chain.txt`) |
| P8 eyes suite | written; needs chain #2 (`runs/chain2_walk.txt`) for the notes and the title digest |
| P9 server suite | written and run: `runs/p9_server.txt` |
| P9 eventgen suite | written; builds three per-player packages with `--reduced-t` |
| P10 scripts | all written (`src/final/*`); the release lanes need the completed package |

The package's load-bearing values come from three long walks launched in
parallel at the start of the session (chain #1, chain #2, the seven decoy
chambers). Their commands and harvested outputs:

```bash
python3 src/gen/chain_jobs.py eyes2 doors mirror > /home/ns8pc/jobs/chains_p6.sh
Start-Process -FilePath wsl.exe -ArgumentList '-d','Ubuntu','--','bash',
  '/home/ns8pc/jobs/chains_p6.sh' -WindowStyle Hidden
# outputs: organizer-private/runs/chain1_walk.txt, chain2_walk.txt,
#          door{1..7}_walk.txt, mirror_chain.txt
```

Build order once those land (one command each):

```bash
python3 src/doors/chambers_gen.py            # chamber texts (needs door walks)
python3 src/final/build_package.py prambh    # the whole package
bash src/final/leak_grep.sh
bash src/final/make_release.sh /mnt/e/drive-upload/prambh/RELEASE
bash src/final/package_check.sh
bash src/final/rebuild_repro.sh
bash src/final/isolated_solve.sh
python3 src/final/attack_static.py
python3 src/final/attack_scripted.py
python3 src/final/floor_proof.py
bash src/final/verify_all.sh                # every suite, serially
python3 src/gen/session_docs.py             # SESSION_1_LOG.md
```

## 5. Final git state

See `git log --oneline`.  Order: spec, p0, p1, p2 x2, p3, p4, p5-wip,
then this session's commits: `p5:` (loom suite, decoy registry, production
params.h, canary header, the two fixes), `p6-p9:` (doors, mirror, eyes,
server, eventgen, their suites and the P10 scripts), and the release
commit.

## 6. Reminders for the audit

- `organizer-private/` must never be inside the zip (`package_check.sh`
  asserts this).
- The registry is the source of truth: `KEYS_PRAMBH.md`,
  `TRAP_CATALOGUE.md`, `TRAP_ATTRACTION.md`, `runs/p5_decoy_tokens.txt`,
  `runs/mirror_chain.txt`.
- A decoy that is not registered is a finding; a registered decoy missing
  where documented is a finding too - `leak_grep.sh` checks both.
- Never close a finding by weakening a chain, a gate, the pacing or
  MIN_JOURNEY (Appendix C.1).

