# Build Spec: "The Cartographer's Ghost" — Offline Multi-Stage RE/Crypto CTF

This build spans multiple Claude Code sessions — one session per phase, to stay well within context limits. Read the **Session Continuity Protocol** section before starting Phase 0. It governs how every phase begins and ends, including this one.

---

## Environment (already set up — do not stop and ask)

- WSL2 is installed and ready. Windows 11 host, WSL2 user `manish`, password `1234` (use for any `sudo` calls needed during setup).
- If a specific tool/package turns out to be missing (musl-tools, exiftool, ImageMagick, etc.), **install it yourself** via `apt` using the sudo password above and continue — do not stop and ask the user. Only stop and ask if something fails to install after a reasonable retry, or requires something outside apt/WSL2 (e.g. a Windows-side install, a paid tool, a license).
- Working directory: `~/cartographer-build/` inside WSL2. Keep all build artifacts there. Git-init it at the very start of Phase 0 if not already done, and commit at the end of every phase (this is your rollback safety net across sessions).

---

## Session Continuity Protocol (governs every phase, read this first)

Each phase is a separate Claude Code session, because the full build will not fit in one context window, and because forcing a fresh read-and-verify pass at each boundary is itself a bug-catching mechanism (a session that "remembers" its own assumptions from ten steps ago is exactly how subtle errors slip through uncaught).

**At the end of every phase**, before ending the session, the agent must:

1. Run every test/verification relevant to that phase and confirm they pass. Zero tolerance: do not write "should work" or "looks correct" anywhere — either it is verified by actually running it, or the phase is not done.
2. Write `~/cartographer-build/logs/PHASE_N_LOG.md` — a **complete, standalone, detailed record** containing:
   - What was built in this phase, with exact file paths
   - Every design decision made and why (especially anything that deviates from or extends this spec)
   - Every constant, seed, key, threshold, or magic number introduced, with its exact value and where it lives
   - The exact commands used to build/compile/test everything, runnable verbatim by the next session
   - Full output of the verification/test run proving it works (paste real output, not a summary)
   - Explicit list of what is NOT yet done, deferred, or assumed-but-unverified
   - Any open questions or judgment calls the next session needs to know about
3. Write `~/cartographer-build/logs/KICKOFF_PHASE_N+1.md` — a short prompt the user will paste into a **new Claude Code session** to start the next phase. This kickoff prompt must explicitly instruct the next session to:
   - Read this original build spec document in full, start to end, in chunks if needed (do not skim or jump to the relevant section — the phases depend on cumulative context this spec provides)
   - Read every `PHASE_*_LOG.md` written so far, in order, in full, in chunks if needed
   - **Independently re-verify** the previous phase's deliverables actually work by re-running the test commands from the log itself — never trust the log's claim of success without reproducing it. If re-verification fails, stop and fix it before adding anything new; do not build on top of an unverified foundation.
   - Only then begin the new phase's work

**At the start of every phase** (including Phase 0, from the user pasting this document fresh), the agent must confirm out loud that it has read the full spec and all prior logs before writing any code or running any commands.

This protocol itself is part of the deliverable — if any phase skips logging or skips re-verification, that phase is not complete.

---

## Design Philosophy

This is a legitimate, self-contained, offline CTF challenge. It runs entirely on the solver's own machine after downloading a folder from Google Drive. TryHackMe hosts only the room description/question — no live backend, no calls to attacker infrastructure, no interaction with real third-party systems or real people's data.

**Two audiences, two different failure modes to exploit — build for both, not primarily one:**

- **Humans** get fooled by things that feel like a discovery, a shortcut, an oversight — satisfying to find, costly to fully chase. Also: fatigue, misreading, overconfidence after an early win, and narrative misdirection (believing the fiction's framing tells you something true about the mechanics, when it doesn't).
- **AI agents**, even very capable ones, get fooled by: pattern-matching to known public writeups, trusting a checksum-valid "looks like a flag" result without independently reproducing it, and — the important one for this build — being *smart* in a place where intelligence doesn't help, because the bottleneck is exhaustive mechanical verification, not insight. See "Token-Cost Design" below.

Target pacing: a skilled solver avoiding every trap finishes in **2–3 hours**. A solver who fully commits to the main decoy branch before backing out loses **roughly 1–1.5 hours** there before a dead end that reads as progress, not failure, and nudges back toward the real path.

---

## Token-Cost Design (assume a very powerful, very intelligent model is attempting this)

Do not design difficulty around "this requires clever insight" — assume whatever model attempts this has the insight. Design difficulty around **places where being smart doesn't shorten the work**, because that's what actually burns a large token/cost budget on a capable model instead of being solved in one elegant leap:

- **Large-but-finite disambiguation spaces that must be exhausted, not guessed.** E.g., several structurally-plausible readings of the Stage 4 riddle, each internally consistent, where only *actually running the full pipeline end-to-end* against each candidate ordering reveals which is correct — no shortcut exists that avoids trying them for real.
- **Long deterministic execution traces with no shortcut.** The Stage 1 VM's self-modifying/indirect-jump instructions should require genuinely stepping through a long trace (hundreds to low-thousands of instructions) — a smart agent can understand *why* the VM does what it does immediately, but still has to actually execute or emulate the full trace to get the real output, because the result depends on accumulated state, not on the algorithm's shape.
- **Verification-expensive traps, not detection-expensive ones.** Don't hide the decoy constants cleverly — let a smart agent find them fast (that's fine, even good). Make *confirming* which of several plausible results is the real one require a full downstream round-trip (build the next stage's input, run it, check it against something else) rather than something inferable from the value's shape alone. Intelligence gets you to the candidates quickly; only mechanical verification tells you which one is real, and there are enough candidates that this adds up.
- **The oracle in Stage 3** already forces many chosen-plaintext queries for the differential attack to work statistically — keep the required sample size real (per Phase 6 calibration) rather than reducible by a clever shortcut, so a smart agent still has to spend the queries.
- Do **not** make anything unsolvable-without-luck or dependent on guessing outside the puzzle's internal logic — token cost should come from legitimate exhaustive verification work, never from randomness.

---

## Overall Architecture

```
cartographer/
├── stage0_start/
├── stage1_vm/
├── stage2_stego/
├── stage3_oracle/
├── stage4_assembly/
├── .cartographer_state
└── README_FOR_SOLVER.txt
```

Native Linux binaries built in WSL2. No stage requires internet or root. Every stage binary links the shared `state.c`/`state.h` library described below.

### The local state file (core "adaptive" mechanic — no live server, everything pre-built and shipped)

- `.cartographer_state`, created on first run of Stage 0: `{first_run_timestamp, per_stage_attempt_count, per_stage_decoy_submitted_flags, last_n_interaction_timestamps, debugger_detected_flag}`.
- HMAC-SHA256 signed with a key obfuscated (not plaintext) in each binary. Tampering invalidates the HMAC and silently resets to first-run defaults rather than erroring — self-defeating tampering, not a suspicious error an agent could grep for.
- Each binary picks between **pre-compiled branches already embedded in its own data section** based on this state — nothing generated live, nothing fetched:
  - **Speed/uniformity escalation**: too-fast time-to-stage, or suspiciously uniform interaction timing (low stddev across `last_n_interaction_timestamps` — the tell of a scripted loop instead of a human or a genuinely-reasoning agent pausing to think), selects the harder pre-built variant of the current stage.
  - **Decoy routing**: submitting a known decoy flag doesn't error — it routes into an extended version of the current stage with flavor text framed as new information, not failure.
  - **Debugger/automation detection** (Stage 1): read by later stages to decide whether to serve a subtly corrupted constant instead of an outright error.

---

## Phase 1 — Stage 0: Orientation + Immediate Real Reward

- `stage0_start` binary: short in-fiction framing (agent writes the flavor text — old cartographer's vanished final survey, or your own theme), initializes `.cartographer_state`, records `first_run_timestamp`.
- Hands over a real, bankable partial flag immediately just for running it correctly per the README instructions — a genuine ungated win, not a trick, so later frustration doesn't feel hostile from the start.

---

## Phase 2 — Stage 1: Custom VM Reversing

- Stack-based bytecode VM in C, statically linked (musl), stripped. **60–90 distinct opcodes**, irregular encoding, self-modifying-style opcodes (reads subsequent bytes as data), indirect jumps from register values, opcode-to-number mapping randomized per build (keep the seed in your private notes only).
- Embedded bytecode program computes the Stage 2 key via iterated modular exponentiation with an irregular twist — modulus/exponent derived from accumulated VM register state, not fixed constants, so the trace must actually run (see Token-Cost Design) rather than being read off statically.
- **Human trap**: a plausible "forgotten debug symbol"-looking constant in `.rodata`, satisfying to discover, wrong — fails downstream at Stage 3 in a non-obvious way rather than crashing immediately, so the solver commits real time before realizing they need to redo Stage 1. This is the main driver of the ~1–1.5hr trap budget — make it genuinely well-disguised, not a token gesture.
- **Human trap #2 (narrative misdirection)**: something in the in-fiction flavor text (a "note from the cartographer," a red-herring map coordinate, a name) should read as if it's a mechanical clue but is purely flavor — rewards careful readers who test it and move on quickly, punishes those who over-invest in treating narrative as mechanism. Keep this fair: a careful solver should be able to falsify it fairly cheaply once they think to test it, not spend an hour on it.
- **AI-agent trap**: 2–3 early instruction sequences that resemble a well-known public CTF VM's loop-decrement-compare-jump idiom closely enough that a model may confidently claim to "recognize" the challenge and reach for a known solution shape — worthless here since opcode numbers are randomized per build, and actively misleading if trusted without dynamic re-verification (this is exactly the kind of shortcut Token-Cost Design should make expensive to fall for).
- **Anti-debug/anti-automation**: `ptrace(PTRACE_TRACEME,...)` self-attach check + timing-based single-step detection. On detection, do not exit or error — silently flip `debugger_detected_flag` and continue with a subtly corrupted (same length/format, wrong value) derived constant, so naive dynamic analysis produces a confident wrong answer.
- Build pipeline: musl-gcc static compile → `strip --strip-all` → scrub residual debug paths/compiler strings.

---

## Phase 3 — Stage 2: Nested Steganography

- **Decoy layer**: naive full-image LSB in a PNG, findable by any standard tool, decodes to a flag-shaped string that passes the Stage 4 checksum format check — genuinely looks legitimate. Submitting it routes into the extended dead-end branch via state-file logic, framed as new information, never as an error.
- **Real layer**: blue-channel-only LSB at a **pixel stride derived from Stage 1's real (not decoy) output** — wrong Stage 1 result pulls garbage, not an error, so the solver has to notice the extracted data doesn't parse rather than being told outright. Compressed with a zlib **custom preset dictionary** (derived from a constant elsewhere in the package) so naive decompression fails until the solver notices and supplies it.
- WAV file: real content in RIFF metadata padding, not audio samples; an obvious-but-irrelevant LSB pattern in the actual samples as a cheap secondary micro-distraction.
- **Human trap (manual/patience-based, not tooling-based)**: make at least one piece of this stage require a fiddly manual step a script-first approach undervalues — e.g., a specific ImageMagick/exiftool flag combination that must be discovered by reading tool documentation/help output carefully rather than guessed from habit, because the default output of common stego tools silently mangles the exact byte range that matters here.

---

## Phase 4 — Stage 3: Local Rate-Limited Chosen-Plaintext Cipher Oracle

- Hand-rolled Feistel-network cipher (not textbook), deliberate subtle statistical bias in the round function, discoverable via differential cryptanalysis given enough chosen-plaintext/ciphertext pairs. Calibrate the required sample size to be real and non-trivial (Phase 6) but not computationally infeasible.
- Local binary (`./oracle <hex_plaintext>` → ciphertext), not networked.
- **Automation detection**: near-uniform call spacing (read from shared state) triggers silent poisoned-ciphertext responses (well-formed, consistent, generated from a different internal key) instead of an error — a scripted brute-force differential attack collects a large, confident, wrong dataset unless jitter is added or the solver notices the sabotage pattern by comparing scripted vs. manually-timed queries.
- **Human trap**: the oracle's help/usage text should describe the input format in a technically-true but easy-to-misread way (e.g., ambiguous hex byte-order phrasing) that a careless human transcribes wrong for a while before the mismatch becomes obvious from consistently-off-looking results — fair, self-correcting once tested carefully, but a real tax on careless reading.

---

## Phase 5 — Stage 4: Assembly Riddle + Final Validator

- Flag assembled from: transformed Stage 1 real output, real Stage 2 payload, Stage 3 cipher key.
- Ordering specified by a short riddle/poem using wordplay for ordinal cues, deliberately easy to misparse on a skim (for both careless humans and pattern-matching models) but resolvable fairly on a careful re-read — not genuinely ambiguous.
- Local `validate` binary: constant-time compare against a stored hash, **no partial-match feedback of any kind** (no "3 of 5 correct") — prevents incremental guess-and-check loops for either audience.

---

## Phase FINAL — Calibration, Verification & Final Deliverables (Single Combined Session)

Consolidates all self-testing, timing calibration, writeups, packaging, and release verification into a single continuous unit of work for a live-hackathon deliverable.

1. **Clean-path solve run**: solve optimally with full design knowledge from Stage 0 to Stage 4. Record real elapsed time per stage — sanity-checks nothing is impossible, not the real calibration signal.
2. **Trap-path solve run**: deliberately fall into the Stage 1 decoy constant and Stage 2 decoy LSB layer, follow to dead ends, recover, finish properly. Record actual elapsed time in the decoy detour. Adjust thresholds/constants until decoy time lands ~1–1.5hrs and total lands 2–3hrs.
3. **Deterministic solvability confirmation**: confirm every stage's real path is deterministically solvable — no luck, no infeasible brute force anywhere on the real path.
4. **`SOLVE_PATH_PRIVATE.md` writeup**: full internal writeup, real flag values, real constants, calibration notes. **Never shipped to solvers.**
5. **Packaging into final `cartographer/` folder**: prepare the full solver package for Google Drive:
   - Binaries: `stage0_start`, `stage1_vm`, `stage2_stego`, `oracle`, `validate`
   - Carrier files: `survey_frame.png`, `survey_tape.wav`
   - Single bare-bones `README_FOR_SOLVER.txt`: what this is, needs WSL2/Linux, how to run stage0, TryHackMe multi-flag submission format — zero internals.
6. **`HINTS.md`**: exactly 5 hints, easiest→hardest to *act on*, individually terse/cryptic but genuinely useful once understood, each nudging toward a specific stage without naming the answer. For the user to hand out manually — no in-challenge hint delivery mechanism.
7. **`TRYHACKME_ROOM_TEXT.md`**: room title/flavor text, exact question text for TryHackMe, the final real answer, one short TryHackMe-native hint (separate from HINTS.md), placeholder line for the Google Drive link.
8. **Final Top-to-Bottom Re-Verification Pass (Isolated Package)**:
   - Perform an isolated verification of the packaged `cartographer/` folder in isolation (as if freshly downloaded from Google Drive, e.g. copied to `/tmp/cartographer-dist/` or equivalent) — not the working `src/` tree.
   - Verify that the package actually runs and solves end-to-end in isolation.
   - Ensure zero leftover build artifacts, scratch files, `.git` metadata, source code, or internal notes are accidentally included.
   - Ensure the package contains ONLY what a solver should receive plus the single bare `README_FOR_SOLVER.txt`.
   - Explicitly verify that no markdown files (no `.md`), no logs, no kickoff prompts, no `docs/`, and no `.git` metadata exist in the Drive-ready package.
9. **Final Go/No-Go Deliverable Report**:
   - Zero known bugs, zero unresolved issues.
   - Explicit final go/no-go statement.
   - List every file in the final Drive-ready `cartographer/` folder and every other deliverable file's path for immediate upload.

---

## Constraints (do not violate)

- Fully offline after download — no server calls, no telemetry, no phoning home.
- Anti-debug/anti-automation techniques are standard CTF reversing tradecraft — nothing that damages the solver's system, persists outside the challenge folder, or resembles real malware (no persistence, no privilege escalation, no network exfiltration, no writes outside the working directory).
- Every trap has a fair, deterministic resolution reachable through legitimate analysis — nothing is a coin flip or requires guessing outside the puzzle's own internal logic.
- No real third-party service, person, or business referenced or scraped — fully self-contained synthetic content.
