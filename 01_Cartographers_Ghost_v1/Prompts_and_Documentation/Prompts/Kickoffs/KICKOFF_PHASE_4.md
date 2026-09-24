# KICKOFF — Phase 4 (Stage 3: Local Rate-Limited Chosen-Plaintext Cipher Oracle)

You are starting Phase 4 of "The Cartographer's Ghost" build. Work strictly in order:

1. READ THE FULL BUILD SPEC first, start to end, in chunks if needed (do NOT skim,
   do NOT jump to the relevant section — phases depend on cumulative context):
   Windows: d:\gandu\01_BUILD_PROMPT_FOR_CLAUDE_CODE.md
   WSL2 (identical copy): /home/manish/cartographer-build/docs/BUILD_SPEC.md

2. READ EVERY PHASE LOG IN ORDER, IN FULL, before writing any code:
   /home/manish/cartographer-build/logs/PHASE_0_LOG.md
   /home/manish/cartographer-build/logs/PHASE_1_LOG.md
   /home/manish/cartographer-build/logs/PHASE_2_LOG.md   (890 lines; read it all)
   /home/manish/cartographer-build/logs/PHASE_3_LOG.md   (~700 lines; read it all)
   Pay special attention to:
     - PHASE_1_LOG D11 canonical flag format ^CARTO\{[a-z0-9_]{8,64}\}$ — every
       future mint MUST conform; D13 single canonical HMAC key; D14 runtime rule
       CREATED==TAMPERED; D17 build pipeline.
     - PHASE_2_LOG D18 (Stage 1 emits key material AND a token), D23 (Stage 2 key
       material = LE64(R6)||LE64(R7)||LE64(R1)||LE64(R2)), D24 (anti-debug), D25
       (escalation variants), D26 (decoy routing: branch B -> bit 1u<<(B-1)), D27
       (the real/decoy/debug candidates), D29/D30, section 9 open questions.
     - PHASE_3_LOG D31 (the sweep derivation from the Stage 1 REAL key), D35 (the
       press = 56-byte zlib preset dictionary in the tape's INFO/ICMT), D37 (the
       VERIFIED exiftool manual-step trap), D38 (the tool holds NO means of
       derivation — it verifies a digest and never the reading), D39/D40 (CLI +
       verdict discipline), D41 (decoy routing to the extended branch), D44
       (escalation is presentation-depth for a verifier; Phase 6 revisits),
       section 8 (DEEPENED DECOY DEAD END is deferred to Phase 6) and section 9
       (question 1: the Stage 2 -> Stage 3 hand-off decision you must make).

3. INDEPENDENTLY RE-VERIFY Phases 0, 1, 2 and 3 — never trust the logs; reproduce.
   RUN THE SUITES SERIALLY (they share cartographer/.cartographer_state and
   interfere if run concurrently). One command does all of it plus the
   determinism/reproducibility/hygiene checks:

     wsl.exe bash -lc 'bash /home/manish/cartographer-build/src/stage2_stego/verify.sh'

   Expected: state 27/27; stage0 36/36; stage1 8/8 + 65/65; stage2 58/58
   differential vectors + 71/71; REGEN-DETERMINISTIC-OK;
   HEADER-DETERMINISTIC-OK; three identical sha256 lines for stage2_stego;
   SCRUB-CLEAN; and the solver-eye smoke run.
   Sanity anchors: stage2_stego sha256
     5058a901eddbd9bc539ba27168c401fbdffd49409d6a82e4bfecd080438a8e4e (62,728 B);
4. Only then build Phase 4 per the spec (Phase 4 — Stage 3: Local Rate-Limited
   Chosen-Plaintext Cipher Oracle):
   - A hand-rolled Feistel-ish network (NOT a textbook design) with a deliberate
     subtle statistical bias in the round function, exploitable by differential
     cryptanalysis given enough chosen-plaintext/ciphertext pairs. The required
     sample size must be real and non-trivial but NOT computationally infeasible
     — pick it now, record it, and let Phase 6 calibrate it against real timing.
   - `./oracle <hex_plaintext>` -> ciphertext, run from the package root, linked
     against the shared state library (attempts, interaction ring, escalation
     variants, decoy routing). musl-static/stripped/scrubbed; lands in
     cartographer/stage3_oracle/.
   - Near-uniform call spacing (read from the shared state ring) must trigger
     SILENT POISONED-CIPHERTEXT responses (well-formed, consistent, generated
     from a different internal key) instead of an error, so a scripted
     brute-force differential attack collects a large, confident, WRONG dataset
     unless it adds jitter or notices the sabotage by comparing scripted vs
     manually-timed queries. The poison must be self-consistent (a second
     poisoned call with the same input must give the same poisoned answer) and
     falsifiable through legitimate analysis; it must NOT be a coin flip.
   - Human trap: the oracle's help/usage text describes the input format in a
     technically-true but easy-to-misread way (e.g. ambiguous hex byte-order
     phrasing) so a careless human transcribes wrong for a while before the
     mismatch becomes obvious from consistently-off results — fair and
     self-correcting, but a real tax on careless reading.
   - DECIDE PHASE_3_LOG SECTION 9 QUESTION 1 EXPLICITLY and log it: how Stage 3's
     key/hand-off derives from Stage 2 (recommendation: from the Stage 2 READING,
     never from a submittable token), and confirm that a wrong Stage 2 reading
     yields a wrong Stage 3 answer that fails later rather than erroring.
   - Do not gate the oracle on "correct" Stage 2 state in a way that reads as an
     error (spec: every dead end must be framed as new information).
   - Reuse the D38 pattern where possible: prefer a verifier that holds a digest
     rather than the derivation, and keep means-of-derivation constants out of
     solver-facing material.
   - Register every new discoverable decoy in src/state/policy.h (D29/D43
     pattern), keep it D11-conforming, and update test_decoy_count's row
     expectations if it asserts specific rows.
   - Calibration is Phase 6's job: do NOT tune policy.h thresholds.

5. End of phase per the Session Continuity Protocol: run every relevant
   verification and paste REAL output into logs/PHASE_4_LOG.md (complete and
   standalone: what was built, every design decision, every constant including
   the round function/bias/sample-size derivation and cipher test vectors, exact
   commands, full test output, not-yet-done list, open questions); write
   logs/KICKOFF_PHASE_5.md; git commit.

Constraints reminder: fully offline; no writes outside the working directory;
every trap has a fair deterministic resolution; keep means-of-derivation
constants, seeds and private write-ups OUT of solver-facing material
(cartographer/ ships; logs/ and src/ are internal). Author via
d:\gandu\_stage\s3_* + a sync script (the s2_sync.sh pattern), or edit repo files
directly in WSL. Keep the suites serial. NOTE the two environment hazards the
Phase 3 log records: the editor's line-number inserts have repeatedly produced
scrambled/truncated files (always re-read a generated file before building), and
WSL wipes /tmp on idle restarts (use $HOME or the repo for anything you must keep
within a session).
   survey_frame.png 81b630a8...712d23c (46,258 B);
   survey_tape.wav  17bb6add...01d29f6 (8,152 B);
   stage1_vm 317d4a84...99f49e1a; stage0_start f2d1e064...1d2486f.
   If anything fails: STOP, fix it, re-verify before adding anything new.