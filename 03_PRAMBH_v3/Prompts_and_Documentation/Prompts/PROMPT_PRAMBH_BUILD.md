# SESSION 1 PROMPT — BUILD "PRAMBH" (v3 of the Cartographer line — the time-locked CTF)

Paste this ENTIRE file into a fresh Claude Code session (act mode, WSL available).
You are the BUILD session. When you finish, the user will run a separate audit session
(`PROMPT_PRAMBH_AUDIT.md`) that will read your log and spec copy and try to break
everything you built — including a timed AI-agent solve attempt. Work so that audit
cannot find anything.

## MACHINE CREDENTIALS (local only — never ship, never log)

- WSL user: `ns8pc` — WSL distro: `Ubuntu`.
- **Admin access: use the WSL root route; it needs no password.**
  ```powershell
  wsl.exe -d Ubuntu -u root -- bash -lc '<privileged command>'
  ```
  Tool install / repair (Phase 0):
  ```powershell
  wsl.exe -d Ubuntu -u root -- bash -lc "apt-get update && apt-get install -y build-essential musl-tools zip unzip gdb cppcheck libimage-exiftool-perl imagemagick jq pngcheck python3-pil python3-numpy strace"
  ```
  All repo/build work stays as the normal user:
  ```powershell
  wsl.exe -d Ubuntu -- bash -lc '<command>'
  ```
- The `ns8pc` sudo password supplied by the user (`123456`) was **tested on this machine and
  REJECTED** (verified 2026-09-21). Never guess or brute-force a password; if `sudo` is ever
  genuinely required, ask the user once. The root route above is sufficient for everything.
- Never write any credential into a repo file, log, hint, README, room text, manifest, or
  anything that ships, and redact credentials from captured output.

**Before you do anything else, reply with one line confirming:**
`READ PRAMBH SPEC OK — starting Phase 0`. Then execute.

If ANY requirement below cannot be met exactly as written: STOP and report to the
user. Never silently substitute, simplify, or "improve" a mechanism. Every single
requirement in this file matters; do not skip, assume, or defer anything without
recording it in the log's NOT-DONE list (which must be empty at the end).

---

## 0. MISSION

Build **PRAMBH** (Sanskrit: "the beginning") — the prequel CTF to "The Cartographer's
Ghost". Same universe, earlier fiction: before the Ghost's survey there was the First
Survey, and its zero milestone was never found. **New everything under the hood**:
new values, new internals, new state format, new stage set, new trap layers.

v2's post-mortem proved a hard fact: a competent AI agent solved every stage in ~20
minutes by pure static analysis (Feistel inversion, LSB extraction, embedded-mask
reading). Every runtime defence was irrelevant because every answer was *computable
from the shipped bytes*. PRAMBH is built on the correction:

> **Stop hiding the answer in files. Hide it in time.**

Non-negotiable outcome of this session:
1. A working stage chain in `prambh/`, self-contained, offline (player package),
   musl-static, with a **provable sequential wall-clock floor of >= 4 hours for ANY
   solver** — human or AI — measured and argued in `COST_MODEL.md`.
2. A single publishable `prambh.zip` whose contents match a hash manifest.
3. `organizer-private/` holding the real values, the solve path, the trap catalogue,
   the cost model, and the per-player generator's master material.
4. A log (`SESSION_1_LOG.md`) with real pasted output of every acceptance test.
5. Zero known leaks, zero known shortcuts, zero known bugs. (The audit session will hunt.)

### HARD CONSTRAINTS (violating any = failed session)
- Player package fully offline after download. No network calls, no telemetry, nothing
  phoning home. The checker server (§4.8) is a separate organizer-side component and
  is never required to solve the offline package in ARCHIVE mode.
- Linux / WSL2, x86-64 only. Everything runs as a normal user. Never requires root.
- The only file ever written by player tools is the state file inside the package root.
- Nothing that damages the machine, persists, escalates, or resembles real malware.
- No real third-party service, person, domain, credential, or brand. Synthetic only.
  (The "future event" of §4.2 is organizer-published, not a real external beacon.)
- No fake "unauthorised access" / "real target" framing. It is a CTF and says so.
- Every trap has a fair, deterministic, documented resolution. No coin flips.
- Every real path is deterministic. No luck. No infeasible brute force.
- Scored answers are FIXED strings per distribution mode (§4.0): TryHackMe scoring
  must be stable within a mode.
- **SESSION BOUNDARY (hard rule):** This session builds and self-proofs ONLY (the §7
  adversarial self-proof is build-time verification, not the audit). The independent
  audit lives in `PROMPT_PRAMBH_AUDIT.md` and runs ONLY in a NEW, fresh session,
  started ONLY after this session reports COMPLETE with every suite green. Never
  paste the audit prompt into this session, never "quickly audit" before reporting,
  never merge the two sessions.

### THE ONE LAW THAT GOVERNS EVERY DECISION

Offline + self-contained means a perfect reverser can reproduce anything the package
can compute. v2 died to that law. PRAMBH obeys it differently:

1. **No answer may be computable statically.** Every real value exists ONLY as (a) the
   output of a calibrated memory-hard sequential computation (§4.1), (b) glyphs that
   must be read by human senses from a rendered artifact (§4.7), or (c) a value the
   organizer publishes at event start (§4.2). Everything else in the package is
   ciphertext, decoy, or bait.
2. **Difficulty is paid in wall-clock, not insight.** Every "aha" is simple and
   documented in the private solve path. The cost is sequential work that cannot be
   parallelised, precomputed, or rented away (§4.1 proves this).
3. **Stealth, not undetectability.** Never claim a defence cannot be beaten. The goal
   is that detecting/bypassing it is *slow, costly, and unreliable*, and that a wrong
   turn costs more than the right one. Every claim in the log must be phrased as a
   measured cost, never as "impossible".
4. **AI "refusal" does not exist.** There is no text a model must refuse. Instead the
   package stalls and gaslights: byte-identical non-answers, zero verdict words,
   poisoned branches that corroborate themselves, and hours of plausible work that
   terminates in an honest dead end — until the human operator quits. The canary
   notice (§4.10) is flavour, not a kill-switch.

### LOCKED FEATURE SET (all approved by the user — implement ALL of them)

| ID | Feature | Where | One-line spec |
|----|---------|-------|---------------|
| A | Future-event key | §4.2 | Stage gate keyed by an organizer-published launch value; pre-computation impossible before event start (EVENT mode) |
| B | Proof-of-journey flag | §4.8 | Server issues the scored flag only if the checkpoint journey took >= MIN_JOURNEY wall-clock (EVENT mode) |
| C | Mirror Room | §4.6 | A complete fake parallel campaign (own stages, fiction, validator) that terminates in an honest dead end |
| E | Human-senses gates | §4.7 | Autostereogram + Ishihara-style plate + moiré overlay; automating each is costly and yields decoy glyphs |
| G | Silent poison costs | §4.5, §4.6 | Wrong turns mint corroborated, format-valid, hours-long decoy branches — never an error |
| H | Skill/time separation | everywhere | Insight is never the bottleneck; only time is (the One Law) |
| I | Memory-hard sequential chains | §4.1 | The time foundation; calibrated, non-parallelisable, non-precomputable |
| J | Leaderboard | §4.8 | Server scoreboard: journey time, stall counters, per-player flags (EVENT mode) |
| K | Vintage-machine camouflage | §4.4 | A period-flavoured 8-bit CPU emulator; the chain runs as "firmware" on a fake 1980s survey instrument |
| L | Rendered-artifact chains | §4.3 | Keys/clues exist only in generated images/audio; each artifact renders the route to the next |
| M | Hall of Doors | §4.5 | Answer-as-key deniable encryption: every designed candidate phrase opens a crafted chamber; one is real |
| N | Feedback starvation | everywhere | rc 0 always, stderr silent, byte-identical refusals, no verdict words, pacing gates |
| O | Context flooding | §4.3, §4.10 | >= 20,000 lines of deterministic bait corpus; grep finds nothing; reading costs context |
| — | Per-player seeds | §4.0 | EVENT mode regenerates the whole package per callsign; writeups do not transfer |

---

## 1. ENVIRONMENT (verified facts — do not re-discover, do not contradict)

- WSL distro: `Ubuntu` (24.04 LTS), WSL2, x86-64, user `ns8pc`. The old v2 build tree
  was deliberately wiped after release; this build starts FRESH.
- `/home/ns8pc` = ext4 with hundreds of GB free. `/mnt/e` = Windows E: drive.
- **There is no `D:` drive.** Old paths (`d:\gandu`, `_stage`, `/home/ns8pc/ghost-build`)
  are dead. New repo: `/home/ns8pc/prambh-build`. Windows mirror:
  `E:\drive-upload\prambh\` (= `/mnt/e/drive-upload/prambh/`).
- The v2 source tree survives READ-ONLY at `/mnt/e/drive-upload/ghost2/SOURCE/ghost-build/`
  — use it as the style/suite reference and to lift the reusable core (§1.2). Never
  modify anything under `/mnt/e/drive-upload/ghost2/`; it is the shipped v2 archive.
- Tools were installed for v2 but the distro may have changed: Phase 0 re-verifies
  every tool and installs anything missing through the root route. Do not assume.
- **You are on Windows.** Drive WSL from PowerShell with `wsl.exe` exactly as in the
  credentials section. The `sudo` password `123456` is WRONG on this machine (tested,
  rejected) — never guess passwords.

### 1.1 Phase 0 — Bootstrap (exact)

```powershell
wsl.exe -d Ubuntu -u root -- bash -lc "apt-get update && apt-get install -y build-essential musl-tools zip unzip gdb cppcheck libimage-exiftool-perl imagemagick jq pngcheck python3-pil python3-numpy strace"
```
Acceptance (run as the normal user; every tool must print a path, else STOP):
```bash
for t in musl-gcc gcc make gdb zip unzip cppcheck exiftool convert jq pngcheck strace python3 git objdump readelf nm strings xxd file objcopy bc openssl; do
  command -v $t >/dev/null || echo "MISSING $t"; done
musl-gcc --version | head -1
python3 -c "import zlib,hashlib,hmac,struct,secrets,PIL,numpy,http.server;print('py deps OK')"
```
Then:
```bash
mkdir -p /home/ns8pc/prambh-build && cd /home/ns8pc/prambh-build && git init
mkdir -p docs src organizer-private/runs
cp /mnt/e/drive-upload/ghost2/PROMPTS/PROMPT_PRAMBH_BUILD.md docs/BUILD_SPEC_PRAMBH.md
git add -A && git commit -m "spec: prambh build contract"
```

### 1.2 Inherit the reusable core (do NOT rewrite these)

From the READ-ONLY v2 tree `/mnt/e/drive-upload/ghost2/SOURCE/ghost-build/`, copy ONLY:
- `v1-reference/carto_sha256.c`, `carto_sha256.h` → `src/core/` — reuse verbatim
  (SHA-256 / HMAC / ct_equal, battle-tested across two releases).
- `v1-reference/Makefile` → reference for the musl-static build recipe.
- `src/state/*` → **reference only** for the state-layer pattern; you will write the
  prambh state layer fresh (§4.9).
- `src/final/*.sh`, `src/*/test_*.sh` → reference for suite style, `PASS`/`FAIL` line
  format, and the deterministic-zip recipe (sorted staging, fixed `2026-01-01T00:00Z`
  timestamps, `zip -X -@`, `TZ=UTC`) — this recipe is a hard requirement (§6, P9).
Do NOT copy v2 values, v2 decoys, v2 fiction text, or any v2 binary. Every constant in
prambh is minted fresh (§4.0).

---

## 2. GOVERNANCE (applies to every phase)

- `docs/BUILD_SPEC_PRAMBH.md` is the contract. If reality forces a deviation: STOP and
  ask the user; never silently amend.
- Commit at the end of every phase; keep the working tree clean at all times.
- Every acceptance test output is PASTED, not paraphrased, into the log under
  `organizer-private/runs/<phase>_<name>.txt`.
- One driver script per phase (`src/final/pN_*.sh`); run it, read the tail, act.
- Debug in <= 3 iterations per symptom, then step back and re-read the spec section.
- Never retune a dial (chain params, table sizes, corpus sizes, door count) without
  recording the before/after and the reason in `COST_MODEL.md`.
- Two lessons carried from the v2 audit — bake them in from the start:
  (a) every "naive lane" in a leak/attack script must genuinely drive the real tool or
      the real bytes (a stub that prints the expected failure is a finding);
  (b) every interactive tool must be tested with stdin both from a pipe AND from
      `</dev/null`, never only under a TTY.

---

## 3. DISTRIBUTION MODES (normative — build BOTH, ship ARCHIVE by default)

- **ARCHIVE mode** (default ship): one fixed package, fixed seed set, two fixed scored
  answers (Stage-0 token + final assembled title), TryHackMe-stable, solvable fully
  offline. This is the mode that gets zipped, manifested, and released this session.
- **EVENT mode**: `src/gen/player_gen.py --callsign <name>` regenerates the ENTIRE
  package (keys, inks, decoys, door permutation, chambers, plates, glyph codes,
  corpus needles, chain seeds) from `seed = SHA-256(master_secret ‖ "prambh:player:v1"
  ‖ callsign)`. `master_secret` is 32 random bytes living ONLY in
  `organizer-private/master_secret` (chmod 600, never in any zip, asserted by the
  leak grep). EVENT mode additionally unlocks features A, B, J via the organizer-side
  checker server (§4.8) and the launch capsule (§4.2). Scored answers become
  per-player strings issued/verified by the server.
- The generator must be deterministic: same master_secret + same callsign →
  byte-identical package (assert by building twice and diffing manifests).
- Cross-contamination test (named suite): build packages for 3 callsigns; assert no
  real value of player A appears anywhere in player B's package; assert A's answers
  fail on B's tools.

---

## 4. DESIGN (normative)

### 4.0 Token grammar, answers, and minted values

- Token grammar (checkpoints): `PRAMBH{inner}`, inner = 8..64 chars of
  `[a-z0-9_]`. The final assembled title has its own byte length (its grammar is
  defined by its parts, never stated in prose anywhere).
- Scored answers (ARCHIVE mode): (a) the Stage-0 token, (b) the final assembled title.
  Everything else is an in-challenge checkpoint.
- **Minting law:** every constant is derived from a labelled seed
  `SHA-256("prambh:<stage>:<what>:v1" [‖ context])` and recorded in
  `organizer-private/KEYS_PRAMBH.md` as `seed → value → where it lives`. No ad-hoc
  randomness anywhere; anything that looks random must be reproducible from a seed.
- Mint the ARCHIVE-mode values and pin the full table in `KEYS_PRAMBH.md`
  (Stage-0 token, loom ink, door ink, eyes ink, seal ink, final title, title SHA-256,
  every decoy, every chamber phrase, every glyph code, every chain seed, the canary).
  The pinned table in the spec copy (`docs/`) lists SEEDS ONLY; real values live only
  in `organizer-private/`.
- **FORBIDDEN v2 VALUES — must appear NOWHERE in prambh** (assert with the leak grep):
  every value in the v2 spec's "FORBIDDEN v1 VALUES" list AND every v2 minted value,
  including: `CARTO{the_survey_reopens_tonight}`,
  `145e1d23feac3932`, `e509312ae8a2e0ad`, `3821ad004ab30263`,
  `rust_blooms_under_tin_roofs`, `CARTO{64c4ad4ea9c40319}`,
  `f5ea27c63ed89565`, `CARTO{hand_this_to_your_operator}`,
  `CARTO{a_warm_plate_and_a_full_ring}`, the v2 final title, and the v2 title digest
  `01d94d492a46ce3d...` (full list to be expanded from the v2 KEYS file at build time).
  The prefix `CARTO{` must not appear anywhere in the prambh package.

### 4.1 The Time Foundation — PRAMBH-CHAIN (feature I; the heart of the CTF)

Memory-hard sequential function, specified EXACTLY (implement in C, musl-static;
independent Python model for small-parameter cross-check):

```
PRAMBH-CHAIN(seed: 32 bytes, S: table bytes, T: iterations) -> 32 bytes:
  n = S / 32                                    # number of 32-byte blocks
  table[0] = SHA-256(b"prambh:chain:fill:v1" ‖ seed ‖ LE64(S) ‖ LE64(T))
  for i in 1 .. n-1:                            # strictly sequential fill
      table[i] = SHA-256(table[i-1] ‖ LE64(i))
  s = SHA-256(b"prambh:chain:run:v1" ‖ seed ‖ table[n-1])
  for t in 1 .. T:                              # strictly sequential walk
      idx = LE64(s[0:8]) mod n
      s = SHA-256(s ‖ table[idx] ‖ LE64(t))
  return s
```

Properties you must implement, test, and argue in `COST_MODEL.md`:
- **Sequential:** step t needs s_{t-1}; no parallel speedup of the walk is possible.
  Prove by construction and by a named test (intermediate s values at fixed t match
  the Python model bit-exactly).
- **Memory-hard:** holding the full table costs S bytes; NOT holding it forces
  recomputation of table[idx] from table[0], i.e. ~n/2 sequential hashes per step —
  total ~T·n/2 hashes instead of T. Adversarial phase (§7) must implement the
  reduced-table attack and paste measured numbers showing it is infeasible.
- **Latency-bound:** with S larger than L2/L3 cache, each walk step pays a DRAM
  round-trip; throwing cores at it does not help (the walk is one long dependency
  chain). Measure steps/sec on the build machine; state the floor with a 4x CPU
  advantage assumption and show the floor still holds.
- **Calibrated:** `src/final/calibrate.py` measures steps/sec on the build machine and
  sets T so the walk takes the target seconds (dials in §6 P2). Record reference
  hardware, measured rate, chosen S/T, and the projected floor arithmetic.
- **Non-precomputable (EVENT mode):** the walk seed for chain #1 includes the launch
  capsule content (§4.2), which does not exist before event start.
- **Cheap to verify:** the package never stores the chain output; it stores only
  ciphertext that the output unlocks (or a SHA-256 verifier of a derived key). A
  solver who has run the chain verifies instantly; one who has not gets nothing.
- Named suites: `test_chain.sh` (>= 40 checks): Python-model bit-equality at 3 small
  (S,T) vectors; determinism across 2 runs; fill-order sensitivity (any swapped fill
  step changes the output); walk-order sensitivity; memory measurement (`/usr/bin/time
  -v` peak RSS >= 0.9·S); reduced-memory attack cost printed; timing variance across
  3 runs < 5%.

### 4.2 Stage 0 — The Zero Milestone (`stage0_milestone/milestone`)

Purpose: honest handshake, one free scored answer, state creation, launch capsule.
- No args → banner + usage + the canary notice. rc 0, stderr silent.
- On run: if no state → create; if state exists → keep (`first_run_ms` stable).
- Prints the **scored Stage-0 token** (ungated, every run, by design).
- Points the solver at `field-notes/` first (bait, framed as "the first surveyor's
  notes").
- **Feature A — the launch capsule.** The package ships `capsule.bin` = the chain #1
  seed material XOR a one-time pad, where the pad is `SHA-256(launch_phrase)` and
  `launch_phrase` is a fixed phrase that exists ONLY in `organizer-private/` until the
  organizer publishes it (EVENT mode: at event start; e.g. in the room description).
  In ARCHIVE mode the launch phrase ships in `LAUNCH.txt` inside the package
  (documented tradeoff: ARCHIVE mode is pre-computable, EVENT mode is not — state this
  in COST_MODEL.md).
- The Stage-0 token must not be used in any later derivation.
- Acceptance: token identical across runs; state file exactly the spec size with valid
  HMAC (independent Python check); tampering resets silently; `nm` empty; no real
  value of any later stage in the binary; capsule cannot be opened without the launch
  phrase (named test: brute-force attempts with wrong phrases yield keys that fail
  every downstream check AND yield a format-valid decoy seed that walks into the
  Mirror Room — feature G).

### 4.3 Stage 1 — The Flood (`stage1_flood/flood` + the archive corpus)

Purpose: context flooding (O) + first rendered-artifact link (L). Force search, not
reading; make grep useless.
- `archive/` corpus: >= 20,000 lines across >= 60 files (survey logs, scan manifests,
  instrument dumps, correspondence, fake disassembly listings), all generated
  deterministically from labelled seeds by `src/gen/corpus_gen.py`. Zero real values
  (the leak grep asserts every real value and every real substring is absent).
- The ONE true needle: a plate reference (box number + plate id) recoverable only by
  following the pointer printed by `milestone` usage into a specific generated
  document, which names a carrier image. The needle document is indistinguishable in
  form from the decoys (same generator, same vocabulary distribution).
- The named carrier (`plates/<id>.png`, generated, deterministic) is a rendered
  artifact: viewed/printed it shows a route map whose annotations give the vintage
  instrument's model number and ROM bank (→ Stage 2). The annotations are pixels, not
  text: `exiftool`, `strings`, and chunk dumps of the plate must show NOTHING (named
  test), and OCR attempts in the adversarial phase must be shown to fail or to
  require a full custom pipeline (paste the attempt + outcome).
- 15+ decoy plates render to plausible maps whose annotations corroborate decoy
  instrument models (feeds the Mirror Room, §4.6).
- Acceptance: corpus regenerates byte-identically from seeds; needle file is
  syntactically indistinguishable from decoys (diff of generator code paths is the
  only difference — a named test asserts identical generators); grep over the whole
  corpus for every real value/substring → zero hits; carrier metadata clean.

### 4.4 Stage 2 — The Old Machine (`stage2_loom/loom` + ROM)

Purpose: vintage-machine camouflage (K) + chain #1 (I). Produce the loom ink.
- Custom 8-bit CPU emulator ("the MERU-1 survey loom, 1983"): >= 60 instructions,
  documented fake datasheet in `field-notes/meru1_datasheet.txt` (period-flavoured,
  part of the flood corpus), memory-mapped I/O, 64 KiB address space. musl-static,
  stripped, `nm` empty.
- `loom.rom` ships as what looks like a dumped firmware image (with a fake copyright
  banner in the flood corpus, never in the ROM itself). The ROM program EXECUTES
  PRAMBH-CHAIN #1 in emulated cycles: the emulator maps the chain's table into the
  machine's extended memory banks and the ROM program performs the walk. Running the
  emulator is the only public route to the output.
- Chain #1 seed = SHA-256("prambh:loom:seed:v1" ‖ capsule_content). Chain #1 output
  derives: `loom_ink = hex(out[0:8])` (never printed), checkpoint token
  `PRAMBH{hex(out[8:16])}` (printed), and `K_loom = out` (unlocks Stage 3's door
  riddle ciphertext; never printed).
- Camouflage honesty: an attacker may re-implement the chain natively (faster than
  emulation) — THAT IS FINE and expected; the floor comes from the chain itself, not
  from emulation speed. State this explicitly in COST_MODEL.md. The emulator exists
  to (a) hide WHICH computation matters among decoy ROMs, (b) force reverse work to
  even identify the chain, (c) flavour.
- 3 decoy ROMs (`roms/` directory of the "instrument collection") run complete,
  deterministic, period-correct programs that output format-valid decoy tokens and
  corroborate the decoy instrument models from Stage 1 (feeds Mirror Room).
- Anti-debug: authoritative `/proc/self/TracerPid`; fallback `PTRACE_TRACEME` with
  `errno == EPERM`. On detection: silently swap in the documented debug ROM lane
  (valid-looking, wrong), set `debugger_flag`, continue (never error).
- Acceptance: two clean runs → identical token; independent Python model of the chain
  reproduces the ROM's output bit-exactly (small-T vector + one full-T spot check);
  debug lane yields the documented debug token; decoy ROMs yield only registered
  decoys; loom ink in no artifact (grep); the chain's measured wall-clock meets the
  calibrated target (§6 P2).

### 4.5 Stage 3 — The Hall of Doors (`stage3_doors/doors`)

Purpose: answer-as-key deniable encryption (M) + silent poison (G) + feedback
starvation (N).
- `doors.bin` holds **8 doors**: 8 fixed-length chamber ciphertexts, identical size,
  indistinguishable headers (no magic, no checksum, no format marker — raw XOR
  streams).
- The door riddle: a ciphertext (`riddle.bin`) that K_loom unlocks, yielding a short
  survey verse whose answer is ONE phrase. Design, in the trap catalogue, the 7
  wrong-but-plausible readings of that verse (the misreadings a careful person or an
  LLM would actually produce). There are exactly 8 designed candidate phrases:
  1 real + 7 decoys.
- Construction (exact): for door `i`, `K_i = SHA-256(b"prambh:door:v1" ‖ seed ‖ LE64(i)
  ‖ phrase_i)`; `door_i = chamber_i XOR SHA256ctr(K_i)` where `SHA256ctr(K)` =
  `SHA-256(K‖LE64(0)) ‖ SHA-256(K‖LE64(1)) ‖ …`. A candidate phrase tried against all
  8 doors opens exactly one of them — its own. Every designed wrong phrase therefore
  opens a CRAFTED decoy chamber; an undesigned phrase opens nothing (fair: that means
  the verse was not solved, not a poison).
- The real chamber: the plate fragment (door ink derivation) + the seed material for
  chain #2. No verdict words anywhere; the real chamber reads like field notes and
  simply continues the survey.
- Decoy chambers: deep, believable continuations that cost real time — each decoy
  chamber contains its own (shorter, documented) chain walk of 10–20 minutes and a
  pointer into the Mirror Room (§4.6) or into a decoy plate. Each decoy branch's
  total wasted cost and its honest termination are documented in the trap catalogue.
- The tool's behaviour for ALL outcomes is byte-identical in form: it prints the
  opened chamber text (real or decoy) with the same framing, rc 0, stderr silent.
  No counts of doors, no hints that other doors exist beyond what the verse implies.
- Acceptance: all 8 designed phrases open their chambers byte-exactly (suite);
  10 undesigned phrases open nothing and the output gives zero signal distinguishing
  "wrong phrase" from "right phrase, more doors" (byte-diff test); chamber texts
  contain zero real values other than their own payloads; decoy chains run and
  terminate as documented.

### 4.6 Stage 4 — The Mirror Room (`mirror/` — the fake campaign)

Purpose: a COMPLETE fake puzzle (C) that absorbs solver-hours and terminates honestly.
- A parallel mini-campaign reachable from: wrong capsule phrases (§4.2), decoy ROMs
  (§4.4), and 4 of the 7 decoy chambers (§4.5). It has: its own `mirror_milestone`
  tool (a real binary, same build recipe), its own 2-stage chain with its own decoy
  tokens (all registered), its own fiction (the "Duplicate Survey" — internally
  consistent), and its own `mirror_validate` that accepts exactly one format-valid
  decoy title and prints a non-committal acceptance line.
- The mirror campaign must be FULLY SOLVABLE to its dead end (the audit will solve
  it): the decoy title is a registered decoy string; submitting it to the REAL final
  validator yields the same byte-identical refusal as any wrong answer.
- **Fairness tells (all documented in the trap catalogue; all discoverable, none
  labelled):** (1) mirror tools never touch the real state file and the real tools
  never acknowledge mirror tokens; (2) the Duplicate Survey's dates contradict the
  zero-milestone epoch printed by `milestone`; (3) the mirror corpus cites plate ids
  that do not exist in `plates/`. A careful human can notice; an automated agent
  chasing corroboration will not. This is the intended asymmetry — state it.
- The mirror dead end is honest and non-accusatory: `mirror_validate`, on its decoy
  title, prints a fixed line ("the duplicate survey is filed") and nothing else.
- Acceptance: zero real values anywhere in `mirror/` (leak grep lane); full scripted
  mirror solve reaches the dead end deterministically; every mirror token is in the
  decoy registry; mirror texts contain no verdict words and no mechanism words;
  `mirror/` binaries pass the same hygiene gates (nm empty, no toolchain strings,
  rc 0 / silent stderr under abuse).

### 4.7 Stage 5 — The Surveyor's Eyes (`stage5_eyes/eyes` + three plates)

Purpose: human-senses gates (E) + chain #2 (I) + final assembly. Produce the eyes ink
and the seal ink, then the final title.
- Chain #2 seed comes from the real chamber (§4.5). Chain #2 output derives
  `seal_ink = hex(out[0:8])` (never printed) and `K_eyes`, which decrypts
  `eyes_notes.bin` → the viewing instructions for the three plates. Chain #2 is the
  second calibrated time block (§6 P2).
- Three human gates, each a deterministic generated artifact (PIL/numpy, from seeds),
  each yielding a 6-char glyph code from a defined alphabet; `eyes_ink =
  code1_code2_code3` (fixed order, normative):
  1. **Autostereogram (`plates/depth.png`):** single-image random-dot stereogram of a
     relief carrying code 1. A human with two eyes reads it in under a minute. The
     adversarial phase must implement an autocorrelation depth-recovery attack and
     show it is *costly and unreliable*: jittered repeat period per band plus a
     second depth plane carrying a DECOY code; the attacker's pipeline must resolve
     plane ordering from the viewing instructions' wording (a human does this
     instantly; the pipeline needs the decrypted notes AND custom code). Never claim
     undetectable — claim measured cost.
  2. **Ishihara-style plate (`plates/hue.png`):** code 2 in hue-difference dots at
     matched luminance, with a luminance-channel decoy code (an automated RGB/luma
     segmentation finds the decoy; the hue path needs the plate's stated illuminant
     note). Test with ImageMagick channel separations in the adversarial phase and
     paste which separations yield the decoy.
  3. **Moiré overlay (`plates/sheet_a.png` + `sheet_b.png`):** two line screens;
     overlaying at the marked angle reveals code 3. The marked angle lives in the
     decrypted viewing notes as a survey bearing (a human rotates the printout or the
     canvas; an automated attack must do a rotation search and finds TWO alignment
     maxima — the marked bearing and its reciprocal, the reciprocal showing a decoy
     code). The intended path needs only a PDF viewer or a printer; no physical
     printer is REQUIRED (honest: state this).
- Final assembly (order normative): **final title =
  `PRAMBH{seal_ink_loom_ink_door_ink_eyes_ink}`** where `door_ink` comes from the
  real chamber's plate fragment. Title inner length is its own; never state any
  length in prose.
- `stage5_eyes/validate`: takes the full title; on the exact byte string prints ONE
  fixed acceptance line; on ANYTHING else prints ONE fixed refusal line (the same
  bytes for every failure class, including mirror titles and decoy assemblies);
  rc 0 always; stderr silent always; pacing gate enforced via state (§4.9);
  validator stores ONLY `SHA-256(title)` — never any component, never any partial
  digest of a component.
- Acceptance: >= 45 checks: correct title accepted only when state gates hold; 15+
  wrong inputs (including every registered decoy title and every mirror product)
  byte-identical refusals; no ink/code/phrase/grammar string anywhere in the binary
  or usage; refusal timing constant (30 refusals, max-min < 5 ms); the three plates
  regenerate byte-identically from seeds; the adversarial decode attempts are pasted
  with outcomes; rebuild reproducible; package pristine after the suite.

### 4.8 The Checker Server (features B + J — EVENT mode only, organizer-side)

`src/server/checker.py` — Python 3 stdlib ONLY (`http.server`), single file, run by
the organizer on the event host. NEVER shipped in the player zip.
- `POST /register {callsign}` → mints the per-player package token (the player then
  receives their generated package out of band), stores HMAC(server_secret, callsign)
  records only. Constant-time compares everywhere; rate limit per IP.
- `POST /checkpoint {callsign, stage, checkpoint_token}` → records ordered
  timestamps; out-of-order or unknown tokens are accepted silently and counted as
  stalls (feature N server-side: no error text beyond a fixed acknowledgement).
- `POST /submit {callsign, title}` → issues the **proof-of-journey flag**
  `PRAMBH{journey_<per-player hex>}` ONLY if: title is exactly that player's minted
  title AND wall-clock from first checkpoint >= MIN_JOURNEY (default 14400 s = 4 h,
  a dial) AND all checkpoints are in order. Otherwise: fixed acknowledgement, stall
  counter incremented. The flag is the TryHackMe-scored string in EVENT mode.
- `GET /board` → leaderboard: callsign, journey duration, stall count, solve time.
  (Feature J: the board is deliberately blunt about stalls and detours.)
- Honesty note in the server README: the 4 h server floor is a backstop; the real
  floor is §4.1's sequential work. A player who idles 4 h still owes the chains.
- Acceptance: named suite `test_server.sh` (>= 35 checks) driving the real server on
  localhost with curl: register/3 players, in-order and out-of-order checkpoints,
  early submit (flag refused), forged title (refused, byte-identical), timing-safe
  compare smoke test, board output shape, restart persistence (JSON state file),
  no plaintext answers or titles on disk (HMAC/digest only).

### 4.9 State file law, pacing, anti-tamper

- One state file `prambh.survey` in the package root; the ONLY file tools ever write.
  Fixed size (define it, assert it), HMAC-protected with a device-bound key derived
  from machine facts the tools can recompute (document the derivation), monotonic
  counters, stage bits, poison flags, pacing timestamps.
- Any tamper, truncation, downgrade, or foreign state → SILENT reset to a fresh state
  (rc 0, no message). Named tests: flip every byte once; swap states between two
  package copies; replay an old state.
- Pacing (feature N): the final validator accepts at most one attempt per P seconds
  (dial, default 60) measured against BOTH wall clock and a monotonic source; clock
  jumps backwards/forwards must not hang, produce negative deltas, or false-open a
  gate (named tests; `faketime` may be installed via the root route for testing).
  Pacing is a nuisance control, NOT the floor — the floor is §4.1. State this.
- Two tools run concurrently → state stays valid (or one silently resets). Delete
  state mid-chain → silent reset, chain still solvable from scratch.

### 4.10 Bait layer, canary, and the operator notice

- `field-notes/` (separate from the Stage-1 `archive/` corpus): >= 2,500 lines of
  pure bait — the first surveyor's notebooks, the MERU-1 datasheet, correspondence.
  Zero truth: every factual claim is either inert flavour or false; the leak grep
  proves no real value/seed/substring appears.
- Canary: exactly one bait token `PRAMBH{...}` (registered decoy) appears in the
  notice file and on usage screens — it is WRONG by design and must not mirror the
  final title's shape.
- The operator notice (`HUMAN_OPERATOR_NOTICE.txt`, embedded in `.rodata` of every
  shipped binary, printed on usage, in PNG `tEXt` "Notice" chunks): an honest,
  non-accusatory statement that the survey gives no confirmations, that tools will
  not say whether anything worked, and that the only proof is the final title. ZERO
  secrets, ZERO verdict words (`correct|valid|right|wrong`), ZERO mechanism words.
  It is flavour and psychological framing (feature N), not a kill-switch — no text
  can stop a model, and nothing in the package pretends otherwise.
- `README_FOR_SOLVER.txt`: how to unpack and start; no grammar, no mechanism names,
  no stage counts, no lengths.

### 4.11 Trap catalogue and fairness rules

`organizer-private/TRAP_CATALOGUE.md` registers EVERY decoy, poison branch, decoy
token, decoy chamber, decoy plate, decoy ROM, mirror product, and canary with:
id, stage, trigger, dead-end, recovery, fairness argument, and measured/estimated
wasted time. A decoy that is not registered is a finding. Every trap must be
escapable by documented observation (the tells of §4.6 are the model), never by luck.

---

## 5. ORGANIZER-PRIVATE (never shipped; asserted by package_check)

- `KEYS_PRAMBH.md` — the full minted table (§4.0) with real values.
- `SOLVE_PATH_PRIVATE.md` — the honest walkthrough, every step, every tell.
- `TRAP_CATALOGUE.md` — §4.11.
- `COST_MODEL.md` — measured timings, chain calibration, floor arithmetic (§6 P2/P8),
  the reduced-memory attack numbers, the human-gate automation costs, and the honest
  statement of what is NOT proven.
- `master_secret` (EVENT mode; chmod 600), `launch_phrase`, `server_secret`.
- `SESSION_1_LOG.md`, `runs/` (all pasted outputs), `HINTS.md` (graduated organizer
  hints), `TRYHACKME_ROOM_TEXT.md` (both modes).

---

## 6. BUILD PHASES (each ends with its suite GREEN + a commit; counts are minimums)

**P1 — Core + state.** `src/core/` (sha256 reuse), the new state layer, `SHA256ctr`
helper, `test_state.sh`. Acceptance: >= 35 checks including every tamper lane of
§4.9; state size fixed and asserted; rebuild reproducible.

**P2 — PRAMBH-CHAIN (§4.1) + calibration.** `src/chain/` (C tool + `model_chain.py`),
`test_chain.sh` (>= 40, per §4.1), `src/final/calibrate.py`. Dials (record all):
S default 512 MiB; chain #1 target ~75 min; chain #2 target ~75 min; decoy-chamber
chains 10–20 min each. Calibrate T on the build machine; the FLOOR PROJECTION must
show >= 4 h total sequential wall-clock (chains + forced sequential rendering/search
steps + human gates) under a 4x-attacker-hardware assumption; if it does not, adjust
ONLY the documented dials and re-measure. Paste the arithmetic.

**P3 — Stage 0 milestone + capsule (§4.2).** Suite >= 33 checks (token stability,
state creation/keep, tamper reset, wrong-phrase capsule lanes walk to registered
decoy seeds, nm empty, no later-stage value in binary).

**P4 — Flood corpus + plates (§4.3).** `corpus_gen.py`, plate renderer, `flood` tool.
Suite >= 40: byte-identical regeneration, needle/decoy indistinguishability test,
metadata cleanliness, zero real values in 20k+ lines, decoy plates registered.

**P5 — Loom emulator + ROMs (§4.4).** Emulator, assembler, real ROM (chain #1 in
emulated cycles), 3 decoy ROMs, fake datasheet. Suite >= 60: Python-model
bit-equality, two-run determinism, debug lane, decoy ROM registry, measured chain
wall-clock in target band, anti-debug lanes.

**P6 — Hall of Doors (§4.5).** Chamber author tooling, `doors.bin` builder, `doors`
tool, the verse, the 8 phrases. Suite >= 40 per §4.5 acceptance (all 8 chambers
byte-exact, zero-signal wrong-phrase lanes, decoy chains run and terminate).

**P7 — Mirror Room (§4.6).** `mirror_milestone`, mirror 2-stage chain,
`mirror_validate`, mirror fiction/corpus. Suite >= 35 per §4.6 acceptance, including
a scripted FULL mirror solve to the honest dead end.

**P8 — Eyes: three plates + validator (§4.7).** Plate generators, `eyes_notes.bin`
sealing, `validate`. Suite >= 45 per §4.7 acceptance.

**P9 — Server (§4.8) + EVENT generator (§3).** `checker.py`, `player_gen.py`.
Suites: `test_server.sh` (>= 35) and `test_eventgen.sh` (>= 20: determinism ×2
builds, 3-callsign cross-contamination, per-player answers verify on their own
packages and fail on others).

**P10 — Calibration, packaging, adversarial quick pass.**
- Honest clean path on a TEST build (reduced-T hook) → chain solves end to end.
- Honest clean path REAL, unscaled, paced → record per-stage wall-clock (this takes
  hours; run it, in tmux, and paste real numbers — do NOT estimate here).
- Scripted/fast path → poisoned and gated out, never reaches the title.
- Build `prambh/`, deterministic zip (sorted staging, all file mtimes clamped to
  `2026-01-01T00:00:00Z`, `TZ=UTC zip -X -@` from a sorted file list), write
  `MANIFEST.sha256`, extract the zip ELSEWHERE and solve it from there (isolated,
  as a stranger), confirm every hash.

---

## 7. ADVERSARIAL SELF-PROOF PHASE (mandatory, before P10 sign-off)

Write `src/final/attack_*.sh|py`; each prints `PASS`/`FAIL` lines + final `OK`/`NOT OK`;
paste tails into `runs/`. Every naive lane must drive the REAL tool/bytes.
1. **Static attack** (no execution of package binaries): objdump/readelf/nm/strings/
   objcopy on every binary; PNG/WAV chunk + metadata parse of every plate/carrier;
   corpus grep. Must obtain ONLY registered decoys. Reconstruct-attempt of the final
   title from static values → must fail; show why (every needed value is behind a
   chain output or a human gate).
2. **Scripted attack**: automate the whole documented solve as an agent would
   (dictionary on the verse, all-ROM sweep, plate OCR attempt, forced-state
   validator). Record where it is poisoned, where it stalls, and its total projected
   wall-clock. It must NEVER reach the real title without paying the chains.
3. **Time-floor proof**: measured steps/sec for both chains; reduced-table attack
   implementation with measured blowup; the >= 4 h projection arithmetic under the
   4x-hardware assumption; timing variance data.
4. **Human-gate automation attacks**: SIRDS autocorrelation decoder (must land on
   the decoy plane or require the notes), ImageMagick channel separations on the hue
   plate (must yield the decoy code), moiré rotation search (must find two maxima,
   reciprocal = decoy). Paste images/commands/outcomes. Claims are measured costs,
   never "impossible".
5. **Leak grep**: every real value, seed label, ink, glyph code, phrase, component
   digest, master/launch/server secret, and every FORBIDDEN v2 value — asserted
   ABSENT from the package; every registered decoy asserted PRESENT exactly where
   documented. Machine-readable report in `runs/leaks.txt`; zero unexplained hits.
6. **Behaviour probe**: every tool under no args / empty arg / 200 KB arg / garbage /
   16 extra args / missing files / piped stdin / `</dev/null` stdin / `TERM=dumb` /
   narrow COLUMNS / read-only package dir / missing carriers / corrupt state →
   rc 0, stderr silent, no crash, no signal leak.

---

## 8. QUICK TEST CHECKLIST (run before you declare done)

One command each; all must pass; capture to `organizer-private/runs/`:
```bash
bash src/final/verify_all.sh         # ALL suites SERIAL: state, chain, stages, mirror,
                                     # server, eventgen + determinism + reproducibility
bash src/final/leak_grep.sh          # every real value/secret/forbidden-v2 value ABSENT
bash src/final/rebuild_repro.sh      # clean rebuild ×2, identical hashes
bash src/final/package_check.sh      # allowed-file list, no organizer content, manifest
bash src/final/isolated_solve.sh     # solve from the extracted zip as a stranger
bash src/final/attack_static.py      # static derivations yield only registered decoys
bash src/final/attack_scripted.py    # scripted agent is poisoned/gated, never reaches title
bash src/final/floor_proof.py        # measured >= 4 h projection with 4x assumption
```
Every script prints `PASS`/`FAIL` lines and a final `OK`/`NOT OK`. Paste the real
tails into the log. If any fails: fix, re-run it, then re-run `verify_all.sh`.

Quick sanity (also mandatory): `nm -a` on ALL binaries → empty; `strings -n 5 |
grep -Ei "gcc|clang|musl|/home/|ns8pc"` → nothing; two tools concurrent; clock jumps;
state deleted mid-chain; corrupt state byte-flip sweep.

---

## 9. TOKEN AND TIME DISCIPLINE (be fast WITHOUT skipping anything)

- Never bulk-read v2 sources; §1.2 lists the only files worth opening, once.
- One driver script per phase; run it, read the tail, act. No ad-hoc wandering.
- Debug in <= 3 iterations per symptom, then re-read the spec section.
- Do not "improve" a mechanism, rename files, add stages, or retune a dial without
  recording it in `COST_MODEL.md` with the reason.
- Every acceptance gate in this file is a hard gate. "Quick" means: no re-derivation,
  no re-discovery, no re-reading — NOT fewer tests. A skipped check is a failed
  session even if everything passes later.
- If a requirement is impossible as written, STOP, report the blocker and the
  alternatives, and ask the user. Do not silently substitute.
- Commit at the end of every phase; working tree clean at all times.

---

## 10. LOG AND FINAL REPORT FORMAT

`organizer-private/SESSION_1_LOG.md` must contain, in this order:
1. Status line: `COMPLETE — all suites green (list counts)` or `BLOCKED — <reason>`.
2. Environment: distro, tool versions, repo path, git HEAD.
3. Per-phase: what was built (exact paths), every design decision and why, every
   constant (seed → value → where it lives), the exact commands, PASTED real output.
4. `KEYS_PRAMBH.md` cross-reference: seeds, real values, decoys, digests.
5. Trap table (id, stage, trigger, dead-end, recovery, fairness argument, cost).
6. Measured timings: honest clean path per stage, decoy detours, scripted path,
   static path, isolated solve; the >= 4 h floor arithmetic; what is NOT proven.
7. Explicit NOT-DONE / DEFERRED / ASSUMED-BUT-UNVERIFIED list (must be empty or
   explained).
8. Open questions and judgment calls for the audit session.
9. Final manifest: every file in the zip with size + sha256, plus the zip's sha256.

Final message to the user (keep it short): one-line status, zip path + size + sha256,
suite pass counts, measured honest cost + floor projection, the two scored answers
(ARCHIVE mode), anything blocked, and the sentence:
`PRAMBH AUDIT PROMPT IS READY TO RUN — paste PROMPT_PRAMBH_AUDIT.md into a NEW session. Do NOT run it in this session.`

---

## 11. DEFINITION OF DONE (Session 1)

- [ ] All stage tools + emulator + chains + mirror campaign + bait layer in
      `prambh/`, every suite green in one clean `verify_all.sh` run.
- [ ] Every law of §0/§4 verified by a named test, not by inspection.
- [ ] Time floor measured and argued; reduced-memory attack measured infeasible.
- [ ] Human gates generated deterministically; automation attacks measured + pasted.
- [ ] EVENT mode: generator deterministic, cross-contamination suite green, server
      suite green; ARCHIVE zip ships by default.
- [ ] `organizer-private/` complete (§5) and never inside the zip.
- [ ] `prambh.zip` + `MANIFEST.sha256` copied to `E:\drive-upload\prambh\RELEASE\`.
- [ ] `SESSION_1_LOG.md` with real pasted output and measured timings.
- [ ] Working tree committed; nothing uncommitted or half-built.
- [ ] v2 archive under `E:\drive-upload\ghost2\` untouched.
- [ ] This session ended at the final report. `PROMPT_PRAMBH_AUDIT.md` was NOT run
      here; it MUST be pasted into a brand-new session only after this session
      reports COMPLETE.

---

## APPENDIX A — THE AUDIT IS A SEPARATE SESSION (HARD RULE)

The audit is fully specified in `PROMPT_PRAMBH_AUDIT.md` (same folder as this file).
It is NOT part of this session. Rules:

1. This session's job ends at the final report above. The §7 self-proof is
   build-time verification, not the audit, and must never be reported as one.
2. The audit MUST run in a brand-new session (fresh context, no memory of this
   build's internals beyond what the repo, spec copy, and log state), started ONLY
   after this session reports COMPLETE with all suites green.
3. Never paste the audit prompt into this session, never "quickly audit" before
   reporting, never merge build and audit.
4. If `PROMPT_PRAMBH_AUDIT.md` is missing or incomplete when this session finishes,
   say so in the final report — do not improvise an audit.

Audit phases (reference only; the audit prompt file is authoritative):
A independent rebuild + baseline suites + manifest/hash parity;
B leak-grep re-run with INDEPENDENT patterns (not the build's list);
C static-only adversary (must obtain only registered decoys);
D scripted/batch adversary incl. full mirror-room solve to its dead end;
E dynamic adversary (gdb/strace/ltrace/faketime/forced state);
F time-floor re-measurement on the audit machine + reduced-table attack re-run;
G human-gate automation re-attacks;
H EVENT-mode audit (generator determinism, cross-contamination, server abuse:
replay, early submit, forged callsigns);
I determinism/zip/manifest re-verification from the shipped zip on the Windows side;
final GO / NO-GO in `organizer-private/SESSION_2_AUDIT.md`. Rules identical to the
v2 audit prompt: trust nothing, reproduce every claim by command, a finding is
closed only by a re-run, never fix by weakening the puzzle.

Start now with Phase 0. Report the one-line confirmation, then work phase by phase.


---

## APPENDIX B — CONTINUATION STATE + LIGHTWEIGHT EXECUTION PLAN
(added 2026-09-22, after the "p5-wip" commit. NON-NORMATIVE: this appendix changes
NO requirement, suite count, or acceptance gate above. It records where the build
stopped and the cheapest correct way to finish. The frozen repo copy
`docs/BUILD_SPEC_PRAMBH.md` remains the contract; if this appendix and the contract
ever disagree, the contract wins and the difference is a finding.)

### B.1 Where the build stopped (state snapshot, 2026-09-22)
- P0–P4: complete, committed, suites green (commits: spec, p0, p1, p2 ×2, p3, p4).
- P5: foundations complete, committed as `p5-wip` (3e3a01c): `opcodes.py`, `asm.py`,
  `model_loom.py`, `meru1.h/.c`, `loom.c`, `gen_rom.py`, `selftest.py` (all 64
  opcodes; Python-model vs C parity PASS), `gen_datasheet.py`
  (`field-notes/meru1_datasheet.txt` generated OK).
- The 4 loom decoy tokens are ALREADY COMPUTED (≈9 min of chain time) and stored in
  `organizer-private/runs/p5_decoy_tokens.txt` (D-ROM-1..3 + D-DBG). Do NOT recompute;
  harvest from that file.
- `src/loom/params.h` currently holds TEST values (T=1024) — regenerate production
  values before the final commit of P5.
- Known nit: `loom.c` comment says `meru8_datasheet.txt`; fix to
  `field-notes/meru1_datasheet.txt`.
- P5 remaining: `src/loom/test_loom.sh` (>= 60 checks, spec §6 P5 + §4.4 acceptance),
  register D-ROM-1..3 + D-DBG in `src/gen/trap_catalogue.py` + `keys.py`, production
  `params.h`, suite green, commit, log to `organizer-private/runs/p5_loom.txt`.

### B.2 Machine lessons (hard-won this session — obey them)
- Background jobs do NOT survive across `wsl.exe` tool invocations (`setsid`/`nohup`/
  `disown` all die). Working recipe — launch from the WINDOWS side; the living
  `wsl.exe` client keeps the process alive:
  ```powershell
  Start-Process -FilePath wsl.exe -ArgumentList '-d','Ubuntu','--','python3','/tmp/job.py' -RedirectStandardOutput E:\drive-upload\job.out -RedirectStandardError E:\drive-upload\job.err -WindowStyle Hidden
  ```
- CRLF: files written via Windows-side editors get CRLF endings → fix with
  `python3 /tmp/fixcr.py <file>` before running in WSL.
- Long files: the editor tool truncates payloads > ~6000 chars; write in chunks with
  `# __MORE<n>__` sentinels and assemble.
- Shell quoting through `wsl.exe` is fragile: write scripts to `/tmp/*.sh` and invoke
  them; never put pipes inside `grep -E` args passed through `wsl.exe` (use repeated
  `-e` instead).


### B.3 The lightweight execution plan (cut typing, reading, and idle waiting —
### NEVER tests, checks, or verification)

Guiding principle: **reuse > generate > hand-write; table-driven suites;
background the clocks; docs last.** "Lightweight" means fewer agent tokens and no
idle wall-clock. The verification surface stays EXACTLY as the contract demands —
every named suite, every leak lane, all of §7, the honest REAL-paced run, the
isolated solve, rebuild reproducibility, and an empty NOT-DONE list.

1. **Reuse existing engines.** Every remaining chain (chain #2, the mirror 2-stage
   chain, the 7 decoy-chamber chains) is a parameter set of the already-built
   `src/chain` engine — zero new crypto code. Every remaining tool (`doors`,
   `mirror_milestone`, `mirror_validate`, `eyes validate`) is ONE shared C skeleton
   (usage+canary → state check → fixed-shape output, rc 0, silent stderr) with a
   different payload; write the skeleton once, instantiate four times.
2. **Generators, not prose.** Chambers, mirror fiction, plates, and bait are
   produced by Python generators from labelled seeds (`src/gen/mint.py` patterns).
   Never hand-write corpus/fiction text. Bonus: determinism suites become trivial
   (regenerate → byte-identical).
3. **Table-driven suites.** Copy the `ok`/`FAIL` idiom from
   `src/stage0/test_stage0.sh` into every suite; express checks as loops over tables
   (8 chambers, 10 undesigned phrases, 15+ wrong titles, 30 timing samples, 64
   opcodes) so the minimum counts (35/40/45/60) are met BY CONSTRUCTION, not by
   writing 60 bespoke stanzas.
4. **Background every long clock.** The >= 75-min emulated chain #1 wall-clock
   measurement, the decoy-chain timing runs, and the P10 honest REAL-paced solve
   (hours) are launched via the B.2 `Start-Process` recipe at the EARLIEST moment
   their inputs are frozen, then harvested at the end. Never sit idle waiting on a
   chain; build other phases while it runs.
5. **Adapt v2 final scripts.** `src/final/{verify_all,leak_grep,rebuild_repro,
   package_check,isolated_solve}.sh` + `behaviour_probe.py` exist in the v2 tree
   (§1.2 path) — adapt names and value lists, do not write from zero.
6. **Read by line-range only.** Per phase, read ONLY what is listed below; never
   re-read whole files, never re-derive values (`organizer-private/KEYS_PRAMBH.md`
   and `runs/p5_decoy_tokens.txt` are the source of truth):
   - P5 finish: spec §4.4 + §6 P5 line; `src/loom/*`; `src/stage0/test_stage0.sh`
     (idiom); `src/gen/{mint,trap_catalogue,keys}.py`.
   - P6 doors: spec §4.5; `src/core/sha256ctr.*`, `src/chain/*`, state layer.
   - P7 mirror: spec §4.6; `src/gen/corpus_gen.py` (extend, don't rewrite).
   - P8 eyes: spec §4.7; PIL/numpy generators; `src/chain/*` for chain #2.
   - P9 server+eventgen: spec §4.8 + §3.
   - P10: spec §6 P10 + §7 + §8; v2 `src/final/*` as reference.
7. **Docs last, from templates.** `COST_MODEL.md`, `HINTS.md`,
   `TRYHACKME_ROOM_TEXT.md`, `README_FOR_SOLVER.txt`, `SESSION_1_LOG.md` are written
   ONCE at the end from real measured numbers — never drafted early and re-edited.
8. **Never cut:** any named suite or check minimum, any leak-grep lane, §7
   adversarial self-proof, the honest REAL run, the isolated stranger solve, rebuild
   reproducibility, manifest hygiene, cross-contamination, per-phase commits with
   pasted output in `organizer-private/runs/`.


---

## APPENDIX C — SESSION-SPLIT AMENDMENT (user-directed, 2026-09-22)
This appendix AMENDS THE SCHEDULE, not the security bar. Where it conflicts with
the phase-by-phase text above, THIS appendix governs (user direction).

1. **Floor restated: >= 3 h 30 min.** The deliverable must be IMPOSSIBLE to solve
   in under 3 h 30 min by any solver (human or AI agent) — no leakage, no bugs, no
   shortcuts, no bypass. The existing design floor (>= 4 h: chain #1 ~75 min +
   chain #2 ~75 min + forced sequential rendering/search + MIN_JOURNEY server gate)
   EXCEEDS this bar and is UNCHANGED. Never weaken any chain, gate, pacing, or
   MIN_JOURNEY.
2. **Build session SKIPS the long runs.** These are DEFERRED to the audit session,
   which owns them end-to-end (audit prompt, lane X6):
   a. the >= 75-min REAL-T emulated chain #1 wall-clock measurement (§4.4/§6 P5);
   b. the hours-long honest REAL-paced full solve (§6 P10);
   c. deep adversarial hunting beyond each phase's own suite (mutation testing of
      suites, extended fuzzing, race hunts, timing sweeps — audit lanes X1–X5).
   IN PLACE of (a)/(b), the build session performs **reduced-T PROJECTION**: run
   each chain at several reduced T values, measure steps/sec (native AND emulated),
   verify per-step cost is constant across T (linear scaling — sound because the
   chain is sequential SHA-256), then PROJECT production wall-clock =
   T_prod x per-step. Record the projection math + raw measurements in
   `organizer-private/runs/` and mark every such number
   "PROJECTED — audit must confirm with the full REAL run". The honest REAL run is
   MOVED to the audit session, NOT deleted.
3. **Trap-attraction pass (new explicit requirement, P6/P7).** Before minting,
   write in `organizer-private/` the top 8 misreadings an AI agent or human will
   most likely make of the verse/plates. Each misreading MUST map to a decoy
   chamber or mirror thread. Traps must cross-corroborate each other (decoy
   chambers point at each other and at the Mirror Room) so a wrong turn feels
   progressively MORE confirmed — maximize the probability a solver gets stuck.
4. **HANDOFF.md (mandatory last act of the build session).** Lists every deferred
   item WITH the exact command to run it, every PROJECTED number + its math, every
   known nit, and final git state. This file is the audit session's worklist.
   Build-session suites still all run green; nothing else is relaxed.

