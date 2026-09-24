# KICKOFF — Phase 6 (Mandatory Self-Testing + Calibration)

You are starting Phase 6 of "The Cartographer's Ghost" build. Work strictly
in order:

1. READ THE FULL BUILD SPEC first, start to end, in chunks if needed (do NOT
   skim, do NOT jump to the relevant section — phases depend on cumulative
   context):
   Windows: d:\gandu\01_BUILD_PROMPT_FOR_CLAUDE_CODE.md
   WSL2 (identical copy): /home/manish/cartographer-build/docs/BUILD_SPEC.md

2. READ EVERY PHASE LOG IN ORDER, IN FULL, before touching anything:
   /home/manish/cartographer-build/logs/PHASE_0_LOG.md
   /home/manish/cartographer-build/logs/PHASE_1_LOG.md
   /home/manish/cartographer-build/logs/PHASE_2_LOG.md
   /home/manish/cartographer-build/logs/PHASE_3_LOG.md
   /home/manish/cartographer-build/logs/PHASE_4_LOG.md
   /home/manish/cartographer-build/logs/PHASE_5_LOG.md
   Pay special attention to:
     - PHASE_1_LOG D11 canonical flag format ^CARTO\{[a-z0-9_]{8,64}\}$;
       D13 single canonical HMAC key; D14 runtime rule CREATED == TAMPERED.
     - PHASE_2_LOG D18 (Stage 1 emits key material AND a token), D23
       (packing = LE64(R6)||LE64(R7)||LE64(R1)||LE64(R2)), D26 (decoy
       routing branch B -> bit 1u<<(B-1)), D27 (real/decoy/debug
       candidates), section 9 questions 1-2.
     - PHASE_3_LOG D31 (sweep from the Stage 1 REAL key), D35 (the press =
       56-byte zlib preset dictionary), D38 (verifier holds a digest, never
       a derivation), D39/D40, D41/D44 (decoy depth + verifier-only
       escalation are Phase 6 calibration items), D42.
     - PHASE_4_LOG D46 (oracle key derives at runtime from the Stage 2
       READING), D47-D49 (cipher, poison, escalation), D50 (decoy
       registry; the Stage-1 token registration was REJECTED as a leak),
       D51 (byte-order trap), D52 (attack + N_REQUIRED = 2560 + the
       pairing-symmetry finding), section 8 open questions 1-6.
     - PHASE_5_LOG D54-D63: the assembly decision (Input 1 = bytes 16..23
       of the Stage 1 real key as hex — NOT the token content), the three
       inks, the riddle verse and its intended reading, the struck-draft
       decoy, the verdict/refusal discipline, and D63's VERIFY-CHAIN
       ORDERING warning (stage3's policy_patch.py rewrites policy.h to 3
       rows; always re-run src/stage4_assembly/policy_patch4.py after it).

3. INDEPENDENTLY RE-VERIFY Phases 0-5 — never trust the logs; reproduce.
   RUN THE SUITES SERIALLY (they share cartographer/.cartographer_state).
   One command does all of it plus determinism/reproducibility/hygiene:
     wsl.exe -d Ubuntu-24.04 -- bash -c 'bash /home/manish/cartographer-build/src/stage4_assembly/verify.sh'
   Expected: state 27/27 (4 decoy rows); stage0 36/36; stage1 8/8 + 65/65;
   stage2 58/58 + 71/71; stage3 33/33; stage4 64/64;
   VALIDATE-REGEN-REPRODUCIBLE-OK; SCRUB-CLEAN; solver-eye smoke run.
   Sanity anchors (Phase 5 hashes — they CHANGED in Phase 5 because
   registering the stage-4 decoy relinked every stage binary):
     stage4 validate   1fa7ed58ec0539d0b9d6a8ba406122325cd53c5037bd2e37d95f8bee7a7404ea (54,536 B)
     stage3 oracle     90312c0c793de09bf44d3c5fd6dcb4f2bc46b44cab3b99e1ebb74801a9402f5d (58,632 B)
     stage2_stego      2d852dd9c49893179669e95a29dcfa6448de3fb4e1f10621e1f7d5b1d494246f
     stage1_vm         7242be164835636be2a82b1694efdd401e474e651833fd2637819a7d8e7dcc86
     stage0_start      e9ba015c8141837a5215d635a2018daa78c56ab76f68a1fd5290127e989177b8
     survey_frame.png  81b630a8d9cf0a7a85ac2fd99e352d6a4a3b432f568900a7ab9da5e88712d23c (46,258 B)
     survey_tape.wav   17bb6addf71803ebf13864fde2c96c9a28927180b9fa4074697b67e2201d29f6 (8,152 B)
   If anything fails: STOP, fix it, re-verify before adding anything new.

4. THEN do Phase 6 per the spec (Phase 6 — Mandatory Self-Testing):
   1. Clean-path run: solve the whole chain optimally with full design
      knowledge (stage0 flag -> stage1 trace/key/token -> stage2 sweep +
      press -> the reading -> stage3 differential attack (N=2560, human-
      paced; use src/stage3_oracle/solve_attack.py --bin for real-binary
      collection) -> assemble the title per the PHASE_5_LOG D57 intended
      reading -> ./stage4_assembly/validate accepts it). Record TIME PER
      STAGE — sanity-checks nothing is impossible; this is not the
      calibration signal.
   2. Trap-path run: deliberately take the Stage 1 decoy constant and the
      Stage 2 decoy LSB layer, follow the decoy branches (stage1 re-ink,
      stage2 coast-press framing, stage3 checkpoint-token-as-reading,
      stage4 struck draft) to their dead ends, recover, finish properly.
      Record ACTUAL elapsed time in the detour.
   3. Calibrate constants until the decoy detour lands ~1-1.5 h and the
      total lands 2-3 h: tune policy.h thresholds (CARTO_T_FAST_SEC_DEFAULT,
      CARTO_STDDEV_LOW_MS, CARTO_MIN_TIMING_DELTAS), Stage 3's
      CARTO_VM_DEBUG_RATIO_LIMIT if needed, and N_REQUIRED pacing —
      THIS is the phase where tuning is allowed. Re-run the full verify
      chain after ANY constant change (relink + all five suites serially).
      Also resolve the PTRACE/SECCOMP fairness item (PHASE_2_LOG question
      5): require BOTH a ptrace failure AND a timing breach, or check
      errno for EPERM specifically, before shipping.
   4. Confirm every stage's real path is deterministically solvable — no
      luck, no infeasible brute force anywhere on the real path (Stage 3:
      verify the 2560-pair budget against the REAL binary, not just the
      model; measure a jittering script's spacing distribution vs
      CARTO_STDDEV_LOW_MS).
   5. Write SOLVE_PATH_PRIVATE.md (repo root or logs/, NEVER in
      cartographer/) — full internal writeup: real flag values (Stage 0
      CARTO{first_ink_in_the_ledger}; Stage 1 token
      CARTO{fd3e8049dfdfc32efe22fe823822b8c0}; Stage 2 reading
      CARTO{no_figure_sits_in_every_pixel} + token
      CARTO{b27692a0d5f63d4f1a0c3fb79afbf81b}; Stage 3 master K
      73070925a159f9e2; FINAL TITLE
      CARTO{73070925a159f9e2_a5d66f1b2b5f596e_no_figure_sits_in_every_pixel}),
      all real constants, measured timings, calibration notes.
   6. Log this phase per the Session Continuity Protocol like every other
      phase, including real measured timings — STOP AND REPORT THE
      TIMINGS TO THE USER BEFORE PHASE 7 BEGINS. If timings are off,
      that is a new phase to fix constants, not something to wave through.

5. End of phase per the Session Continuity Protocol: run every relevant
   verification (the stage4 verify.sh chain) and paste REAL output into
   logs/PHASE_6_LOG.md (complete and standalone: what was measured, every
   tuning change + why + before/after values, exact commands, full test
   output, the clean-path and trap-path timing tables, not-yet-done list,
   open questions); write logs/KICKOFF_PHASE_7.md; git commit.

Constraints reminder: fully offline; no writes outside the working
directory; every trap has a fair deterministic resolution; keep
means-of-derivation constants, seeds, real flag values and private
write-ups OUT of solver-facing material (cartographer/ ships; logs/ and
src/ are internal; SOLVE_PATH_PRIVATE.md is NEVER shipped). Author via
d:\gandu\_stage\s5_* + a sync script (the s4_sync.sh pattern), or edit
repo files directly in WSL. Keep the suites serial. Remember the
environment hazards: CRLF (normalize every staged script: run syncs as
`tr -d "\r" < script | bash`), large editor writes (chunk + re-read),
pwsh backtick mangling (NO backticks in any pwsh->bash payload; the
PHASE_5_LOG section 6 item 3), WSL /tmp wipes, and D63's verify-chain
ordering (stage3 policy_patch.py then stage4 policy_patch4.py).

---

## 6. Workspace layout (reorganized at the end of Phase 5 -- read d:/gandu/README.md)

- Windows: the master prompt stays at
  d:\gandu\01_BUILD_PROMPT_FOR_CLAUDE_CODE.md (referenced by every log);
  d:\gandu\_stage is your editor scratch -- author Phase-6 files there as
  s5_*, plus an s5_sync.sh on the s4_sync.sh pattern; everything from
  earlier phases is frozen under d:\gandu\_stage\archive\.
- WSL repo: docs/ (spec copy), logs/ (PHASE_*.md + KICKOFF_*.md protocol
  logs), logs/runs/ (verification captures), src/<stage>/ (sources +
  suites + per-stage verify.sh), cartographer/ (the solver package --
  keep it internal-free), README.md (layout + conventions).
- Run captures are now written to logs/runs/ by the verify drivers.
