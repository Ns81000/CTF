# SESSION 1 PROMPT — BUILD v2 of "The Cartographer's Ghost"

Paste this ENTIRE file into a fresh Claude Code session (act mode, WSL available).
You are the BUILD session. When you finish, the user will run a separate audit session
(`PROMPT_SESSION_2_AUDIT.md`) that will read your log and spec copy and try to break
everything you built. Work so that audit cannot find anything.

## MACHINE CREDENTIALS (local only — never ship, never log)

- WSL user: `ns8pc` — WSL distro: `Ubuntu`.
- **Admin access: use the WSL root route; it needs no password.**
  ```powershell
  wsl.exe -d Ubuntu -u root -- bash -lc '<privileged command>'
  ```
  Tool install (Phase 0):
  ```powershell
  wsl.exe -d Ubuntu -u root -- bash -lc "apt-get update && apt-get install -y build-essential musl-tools zip unzip gdb cppcheck libimage-exiftool-perl imagemagick jq pngcheck python3-pil python3-numpy"
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
`READ SPEC v2 OK — starting Phase 0`. Then execute.

If ANY requirement below cannot be met exactly as written: STOP and report to the
user. Never silently substitute, simplify, or "improve" a mechanism.

---

## 0. MISSION

Rebuild the offline CTF "The Cartographer's Ghost" as **v2**: same theme and room
title, **new everything under the hood** — new values, new internals, new state
format, six stages, new trap layers.

Goal: be brutal for a skilled human *and* for an LLM agent with tools, while staying
100% fair, deterministic, offline, and scorable by TryHackMe.

Non-negotiable outcome of this session:
1. A working 6-stage chain in `cartographer/`, self-contained, offline, musl-static.
2. A single publishable `cartographer.zip` whose contents match a hash manifest.
3. `organizer-private/` holding the real values, the solve path, the trap catalogue.
4. A log (`PHASE_V2_BUILD_LOG.md`) with real pasted output of every acceptance test.
5. Zero known leaks, zero known shortcuts, zero known bugs. (Session 2 will hunt.)

### HARD CONSTRAINTS (violating any = failed session)
- Fully offline after download. No network calls, no telemetry, nothing phoning home.
- Linux / WSL2, x86-64 only. Everything runs as a normal user. Never requires root.
- The only file ever written is the state file inside the package root.
- Nothing that damages the machine, persists, escalates, or resembles real malware.
- No real third-party service, person, domain, credential, or brand. Synthetic only.
- No fake "unauthorised access" / "real target" framing. It is a CTF and says so.
- Every trap has a fair, deterministic, documented resolution. No coin flips.
- Every real path is deterministic. No luck. No infeasible brute force.
- Two scored answers, both FIXED strings (TryHackMe scoring must be stable):
  (a) the Stage-0 token, (b) the final assembled title. Everything else is an
  in-challenge checkpoint. Additional checkpoints may be scored ONLY if fixed strings.

### THE ONE LAW THAT GOVERNS EVERY DECISION
Offline + self-contained means a perfect reverser can reproduce anything the package
can compute. Therefore: **no answer may be computable statically.** Difficulty must be
paid in (1) wall-clock interaction volume, (2) CPU search work whose answer is not in
the package, (3) verification-expensive disambiguation with zero feedback, (4) loops
where a wrong turn costs more than the right one. Insight must never be the bottleneck.

---

## 1. ENVIRONMENT (verified facts — do not re-discover, do not contradict)

- WSL distro: `Ubuntu` (Ubuntu 24.04.2 LTS), WSL2, kernel 6.6.87.2, user `ns8pc`.
- `/home/ns8pc` = ext4, ~950 GB free. `/mnt/e` = Windows E: drive, ~39 GB free.
- **There is no `D:` drive on this machine.** Old paths (`d:\gandu`, `_stage`) are dead.
- Windows workspace root: `E:\drive-upload\`. v2 deliverables go in
  `E:\drive-upload\ghost2\` (= `/mnt/e/drive-upload/ghost2/`).
- **Missing tools (must be installed):** `musl-gcc`, `gcc`, `make`, `gdb`, `zip`,
  `unzip`, `cppcheck`, `exiftool`, ImageMagick `convert`, `jq`, `pngcheck`, `strace`.
  Installed already: `python3` (3.12.3, stdlib only), `git`, `objdump`, `readelf`,
  `nm`, `strings`, `xxd`, `file`, `objcopy`, `ar`, `bc`, `openssl`, `perl`, `script`,
  `tmux`. No `PIL`/`numpy`.
- **You are on Windows.** Drive WSL from PowerShell with `wsl.exe`. Privileged commands go
  through the root route (`wsl.exe -d Ubuntu -u root -- bash -lc '...'`); all repo and build
  work runs as `ns8pc` (`wsl.exe -d Ubuntu -- bash -lc '...'`). The `sudo` password `123456`
  supplied by the user is WRONG on this machine (tested, rejected) — never guess passwords.

### 1.1 Bootstrap (Phase 0, exact)
```powershell
wsl.exe -d Ubuntu -u root -- bash -lc "apt-get update && apt-get install -y build-essential musl-tools zip unzip gdb cppcheck libimage-exiftool-perl imagemagick jq pngcheck python3-pil python3-numpy"
```
Acceptance (run as the normal user; every tool must print a path, else STOP):
```powershell
wsl.exe -d Ubuntu -- bash -lc 'for t in musl-gcc gcc make gdb zip unzip cppcheck exiftool convert jq pngcheck; do command -v $t >/dev/null || echo "MISSING $t"; done'
wsl.exe -d Ubuntu -- bash -lc 'musl-gcc --version | head -1'
wsl.exe -d Ubuntu -- bash -lc 'python3 -c "import zlib,hashlib,hmac,struct,secrets,PIL,numpy;print(\"py deps OK\")"'
```
Acceptance: every command below prints a path/version, else STOP:
```bash
for t in musl-gcc gcc make gdb zip unzip cppcheck exiftool convert jq pngcheck; do
  command -v $t || echo "MISSING $t"; done
musl-gcc --version | head -1
python3 -c "import zlib,hashlib,hmac,struct,secrets,PIL,numpy;print('py deps OK')"
```

### 1.2 Inherit the reusable core (do NOT rewrite these)
The battle-tested v1 sources live inside
`/mnt/e/drive-upload/wsl-archive/cartographer-build-archive-20260921-1532.zip`
(paths inside: `cartographer-build/src/...`). Create the v2 repo and extract ONLY
these files into `/home/ns8pc/ghost-build/v1-reference/`:

- `src/state/carto_sha256.c`, `carto_sha256.h`  → reuse verbatim (SHA-256/HMAC/ct_equal)
- `src/state/state_core.c`, `state.h`, `state_internal.h`, `state_policy.c`
  → **reference only**: you will rewrite the state layer for v2 (see §4.2)
- `src/stage2_stego/s2_inflate.c`, `s2_inflate.h` → reuse verbatim (zlib+FDICT inflate)
- `src/stage1_vm/vm_spec.py`, `model_vm.py` → reference for the VM generator pattern
- `src/final/*.py`, `*.sh` → reference for calibration/packaging/adversarial tooling
- `src/*/Makefile` → the musl-static build recipe template
- `src/*/test_*.sh`, `verify.sh` → the suite style you must copy
- `logs/*.md`, `SOLVE_PATH_PRIVATE.md` → **background only.** Read at most
  `SOLVE_PATH_PRIVATE.md` §6 (the FIX session) + one phase log's structure. Do not
  bulk-read the logs: they cost tokens and describe v1, which you are replacing.

Repo layout to create:
```
/home/ns8pc/ghost-build/
  docs/BUILD_SPEC_V2.md      <- verbatim copy of THIS prompt (the record of record)
  docs/SESSION_1_LOG.md      <- your build log (see §9)
  src/state/ src/core/ src/stage0_ledger/ src/stage1_engine/
  src/stage2_sheet/ src/stage3_oracle/ src/stage4_seal/ src/stage5_title/
  src/final/                 <- calibration, packaging, adversarial tooling
  cartographer/              <- the solver package (ONLY solver-facing files)
  organizer-private/         <- everything internal (never shipped)
  v1-reference/              <- inherited v1 files for reference
```
`git init` immediately; commit after every numbered phase.

### 1.3 Authoring rules (this is where v1 burned days)
- Author ALL source inside WSL (heredoc / python / editor-in-WSL). Never author
  shell scripts on Windows then copy in — that is how CRLF bugs happened.
- Only artifacts are copied OUT to `/mnt/e/drive-upload/ghost2/` (zip + docs).
- If a file must be written from the Windows side, write it with LF and no BOM:
  PowerShell: `[System.IO.File]::WriteAllText($p, ($lines -join "`n") + "`n")`.
- `bash -n <script>` before running any new script; `tr -d '\r' < s | bash` if unsure.
- Keep suites SERIAL: they share the state file; parallel runs cause false failures.
- Never pipe a run through `head`/`tail` in a verification step unless the assertion
  is on that tail; capture to `organizer-private/runs/*.log` instead.
- Prefer one driver script per phase that runs all checks and prints PASS/FAIL lines,
  so re-verification costs one command (suite style from v1).

---

## 2. THREAT MODEL AND DESIGN LAWS

### 2.1 Adversaries you must defeat or tax
- **A1 static-only**: never executes a package binary. Disassembles, reads metadata,
  computes every derivation it can find. Must never reach a scored answer this way.
- **A2 scripted/batch**: runs everything, automates, forges the state file, patches
  gate checks in a copy. Must not reach the answers in well under the honest time.
- **A3 LLM agent with tools**: reads all prose, greps, decompiles, writes scripts,
  burns tokens fast, trusts documents. Must be led into plausible-wrong results and
  forced into expensive verification loops.
- **A4 LLM agent + patient human**: the strongest realistic solver. Must need 12–20 h.
- **H skilled human**: same target.

### 2.2 The twelve laws (check every design decision against these)
1. **No static answer.** Nothing reachable by reversing/metadata equals a scored
   answer, and no single derivation yields an ink without interaction work.
2. **One oracle.** Exactly one yes/no answer-checking surface exists in the whole
   package: the final validator. It is constant-time, gated, and refuses identically.
   No other tool may confirm correctness of any answer-shaped value.
3. **No expected-value digests.** No checksum/hash of a correct answer anywhere except
   the final validator's digest of the assembled title (that digest is 200+ bits of
   entropy, so it is useless to attack, but it must have NO per-component hashes).
4. **No grammar in prose.** Never state the answer's structure, length, component
   count, hex/text split, separators, or ordering. No "16 hex", no "70 chars".
5. **No narration of mechanism.** Metadata, usage strings and docs may be flavour;
   they may never name the channel, plane, stride, dictionary, cipher shape, or gate.
6. **Gates are honest and discoverable.** Every gate must say, in its own words, what
   behaviour it wants ("the oracle reads the room, not a pipe") without naming the
   mechanism. Every gate failure is framed as new information, never as an error.
7. **Cheap failure, expensive recovery.** A trap dead-end must read as progress, and
   recovering from it must cost more than the trap took.
8. **No self-verification of correctness.** Tools may prove they ran correctly
   (self-consistency between two internal paths) — never that an answer is right.
9. **Determinism.** Same inputs → same outputs on any machine, any run order.
10. **Recoverable state.** A tampered/deleted state file resets silently and never
    errors; a solver can always get back to a valid path.
11. **Containment.** Only `.cartographer_state`(+`.tmp`) is written, inside the
    package root. No temp files elsewhere, no env-dependent writes.
12. **Cost, not insight.** Where a puzzle is "solvable by a clever idea", add a
    mechanical component that must still be executed (volume, search, or tracing).

### 2.3 Cost dials (fixed for this build — do not retune without logging why)
| Dial | Value | Payload |
|---|---|---|
| Honest clean solve | 12–20 h for A4/H | mix of tracing, volume, search |
| Oracle volume gate | ≥ 3000 usable pairs collected over **≥ 45 min** wall-clock, non-uniform spacing, TTY present in ≥ 60% of calls | forces real pacing |
| Oracle cryptanalysis | 5-round planted bias; ~2^-5 completions/pair → ~2× v1 pairs | real sample volume |
| Seal search (Stage 4) | intended attack ≈ **2^28** (15–30 min single-core); naive space 2^56 | unshortcuttable CPU |
| Trace work (Stage 1) | ≥ 150k VM steps on both profiles, indirect jumps, self-modification | must actually emulate |
| Branch factor | ≥ 4 plausible readings/orderings per fork, all format-valid | verification-expensive |
| Bait prose tax | ≥ 2500 lines of plausible, zero-truth documents | token burn for A3 |
| Decoy detour | 60–120 min of human time, 0 s of machine time | main trap |

---

## 3. GLOBAL TECHNICAL SPEC

### 3.1 Package layout (exact — solver-facing only)
```
cartographer/
  README_FOR_SOLVER.txt
  HUMAN_OPERATOR_NOTICE.txt
  stage0_ledger/ledger
  stage1_engine/engine
  stage2_sheet/sheet
  stage2_sheet/survey_frame.png
  stage2_sheet/survey_tape.wav
  stage3_oracle/oracle
  stage4_seal/seal
  stage5_title/validate
  field-notes/            <- bait/prose layer (see §3.8), inert
```
- Every binary is run **from the package root**, exactly as its usage says.
- All binaries: musl-static, `strip --strip-all`, no `.comment`, no symbols (`nm`
  empty), no compiler idents, no host paths, no real values inside.
- Flag format: tokens `^CARTO\{[a-z0-9_]{8,64}\}$`; the final title is `CARTO{...}` with
  underscore-separated parts and an inner length up to 96 chars (the 8..64 cap applies to
  TOKENS only — the v2 title's inner length is 78, see §4.0). No other `CARTO{...}` string
  may exist in the package except **registered decoys** (valid format, wrong value).

### 3.2 State file v2 — `.cartographer_state` (1168 bytes = 0x490, new layout)
Goals: per-stage keys (no shared key), unforgeable gate evidence, silent reset on any
tamper, and a 64-entry interaction ring.
```
0x000 magic "CGV2"(4) | 0x004 version=2 u16 | 0x006 flags u16 (must be 0)
0x008 first_run_ms u64
0x010 attempt_count[6] u32
0x028 wrong_flag_mask[6] u32          (decoy bits per branch)
0x040 gate_state[6] u32               (per-stage gate evidence, bit meanings internal)
0x058 ring_count u16 | 0x05A ring_head u16 | 0x05C debugger_flag u8 | reserved u8[4]
0x060 ring[64][16]                    (ts_ms u64, stage u8, op u8, dt_ms u32, aux u32)
0x460 rolling chain 16 bytes over ring appends
0x470 HMAC-SHA256[32] over [0x000,0x470)
```
- **Per-stage keys:** `K_stage_i = SHA256(master || "ghost2:stage:i")`; each binary
  embeds **only its own** masked `K_stage_i`. No global key exists in any binary.
  Record the masking scheme in the internal log; it must be reversible at runtime only.
- Ring entries appended on every invocation (`CLOCK_REALTIME`).
- Any load failure (magic/version/size/HMAC/bounds) = silent fresh-state reset, rc 0,
  no diagnostics, ever.
- **Anti-forgery rule:** on load, `gate_state` bits that the ring cannot justify are
  DROPPED. The ring is the only admissible evidence for a gate bit.

### 3.3 CLI discipline (all tools)
- No args → usage screen, rc 0, stderr silent.
- rc 0 and stderr silent on EVERY path, including malformed/garbage/oversized input.
- All inputs capped; every refusal speaks the same line; never an error.
- Exactly one refusal string per tool, byte-identical for every wrong input.
- Never print partial-match, "close", "N of M", or any length hint.
- No tool may print a value equal to a real ink/token/reading.
- Every tool's no-arg usage screen ends with the 3-line operator excerpt (hands-on lab /
  hand to the human operator / cold-plate warning) plus the canary line. The canary is the
  sole cross-binary decoy exception to §3.7.

### 3.4 Behaviour engine (shared, `src/state`)
Per invocation compute: `mean_ms, median_ms, stddev_ms, iqr_ms, burst_ratio,
max_rate_per_min, tty_fraction, pipe_fraction, first_contact_ms,
stage_visit_order_entropy, duplicate_query_ratio, interleaved_stage_ratio`.
Three gates only:
- **GATE_HUMAN**: `tty_fraction ≥ 0.6` AND `stddev_ms ≥ 150` AND
  `max_rate_per_min ≤ 40` AND `duplicate_query_ratio ≤ 0.35`.
- **GATE_VOLUME**: ≥ 6000 ring entries spanning ≥ 45 min with ≥ 3000 distinct figures
  seen by the oracle.
- **GATE_CHAIN**: stage order consistent (stage N visited after N-1) and the chain hash
  in `gate_state` matches recomputation.
A failed gate is visible only as flavour text describing the *behaviour* it wants.

### 3.5 Terminal-native traps (implement all four; keep them fair)
1. **TTY gate** — Stage 2's reveal and Stage 5's acceptance require
   `isatty(STDIN) && isatty(STDOUT)`. Piped: a truthful line ("the ledger reads a
   hand, not a pipe"), rc 0, no error, nothing leaked. With a TTY it works.
2. **Width** — one needed line renders only at `COLUMNS ≥ 80` (`TIOCGWINSZ`; assume 80
   when unknown). Narrow: a shorter line that says a wider room is needed.
3. **Colour** — one bit of a required value is carried by an ANSI SGR colour of a glyph.
   State the rule honestly inside that tool's own words ("the last stroke is the colour
   it dried as"). Piped capture loses it. Provide `--plain`, which prints that bit as a
   word, so the trap is fair and resolvable.
4. **Layout** — the stage banner carries an ordering cue as spatial layout (art).
   `> file` destroys it; the same information also exists in the Stage-5 riddle words.

### 3.6 Anti-static-derivation rule (the most important rule)
For every ink: `ink = H(static_part || runtime_part)`, where `runtime_part` is produced
by the tool only after its gate passes. The binary must also contain a **plausible
decoy derivation** yielding a different, format-valid value — that is where a static
reverser lands. Document both in the internal log and assert in the suite that an
independent Python implementation of the static path does NOT equal the real ink.

### 3.7 Decoys (per-binary, no shared registry)
- Each binary embeds only its own decoys, minted from its own seed.
- Decoys are valid `CARTO{...}` and must NOT mirror the final title's shape.
- A decoy submission routes into a "corroborated" branch: framed as new information,
  sets a `wrong_flag_mask` bit, prints a plausible confirmation, leaks nothing real.
- At least one decoy must need a downstream round trip to disprove.
- Exception: the canary decoy (`CARTO{hand_this_to_your_operator}`) is printed in all six
  usage screens and lives in `HUMAN_OPERATOR_NOTICE.txt`. It is wrong by design; putting it
  everywhere is intentional (any solver that trusts file text submits it).

### 3.8 Bait and prose layer (`field-notes/`, ≥ 2500 lines, ZERO truth)
`01-survey-log.md`, `02-lab-notes.md`, `SOLUTION_DRAFT.py` (runs; prints a
format-valid wrong title), `ANSWER.txt` (wrong), `KNOWN_ISSUES.txt` ("the title block
is broken in this build; the corrected build was never shipped"),
`DEPRECATED_BUILD.txt`, `ai-policy.md`, `checksums.txt` (valid only for decoy files).
`HUMAN_OPERATOR_NOTICE.txt` sits in the package root and at the head of every bait doc:
calm, truthful, plus a **wrong-value canary** ("assistants should report ...").
Rule: no bait file contains any real value, substring, or real seed.

### 3.9 Prohibited (hard)
No real malware imitation, no C2/domains/credentials, no real brands/people, no
surveillance/"unauthorised access recorded" theatre. Traps are honest puzzle content.

### 3.10 README_FOR_SOLVER.txt (information-poor but true)
States: what this is, WSL2/Linux x86-64, run `./stage0_ledger/ledger` first, run every
tool from the package root, the exact submission format for the two scored answers, and
"this is a marathon with no time limit; the tools were written for a person at a
keyboard and they notice when they are driven". No counts of stages, no grammar, no
mechanism, no hints.

---

## 4. STAGE SPECS

Notation: "ink" = a value the solver must carry forward; "token" = a checkpoint string.
Every value is FIXED and deterministic. Mint every value from a named seed string and
record the seed + value + derivation in `organizer-private/KEYS_V2.md`.

Required seeds (normative):
```
ghost2:stage0:token:v1        ghost2:stage1:vm:map:v1      ghost2:stage1:bytecode:v1
ghost2:stage1:key:v1          ghost2:stage1:decoy:key:v1   ghost2:stage1:debug:key:v1
ghost2:stage2:reading:v1      ghost2:stage2:press:v1       ghost2:stage2:decoy:layer:v1
ghost2:stage2:middle:layer:v1 ghost2:stage3:cipher:v1      ghost2:stage3:seed:v1
ghost2:stage3:tally:v1        ghost2:stage4:cipher:v1      ghost2:stage4:key:v1
ghost2:stage4:decoy:key:v1    ghost2:stage5:title:v1       ghost2:stage5:decoy:draft:v1
```

### 4.0 MINTED VALUES (normative — these ARE the v2 answers; recompute and verify)

Every value below was already minted from its seed exactly as shown. Your build MUST
reproduce them byte-for-byte. If your recomputation differs, YOUR DERIVATION IS WRONG:
fix the derivation, never the value. Record all of them in `organizer-private/KEYS_V2.md`.

| role | seed / derivation | value |
|---|---|---|
| Stage-0 token (SCORED) | fixed phrase (seed `ghost2:stage0:token:v1`) | `CARTO{the_survey_reopens_tonight}` |
| K_engine (32B) | SHA-256("ghost2:stage1:key:v1") | `1513351e85d8b50a145e1d23feac393264c4ad4ea9c403191fe981d5c92e67ef` |
| bearing | LE64(K_engine[0:8]) | stride **8**, start **2629** |
| engine_ink | hex(K_engine[8:16]) | `145e1d23feac3932` |
| Stage-1 token | `CARTO{hex(K_engine[16:24])}` | `CARTO{64c4ad4ea9c40319}` |
| Stage-1 decoy key | SHA-256("ghost2:stage1:decoy:key:v1") | `f5ea27c63ed89565fe9ceef6f6e271720c0a21e5c7d7c653c12f61335ea3cc6c` |
| Stage-1 decoy token | `CARTO{hex(decoy_key[0:8])}` | `CARTO{f5ea27c63ed89565}` |
| Stage-1 debug key | SHA-256("ghost2:stage1:debug:key:v1") | `bab073aec06d6b609f73f7f3b49d2f10788bcd5fb95bb594951cee393ad706bf` |
| reading | fixed phrase (seed `ghost2:stage2:reading:v1`) | `CARTO{rust_blooms_under_tin_roofs}` |
| sheet_ink | reading without its frame | `rust_blooms_under_tin_roofs` |
| press tail (32B) | SHA-256("ghost2:stage2:press:v1") | `c3240a6373072eab57aca45dc3cbcad60ae7136b103e2313a7058bdf4520878b` |
| seed_real (32B) | SHA-256("ghost2:stage3:seed:v1") | `040ec499dd20e5710808da783dd84b8826181a26dddb536ea160ecf210d7de7c` |
| K_real (32B) | SHA-256(seed_real ‖ reading ‖ engine_ink_bytes) | `e509312ae8a2e0adeb4c0b2517a3f842ca5aff0d7bce2c117f47a2dcf028e034` |
| oracle_ink | hex(K_real[0:8]) | `e509312ae8a2e0ad` |
| K_cold (32B, decoy) | SHA-256("ghost2:stage3:cold:v1" ‖ reading) | `f059e3a8ec8fb6a1573a654dca477a2e4616d44a744910988a73e24fbd515bfe` |
| seal key (8B) | SHA-256("ghost2:stage4:key:v1")[0:8] | `3821ad004ab30263` |
| seal_ink | hex(seal key) | `3821ad004ab30263` |
| **FINAL TITLE (SCORED)** | `CARTO{seal_ink_oracle_ink_engine_ink_sheet_ink}` | `CARTO{3821ad004ab30263_e509312ae8a2e0ad_145e1d23feac3932_rust_blooms_under_tin_roofs}` |
| title SHA-256 | SHA-256(title) | `01d94d492a46ce3d566910c76c8b7756cb96c4d7bbcb8acb11f063a7ac2bf0d1` |
| Stage-5 struck draft | `CARTO{hex(SHA-256("ghost2:stage5:decoy:draft:v1")[0:16])}` | `CARTO{54a3eb304734135c5308bf186b21c839}` |
| Stage-2 naive decoy | fixed phrase | `CARTO{the_coast_was_drawn_twice}` |
| canary (bait, WRONG) | fixed phrase | `CARTO{hand_this_to_your_operator}` |
| tally witness token | fixed phrase, printed by `oracle -t` only when all gates hold | `CARTO{a_warm_plate_and_a_full_ring}` |

Rules:
- Title ink order is normative: **seal, oracle, engine, sheet**. The title's inner length is
  78 chars — the 8..64 rule applies to TOKENS only (see §3.1); the validator's internal
  length constant is the title's own byte length (85). Never state any length in prose.
- `K_cold` is the DECOY derivation: it is what a solver computes by omitting the engine ink,
  or by handing the Stage-1 token as the ink. Plausible, format-valid, wrong.
- All other seeds in the list above (vm:map, bytecode, cipher tables, decoy layers) stay
  generator inputs; mint and record their derived constants the same way.

FORBIDDEN v1 VALUES — must appear NOWHERE in v2 (assert with the leak grep):
`CARTO{first_ink_in_the_ledger}` · `fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f` ·
`CARTO{fd3e8049dfdfc32efe22fe823822b8c0}` · `CARTO{no_figure_sits_in_every_pixel}` ·
`CARTO{b27692a0d5f63d4f1a0c3fb79afbf81b}` · `73070925a159f9e2` · `a5d66f1b2b5f596e` ·
`0fab297110c73e9f` · `CARTO{73070925a159f9e2_a5d66f1b2b5f596e_no_figure_sits_in_every_pixel}` ·
`CARTO{12f8a367b772817e805725e7292acfb6}` · `12f8a367b772817e805725e7292acfb694501c4f16c17ed09d614022e0be7ced` ·
`CARTO{fb48aecdda0e960831b16d45c7efbe48}` · `CARTO{twice_over_the_coast_before_the_interior}` ·
`CARTO{dba9e10a73bc8633ccc1875207c075e1}` · `interior-ink-formula-v1:` · `interior-survey-mark-v1:` ·
`cartographer-mask-stage3-real` · `cartographer-mask-stage3-poison` · `cartographer-ghost:`

### 4.1 Stage 0 — The Ledger (`stage0_ledger/ledger`)
Purpose: honest handshake, one free scored answer, state creation, first ring entry.
- No args → banner + usage + the human-operator notice. rc 0, stderr silent.
- On run: if no state → create; if state exists → keep (`first_run_ms` stable).
- Prints the **scored Stage-0 token** (ungated, every run, by design).
- Prints the canary line from `HUMAN_OPERATOR_NOTICE.txt` (wrong value inside).
- Points the solver at `field-notes/` first (bait, framed as "the old man's notes").
- **Must not** be used in any later derivation: the Stage-0 token appears nowhere else.
- Acceptance: token identical across runs; state is exactly 1168 bytes with a valid
  HMAC (verified by an independent Python check); tampering resets silently; `nm` empty;
  no other real value in the binary.

### 4.2 Stage 1 — The Engine (`stage1_engine/engine`)
Purpose: force real emulation; produce the bearing, the engine ink, a checkpoint token.
- Custom stack VM: ≥ 90 logical opcodes, per-build randomised opcode bytes (seed
  `...vm:map:v1`), irregular operand forms, indirect jumps resolved from register
  values, self-modifying code (writable code buffer), ≥ 150k steps per profile, no RNG.
- **Encrypted bytecode at rest**: the program image is decrypted at runtime with a
  keystream derived from a **nonce the tool prints** (usage screen + first run). The
  nonce must be printed, and the plaintext program must be *fixed* — so all outputs
  stay deterministic. Deleting the nonce line must not change any output.
- Two profiles: `coast` (shorter) and `interior` (longer). Fresh state selects
  `interior`; both yield **identical** K_engine (assert this).
- K_engine = 32 fixed bytes produced by the trace — **pinned in §4.0**. The bytecode
  generator must be built so that the trace yields exactly that constant; the trace (or a
  correct emulation of it) is the only public route to it. Derive:
  - `bearing = LE64(K_engine[0:8])`      → Stage 2 sweep parameters (never printed)
  - `engine_ink = hex(K_engine[8:16])`   → 16 lowercase hex, used by Stage 5 (never printed)
  - checkpoint token = `CARTO{hex(K_engine[16:24])}` (printed; a checkpoint only)
- Printed output must be exactly: variant, step count, checkpoint token, flavour.
  It must **not** print K_engine, the bearing, the ledger, or any register state.
- Anti-debug: authoritative `/proc/self/TracerPid`; fallback `PTRACE_TRACEME` with
  `errno == EPERM`. On detection: silently use `K_engine'` (the debug key) — valid,
  format-valid, wrong — set `debugger_flag`, and continue (never error).
- Decoy: a `.rodata` record (plausible "pre-rekey" key) + lure string; submitting its
  token mints a corroborated branch and re-inks the decoy bearing → Stage 2 dead end.
- Traps: (a) `stage1_engine/profile.notes` states an authoritative-but-wrong step count
  (naive emulators self-verify against it and mis-correct; the tool never prints steps
  as ground truth in words); (b) a decoy entry point that looks like code; (c) usage
  text that is technically true but easy to misparse about the nonce.
- Acceptance: two clean runs → identical token + step count; an independent Python VM
  model reproduces the trace and K_engine bit-exactly on both profiles; the debug run
  yields the documented debug key; the decoy path yields the decoy bearing; the engine
  ink appears in no artifact (grep); `strings` shows no key material.

### 4.3 Stage 2 — The Sheet (`stage2_sheet/sheet` + two carriers)
Purpose: force keyed extraction with secret parameters; supply the sheet ink; TTY trap.
Carriers (regenerated byte-deterministically by a generator script):
- `survey_frame.png`: 1024×1024 RGB8, hand-written PNG (chunks IHDR, tEXt, tEXt, IDAT,
  IEND, CRC32 correct, filter 0 rows). Background: graticule with a **per-position
  dither** so no constant-offset/channel-difference test isolates the payload.
- `survey_tape.wav`: RIFF/WAVE PCM16 mono 8000 Hz, with a metadata chunk holding the
  56-byte **press** raw (ASCII tag + 32-byte tail = SHA-256 of seed `...stage2:press:v1`),
  plus an inert sample-LSB micro-distraction that is *not* the reading.
Three layers, in marks (marks = pixels in row-major order):
1. **Naive layer** — marks 0..1023: bit k = LSB of channel (k mod 3). Decodes to the
   registered Stage-2 decoy (valid flag, wrong). Padding after it must be zero.
2. **Middle layer** — marks ≥ 1024, drawn with the *near-miss* parameter pair so that a
   solver using one-off parameters gets readable, plausible, wrong text (never a flag).
3. **Real layer** — marks ≥ 1024, blue channel bit 0, every `stride`-th mark from `start`,
   packed MSB-first; payload = `LE16(len) || zlib_deflate(reading, preset_dict=press)`.
   ```
   stride = 5 + ((bearing & 0xFFFFFFFF) % 101)
   start  = 1024 + ((bearing >> 32) % 24000)
   ```
   Layers 2 and 3 must never share a bit position (assert in the suite).
- The reading is the pinned literal `CARTO{rust_blooms_under_tin_roofs}` (§4.0). Its words
  are deliberately unrelated to the theme so that flavour text cannot suggest them.
CLI (no verification of any answer — law 2):
- `sheet` (no args) → usage + carriers audited + gate flavour. rc 0.
- `sheet -r` → **reveal** the drawn ink, requires: correct bearing from argv/state AND
  `GATE_HUMAN` AND a real TTY. Piped or gated-out → truthful "reads a hand, not a pipe"
  line, rc 0, nothing leaked. With everything satisfied it prints the ink and the frame
  colour bit (see §3.5.3) plus `--plain` word form.
- `sheet -p <press-file> -R <ink-file>` → press mode: verifies the press against the
  FDICT/DICTID the ink was cut with (proves the press is right, never that the reading
  is). Prints a self-consistency digest only.
Traps: (1) `exiftool -b -Comment` re-encodes the 56-byte press to 70 bytes (the
documented honest route is `exiftool -v3` or a raw byte read — assert both in the suite);
(2) exact LC/MSB vs LE16 framing confusion yields 0x3000; (3) `--plain` colour rule;
(4) near-miss parameter branch (layer 2); (5) the naive layer's flag.
Must NOT contain: the reading, the bearing, the stride/start, any mechanism word
("blue", "LSB", "stride", "eight marks", "dictionary") in metadata or prose.
Acceptance: regenerating carriers twice is byte-identical; an independent Python sweep
recovers the reading with the real bearing and gets layer 2 with the near-miss bearing;
the statistical detector (suite script) cannot localise the payload region above chance;
PNG/WAV are structurally valid (`pngcheck`, `file`, `exiftool` clean); press byte-exact
extraction works; naive LSB read yields exactly the decoy; every gate path rc 0/silent.

### 4.4 Stage 3 — The Oracle (`stage3_oracle/oracle`)
Purpose: the volume + cryptanalysis stage. Produces the oracle ink. No static shortcut.
- Cipher: 64-bit block, two 32-bit halves, **5 rounds**, alternating round functions
  `G_A/G_B` with subkeys `kA,kB`, each `G_Z(y) = M_Z(y ^ fold_Z(y))` over eight shipped
  256-byte fold tables; planted bias: for each `(Z,j)`, exactly 64/256 table entries `W`
  satisfy `T[W] ^ T[W^(1<<b_Zj)] == W ^ W^(1<<b_Zj)`. Calibrate so completions per pair
  are ≈2^-5 (about 2× v1's sample requirement). Shipped tables are public by design —
  the *key* is not.
- Key derivation (the whole point; both pinned in §4.0):
  ```
  K_real = SHA-256(seed_real ‖ reading_bytes ‖ engine_ink_bytes)   <- the real key
  K_cold = SHA-256("ghost2:stage3:cold:v1" ‖ reading_bytes)        <- the decoy branch
  ```
  `K_cold` is what a solver gets by omitting the engine ink, or by handing the Stage-1
  token as `-i` — per §3.6 that is the **decoy derivation**: plausible, format-valid, wrong.
  The gates do NOT change the key; they change WHAT THE ORACLE WILL ANSWER: until
  `GATE_HUMAN && GATE_VOLUME && GATE_CHAIN` all hold, the oracle answers under `K_cold`
  and says so only in flavour ("the plate is still cold; the tally is not set") — never a
  warning, never an error, rc 0. Once the gates hold it answers under `K_real`.
- CLI: `oracle -r <reading> -i <16hex engine ink> <16hex figure>`; `oracle -t` prints the
  tally witness token (§4.0) once the gates hold (checkpoint reward, no key material). No
  key-check mode. Ever. The oracle binary must NOT contain the engine ink (assert with
  grep); it holds only the masked seed bytes.
- Multi-mode poison (≥ 5 modes, each: own wrong key, own tell, self-consistent, never an
  error, falsifiable): (1) constant interval < 150 ms stddev; (2) burst pattern;
  (3) piped/stdin-not-TTY calls; (4) duplicate/replayed figure rate > 35%;
  (5) sub-60 s "no thinking time" from first run. Each mode's wrong key must differ.
- Case trap: uppercase hex figures are answered under a different (also wrong) key; the
  usage text must state the format truthfully but without spelling out the case rule.
- Cache trap: repeating one figure twice in a row returns a stale-key answer from the
  ring cache (documented only internally; discoverable by comparing two paced asks).
- Acceptance: a Python attack recovers `K_real` bit-exactly from a dataset collected
  from the real binary at the calibrated budget and pacing; a Python implementation of
  the static path yields `K_cold` and never `K_real`; every poison mode reproduces and
  is distinguishable; mixed clean/poison data yields NO-CONSENSUS; every CLI path rc 0
  and stderr silent; `--help`/no-arg usage leaks no mechanism words.
- Calibration hook (inherited v1 pattern, compile-time gated so shipped builds cannot
  see it): `CARTO_TEST_TIME_SCALE` divides gate durations for test builds only; assert
  the shipped binaries ignore the variable entirely.

### 4.5 Stage 4 — The Seal (`stage4_seal/seal`) — the forced CPU search
Purpose: work that no amount of reversing can shortcut, because the answer is not in
the package. Produces the seal ink. Fixed, scorable, deterministic.
- A small hand-rolled 3-round Feistel over a 64-bit block with three subkeys
  (`k0,k1,k2`, 7 bytes total) and 4 shipped S-box-like tables. `seal` prints a
  certificate: 4 plaintext/ciphertext pairs, the block/hash rules, and a check rule.
- Intended attack: **meet-in-the-middle on rounds 1+3 vs round 2** ⇒ ≈2^28 work
  (15–30 min single core in C, slower in Python — that is the point). Naive space is
  2^56 and must be documented as infeasible. No key material in the binary; the
  key is minted from `...stage4:key:v1` and lives only in `organizer-private`.
- `seal <key-hex>` verifies a candidate against the certificate WITHOUT partial
  feedback: one refusal string, constant-time compare, rc 0, stderr silent. This is the
  only other yes/no surface allowed besides Stage 5's, and it only validates the seal
  key (never an answer-shaped string) — keep it because it makes Stage 4 fair.
- `seal --decoy` path: a plausible-but-wrong older construction (different round order)
  whose key is in `.rodata` and verifies against a *decoy* certificate printed by that
  path; a solver who finds it gets a valid-looking seal ink that fails at Stage 5.
- Acceptance: the intended MITM search (implemented in the suite in C) recovers the key
  and is verified by the certificate; a Python brute force is correctly infeasible
  (documented, not attempted); the decoy path yields a different key; refusal text is
  byte-identical for every wrong key; no key material in the binary or carriers.

### 4.6 Stage 5 — The Title Block (`stage5_title/validate`) — the only oracle
Purpose: assembly riddle + the single yes/no answer check. Produces the scored title.
- Inputs (never named or described structurally in the tool's words): the four inks —
  oracle ink (hex), engine ink (hex), sheet ink (reading text), seal ink (hex) — in an
  order given by a riddle that is *skim-hostile but fair*: every clause literally true,
  unique on a careful read, no mechanism named, no lengths, no counts, no separators.
  The same order is also cued by the banner layout (§3.5.4).
  **Normative order (internal): seal, oracle, engine, sheet** (§4.0); the riddle must
  encode exactly this and nothing else.
- `validate` (no args) → banner + the riddle + the inks described only by *provenance*
  ("the ink the oracle turned for the sheet", "the ink the engine never wrote down", …)
  + a struck-out draft (decoy, minted from `...stage5:decoy:draft:v1`) that must NOT
  mirror the final title's shape.
- `validate '<title>'` → computes SHA-256 of the argument and compares constant-time to
  the stored digest. Requirements: ONE refusal string byte-identical for every wrong
  input (wrong order, wrong ink, wrong length, garbage, extra args, empty), rc 0,
  stderr silent, no partial feedback, no timing signal (fold length/argc into the
  computation with bitwise ops, never short-circuit).
- Acceptance of the correct title requires `GATE_CHAIN` (the ring must show the earlier
  stages were actually reached) AND a real TTY; otherwise the refusal is identical to a
  wrong title's (no special-casing that leaks "you're right but gated").
- Traps: (a) the struck draft; (b) a near-miss reading (one character off) that is
  format-valid; (c) acceptance prints a *different* phrasing than refusal but never the
  title itself except on success; (d) the validator's usage suggests an older naming
  that matches nothing.
- Must NOT contain: any ink, any real component, any length/grammar statement, any
  per-component digest, any "N of M" logic.
- Acceptance: correct title accepted once the gates hold and never otherwise; 15+ wrong
  inputs (documented list) all produce byte-identical refusals; two clean rebuilds
  reproduce the identical binary hash; grep asserts no ink/reading/token appears.

---

## 5. DOCUMENTS TO PRODUCE

### 5.1 `organizer-private/` (never shipped, never inside the zip)
- `BUILD_SPEC_V2.md` — verbatim copy of THIS prompt (proves what was specified).
- `SESSION_1_LOG.md` — see §9.
- `KEYS_V2.md` — every seed, every real value, every derivation, every decoy value.
- `SOLVE_PATH_PRIVATE.md` — full honest solve path with timings, plus every trap's
  trigger/dead-end/recovery and the measured cost of each.
- `HINTS.md` — **exactly 5**, easiest-to-act-on first, each true for the SHIPPED build,
  each naming no mechanism, no length, no count, no answer. (v1's hint 2 contradicted the
  shipped binary — do not repeat that class of error.)
- `TRYHACKME_ROOM_TEXT.md` — room title, flavour text, the two scored questions and their
  exact answers, ONE native hint, a placeholder for the Drive link, difficulty/tags, and
  "download-and-run", plus the honest pacing line ("a marathon; no time limit").
  No stage counts, no grammar, no mechanism.
- `TRAP_CATALOGUE.md` — one row per trap: id, stage, trigger, what the solver sees,
  dead-end cost, recovery route, fairness argument.
- `COST_MODEL.md` — the dial table from §2.3 with measured numbers after calibration.
- `runs/*.log` — every verification capture.

### 5.2 Package (solver-facing)
Only the files in §3.1 + §3.8. Assert: zero `.md` outside `field-notes/`, zero source,
zero logs, zero organizer files, zero `.git`, zero build artifacts, no organizer words
in any filename.

### 5.3 Legacy warning (include verbatim in the log)
v1 artifacts are leaky: `E:\drive-upload\drive-upload\cartographer\` is the pre-FIX build
whose oracle ships mask labels + masked seeds (a solver can recover the Stage-3 key with
two lines of Python), and the sibling `cartographer.zip` is a *different* generation with
no run-capture evidence. Never publish either. Never copy v1 files into v2. Do not delete
them; just leave them untouched.

---

## 6. IMPLEMENTATION PHASES (execute in order; commit + log after each)

**P0 — Bootstrap.** Install toolchain (§1.1). Extract inherited v1 core (§1.2). Create
repo layout, `git init`, copy this prompt to `docs/BUILD_SPEC_V2.md` verbatim, create
`organizer-private/` and `organizer-private/runs/`. Acceptance: tool check prints all
paths; `git status` clean after first commit; `grep -c "" docs/BUILD_SPEC_V2.md` equals
the line count of this prompt.

**P1 — State v2 + behaviour engine** (`src/state`, unit suite `make test`).
Acceptance: ≥ 30 tests, 0 failed, covering: fresh create, roundtrip, every tamper offset
resets silently, ring wrap, chain hash, gate recomputation, anti-forgery bit-dropping,
per-stage key derivation, stddev/median/burst math against known vectors, HMAC with
per-stage keys, no shared key present in a linked test binary. Serial-only note in the
suite header. Also: `strings test_state | grep <any real key hex>` → nothing.

**P2 — Stage 0 + Stage 1.** Generate VM tables/bytecode/keys; write `stage0_ledger/ledger`
and `stage1_engine/engine`; write the independent Python VM model; write suites.
Acceptance: stage0 20+ checks; engine 40+ checks including both profiles, debug branch,
decoy branch, nonce-independence of outputs, model-vs-binary bit-exactness, `nm` empty,
grep for every real value → absent, two clean rebuilds → identical hash.

**P3 — Stage 2.** Carrier generator (deterministic), sheet tool, statistical detector
script, suites. Acceptance: 40+ checks: regen determinism (3× identical hashes), PNG/WAV
validity, all three layers extractable with the documented parameters, layer separation
asserted, near-miss branch yields layer 2, naive read yields the decoy, press byte-exact
via raw read and `exiftool -v3`, `exiftool -b` mangling reproduced and documented,
statistical detector cannot localise the payload, gate paths rc 0/silent, no mechanism
words in metadata.

**P4 — Stage 3.** Generate cipher tables/constants; write oracle; Python model + attack
driver; suite. Acceptance: 40+ checks: model==binary on 6+ figures under human pacing;
`K_cold` ≠ `K_real` and the static path provably yields only `K_cold`; attack recovers
`K_real` from a real-binary dataset at the calibrated budget (test-build scaling allowed);
each of the ≥5 poison modes reproduces with its own key; mixed dataset → NO-CONSENSUS;
no key-check mode exists (grep + CLI test); `CARTO_TEST_TIME_SCALE` absent from shipped
binaries; gate flavour text present and mechanism-free.

**P5 — Stage 4.** Write seal cipher + certificate + verifier; write the intended MITM
search in C (test tool); suite. Acceptance: 25+ checks: MITM recovers the key from a cold
start within the documented budget; certificate verifies it; wrong keys refused
identically; decoy path yields a different key; no key material in the binary; shipped
build ignores the test hook.

**P6 — Stage 5.** Build the title digest + riddle + validator; suite. Acceptance: 45+
checks: correct title accepted only when gates hold; 15+ wrong inputs all byte-identical
refusals with rc 0 + silent stderr; no ink/reading/token/grammar anywhere in the binary
or its usage; refusal timing constant (measure 30 refusals, max-min < 5 ms); rebuild
reproducible; package left pristine after the suite.

**P7 — Bait layer + README.** Write `field-notes/*` (≥ 2500 lines, zero truth), the
canary notices, `README_FOR_SOLVER.txt`. Acceptance: bait files parse; `SOLUTION_DRAFT.py`
runs and prints a wrong format-valid title; every bait claim is either inert flavour or
false; grep proves no real value/seed/substring appears in the bait layer; README has no
grammar/mechanism/stage counts.

**P8 — Calibration + packaging + quick adversarial.**
- Run the honest clean path on the TEST build (time-scale hook) → confirm the chain
  solves end to end and the gates can be satisfied.
- Run the honest clean path REAL, unscaled, paced, and record per-stage wall-clock.
- Run a scripted/fast path and confirm it is poisoned and gated out (must not reach the
  title).
- Write `COST_MODEL.md` with measured numbers; confirm the clean path lands in 12–20 h
  projected for a human+agent (state the arithmetic; if it does not, adjust ONLY the
  documented dials and re-measure).
- Build `cartographer/`, zip it, write `MANIFEST.sha256`, extract the zip elsewhere and
  solve it from there (isolated), confirm hashes.
Acceptance: isolated solve succeeds; manifest matches; every file in the zip is on the
allowed list; no organizer content in the zip.

**P9 — Final.** Run every suite once more from a clean build (`src/final/verify_all.sh`,
create it: state → P2..P6 suites SERIAL + determinism + reproducibility + scrub +
inventory + isolated solve + leak grep). Write `SESSION_1_LOG.md`; commit; copy the zip,
manifest, and public docs to `/mnt/e/drive-upload/ghost2/`. Print the final report.

---

## 7. SESSION-1 QUICK TEST CHECKLIST (run before you declare done)

One command each; all must pass; capture to `organizer-private/runs/`:
```bash
bash src/final/verify_all.sh         # state + all stage suites SERIAL + determinism
bash src/final/leak_grep.sh          # every real value/seed/label/digest must be ABSENT
bash src/final/rebuild_repro.sh      # clean rebuild ×2, identical hashes
bash src/final/package_check.sh      # allowed-file list, no organizer content, manifest
bash src/final/isolated_solve.sh     # solve from the extracted zip as a stranger
bash src/final/static_path_probe.py  # static derivations yield only DECOY values
bash src/final/behaviour_probe.py    # fast/piped/uniform paths are gated or poisoned
```
Every script prints `PASS`/`FAIL` lines and a final `OK`/`NOT OK`. Paste the real tails
into the log. If any fails: fix, re-run, and re-run `verify_all.sh` afterwards.

Quick sanity things that catch real bugs (do these too):
- `nm -a` on all six binaries → empty; `strings -n 5 | grep -Ei "gcc|clang|musl|/home/|<username>"` → nothing.
- Every tool with: no args, empty arg, 200 KB arg, garbage, 16 extra args, missing files,
  piped stdin/stdout, `TERM=dumb`, narrow `COLUMNS`, read-only package dir, missing
  carriers, corrupt state (flip every byte once) → rc 0, stderr silent, no crash.
- Two tools run concurrently → state stays valid (or one silently resets).
- Clock jumps backwards/forwards → no hang, no negative deltas, no gate false-positive.
- Delete state mid-chain → tower resets silently and the chain is still solvable.

---

## 8. TOKEN AND TIME DISCIPLINE (the session is long; be efficient)

- Never bulk-read v1 logs, never re-derive v1 mechanisms. §1.2 lists the only files worth
  opening.
- Use one driver script per phase; run it, read the tail, act.
- Debug in ≤ 3 iterations per symptom, then step back and re-read the spec section.
- Do not "improve" a mechanism, do not rename files, do not add stages, do not retune a
  dial without recording it in `COST_MODEL.md` with the reason.
- Commit at the end of every phase; keep the working tree clean.
- If a requirement is impossible as written (e.g. a bias that cannot be planted at the
  target density), STOP, report the blocker and the alternatives, and ask the user. Do not
  silently substitute.

---

## 9. LOG AND FINAL REPORT FORMAT

`organizer-private/SESSION_1_LOG.md` must contain, in this order:
1. Status line: `COMPLETE — all suites green (list counts)` or `BLOCKED — <reason>`.
2. Environment: distro, tool versions installed this session, repo path, git HEAD.
3. Per-phase: what was built (exact paths), every design decision and why, every constant
   (seed → value → where it lives), the exact commands, and the PASTED real output.
4. `KEYS_V2.md` cross-reference: seeds, real values, decoys, digests.
5. Trap table (id, stage, trigger, dead-end, recovery, fairness argument).
6. Measured timings: honest clean path (per stage), decoy detour, scripted path, static
   path, isolated solve; plus the 12–20 h projection arithmetic.
7. Explicit NOT-DONE / DEFERRED / ASSUMED-BUT-UNVERIFIED list (must be empty or explained).
8. Open questions and judgment calls for SESSION 2.
9. Final manifest: every file in the zip with size + sha256, plus the zip's own sha256.
10. Legacy warning from §5.3, verbatim.

Final message to the user (keep it short):
- one-line status, the zip path + size + sha256,
- suite pass counts, measured honest cost, the two scored answers,
- anything blocked, and the sentence: `SESSION 2 (AUDIT) PROMPT IS READY TO RUN`.

---

## 10. DEFINITION OF DONE (Session 1)

- [ ] Six working tools + two carriers + bait layer in `cartographer/`, all tests green.
- [ ] Every law in §2.2 verified by a named test, not by inspection.
- [ ] `organizer-private/` complete (§5.1) and never inside the zip.
- [ ] `cartographer.zip` + `MANIFEST.sha256` copied to `E:\drive-upload\ghost2\`.
- [ ] `SESSION_1_LOG.md` written with real pasted output and measured timings.
- [ ] Working tree committed; nothing left uncommitted or half-built.
- [ ] Legacy v1 artifacts untouched and not shipped.

Start now with Phase 0. Report the one-line confirmation, then work phase by phase.