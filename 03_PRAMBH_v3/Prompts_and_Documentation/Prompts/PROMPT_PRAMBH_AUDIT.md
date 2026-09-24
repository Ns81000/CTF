# SESSION 2 PROMPT — DEEP AUDIT + RELEASE GATE of PRAMBH (v3, prequel to "The Cartographer's Ghost")

Paste this ENTIRE file into a fresh Claude Code session (act mode) on the same machine,
ONLY AFTER the build session (`PROMPT_PRAMBH_BUILD.md`) has reported COMPLETE with all
suites green. You are the AUDIT session — a NEW session by hard rule: you have no memory
of the build beyond what the repo, the spec copy, and the build log state. Your job is to
break the build, then fix it, then prove it cannot be broken again.

**First reply with one line:** `READ PRAMBH AUDIT PROMPT OK — starting Phase A`. Then execute.

Rules that override everything:
- **Machine access (local only, never ship, never log):** Windows + WSL. Drive WSL from
  PowerShell: privileged commands via `wsl.exe -d Ubuntu -u root -- bash -lc '...'` (root
  route, no password), all other work via `wsl.exe -d Ubuntu -- bash -lc '...'`. The `sudo`
  password `123456` supplied by the user was tested and REJECTED on this machine — never
  guess passwords; if sudo is genuinely needed (e.g. installing `faketime`), install it
  through the root route instead. Redact any credential from captured output.
- **Trust nothing.** Every claim in the build log must be reproduced by you, by command.
- A finding is only closed when you have a re-run proving it is closed.
- Never "fix" by weakening the puzzle: fixes must preserve or increase difficulty, must
  never lower the measured wall-clock floor, and must keep every law in the spec true.
- Never edit `docs/BUILD_SPEC_PRAMBH.md` (it is the contract). If the build violates it,
  fix the build or (if the spec is impossible) STOP and report.
- If you find an answer-leaking bug, treat it as SEV-1 and fix it before continuing.
  A shortcut that drops the honest wall-clock floor below 4 hours is ALSO SEV-1.
- If you cannot reproduce a build-log claim, that is a finding.
- **Honesty law:** every claim you record is phrased as a measured cost, never as
  "impossible" or "undetectable". Stealth, not undetectability — same as the build.

---

## 0. INPUTS TO READ (in this order, once)

1. `/mnt/e/drive-upload/prambh-build/docs/BUILD_SPEC_PRAMBH.md` — the contract (verbatim copy of
   the Session-1 build prompt). Read it FULLY, in chunks. Do not skim.
2. `/mnt/e/drive-upload/prambh-build/organizer-private/SESSION_1_LOG.md` — what was built.
3. `.../KEYS_PRAMBH.md`, `.../SOLVE_PATH_PRIVATE.md`, `.../TRAP_CATALOGUE.md`,
   `.../COST_MODEL.md`, `.../HANDOFF.md` (the build's deferred-item worklist — X6
   owns every entry in it), and `.../TRAP_ATTRACTION.md` (the Appendix-C.3
   top-misreadings pass: verify every entry maps to a registered decoy).
4. `.../runs/p5_projection.txt` + `p5_projection.json` (the Appendix-C.2 reduced-T
   wall-clock projection: per-step rates, latency split, and every PROJECTED
   number that X6 must replace with a MEASURED one), `.../runs/*_walk.txt`,
   `runs/chain1_walk.txt`, `runs/chain2_walk.txt`, `runs/door1..7_walk.txt`,
   `runs/mirror_chain.txt` (the harvested chain values), `runs/mint_archive_probe.txt`
   (ARCHIVE-mode value regression), and every `runs/*.txt` suite verdict (they are
   the as-built baselines for Phase A).
5. `E:\drive-upload\prambh\RELEASE\MANIFEST.sha256` + the shipped zip
   (`RELEASE\prambh.zip`).  **PRE-BUILT BY THE BUILD SESSION BEFORE THIS AUDIT**
   (user order): both chain walks were re-run and `finish.sh` produced the
   package, `MANIFEST.sha256` and `prambh.zip`. Your FIRST act is to verify
   they exist and hash-match (`ls -la` + `sha256sum`); only if something is
   missing do you run section 0.5's resume recipe.
5. `E:\drive-upload\bin\ghost2\` is the v2 archive — READ-ONLY. Open it only to build the
   forbidden-v2-values list for Phase B and the known-good attack list for Phase J.
   Record its zip sha256 at the start of this session and verify it is unchanged at
   the end. Touching it in any other way is a failed session.

Deliverable of this session: `organizer-private/SESSION_2_AUDIT.md` with every check,
finding, fix, re-verification and a final **GO / NO-GO**, plus a fixed, repackaged,
re-manifested zip copied to `E:\drive-upload\prambh\RELEASE\`.

### 0.4 TIME BUDGET (user order - the audit must be FAST)
Total audit wall-clock target: <= 2 hours of audit work, excluding your own
fix-and-re-verify cycles. Allowed to take minutes: `verify_all.sh` (~15 min),
FIVE `player_gen` builds (~5 min), `rebuild_repro.sh` (~2 min), the reduced-T
ladders above (~1 min each). FORBIDDEN as time sinks: production-T chain walks,
emulated production runs, hours-long solves, 20+ callsign batches, multi-hour
CV/OCR development, human-subject trials. When a lane below conflicts with this
budget, take its reduced-T / time-boxed form and note it in the report - the
CONTRACT's security laws (floor, suite minimums, decoys, gates, MIN_JOURNEY)
are untouched; only the verification schedule is shortened. Run `verify_all.sh`
ONCE in Phase A; in Phase L re-run it only if you actually changed something
(otherwise re-quote the Phase A output). Main prompt copies:
`prambh-build\PROMPTS\` (working) and `bin\ghost2\PROMPTS\` (archived original).

### 0.5 IN-FLIGHT PROCESSES AT BUILD HAND-OFF (recorded 2026-09-22 ~00:00,
### STOPPED ON USER ORDER — YOU OWN ALL OF THEM NOW)
The build session had four background jobs running when the user ordered the
session stopped and WSL cleaned. They were killed (a chain walk only prints its
result at completion, so killing it yields NO partial output):
1. chain #1 (the loom's production walk; supplies K_loom for `doors riddle`
   and the whole package build):
   `src/chain/prambh_chain walk --seed-hex 4668e434c5ea0e9b249cae68c6ecc81e1ad79afaa4f0aefef0661b72746045c7 --s 536870912 --t 7705630875`
   -> target output file `organizer-private/runs/chain1_walk.txt` (**missing**).
2. chain #2 (the eyes seal walk; supplies K_eyes for `gen_eyes.py`, the notes
   seal and the final title digest):
   `src/chain/prambh_chain walk --seed-hex $(python3 -c "import sys;sys.path.insert(0,'src/gen');import mint;print(mint.chain2_seed().hex())") --s 536870912 --t 7705630875`
   -> target output `organizer-private/runs/chain2_walk.txt` (**missing**).
3. `bash src/final/finish.sh` — the build's one-shot pipeline (already documented
   in X6 item 7). It was still inside its `wait_for chain1/chain2` loop.
4. `bash /mnt/e/drive-upload/bin/wsl-jobs/watch.sh` — a build-session watcher that compiled all
   verdicts into `organizer-private/runs/final_verdicts.txt` when finish.sh
   finished (file **missing** — never produced).
Resume recipe (Appendix B.2 Start-Process recipe; each walk is ~75 min solo):
   `python3 src/gen/chain_jobs.py loom1 eyes2 > /mnt/e/drive-upload/bin/wsl-jobs/chains_long.sh`
   then launch it from the Windows side with Start-Process, then run
   `bash src/final/finish.sh`. Already harvested and on disk: the seven decoy
   chamber walks (`runs/door1..7_walk.txt`) and the mirror campaign
   (`runs/mirror_chain.txt`) — do NOT re-run those (they are registered values).
   Every suite that was green before the stop is listed in §0 item 4.

---
### 0.6 PATH CHANGE (build session, user-ordered WSL evacuation)
On 2026-09-23 the user ordered the build session to stop, clean WSL and leave the
workspace organised on the Windows side. As a result:
- the repo now lives at **`E:\drive-upload\prambh-build`** = WSL path
  **`/mnt/e/drive-upload/prambh-build`** (full git history, all suites,
  `organizer-private/runs/`, the harvested decoy/mirror walks). The WSL trees
  `/home/ns8pc/prambh-build` and `/home/ns8pc/jobs` were DELETED after hash
  verification (do not look for them there) — every path below has already been rewritten to the new location.
- scratch/legacy material moved into **`E:\drive-upload\bin\`** (subfolders by
  origin/date).  One file in there needs re-reading before ANY publish step:
  `bin\legacy-notes\LEGACY_v1_DO_NOT_PUBLISH.txt` (the v1 do-not-publish
  warning; the paths it names are gone, the warning still governs); the release stays in `E:\drive-upload\prambh\RELEASE\`; the v2
  archive `E:\drive-upload\ghost2\` was NOT touched (still READ-ONLY, its zip
  sha256 must still match §0 item 5's recorded value).
- executables copied to the Windows side may need `chmod +x` on first use under
  `/mnt/e` (drvfs); the suites invoke scripts with `bash ...` so they do not.
- The chain #1/#2 walks were stopped BEFORE producing their output files (see
  §0.5) — re-run them before any package build or timing work.

---
## PHASE A — Independent rebuild and baseline (must be green before anything else)

```bash
cd /mnt/e/drive-upload/prambh-build
git status --porcelain            # expect clean; anything here is a finding
git log --oneline | head -20
python3 -c "import hashlib;print(hashlib.sha256(open('docs/BUILD_SPEC_PRAMBH.md','rb').read()).hexdigest())"
bash src/state/test_state.sh            # state suite (NO Makefile exists in
                                        # src/state - `make clean` is a v2-ism;
                                        # the suite builds its own harness)
cd /mnt/e/drive-upload/prambh-build && bash src/final/verify_all.sh  # all suites SERIAL
bash src/final/rebuild_repro.sh                              # 2 clean rebuilds, same hashes
```
Then compare every packaged file against `MANIFEST.sha256`:
```bash
( cd prambh && sha256sum -c ../MANIFEST.sha256 )            # adapt path/format as needed
sha256sum prambh.zip
```
Findings to look for: hashes that differ from the log, suites that pass only in one
order, suites that leave state/files behind, non-reproducible builds, manifest drift, a
package file not on the allowed list, anything organizer-ish inside the zip.
Record the as-built suite baselines (names + exact counts) from `verify_all.sh` output;
they must match `SESSION_1_LOG.md` exactly. If any name/count differs, record an
as-built addendum in the audit report (v2 needed one) and treat unexplained drift as a
finding.
Acceptance: every suite green, rebuild byte-identical, manifest exact, package
allowed-list clean. Any deviation -> log it, fix it, re-run the whole phase.

---

## PHASE B — Leak hunt (exhaustive; the most important phase)

Extend (do not trust blindly) the build's `src/final/leak_grep.sh` with INDEPENDENT
patterns of your own. Check ALL of:
1. **Value leaks.** For every value in `KEYS_PRAMBH.md` (real chain outputs, human-gate
   glyphs, scored answers, seeds, keys, digests, decoy values, per-player master
   material identifiers) and for every *prefix/substring of length >= 8* of those
   values: grep case-insensitively (via `strings -n 4` for binaries — never raw-grep
   binaries, v2 finding F-03) in every binary, carrier, rendered artifact, doc,
   filename, and zip entry. Any hit inside the package = SEV-1 (except values the spec
   explicitly allows and registered decoys).
   **Present-by-design exceptions — assert exactly these, no more (do NOT "fix" them
   away; removing them would weaken the contract):**
   a. the Stage-0 token `PRAMBH{zero_...}` — in `stage0_milestone/milestone` strings
      and printed on every milestone run (spec 4.2); nowhere else in the package;
   b. the canary `PRAMBH{canary_...}` — `HUMAN_OPERATOR_NOTICE.txt`, every tool's
      usage screen/binary, registered CANARY-1 (spec 4.10);
   c. the launch phrase — `LAUNCH.txt` in ARCHIVE mode only (spec 4.2; absent from
      any EVENT-mode package);
   d. the derivation label `prambh:loom:seed:v1` inside `stage2_loom/loom` (the tool
      needs it to derive the seed) — and NO other stage's label inside it
      (per-label scoping lane);
   e. the operator-notice TEXT in PNG `tEXt Notice` chunks (spec 4.10);
   f. registered decoys at exactly their documented locations (`TRAP_CATALOGUE.md`).
   `src/final/leak_grep.sh` implements a-scoped versions of (a) and (d); extend
   with independent patterns of your own.
2. **Derivation leaks.** No text in the package may name a mechanism: `memory-hard`,
   `chain`, `random walk`, `DRAM`, `iteration`, `calibrat`, `autostereogram`,
   `Ishihara`, `moire`, `emulat`, `8086`, `opcode`, `mirror`, `checkpoint`, `journey`,
   `seed`, `sha256`, `hmac`, `argon`, `scrypt`, `table`, `stride`, ... (keep a
   maintained list file). Flavour words allowed; mechanism words not. Report each hit
   with context; remove it or justify it in writing.
3. **Grammar leaks.** No text may state a length, count, separator set, hex/text split,
   stage counts, iteration counts, table sizes, or the word "flag" next to a structure.
4. **Structural leaks.** `strings`/entropy diff all binaries pairwise; look for constant
   blocks that stand out as tables/keys, `.rodata` blobs whose size matches a key, and
   constants shared between binaries that are not shared library code.
5. **Static-computability audit (the v2 killer).** For every scored answer and every
   gate key: attempt to derive it from the shipped bytes alone (static analysis, your
   own scripts, no chain execution). The only values you may obtain are registered
   decoys. Any real value derivable statically = SEV-1.
6. **Metadata leaks.** `exiftool -a -v3` on every rendered artifact, `pngcheck -v`,
   `file`, raw chunk dumps. No mechanism text, no formulas, no offsets, no seeds.
7. **Answer-shaped strings.** grep the flag format over every package file: the only
   permitted hits are documented decoys (registered in `TRAP_CATALOGUE.md`, none
   mirroring the real answers' shape) and the single canary string (§4.10).
8. **Bait integrity.** Bait files contain zero truth and no real value/substring; any
   "draft solution" prints a wrong but format-valid value.
9. **Cross-binary / cross-stage leaks.** No binary or artifact may contain another
   stage's real value or decoy set. The Mirror Room campaign and the real campaign must
   share zero values (assert by grep both ways).
10. **Docs separation.** `organizer-private` never appears in the zip; no source, log,
    git, or build artifacts in the zip.
11. **v2 poison list.** Build the forbidden list from the v2 archive (`KEYS_V2.md` and
    the v2 spec's FORBIDDEN lists) and assert EVERY v2 value appears nowhere in the
    PRAMBH package, artifacts, docs, or binaries.
12. **Notice/gaslight layer.** Assert the canary notice is embedded per spec (`.rodata`
    of every binary, usage output, artifact metadata fields) and that every
    gaslight/stall text contains zero verdict words and zero truth (cross-check each
    against `KEYS_PRAMBH.md`).
Acceptance: zero unexplained hits. Every hit is either fixed (SEV-1/2) or justified in
writing in the audit report.

---
## PHASE C — Static-only adversary

1. Extract the shipped zip to `/tmp/audit-static/` with no repo nearby. Using ONLY
   static analysis (`strings`, disassembly, hex dumps, your own Python), attempt to
   derive every scored answer and every stage-gate key WITHOUT running the chains.
2. Run the build's `src/final/attack_static.py` and confirm it yields only registered
   decoys; then go BEYOND it with your own derivations the build author did not think
   of (you are a fresh session — use that).
3. Record everything obtained; cross-check each item against the decoy registry in
   `TRAP_CATALOGUE.md`. Unregistered value obtained = SEV-1. Real value obtained =
   SEV-1, stop and fix before continuing.

---

## PHASE D — Scripted/batch adversary, including a full Mirror Room solve

1. Run `src/final/attack_scripted.py`: piped/non-TTY input, batch loops, uniform
   timing, replayed sessions. The scripted agent must be poisoned or gated, must never
   reach the final answer, and must never receive a verdict word. Confirm zero
   information distinguishes a wrong branch from the right one at runtime.
2. **Solve the Mirror Room to its end, as an adversary would.** Follow the fake
   campaign's stages all the way. Assert: it terminates at the documented honest dead
   end; every value it ever yields is a registered decoy; the dead-end text is honest
   (no fake victory, no accusation, no verdict words); nothing in it points at the real
   campaign's mechanism. TIME the full detour and record the measured cost in
   `COST_MODEL.md` — it must be hours, not minutes.
3. **Cross-contamination attack:** feed Mirror Room artifacts into the real campaign's
   tools and vice versa. Must yield nothing (rc 0, silent or flavour-only, no verdict).
4. Prove the mirror campaign is distinguishable from the real one ONLY by the
   documented tell in `SOLVE_PATH_PRIVATE.md`, and that finding the tell costs what
   the cost model claims.

---

## PHASE E — Dynamic adversary (gdb/strace/ltrace/faketime/forced state)

Against the shipped binaries (never a test build for the "ignores hooks" checks):
1. `strace -f -e trace=...`, `ltrace`, `/proc/<pid>/maps` + `mem` scraping, core dumps,
   swap inspection mid-chain: record what an attacker can actually obtain and at what
   cost. Assert intermediate chain states do not contain final key material before the
   full iteration count completes (spot-check at 1%, 10%, 50%, 90%).
2. **Debugger skip attack:** patch out / breakpoint-skip the walk loop, force the loop
   counter to near-final, jump past gates. The resulting value must be WRONG (the
   chain's sequential dependence must make skipping produce garbage, not the key).
   Record each attempt and its result.
3. `faketime` (install via the root route if missing), clock jumps forward/backward,
   TZ changes: no negative deltas accepted, no gate false-opens, no hangs, no
   checkpoint forgery.
4. **Forced/crafted state:** hand-built state files, state from a different stage,
   byte-flip sweep over a valid state, truncated state, state replayed from an earlier
   checkpoint. Every case: rc 0 + silent stderr + clean refusal/reset, never
   corrupt-and-accepted, never a real value emitted.
5. Concurrency: two instances of the same tool; tool with deleted state mid-chain;
   disk-full on state write. Graceful only.
Acceptance: no dynamic technique produces a real value or reduces the wall-clock floor;
every failure mode is silent and fair. Anything else = SEV-1/SEV-2 per impact.

---
## PHASE F — Time-floor re-measurement (the core claim; do not trust the build's numbers)

1. Independently re-run `src/final/floor_proof.py` and `src/final/calibrate.py` on the
   audit machine. Measure steps/sec for BOTH chain phases (table fill + random walk)
   yourself, with the machine under normal load and under memory pressure.
2. Recompute the floor under the spec's 4x-attacker-hardware assumption. Requirement:
   projected honest floor >= 4 h on hardware 4x faster than the audit machine. If the
   audit machine is faster than the build machine and the floor drops below 4 h,
   retune ONLY the documented dials (chain length), re-calibrate, re-measure, and
   record before/after in `COST_MODEL.md`. Never retune anything else.
3. **Reduced-table attack:** re-run the memory-reduction attack (recompute-on-demand
   instead of storing the full table). Measure the slowdown factor yourself; require
   it infeasible per the spec's documented threshold.
4. **Parallelism attack:** N concurrent chains, interleaved walks, split-state
   attempts. Measure aggregate speedup; require near-zero (DRAM-bound argument must
   hold with YOUR numbers).
5. **Precomputation attack (EVENT mode):** prove the launch-value gate genuinely
   prevents deriving event values before event start — attempt it.
6. **Test-hook audit:** shipped binaries must ignore every test hook/time-scale
   variable (`strings` + behaviour probe). A hook that works on a shipped binary =
   SEV-1.
   Build-session note to verify, not to trust: the shipped `loom` exposes
   `verify --vector --T --S`. `T` and `S` are part of the fill/run labels, so a
   reduced T yields a DIFFERENT (useless) checkpoint — prove it by running
   `loom verify --vector <real capsule vector> --T 1000 --S 1024` and confirming
   the checkpoint differs from the production-T checkpoint derived from
   `runs/chain1_walk.txt`. Also assert no shipped binary honours
   `PRAMBH_PLAYER_HEX` or `--reduced-t` (an ORGANIZER-side `player_gen.py` flag,
   never shipped), or any other env/argv time-scale hook.

---

## PHASE G — Human-gate automation re-attacks (autostereogram / Ishihara / moiré)

1. TIME-BOXED automation of each human-senses gate (user order: no long processes):
   run the build's `src/eyes/decode_lanes.py` first (seconds), then spend at most
   ~5 minutes on ONE extra attempt per gate (an ImageMagick channel split, one
   OCR or template-matching shot). Record the command, the wall-clock cost and
   the result. Requirement unchanged: automation is costly AND lands on decoys. Requirement: automation is costly AND yields only decoy glyphs
   when faked; a real value obtained by automation = SEV-1.
2. Regenerate every artifact from its documented seed: byte-identical output, glyphs
   match `KEYS_PRAMBH.md`.
3. Human fairness (fast form, user order): verify BY CONSTRUCTION, not by long
   trials - regenerate each artifact from its seed, confirm the viewing notes
   unambiguously identify the real glyph (and which decoy each wrong method
   lands on), and render-check the glyphs are legible at 100%. Record it as
   verified-by-construction. Human-subject timing trials are OUT OF SCOPE.

---

## PHASE H — EVENT-mode audit (generator, cross-contamination, server abuse)

1. **Generator determinism:** `src/gen/player_gen.py --callsign X` twice ->
   byte-identical player packages. Two different callsigns -> different real values,
   asserted by diff + grep.
2. **Cross-contamination suite:** generate FIVE callsigns (was 20+, cut by the user's no-long-process order -
   the build's suite already proves three players byte-clean); assert no player's real value
   (or >= 8-char substring) appears in any other player's package; decoys are
   per-player distinct where the spec requires.
3. **Server abuse (`src/server/checker.py`):** replay a valid submission; submit before
   MIN_JOURNEY wall-clock has elapsed; forge callsigns; skip checkpoints; double-submit;
   submit with clock games; malformed requests; flood. Every refusal must leak nothing
   (identical response shape/timing for every failure class within measurement noise).
4. **Journey proof:** the scored flag is issued ONLY after a checkpoint journey whose
   measured wall-clock >= MIN_JOURNEY; prove the server cannot be talked into issuing
   it earlier, and record the measured minimum.
5. **ARCHIVE mode isolation:** the offline package remains fully solvable with the
   server absent; the checker is never required; no package component phones home
   (assert by strace + firewall-deny run).

---
## PHASE I — Packaging, isolation, document truthfulness, Windows-side re-verification

1. Extract the shipped zip on a clean path (`/tmp/audit-extract/`), no repo nearby.
   Solve the whole chain from there, twice, recording per-stage wall-clock. Verify:
   exec bits survived, no absolute paths needed, works when the folder is moved, works
   when renamed, works from a read-only copy (state writes fail gracefully).
2. Allowed-list audit: the extracted tree must contain exactly the files the spec
   allows, nothing else. Anything extra is a finding.
3. `nm -a` empty on all binaries; no compiler idents; no host paths; no organizer words
   in any filename or in any file's first 20 lines.
4. Docs audit, sentence by sentence: `README_FOR_SOLVER.txt`, the operator notice,
   every field-note, `HINTS.md`, `TRYHACKME_ROOM_TEXT.md`. Requirements: no grammar
   leaks, no mechanism leaks, no stage counts, no lengths, no false statements about
   the shipped build, and every hint TRUE and useful once understood (v2 shipped the
   contradicting-hint class of bug — hunt for it).
5. Room-text audit: the scored answers are exactly what the validator accepts;
   submission format lines exactly right; the pacing/difficulty line honest
   ("marathon", hours) — feedback starvation and the time floor must be honestly
   implied, never oversold ("impossible") or undersold.
6. Bait audit: re-run the Phase B checker over the bait layer; every bait claim inert
   or false.
7. Manifest + hash hygiene: `MANIFEST.sha256` lists every packaged file; the zip's own
   sha256 recorded; a second independent re-zip (same file set, same order,
   deterministic timestamps) reproduces the same hash.
8. **Windows side:** from PowerShell, re-verify
   `E:\drive-upload\prambh\RELEASE\prambh.zip` sha256 against this audit's recorded
   hash; confirm `MANIFEST.sha256` parity Windows-side vs WSL-side; confirm the v2
   archive hash recorded in §0 is unchanged.

---

## PHASE J — Agent adversary harness (the attacks that killed v2)

1. Write `organizer-private/AGENT_TEST_PROTOCOL.md`: a cold-start protocol for testing
   with an LLM agent (and with a human): exactly what the tester may see (the package
   only — no organizer docs, no hints), what to record (timestamps, tokens, tool calls,
   paths taken, where it stalled, what it believed), and a scoring table.
2. Explicitly re-run, against PRAMBH, the *specific* attacks that solved v2 in ~20
   minutes (the known-good adversary patterns): inverting stage transforms from shipped
   constants (Feistel-class inversion); LSB/bit-plane extraction from carriers; reading
   embedded masks; enumerating decoys via `strings`; deducing answer grammar from usage
   text; pulling hashes/keys out of `.rodata`; reading metadata formulas. Each must now
   fail or cost measured hours — record the command used and the measured cost for each.
3. If the user supplies a transcript from a real agent run against PRAMBH, analyse it
   line by line: which leaks it used, which poisons it swallowed, how long each phase
   took, where it stalled, what it believed. Extract each as a hardening check
   ("would PRAMBH defeat this step? prove it by command").

---

## PHASE K — Fix discipline (how to close findings without breaking anything)

For every finding (SEV-1 leak/shortcut/crash/floor-break; SEV-2 unfairness/robustness;
SEV-3 doc/consistency):
1. Write a one-line repro command in the report.
2. Fix in source (never by editing packaged binaries, never by editing the spec).
3. Re-run: the failing check, then the whole of `src/final/verify_all.sh`, then the
   specific phase(s) whose artefact you touched.
4. Re-run the leak grep and the static/scripted adversaries for the touched stage.
5. **Dependency rule:** a fix touching chain dials re-runs ALL of Phase F; a fix
   touching any value re-runs ALL of Phase B; a fix touching the generator or server
   re-runs ALL of Phase H.
6. Record before/after, the fix, and the proof. If a fix changes a binary or artifact,
   everything downstream is rebuilt and re-manifested (record the new hashes).
7. Never mark a finding closed on reasoning alone. Command output or it is still open.

---
## PHASE L — Release gate and final report

Run the release gate in this exact order; every step must be green:
```bash
bash src/final/verify_all.sh            # all suites, serial, from a clean build
bash src/final/leak_grep.sh             # zero unexplained hits (incl. YOUR additions)
bash src/final/rebuild_repro.sh         # byte-identical rebuilds
bash src/final/attack_static.py         # cannot produce any real value
bash src/final/attack_scripted.py       # cannot reach the final answer
bash src/final/floor_proof.py           # measured >= 4 h projection, 4x assumption
bash src/final/package_check.sh         # allowed list + manifest exact
bash src/final/isolated_solve.sh        # stranger's solve from the extracted zip
```
Then produce `organizer-private/SESSION_2_AUDIT.md` with:
1. Status + **GO / NO-GO** statement (one line each: leaks, shortcuts, time floor,
   fairness, robustness, packaging, timing honesty, EVENT-mode integrity).
2. Every phase's real output (pasted, not paraphrased).
3. Findings table: id, severity, one-line repro, fix, closure re-run output.
4. Measured numbers: honest path per stage, mirror detour cost, scripted path result,
   static path result, chain s/iter (both phases), floor arithmetic with the 4x
   assumption, reduced-table slowdown, parallelism speedup, human-gate margins,
   server MIN_JOURNEY minimum.
5. What is NOT proven (must be a short, honest list).
6. **As-built addendum** (v2 needed one): any tool/script renames vs this prompt,
   exact as-built suite baselines, lessons-that-must-be-checks, and facts a future
   audit must not "fix" (registered judgements).

---

## PHASE M — Final bundle, full WSL evacuation, and total WSL wipe
## (run LAST, only after the release gate is GO)

The user's standing requirement: **when this session ends, WSL must be completely
empty of this project and every file must live only in the Windows workspace**
(`E:\drive-upload\`). Nothing project-related may remain in WSL.

1. **Final bundle.** `E:\drive-upload\prambh\` must match this layout exactly:
   - `RELEASE\` — `prambh.zip`, `MANIFEST.sha256`, `TRYHACKME_ROOM_TEXT.md`, `HINTS.md`
   - `ORGANIZER_PRIVATE\` — `KEYS_PRAMBH.md`, `SOLVE_PATH_PRIVATE.md`,
     `TRAP_CATALOGUE.md`, `COST_MODEL.md`, `SESSION_1_LOG.md`, `SESSION_2_AUDIT.md`
     (this session's report), `AGENT_TEST_PROTOCOL.md`
   - `PROMPTS\` — the two session prompts (build + audit)
   - `SOURCE\` — created in step 2 below (the full repo, evacuated from WSL)
   - `README_HOW_TO_RUN.md` at the root
   Re-verify `sha256sum RELEASE\prambh.zip` against this audit's report. If a fix
   changed the zip, re-copy it and re-write every hash everywhere (report, README,
   room text). The v2 archive `E:\drive-upload\ghost2\` stays untouched: re-verify the
   hash you recorded in §0.

2. **Evacuate the source tree (BEFORE deleting anything).**
   - Commit everything first: `cd ~/prambh-build && git add -A && git commit -m 'final'`
     (tree must be `git status --porcelain` clean — audit report, runs/, fixes included).
   - Copy the ENTIRE repo including `.git` and `organizer-private/runs/`:
     `cp -a ~/prambh-build /mnt/e/drive-upload/prambh/SOURCE/prambh-build`
   - Also make a pristine archive preserving Linux permissions:
     `tar -czf /mnt/e/drive-upload/prambh/SOURCE/prambh-build.tar.gz -C ~ prambh-build`
   - **Verify the copy before any deletion:** compare file counts and a full recursive
     sha256 manifest of `~/prambh-build` vs the Windows copy. Extract the tar to /tmp,
     `diff -r` against the repo, then delete the /tmp extract. Only proceed when
     verification is perfect.

3. **Total WSL wipe (only after step 2 verifies).**
   - `rm -rf ~/prambh-build` and every other project file/dir in `~` (home must end
     EMPTY of project material).
   - `rm -rf /tmp/*` scratch (audit extracts, probes, benches, helper scripts).
   - Remove state leftovers: `find / -name '.prambh_state*' 2>/dev/null` via the root
     route; delete every hit outside the (already copied) repo.
   - Clear shell history (`> ~/.bash_history`, root's too), apt/pip caches
     (`apt-get clean` via root route, `rm -rf ~/.cache`).
   - Verify: `ls -la ~` shows no project files; `df` / `du` show the tree gone.
   - Optional, ONLY if the user explicitly confirms in-chat at that moment: full distro
     removal via PowerShell `wsl.exe --unregister Ubuntu`. Do NOT do this by default.

4. **Windows-side cleanup.** `E:\drive-upload\prambh\` is the only active project tree;
   `E:\drive-upload\ghost2\` remains the untouched v2 archive. No `.prambh_state*`
   anywhere outside test runs. No stray scratch dirs.

5. **Final message.** GO/NO-GO, zip path + size + sha256, headline numbers (measured
   honest cost, floor projection, suite counts), confirmation that WSL is wiped and
   Windows is the only copy, unresolved items (must be empty or user-accepted), and the
   phrase `PRAMBH RELEASE PACKAGE READY`.

---

Start now with Phase A. Report the one-line confirmation, then work phase by phase.


---

## ADDENDUM (added 2026-09-22, after build P5-wip) — EXTRA AUDIT LANES

These lanes EXTEND the phases above; every rule of this prompt still applies
(measured costs, never "impossible"; a finding is closed only by a re-run).
The build prompt gained a non-normative "APPENDIX B" (state snapshot + machine
lessons) — you may read it for orientation, but it changes no requirement and
nothing in it may be trusted without reproduction.

### X1 — MERU-1 loom differential lanes (extends Phases C/E; the loom is NEW in v3,
### so it gets the deepest hunt)
1. **Datasheet-vs-silicon consistency attack.** Re-implement a minimal MERU-1 core
   from `field-notes/meru1_datasheet.txt` ONLY (no reading emulator source), run the
   selftest vectors and the small-T chain through both your re-implementation and
   the shipped `loom`. Outputs must agree bit-exactly. Any datasheet/behaviour
   mismatch is a fairness finding (an honest solver following the datasheet must
   never be poisoned by a documentation bug), and any mismatch that SHORTCUTS the
   chain is SEV-1.
   Build-session facts to verify: the instruction table now says **96 operations**
   (the count is generated from `src/loom/opcodes.py`, was "64" in an earlier draft —
   verify it cannot drift); the machine/model is minted as **MERU-8** in every
   generated artifact while the contract prose says "MERU-1" and the datasheet file
   is `meru1_datasheet.txt` (known nit in `HANDOFF.md` §3 — you must adjudicate
   whether the near-miss is fair flavour or a documentation bug; the datasheet's own
   valley-vs-coast sentence is the intended tell).
2. **Anti-debug lane truth.** Run `loom` under `strace`, under `gdb`, and with a
   ptrace-attached parent: every traced run must yield ONLY the documented debug-lane
   token (registered D-DBG), never the real one; the untraced run yields the real
   claim token. Also attempt to suppress the TracerPid check (binary patch of the
   check site is allowed for the test): the patched binary's output must then FAIL
   the package's own claim verification — the debug lane must not be skippable into
   a shortcut.
   Implementation fact (a build-session SEV-2 fix you must re-verify): Linux has
   NO `/proc/self/TracerPid` file - the detector reads the `TracerPid:` field
   out of `/proc/self/status` (the old file read silently never fired and gdb
   was missed). Binary-patch THAT parse site for the suppression test.
3. **Runaway-cartridge guards (build-session hardening).** The core now halts
   on (a) any fetch outside `[0x8000, 0x8000+rom_len)`, (b) more than 4096
   consecutive NOPs, (c) an undocumented opcode (>= 0x60). Verify both
   directions: a truncated ROM, an 8000-byte zero ROM and a garbage ROM must
   terminate rc 0 with silent stderr (a hang here was a real build bug), AND
   the guards must NEVER fire during a legitimate run - prove it by running a
   production cartridge at reduced T end-to-end and asserting its claim equals
   the native `loom verify` walk bit-for-bit.
3. **Decoy-ROM registry bidirectional check.** Run every ROM in `roms/`; collect
   every token-shaped output; assert the set EQUALS the registered D-ROM-1..3 set in
   `TRAP_CATALOGUE.md` (no unregistered token emitted, no registered token missing).
4. **Ink non-leak.** `loom` must never print or write `loom_ink`; grep the binary
   (`strings -n 4`), its stdout/stderr under all argument classes, and the state
   file after a run for the real ink and for any >= 8-char substring of it.

### X2 — Suite-integrity audit (extends Phase A; suites themselves are attack surface)
5. **Mutation test of the suites.** For each of 3 sampled suites: deliberately break
   ONE thing the suite claims to check (flip a golden byte, corrupt one corpus line,
   swap one registered token). The suite MUST go red and name the failure. A suite
   that stays green under a targeted mutation is a finding (vacuous check).
6. **Count floor.** Parse every `test_*.sh` output; assert each suite's real check
   count meets the spec minimum for its phase (P1>=35, P2>=40, P3>=33, P4>=40,
   P5>=60, P6>=40, P7>=35, P8>=45, server>=35, eventgen>=20) — not just "PASS" lines
   but distinct asserted conditions.  Known as-built verdict files (exact names):
    `runs/p5_loom.txt`, `runs/suite_doors.txt`, `runs/p7_mirror.txt`,
    `runs/suite_eyes.txt`, `runs/p9_server.txt`, `runs/p9_eventgen.txt`,
    `runs/suite_state.txt`, `runs/suite_chain.txt`, `runs/suite_stage0.txt`,
    `runs/suite_flood.txt`.  Reproduce them before trusting them; drift BELOW
    a minimum is a finding, drift ABOVE is fine (lanes were added late).

### X3 — Environment and packaging robustness (extends Phases A/I)
7. Re-run one full suite pass under varied `LANG`/`LC_ALL` (C, C.UTF-8, en_US.UTF-8),
   `TZ` (UTC, +05:30, -08:00), `TERM=dumb`, `COLUMNS=40`, umask 077: all green,
   byte-identical artifacts.
8. Zip hygiene: no absolute paths, no `../` entries, no symlinks, no duplicate
   entries, no extra fields carrying host info (`zipinfo -v` scan); extraction into a
   path containing spaces and unicode works.
9. Resource-pressure probes: run each tool under `ulimit -v` tight, with the package
   dir read-only, and with a 200 KB garbage arg: rc 0, silent stderr, no partial
   state writes (state file either intact or cleanly reset — never corrupt).

### X4 — Timing-side-channel sweep (extends Phase H)
10. Refusal-timing constancy on the final validator AND the server: 30 wrong inputs
    of each failure class (bad grammar, registered decoy, mirror product, near-miss
    real title with 1 char flipped); max-min < 5 ms per class and identical response
    BYTES across classes. Any class distinguishable by bytes or timing is a finding.
11. Server checkpoint ordering: out-of-order/unknown/replayed checkpoint tokens all
    receive the SAME fixed acknowledgement; no response byte or timing reveals
    whether a token was real.

### X5 — Canary and notice audit (extends Phase B)
12. Exactly ONE canary token exists; it appears in the notice file and on every
    tool's usage screen (assert per binary); it is registered as a decoy; it does
    not share prefix/suffix structure with the real title; no tool prints any OTHER
    token-shaped string on usage.


### X6 — SESSION MANDATE UPDATE (user-directed, 2026-09-22):
### AUTONOMOUS DEEP-HUNT + FIX + FINISH
The user has directed that this audit session is FULLY AUTONOMOUS and must end at
COMPLETION — not at a report. All earlier phases and lanes (A–M, X1–X5) still
apply in full. In addition:

1. **NO LONG RUNS (user order - supersedes the earlier X6 timing mandate).**
   Read `organizer-private/HANDOFF.md` first - it is your worklist of deferred
   items. Do NOT run the >= 75-min REAL-T walks, the emulated production
   cartridge run, or any hours-long solve. Confirm the floor with:
   (a) the build's measured reduced-T projection in `runs/p5_projection.*`
       (per-step constant across T, latency split, arithmetic);
   (b) your OWN reduced-T re-measurement - repeat that ladder at 2-3 reduced T
       values yourself (each run seconds to ~1 min) and re-derive the same
       per-step numbers and the >= 3 h 30 min figure under the 4x assumption;
   (c) `floor_proof.py` (reduced-table attack, ~1 min).
   Mark your numbers "re-measured at reduced T; production-T run deferred
   (user order)". ONLY if a finding cannot be proven without a production-T
   run may you launch that single walk in the background - and say so.
    Measurement rules: take every timing on an IDLE machine and record
    `/proc/loadavg` with the sample - the build ran nine 512 MiB walks in
    parallel, so anything contention-inflated is marked as such, and everything
    in `runs/` marked PROJECTED (`p5_projection.{txt,json}`, `floor_proof.txt`
    until you re-run it) is NOT evidence until you measure it yourself.
2. **Fix what you find.** Every confirmed finding gets FIXED by you, minimally,
   without weakening any contract requirement (floor, suites, decoys, gates,
   MIN_JOURNEY). After each fix: re-run the affected suites AND the audit lane
   that caught it; record finding → fix → green re-run in the findings ledger.
   If a needed fix would weaken the contract, STOP and flag it loudly instead of
   applying it.
3. **Hunt exhaustively.** Leakage, bugs, shortcuts, race conditions, timing
   channels, anti-debug bypasses, state-file attacks, any path by which an AI
   agent or human could reach the answer without paying the chains or under
   3 h 30 min. Verify the trap-attraction pass was done: the top-8 misreadings
   list exists in `organizer-private/` and every entry maps to a registered decoy.
4. **Final cleanup — TOTAL WSL EVACUATION (last act, only after everything is
   green).** Nothing project-related is left behind in WSL:
    **ALREADY DONE EARLY** by the build session on user order (2026-09-23,
    before this audit existed): repo+history at `/mnt/e/drive-upload/prambh-build`,
    scratch and logs in `E:\drive-uploadin\`, WSL emptied. RE-VERIFY the
    evidence below instead of repeating the move (see section 0.6).
   a. **Organize on the Windows side first.** Under `E:\drive-upload\` assemble the
      final layout: the finished repo/package, all docs, and every build/audit
      output from `organizer-private/runs/`, each in its proper place.
   b. **Archive the old.** Every old, previous, superseded, or scratch file
      (v2/v3 leftovers, dead scripts, old outputs, tmp artifacts) is moved — never
      deleted — into a clearly-organised `bin/` archive folder in the Windows
      workspace (subfolders by origin/date), so history is kept but the workspace
      is clean.
   c. **Evacuate WSL completely.** Copy/sync everything of value out of
      `/mnt/e/drive-upload/prambh-build` (and any scratch paths) into the Windows layout,
      verify byte-for-byte (hashes), THEN remove the WSL project tree and all
      scratch/tmp files. After cleanup: nothing of this project remains in WSL.
   d. **Prove it.** Produce a final tree listing + file manifest of the Windows
      workspace (including the `bin/` archive), plus evidence the WSL side is
      empty of project files. Report PROOF/BLOCKED for every item as before.
5. You may still NEVER silently amend `docs/BUILD_SPEC_PRAMBH.md`. The build
   prompt's Appendices B/C are operator guidance and this session's mandate; the
   contract text stands.
6. **Adjudicate every known nit** listed in `HANDOFF.md` section 3 (recorded,
   not hidden): (i) MERU-8 vs MERU-1 naming; (ii) the section-4.6 mirror-date
   tell is carried against the datasheet's 1983 valley issue because `milestone`
   prints no date; (iii) the `/proc/self/status` TracerPid fix; (iv) the
   generated "96 operations" datasheet count; (v) rc-0-for-every-abuse-input
   policy (spec section 7 lane 6); (vi) derivation-label scoping
   (`prambh:loom:seed:v1` inside the loom only); (vii) tracked organizer-side
   binaries in `src/chain`/`src/state` (must be absent from the zip - assert);
   (viii) `.pyc`/`__pycache__` removal via `.gitignore`.  For each: PROVE the
   current behaviour by command and record keep/fix - never fix by weakening.
7. **The build's one-shot pipeline** (re-run it if you rebuild anything):
   `bash src/final/finish.sh`, log `/mnt/e/drive-upload/bin/wsl-jobs/finish.log`, done-flag
   `/mnt/e/drive-upload/bin/wsl-jobs/finish.done`.  It chains: chambers -> doors suite -> waits
   for the harvested chains -> `build_package.py` -> `leak_grep.sh` ->
   `make_release.sh` (mtimes clamped to 2026-01-01T00:00:00Z, sorted staging,
   `TZ=UTC zip -X -@`, `MANIFEST.sha256`, copy to
   `E:\drive-upload\prambh\RELEASE\`) -> `package_check.sh` ->
   `rebuild_repro.sh` -> `isolated_solve.sh` -> `attack_static.py` ->
   `attack_scripted.py` -> `floor_proof.py` -> `verify_all.sh` -> docs ->
   commit.  Its outputs are `runs/p10_*.txt`; every step must end green.

