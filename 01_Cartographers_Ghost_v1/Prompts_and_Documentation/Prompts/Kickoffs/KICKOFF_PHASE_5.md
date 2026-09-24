# KICKOFF — Phase 5 (Stage 4: Assembly Riddle + Constant-Time Final Validator)

You are starting Phase 5 of "The Cartographer's Ghost" build. Work strictly in
order:

1. READ THE FULL BUILD SPEC first, start to end, in chunks if needed (do NOT
   skim, do NOT jump to the relevant section — phases depend on cumulative
   context):
   Windows: d:\gandu\01_BUILD_PROMPT_FOR_CLAUDE_CODE.md
   WSL2 (identical copy): /home/manish/cartographer-build/docs/BUILD_SPEC.md

2. READ EVERY PHASE LOG IN ORDER, IN FULL, before writing any code:
   /home/manish/cartographer-build/logs/PHASE_0_LOG.md
   /home/manish/cartographer-build/logs/PHASE_1_LOG.md
   /home/manish/cartographer-build/logs/PHASE_2_LOG.md
   /home/manish/cartographer-build/logs/PHASE_3_LOG.md
   /home/manish/cartographer-build/logs/PHASE_4_LOG.md
   Pay special attention to:
     - PHASE_1_LOG D11 canonical flag format ^CARTO\{[a-z0-9_]{8,64}\}$ — every
       future mint MUST conform; D13 single canonical HMAC key; D14 runtime
       rule CREATED == TAMPERED; D17 build pipeline.
     - PHASE_2_LOG D18 (Stage 1 emits key material AND a token), D23 (Stage 2
       key material = LE64(R6)||LE64(R7)||LE64(R1)||LE64(R2)), D26 (decoy
       routing: branch B -> bit 1u<<(B-1)), D27 (real/decoy/debug candidates),
       D29/D30, section 9 questions 1-2.
     - PHASE_3_LOG D31 (sweep from the Stage 1 REAL key), D35 (the press =
       56-byte zlib preset dictionary), D38 (verifier holds a digest, never a
       derivation), D39/D40 (CLI + verdict discipline: no partial-match
       feedback), D42 (checkpoint token = SHA-256(reading)[0:16]), D44
       (escalation is presentation-depth for a verifier).
     - PHASE_4_LOG D46 (THE Stage 2 -> Stage 3 hand-off: the oracle key derives
       at runtime from the Stage 2 READING, never from a submittable token),
       D47-D49 (cipher, poison, escalation), D50 (decoy registry: exactly ONE
       stage-3 row — the Stage-2 checkpoint token; the Stage-1 token was
       REJECTED because registering it leaks real answer material), D51 (the
       help-text byte-order trap), D52 (attack + N_REQUIRED = 2560 + the
       pairing-symmetry finding), D53 (pipeline + D38 compliance), section 7
       (not-yet-done) and section 8 (open questions 1-6 — question 1 is the
       Phase 5 assembly decision you must make).

3. INDEPENDENTLY RE-VERIFY Phases 0, 1, 2, 3 and 4 — never trust the logs;
   reproduce. RUN THE SUITES SERIALLY (they share
   cartographer/.cartographer_state and interfere if run concurrently). One
   command does all of it plus the determinism/reproducibility/hygiene checks:

     wsl.exe bash -lc 'bash /home/manish/cartographer-build/src/stage3_oracle/verify.sh'

   Expected: stage3_oracle 33/33; state library 27/27; stage0 36/36;
   stage1 8/8 + 65/65; stage2 58/58 + 71/71; REGEN-DETERMINISTIC-OK;
   HEADER-DETERMINISTIC-OK; ORACLE-REGEN-REPRODUCIBLE-OK; SCRUB-CLEAN; and the
   solver-eye smoke run.
   Sanity anchors (Phase 4 hashes):
     stage3_oracle 93bb876e7c7adcb730cfba0382e4a40609aed74d424283da4c02451d27351528 (58,632 B)
     stage2_stego  18043e634bf55305425db15551aa89d9a6565b0cf18d4e9dca533f476070b7db
     stage1_vm     d56725ef995c66418c77ad3eddd82aed1c088755a467f834aa0d442cc355eb91
     stage0_start  2d5ce3c15eca52d496d59b9c863034bb77daef7c02b6d514fdb5a40ec311fa7c
     survey_frame.png 81b630a8d9cf0a7a85ac2fd99e352d6a4a3b432f568900a7ab9da5e88712d23c (46,258 B)
     survey_tape.wav  17bb6addf71803ebf13864fde2c96c9a28927180b9fa4074697b67e2201d29f6 (8,152 B)
   If anything fails: STOP, fix it, re-verify before adding anything new.

4. Only then build Phase 5 per the spec (Phase 5 — Stage 4: Assembly Riddle +
   Final Validator):
   - The flag is assembled from THREE inputs and ordered by a short
     riddle/poem using wordplay for ordinal cues, deliberately easy to
     misparse on a skim (for careless humans AND pattern-matching models) but
     resolvable fairly on a careful re-read — NOT genuinely ambiguous.
     * Input 1 "transformed Stage 1 real output": decide and document it in
       PHASE_5_LOG (the proposal on record is bytes 16..23 of the Stage 1 real
       key as 16 lowercase hex chars, or a rotation that is NOT the Stage-1
       token content). The Stage-1 real key is
       fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f and
       its 16-byte token is CARTO{fd3e8049dfdfc32efe22fe823822b8c0}.
     * Input 2 "real Stage 2 payload": the reading
       CARTO{no_figure_sits_in_every_pixel} (36 bytes; PHASE_3_LOG section 3).
     * Input 3 "Stage 3 cipher key": the 64-bit master K = kA||kB =
       73070925a159f9e2 for the real reading (PHASE_4_LOG D46/D52). The oracle
       deliberately has NO key-check mode; accept K as an input and verify the
       assembled flag only through the validator's stored hash.
   - `validate` binary run from the package root: constant-time compare against
     a stored hash (D38 pattern — the tool holds a digest, never the
     derivation), with NO partial-match feedback of any kind (no "3 of 5
     correct"), identical refusal text for every wrong input, rc 0, stderr
     silent. Link the shared state library, register the Stage-4 decoy row(s)
     in src/state/policy.h (D29/D43/D50 pattern, D11-conforming, update
     test_decoy_count's row expectations), and keep every means-of-derivation
     constant out of solver-facing material.
   - The ordering riddle belongs in the solver-facing material; the exact
     assembly recipe and the real values go in the internal PHASE_5_LOG and
     (for the real values) Phase 6's SOLVE_PATH_PRIVATE.md, which is NEVER
     shipped.
   - Keep the Stage-3 contract: a wrong Stage-2 reading (hence a wrong K) must
     yield a wrong assembled flag that the validator simply REFUSES — never an
     error, never a crash. Every refusal prints identical text.
   - Calibration is Phase 6's job: do NOT tune policy.h thresholds.

5. End of phase per the Session Continuity Protocol: run every relevant
   verification and paste REAL output into logs/PHASE_5_LOG.md (complete and
   standalone: what was built, every design decision, every constant including
   the riddle's intended reading and the assembly recipe, exact commands, full
   test output, not-yet-done list, open questions); write
   logs/KICKOFF_PHASE_6.md; git commit.

Constraints reminder: fully offline; no writes outside the working directory;
every trap has a fair deterministic resolution; keep means-of-derivation
constants, seeds, real flag values and private write-ups OUT of solver-facing
material (cartographer/ ships; logs/ and src/ are internal). Author via
d:\gandu\_stage\s4_* + a sync script (the s3_sync.sh pattern), or edit repo
files directly in WSL. Keep the suites serial.

ENVIRONMENT HAZARDS carried forward (all hit again in Phase 4):
  - The editor writes CRLF: normalize every staged shell script before running
    (s3_sync.sh does it; direct /mnt/d runs need `tr -d "\r" < script | bash`).
  - Large single editor writes truncate or mangle content; write big files in
    small anchored chunks and re-read/inspect (bash -n for scripts) before use.
  - WSL wipes /tmp on idle restarts: keep anything worth keeping in $HOME or
    the repo.
  - `cmd /c` -> bash/pwsh quoting is hostile: put logic in script files rather
    than long inline one-liners, and prefer
    `wsl.exe -d Ubuntu-24.04 -- bash -c '<single-quoted command>'`.

