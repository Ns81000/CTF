# KICKOFF — Phase 2 (Stage 1: Custom VM Reversing)

You are starting Phase 2 of "The Cartographer's Ghost" build. Work strictly in order:

1. READ THE FULL BUILD SPEC first, start to end, in chunks if needed (do NOT skim,
   do NOT jump to the relevant section — phases depend on cumulative context):
   Windows: d:\gandu\01_BUILD_PROMPT_FOR_CLAUDE_CODE.md
   WSL2 (identical copy): /home/manish/cartographer-build/docs/BUILD_SPEC.md

2. READ EVERY PHASE LOG IN ORDER, IN FULL, before writing any code:
   /home/manish/cartographer-build/logs/PHASE_0_LOG.md
   /home/manish/cartographer-build/logs/PHASE_1_LOG.md
   (Pay special attention to: PHASE_1_LOG D11 canonical flag format
   ^CARTO\{[a-z0-9_]{8,64}\}$ — all future mints MUST conform; D13 single
   canonical HMAC key; D14 runtime rule CREATED==TAMPERED; D17 build pipeline
   incl. objcopy --remove-section .comment.)

3. INDEPENDENTLY RE-VERIFY Phases 0+1 — never trust the logs; reproduce:
     wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/state && make clean && make test && file test_state'
   Expect: 26 tests run, 0 failed, ALL TESTS PASSED, statically linked.
     wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/stage0 && make && ./test_stage0.sh'
   Expect: 36 tests run, 0 failed, ALL TESTS PASSED.
   If anything fails: STOP, fix it, re-verify before adding anything new.

4. Only then build Phase 2 per the spec (Phase 2 — Stage 1: Custom VM Reversing):
   - Stack-based bytecode VM in C, statically linked (musl), stripped;
     60-90 distinct opcodes, irregular encoding, self-modifying-style opcodes,
     indirect jumps from register values, opcode-to-number mapping randomized
     per build (keep the seed in PHASE_2_LOG.md — internal, never solver-facing).
   - Embedded bytecode computes the Stage 2 key via iterated modular
     exponentiation with an irregular twist; modulus/exponent derived from
     accumulated VM register state so the trace must actually run.
   - The shared state library must be linked and updated (attempts, interaction
     ring, CARTO_ESC_* handling per spec/PHASE_1_LOG D15) — Stage 1 is where
     escalation variants and the anti-debug ptrace/timing detection begin.
   - Traps per spec: .rodata "forgotten debug constant" decoy (main 1-1.5hr
     budget), narrative-misdirection flavor, AI-agent pattern-match bait
     (public-VM idiom lookalikes), ptrace(PTRACE_TRACEME)+timing detection that
     silently flips debugger_detected_flag and serves a corrupted constant.
   - Flag/key output: mint per D11 format ONLY if Stage 1 emits a submittable
     string; otherwise emit Stage 2 key material (see PHASE_1_LOG Q1 — decide
     and document).
   - Author via the documented staging pipeline (editor -> d:\gandu\_stage\s1_*
     -> /mnt/d copy + CRLF->LF normalize) or edit repo files directly in WSL;
     reuse src/stage0/Makefile as the build-pipeline template.

5. End of phase per the Session Continuity Protocol: run every relevant
   verification and paste REAL output into logs/PHASE_2_LOG.md (complete and
   standalone: what was built, every design decision, every constant incl. the
   opcode-mapping seed with exact value + location, exact commands, full test
   output, not-yet-done list, open questions); write logs/KICKOFF_PHASE_3.md;
   git commit.

Constraints reminder: fully offline; no writes outside the working directory;
every trap has a fair deterministic resolution; keep opcode-mapping seeds and
private constants OUT of solver-facing material (logs are internal).
