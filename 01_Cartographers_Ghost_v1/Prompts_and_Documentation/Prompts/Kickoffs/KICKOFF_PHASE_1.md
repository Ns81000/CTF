# KICKOFF — Phase 1 (Stage 0: Orientation + Immediate Real Reward)

You are starting Phase 1 of "The Cartographer's Ghost" build. Work strictly in order:

1. READ THE FULL BUILD SPEC first, start to end, in chunks if needed (do NOT skim,
   do NOT jump to the relevant section — phases depend on cumulative context):
   Windows: d:\gandu\01_BUILD_PROMPT_FOR_CLAUDE_CODE.md
   WSL2 (identical copy): /home/manish/cartographer-build/docs/BUILD_SPEC.md

2. READ /home/manish/cartographer-build/logs/PHASE_0_LOG.md IN FULL before writing
   any code or running any build commands.

3. INDEPENDENTLY RE-VERIFY Phase 0 — never trust the log's claims; reproduce them:
     wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/state && make clean && make test && file test_state'
   Expect: 26 tests run, 0 failed, ALL TESTS PASSED, statically linked binary.
   If anything fails: STOP, fix it, re-verify before adding anything new.

4. Only then build Phase 1 per the spec:
   - stage0_start binary: short in-fiction framing (write the flavor text yourself —
     old cartographer's vanished final survey or your own theme), initializes
     .cartographer_state via the EXISTING shared state library (src/state/), records
     first_run_timestamp, and hands over a real, bankable partial flag immediately —
     a genuine ungated win, not a trick.
   - Decide and document the canonical FLAG FORMAT (Phase 0 left "CARTO{...}"
     tentative) and mint the Stage-0 real flag + record every constant in your log.
   - Build musl static, strip --strip-all, scrub residual debug paths/compiler strings.
   - Reuse the authoring pipeline described in PHASE_0_LOG.md section 1/4 (staging
     dir + /mnt/d copy + CRLF normalize), or edit repo files directly in WSL.

5. End of phase per the Session Continuity Protocol: run every relevant verification
   and paste REAL output into logs/PHASE_1_LOG.md (complete and standalone: what was
   built, every design decision, every constant with exact value + location, exact
   commands, full test output, not-yet-done list, open questions); write
   logs/KICKOFF_PHASE_2.md; git commit.

Constraints reminder: fully offline; no writes outside the working directory; every
trap has a fair deterministic resolution; keep opcode-mapping seeds and private
constants OUT of solver-facing material (logs are internal).
