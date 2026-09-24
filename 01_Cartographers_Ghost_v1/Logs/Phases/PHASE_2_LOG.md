# PHASE 2 LOG — Stage 1: Custom VM Reversing (the Survey Engine)

Status: COMPLETE — all verifications passing (65/65 stage1 end-to-end checks,
8/8 detection-verdict unit checks, 26/26 Phase-0 state-library regression,
36/36 Phase-1 stage0 regression, independent python-model cross-check of the
C interpreter, reproducible build, deterministic regeneration). Repo:
/home/manish/cartographer-build (git branch `main`). Date of session:
2026-09-19.

## 0. Protocol confirmation (Session Continuity Protocol)

Before writing any code or running any build command, this session:

1. READ the full build spec start to end:
   d:\gandu\01_BUILD_PROMPT_FOR_CLAUDE_CODE.md (all 164 lines, in chunks;
   identical copy at /home/manish/cartographer-build/docs/BUILD_SPEC.md).
2. READ /home/manish/cartographer-build/logs/PHASE_0_LOG.md IN FULL (295
   lines) and /home/manish/cartographer-build/logs/PHASE_1_LOG.md IN FULL
   (314 lines), in order.
3. INDEPENDENTLY re-verified Phases 0 and 1 — reproduced, did not trust the
   logs (real output in section 5).

Both foundation suites passed on the first re-verification run, so no repair
work was needed before Phase 2 began.

## 1. What was built (exact paths, all in /home/manish/cartographer-build)

Authoring pipeline: the editor wrote staging files d:\gandu\_stage\s1_*; a
one-shot copy script (d:\gandu\_stage\s1_sync.sh, run verbatim as
`wsl.exe bash -lc 'tr -d "\r" < /mnt/d/gandu/_stage/s1_sync.sh | bash'`)
copied them into the repo with CRLF->LF normalisation. Repo copies are
canonical; staged copies are the editable source of record for Windows.

- src/stage1_vm/vm_spec.py      — ISA single source of truth + seeded
                                  randomiser + assembler + header generator
                                  (758 lines; INTERNAL, not shipped)
- src/stage1_vm/vm_tables.h     — GENERATED + committed: VM_OP_COUNT=86 enum,
                                  per-build kOpByte[] (86 distinct opcode
                                  bytes drawn from 0..255), kOpForm[],
                                  kOpEndian[]
- src/stage1_vm/vm_program.h    — GENERATED + committed: kProgram0 (692 B),
                                  kProgram1 (759 B); no key material inside
- src/stage1_vm/vm_layout.json  — GENERATED + committed: machine-readable
                                  layout for the python model (seed, op
                                  table, program hex)
- src/stage1_vm/vm.h / vm.c     — the interpreter (41 + 378 lines): data-
                                  driven decode from the per-build form
                                  table, 12 registers, 256-entry stack,
                                  64-word data memory, private WRITABLE code
                                  buffer (real self-modification), step
                                  counter, fault flag, vm_pack_key()
- src/stage1_vm/stage1_vm.c     — the Stage 1 main (254 lines): state
                                  lifecycle, escalation variant selection,
                                  anti-debug (ptrace + timing), decoy
                                  routing, key packing, token minting,
                                  flavor text, decoy .rodata record
- src/stage1_vm/decoy_blob.h    — GENERATED + committed by gen_decoys.py:
                                  kStage1ForgottenKey[32] + lure note
- src/stage1_vm/gen_decoys.py   — decoy generator (INTERNAL; refuses to mint
                                  a non-D11 decoy flag)
- src/stage1_vm/vm_debug.h      — pure timing-verdict helper (shared by the
                                  shipped binary and the internal unit test)
- src/stage1_vm/model_vm.py     — INDEPENDENT python implementation of the
                                  documented ISA (441 lines) + --selftest +
                                  --emit; INTERNAL, not shipped
- src/stage1_vm/test_detect.c   — 8 unit checks for the timing verdict
- src/stage1_vm/forge_state.py  — internal HMAC-valid state forger (copy of
                                  the test suite's helper, for later phases)
- src/stage1_vm/test_stage1.sh  — 65-check end-to-end verification suite
- src/stage1_vm/Makefile        — musl static build + strip + scrub; test,
                                  test_detect, stage1_vm.dbg, clean targets
- src/stage1_vm/listings/       — GENERATED internal disassembly listings
                                  (vm_profile0.txt 174 lines, vm_profile1.txt
                                  194 lines) for audit/review
- src/state/policy.h            — placeholder decoy REPLACED by the real
                                  Stage-1 decoy (D29); mechanism untouched
- src/state/test_part2.c        — test_decoy_lookup made table-driven (D29)
- src/state/Makefile            — -fno-ident folded in (D29; PHASE_1_LOG D17
                                  follow-up)
- cartographer/stage1_vm/stage1_vm — THE DELIVERABLE BINARY (62,728 bytes;
                                  sha256
                                  317d4a846af9168ed34b1283ae05bccdebb659ade342343d63a16fcc99f49e1a;
                                  reproducible: identical hash across rebuilds)
- .gitignore                    — += src/stage1_vm/stage1_vm.dbg,
                                  src/stage1_vm/test_detect, __pycache__/
- logs/PHASE_2_LOG.md, logs/KICKOFF_PHASE_3.md — this phase's artifacts

Solver package layout: the binary lives at cartographer/stage1_vm/stage1_vm
and is run FROM the cartographer/ package root (same convention as Stage 0);
it passes "./.cartographer_state" explicitly, so the state file stays at the
package root next to the stage directories (spec tree).

## 2. Design decisions and why

D18. STAGE 1 OUTPUT (answers PHASE_1_LOG open question Q1, DECIDED): the VM
     emits BOTH (a) the Stage 2 key material and (b) a D11-conforming
     submittable token. Key material = 32 bytes, printed as 64 lowercase hex
     chars. Token = "CARTO{" + lowercase hex of the FIRST 16 KEY BYTES + "}"
     (38 chars; contents 32 chars, all in [0-9a-f], conforming to
     ^CARTO\{[a-z0-9_]{8,64}\}$). Rationale: (i) Stage 2 needs concrete key
     material (its pixel stride is derived from Stage 1's REAL output);
     (ii) the token gives the solver a bankable checkpoint, same reward
     grammar as Stage 0's ungated win; (iii) minting the token from the key
     means only a correctly-run trace can produce it. TRADE-OFF RECORDED: a
     wrong token (decoy or debugger path) is format-valid, so if Phase 7
     makes intermediate tokens TryHackMe-scored answers, a decoy gets
     rejected instantly and the trap cheapens. RECOMMENDATION for Phase 7:
     score only the Stage-0 flag and the final assembled flag; treat the
     Stage-1 token as an in-challenge checkpoint. Revisit in Phase 6/7.
     Phase 5 must define the "transformed Stage 1 real output" used in the
     final flag assembly; it must NOT be the token itself (section 9).

D19. VM ARCHITECTURE: stack-based register machine, 86 LOGICAL opcodes
     (spec band 60-90; 82 with distinct semantics + 4 irregular-encoding
     padding opcodes NOPA/NOPB/ENC/ENCS), 12 general 64-bit registers
     (R0..R11), 256-entry value stack, 64-word data memory, a 1024-byte
     PRIVATE WRITABLE code buffer (the embedded image is copied into it, so
     CSTORE/CXOR/CADD genuinely modify the running program), condition flags
     z/s/c, a scratch "port", a step counter (counts every executed
     instruction INCLUDING the final HALT) and a fault flag (invalid opcode
     byte -> fault). Register roles in the embedded program: R0 loop
     counter, R1 modulus, R2 base, R3 exponent, R4 stride, R5 bit index,
     R6 result (the modexp accumulator), R7 the "ledger" (accumulator;
     ACC/ACCC/ACRM/ACCS fold into it), R8/R9/R10/R11 scratch (R10 doubles as
     the detection-gate seed). Flag rules: ADD/ADDI/SUB/SUBI set z,s,c;
     MUL/MULI/UMULH/DIV/MOD/AND*/OR*/XOR*/SHL*/SHR*/SAR set z,s and clear c;
     NOT/NEG/INC/DEC set z,s only; CMP/CMPI set z,s,c (c = unsigned a<b);
     TEST sets z, clears s,c; SEL reads z; MULMOD/ADDMM/SUBMM/POWM set z,s;
     rotates (ROTL/ROTLI/ROTR) touch NO flags; MOV*/CLOAD/MOVL/POKE/PEEK
     touch no flags.

D20. PER-BUILD RANDOMISATION (spec: "opcode-to-number mapping randomized per
     build"): seed 0xCA4705E1 (vm_spec.py DEFAULT_SEED; recorded here ONLY).
     build_tables(seed) does: (1) for each logical opcode draw an operand
     form — 8 flexible ops (MOVI32, ADDI, SUBI, MULI, ANDI, ORI, XORI,
     CMPI) may take "ri32" OR the irregular "i32r" (immediate BEFORE the
     register) — and an operand endianness bit for every 16/32-bit operand
     form (0=LE, 1=BE); (2) draw 86 DISTINCT opcode bytes from the FULL
     0..255 space (Fisher-Yates shuffle of range(256)), so invalid bytes are
     scattered uniformly and instruction boundaries are NOT guessable from a
     "byte >= opcode count" heuristic. The generated header carries only the
     FORWARD map kOpByte[logical]; the inverse (byte -> logical) decode
     table is built at runtime into .bss (g_dec[256]), so the file image
     never contains a ready-made decoder table.

D21. ENCODING IRREGULARITY (spec): variable length 1..10 bytes; operand
     widths per form (none/i8/i16/i32/i64/r/rr/r3/ri8/ri32/i32r/ri64/rel8/
     rel16/rrel16/a8); "rr" packs two 4-bit register numbers into one byte;
     rel8/rel16 are relative to the END of the instruction; absolute label
     operands (u32/u64) are code-buffer offsets. The irregular gem is CREAD:
     its declared form is "r" (one register byte) and its semantics read the
     byte AFTER the instruction as DATA and consume it, so a CREAD
     instruction is effectively 3 bytes (opcode, register, data) and a
     straight-line decoder that treats the data byte as an opcode mis-steps.
     SKIPC skips operand bytes; NOPA/NOPB/ENC/ENCS consume odd-width operand
     bytes while doing nothing.

D22. THE EMBEDDED PROGRAM (profile 0 = "coastal", 692 bytes, 4083 executed
     steps; profile 1 = "interior", 759 bytes, 7266 steps). Phases:
      0  detection gate (offset 0x0000): ANDI R10,1; JNZ dbg_path — the host
         seeds R10 with 0 (clean) or 1 (detected); the detected path folds
         DETECT_SEED/DETECT_SEED2 into the ledger and rejoins the identical
         trace, so a detected run produces a well-formed but WRONG key.
      A  AI-AGENT BAIT (0x0034-0x0051): MOVI32 R6,12 / DEC R6 / JNZ / CMPI
         R6,0 / JZ — the classic public-VM loop-decrement-compare-jump
         idiom, inert (R6 only). A dead MOVI32/JMP pair follows. Because
         opcode bytes are per-build, a model pattern-matching a known VM's
         byte values mis-decodes; and this idiom does nothing here.
      B  ledger seeding from RAW CODE BYTES: MOVI64 R8,&mut_echo; CLOAD; ACC;
         MOVI64 R8,&bait_a; ACCC (folds the bait loop's own opcode byte).
         The key therefore depends on the actual code image.
      C  CREAD sweep (8x CREAD/ACC): 8 data bytes consumed as data, never
         decoded (the second AI trap: a straight-line decoder hits them as
         "instructions").
      D  INDIRECT DISPATCH: JMPR R9 via a register value (bait JMPR R8 into
         a dead landing block 0x00b4-0x00c1 that would loop harmlessly and
         then rejoin), reached through an opaque CMPI/JZ on R10==0.
      E  INDIRECT CALL: MOVI64 R8,&survey_sub; CALLR R8; ... ; RET (the
         subroutine folds sub_data bytes and ACC_A through the stack).
      F  SELF-MODIFICATION of executed-image bytes: mut_echo is CSTOREd to
         0x5A, CXORed with 0xA5 (->0xFF), CADDed +1 (->0x00), CXORed with
         0x37 (->0x37), then CLOADed and folded into the ledger; the operand
         byte of a LATER EXECUTED NOPA (nop_slot) is CXORed 0x00->0x11
         before it executes and is folded via ACCS. The key depends on bytes
         the program rewrote.
      G  derivation of modulus/base/exponent/stride/index FROM THE LEDGER:
         m = (R7 | 0x4000000000000001) & 0x7FFFFFFFFFFFFFFF   (>=2^62, odd)
         B = (((rotl(R7,29) ^ 0x9E3779B97F4A7C15) | 0x2000000000000001)
              & 0x7FFFFFFFFFFFFFFF) % m                        (guard <3 -> 3)
         E = ((rotl(R7,47) ^ 0xD6E8FEB86659FD93) & 0x3FFFFFFFFFFFFFFF) | 1
         S = ((R7 >> 8) % 30) * 2 + 1;  if S == 31: S = 33  (odd, coprime 62)
         I = (R7 >> 16) % 62                                (start bit index)
      H  THE ITERATED MODEXP WITH THE IRREGULAR TWIST (62 rounds): res=1;
         per round res = res*res % m; the exponent BIT CONSUMED is not bit k
         but bit I, where I walks (I + S) % 62 with S derived from the
         ledger — i.e. the bit ORDER is a state-derived stride permutation;
         when the bit is set: res = res*B % m, then t = (round_counter *
         0x2545F4914F6CDD1D) mod 2^64, res = (res ^ t) % m. An unused POWM
         opcode exists (square-and-multiply) but the program never calls it
         — bait for "just use the built-in modexp" shortcuts.
      I  final mix (8 rounds): res = (res * (rotl(R7, counter) | 1)) % m.
      J  inert survey noise (384 iterations; dummy registers R10/R11 only;
         POKE/PEEK/OPAQUE; LOOP dec-counter-jump — a second idiom-shaped
         loop). Feeds NO key register, so both variants stay identical.
      K  self-modifying sweep over pad0 (12 passes): CXOR code[pad0+k] ^=
         (k + 0x9D), CLOAD the mutated byte, fold into the LEDGER (so this
         mutation DOES move the key); identical pass count in both profiles
         (see D25).
      L  profile 1 ONLY ("interior"): a 1536-step hardening loop (ROTLI/MUL/
         POKE/PEEK/XOR/2xOPAQUE/LOOP) plus a 12-pass self-modifying sweep
         over pad1 folded into a DUMMY register. All profile-1-only work
         touches registers/bytes excluded from the key packing, which is why
         the escalated variant yields the IDENTICAL key (verified).
      M  second mutation of the executed NOPA operand (0x11 ^ 0x63 = 0x72),
         executed, then read back and folded into the ledger.
      N  epilogue: MOVI8 0 into R0,R8,R9,R10,R11 (so the final ledger is
         IDENTICAL for both profiles), HALT; then the never-executed data
         regions mut_echo(16), pad0(16), pad1(16), sub_data(8).

D23. KEY PACKING (the "Stage 2 key material"): key = LE64(R6) || LE64(R7) ||
     LE64(R1) || LE64(R2) (32 bytes) — the engine's final ledger, no hashing
     step. Why: (a) the result genuinely depends on accumulated state (every
     modexp input is derived from the ledger, which is folded from
     self-modified code bytes); (b) a solver can VERIFY an emulation against
     the printed ledger and step count (fairness aid); (c) no hidden domain
     strings, so nothing depends on secret constants. Clean-run values:
     R1=6e595f2b1b6fd6a5, R2=0f012442cf11814c, R6=2ec3dfdf49803efd,
     R7=c0b8223882fe22fe (R3 exponent 3dbaa994c9cc7025, R4 stride 0x25=37,
     R5 start index 0x2d=45).

D24. ANTI-DEBUG (spec: ptrace TRACEME self-attach + timing single-step
     detection, silent):
      - detect_via_ptrace(): ptrace(PTRACE_TRACEME,0,0,0) < 0 => already
        traced (gdb/strace class tracers) => detected. Verified harmless on
        normal runs (rc=0, output and exit code unaffected).
      - timing: a fixed calibration loop (2,000,000 LCG iterations, volatile
        sink so -O2 cannot delete it) measures machine speed; the VM trace
        is measured separately; verdict = carto_timing_verdict(base, vm)
        from vm_debug.h: detected iff vm/base > CARTO_VM_DEBUG_RATIO_LIMIT
        (20.0). A single-stepped trace is ~100x; a slow machine or valgrind
        slows BOTH loops together and keeps the ratio ~1 (no false accuse).
      - On detection the binary does NOT error: it sets debugger_detected in
        the state file, RE-RUNS the engine with the detection gate R10=1 so
        the perturbation happens INSIDE the program (no output patching to
        spot), and prints the resulting corrupted constant — same length,
        same format, wrong value. The printed step count differs (4081 vs
        4083 clean; 7264 vs 7266 escalated), which is a fair, cheap route to
        DISCOVERING the anti-debug (deliberate: traps must be falsifiable).
      - FAIRNESS DECISION: a persisted debugger_detected flag from an
        earlier run only ESCALATES the variant (harder trace); it does NOT
        corrupt later clean runs, so a one-time debugger visit can never
        permanently poison the real answer. A tampered/reset state file
        clears the flag silently (self-defeating tampering).

D25. ESCALATION VARIANTS (both PRE-BUILT, per spec "nothing generated live"):
     profile 0 "coastal" (standard trace) and profile 1 "interior" (harder:
     +3183 executed steps, extra self-modification). Selection mask =
     CARTO_ESC_TIME_FAST | CARTO_ESC_TIMING_UNIFORM | CARTO_ESC_DEBUGGER
     (persisted flag) — any escalation reason picks the harder variant.
     Both variants compute the IDENTICAL key: the extra work touches only
     R0/R8..R11 and pad1, all excluded from the packing (R6/R7/R1/R2), and
     phases J/K use the SAME iteration counts in both profiles so the
     ledger folds stay byte-identical. The output line "engine variant:"
     names the served variant ("coastal"/"interior") — honest, and useful
     for verifying variant invariance. Phase-0 threshold placeholders were
     NOT touched (calibration is Phase 6); note the consequence: on a FRESH
     state (first_run just now) CARTO_ESC_TIME_FAST fires, so a solver's
     first Stage-1 run within 90s of Stage 0 serves "interior". Harmless
     (same key), and the threshold is a Phase-6 calibration item.

D26. DECOY ROUTING: carto_lookup_decoy(CARTO_STAGE1, token) >= 1 routes the
     caller into the extended branch. Branch ids are 1-based; the state bit
     persisted is (1u << (branch - 1)) — convention recorded for Phases 3-4.
     Extended-branch behaviour: exit 0, stderr silent, extended flavor
     ("corroborated reading"), and it RE-INKS THE DECOY CHECKPOINT (the
     .rodata decoy key + the decoy token) as if it were the answer — framed
     as new information, never an error, and it never prints the real key.
     An unregistered token gets a neutral "(the ledger does not recognise
     that ink)" line and the normal run; the engine's own token gets
     "(the ledger recognises that ink)". policy.h now registers the real
     Stage-1 decoy (D29) so the decoy token is discoverable via `strings`
     in every stage binary — accepted (spec: let a smart agent find decoys
     fast; confirmation is what stays expensive).

D27. THE THREE CANDIDATES (trap design; verification-expensive, not
     detection-expensive, per Token-Cost Design):
       1. REAL  fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f
                (+ token CARTO{fd3e8049dfdfc32efe22fe823822b8c0})
       2. DECOY 12f8a367b772817e805725e7292acfb694501c4f16c17ed09d614022e0be7ced
                — the ".rodata forgotten debug constant"
                (kStage1ForgottenRecord.key + the lure string
                "stage2_key_checkpoint (pre-rekey) -- kept for the 0.4
                survey; do not ship"), minting the registered decoy token
                CARTO{12f8a367b772817e805725e7292acfb6}. A solver who takes
                it proceeds to Stage 2 with a valid-looking key; the wrong
                stride pulls garbage that does NOT parse, and only the
                downstream round trip reveals the mistake (spec Phase 2
                trap #1, main 1-1.5 hr budget).
       3. DEBUG fb48aecdda0e960831b16d45c7efbe485d69b61bda262b5c72af18d9b88d1621
                — what a debugger run produces (the engine's own detected
                branch, steps 4081/7264). NOT stored anywhere in the
                binary; it only exists after a detected run.
     All three are 32 bytes and all three look like digests; only mechanical
     verification (running cleanly, or emulating and checking the ledger and
     step count, or the Stage 2 round trip) tells them apart.
     Narrative misdirection (spec trap #2): the flavor text's margin note —
     "The true figure lies not on the coast but at the third survey mark,
     westward; count them and the ledger will open." — reads as a mechanical
     clue (third mark / westward / count) but is pure flavor: no input to
     the engine, and cheaply falsifiable (the engine's derivation depends
     only on its own ledger; the note changes nothing).
     AI-agent bait (spec trap #3): the DEC/JNZ + CMPI/JZ idiom at
     0x0034-0x0051, the dead landing block at 0x00b4-0x00c1, the unused POWM
     opcode, and the CREAD data bytes that read like instructions. Opcode
     numbering is per-build, so a recognised "public VM" shape has no
     transferable byte values.

D28. FAIRNESS/DETERMINISM: the VM has no clock, no RNG and no environment
     input; all three candidate values are reproducible bit-exactly (the C
     binary and the python model agree on all four profile/detect
     combinations); every trap has a legitimate deterministic resolution:
     (a) run the binary cleanly (intended), (b) emulate and cross-check
     steps/ledger, (c) notice the step-count delta or the state flag and
     investigate the anti-debug, (d) reject the decoy at Stage 2. Nothing
     requires guessing outside the puzzle's own logic. Constraint
     compliance: fully offline; writes only ./.cartographer_state (plus its
     atomic .tmp during rename) inside the working directory.

D29. STATE-LIBRARY CHANGES (mechanism untouched, per PHASE_0 D10/D14):
     (1) policy.h: the Phase-0 PLACEHOLDER decoy entry (which violates the
     final D11 format with its hyphens) is REPLACED by the real Stage-1
     decoy { stage 1, CARTO{12f8a367b772817e805725e7292acfb6}, branch 1 };
     CARTO_DECOY_TABLE_LEN stays 1 (more decoys arrive in Phases 3-4).
     (2) test_part2.c test_decoy_lookup is now TABLE-DRIVEN (reads
     carto_decoy_table[0]) so future registrations cannot invalidate the
     mechanism test; same test name, same 26-test count.
     (3) src/state/Makefile: -fno-ident folded into CFLAGS (PHASE_1_LOG D17
     recommended this in Phase 2; build flags only). Verified 26/26 after
     the change; the stage-side objcopy --remove-section .comment scrub
     remains as defence in depth.

D30. BUILD PIPELINE (per spec, same recipe as Stage 0):
     musl-gcc -O2 -Wall -Wextra -std=c11 -static -fno-ident
       (vm.c + stage1_vm.c + ../state/libstate.a)
     -> strip --strip-all -> objcopy --remove-section .comment.
     Internal-only builds (never shipped): test_detect (verdict unit tests)
     and stage1_vm.dbg (-O0 -g, unstripped, used by the gdb-based anti-debug
     tests). Deliverable is reproducible: two clean rebuilds produced the
     identical sha256 317d4a84...99f49e1a. Generated artifacts (vm_tables.h,
     vm_program.h, vm_layout.json, decoy_blob.h, listings/) regenerate
     byte-identically from vm_spec.py / gen_decoys.py (verified by sha256
     before/after regeneration).

## 3. Every constant introduced (exact values + location)

VM SEED (INTERNAL; this log + vm_spec.py DEFAULT_SEED only — never in any
solver-facing file, though naturally recoverable from the committed tables):
- 0xCA4705E1  (python random.Random seed for forms, endianness, opcode bytes)

VM shape: VM_OP_COUNT 86, VM_CODE_SIZE 1024, VM_NREG 12, VM_STACK_SIZE 256,
VM_DATA_SIZE 64 (vm_tables.h / vm_spec.py).

Program constants (vm_spec.py; compiled into the embedded bytecode, mirrored
as C #defines in vm.c):
- ACC_A    0x9E3779B97F4A7C15   (ACC fold additive)
- ACC_B    0xC2B2AE3D27D4EB4F   (ACCC fold additive)
- ACC_C    0xBF58476D1CE4E5B9   (ACRM fold multiplier)
- ACC_D    0x94D049BB133111EB   (ACCS fold multiplier)
- MIX_A    0xD6E8FEB86659FD93   (exponent fold xorshift)
- TWIST_K  0x2545F4914F6CDD1D   (per-round xor perturbation step)
- NOISE_A  0x243F6A8885A308D3   (inert noise seed)
- NOISE_B  0x13198A2E03707344   (inert noise seed)
- DETECT_SEED  0xDEADBEEFCAFEF00D  (ledger perturbation on detection)
- DETECT_SEED2 0x5EEDDEADBEEF1234  (second perturbation on detection)
- MASK63 0x7FFFFFFFFFFFFFFF, MASK62 0x3FFFFFFFFFFFFFFF,
  FORCE_HI 0x4000000000000001, BASE_HI 0x2000000000000001
- ROUNDS 62, MIX_ROUNDS 8, NOISE_ITERS 0x0180 (384), MUT_PASSES 0x000C (12),
  HN_ITERS 0x0180 (1536; profile-1-only loop)
- DATA_BLK 69 3f d1 07 bb 52 2c e4 (CREAD-swept data bytes)
- mut_echo/pad0/pad1 initial patterns: 00..0f / 5A^(3k) / C3-5k

Clean-run ledger (profile 0): R1=6e595f2b1b6fd6a5 R2=0f012442cf11814c
R6=2ec3dfdf49803efd R7=c0b8223882fe22fe (R3=3dbaa994c9cc7025, R4=0x25=37,
R5=0x2d=45). Executed steps: 4083 coastal / 7266 interior / 4081
coastal+detected / 7264 interior+detected.

THE THREE CANDIDATE CONSTANTS (see D27):
- Stage 2 key material, REAL (exists only after a clean trace):
  fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f
- Stage 1 token, REAL (minted at runtime; D11-conforming):
  CARTO{fd3e8049dfdfc32efe22fe823822b8c0}
- decoy key (kStage1ForgottenKey, .rodata of stage1_vm):
  12f8a367b772817e805725e7292acfb694501c4f16c17ed09d614022e0be7ced
- decoy token (registered in src/state/policy.h, stage 1, branch 1 -> bit 0):
  CARTO{12f8a367b772817e805725e7292acfb6}
- decoy derivation seed (INTERNAL: gen_decoys.py + this log only; the seed
  string is NEVER compiled into any binary):
  "cartographer-ghost:stage1:decoy:forgotten-debug-key:v1"
- decoy lure string (in .rodata, deliberately findable):
  "stage2_key_checkpoint (pre-rekey) -- kept for the 0.4 survey; do not ship"
- debugger-path key (exists only after a detected run; NOT in the binary):
  fb48aecdda0e960831b16d45c7efbe485d69b61bda262b5c72af18d9b88d1621
  (debugger-path token, also minted at runtime and equally wrong:
  CARTO{fb48aecdda0e960831b16d45c7efbe48})

Detection constants:
- CARTO_VM_DEBUG_RATIO_LIMIT 20.0 (vm_debug.h; Phase 6 may calibrate)
- calibration loop: 2,000,000 LCG iterations (stage1_vm.c)
- PTRACE_TRACEME self-attach check (stage1_vm.c detect_via_ptrace)
- detection gate: R10 = 0/1 seeded by the host into the VM

Deliverable: cartographer/stage1_vm/stage1_vm, 62,728 bytes, sha256
317d4a846af9168ed34b1283ae05bccdebb659ade342343d63a16fcc99f49e1a.

No changes to: policy thresholds (CARTO_T_FAST_SEC_DEFAULT 90s,
CARTO_STDDEV_LOW_MS 1500ms, CARTO_MIN_TIMING_DELTAS 4 — Phase-0 placeholders,
Phase 6 calibrates), the state file format, the state library API, the
canonical HMAC key/masks, or the Stage-0 flag.

## 4. Exact commands (runnable verbatim)

C13. Sync the staged Phase 2 sources into the repo (CRLF->LF normalised):
wsl.exe bash -lc 'tr -d "\r" < /mnt/d/gandu/_stage/s1_sync.sh | bash'

C14. One-shot state-library edits (idempotent; both already applied):
wsl.exe bash -lc 'tr -d "\r" < /mnt/d/gandu/_stage/s1_policy_update.py > /tmp/s1_policy_update.py && python3 /tmp/s1_policy_update.py'
wsl.exe bash -lc 'tr -d "\r" < /mnt/d/gandu/_stage/s1_state_makefile_update.py > /tmp/s1_mk.py && python3 /tmp/s1_mk.py'

C15. State-library regression (26 checks; MUST precede the stage builds —
     they link ../state/libstate.a):
wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/state && make clean && make test && file test_state'

C16. Stage-0 regression (36 checks):
wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/stage0 && make && ./test_stage0.sh'

C17. THE Phase 2 build + verification (regenerates all generated headers,
     runs the 8 verdict unit checks, then the 65 end-to-end checks; needs
     gdb for the anti-debug section):
wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/stage1_vm && make test'

C18. Independent python model:
wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/stage1_vm && python3 model_vm.py --selftest'
wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/stage1_vm && python3 model_vm.py --profile 0 --detect 0 --emit'

C19. Regeneration determinism (expect an empty diff):
wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/stage1_vm && sha256sum vm_tables.h vm_program.h vm_layout.json > /tmp/gen1.txt && python3 vm_spec.py >/dev/null && sha256sum vm_tables.h vm_program.h vm_layout.json > /tmp/gen2.txt && diff /tmp/gen1.txt /tmp/gen2.txt && echo REGEN-DETERMINISTIC-OK'

C20. Manual smoke run (as a solver would, from the package root):
wsl.exe bash -lc 'cd /home/manish/cartographer-build/cartographer && rm -f .cartographer_state && ./stage1_vm/stage1_vm'
     (the variant line will read "interior" on a fresh state — see D25;
     forge a human-paced state with src/stage1_vm/forge_state.py to see
     "coastal")

C21. gdb anti-debug checks (invoked by test_stage1.sh sections 6 and 7):
   ptrace path:   gdb -batch -q -ex run --args ./stage1_vm/stage1_vm  (in PKG)
   timing path (ptrace bypassed, trace single-stepped):
   gdb -batch -q -ex "set confirm off" \
       -ex "break detect_via_ptrace" -ex run -ex "return 0" \
       -ex "break vm_run" -ex continue -ex "stepi 4000" -ex "delete 2" \
       -ex continue --args ../src/stage1_vm/stage1_vm.dbg

C22. Reproducibility + scrub spot-checks:
wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/stage1_vm && rm -f ../../cartographer/stage1_vm/stage1_vm && make >/dev/null && sha256sum ../../cartographer/stage1_vm/stage1_vm'
wsl.exe bash -lc 'strings -n 4 /home/manish/cartographer-build/cartographer/stage1_vm/stage1_vm | grep -Eic "(GCC|clang|musl|/home/manish|cartographer-build)"'
   (expect 0)

WARNING (learned this session): C15, C16 and C17 MUST run serially. The
stage0 and stage1 suites share the same package-root .cartographer_state;
run concurrently they interfere (deletes/tamper mid-run) and produce
spurious failures that vanish when re-run alone.

## 5. Verification run — full real output

(a) C15, state-library regression (after the -fno-ident change):

```
rm -f *.o libstate.a test_state
musl-gcc -O2 -Wall -Wextra -std=c11 -static -fno-ident -c carto_sha256.c -o carto_sha256.o
musl-gcc -O2 -Wall -Wextra -std=c11 -static -fno-ident -c state_core.c -o state_core.o
musl-gcc -O2 -Wall -Wextra -std=c11 -static -fno-ident -c state_policy.c -o state_policy.o
ar rcs libstate.a carto_sha256.o state_core.o state_policy.o
musl-gcc -O2 -Wall -Wextra -std=c11 -static test_part1.c test_part2.c libstate.a -o test_state -lm
python3 gen_vectors.py
68 vectors written; canonical probe: b32ef0b76dc05f0d1d0916cc361c427cf4dee9ec48529d17e9399f9f8f700910
./test_state
== cartographer state library unit tests ==
[PASS] test_sha_selftest       [PASS] test_hmac_selftest
[PASS] test_key_selftest       [PASS] test_key_canonical
[PASS] test_fresh_create       [PASS] test_roundtrip
[PASS] test_tamper_silent_reset
[PASS] test_truncated          [PASS] test_extended
[PASS] test_bad_magic          [PASS] test_garbage
[PASS] test_hmac_ring_flip     [PASS] test_save_deterministic
[PASS] test_no_tmp_residue     [PASS] test_ring_wrap
[PASS] test_stddev_reference   [PASS] test_stddev_insufficient
[PASS] test_escalate_fast      [PASS] test_escalate_uniform
[PASS] test_escalate_human     [PASS] test_escalate_debugger
[PASS] test_decoy_lookup       [PASS] test_decoy_persist
[PASS] test_attempts_persist   [PASS] test_debugger_persist
[PASS] test_hmac_differential
== 26 tests run, 0 failed ==
ALL TESTS PASSED
test_state: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), statically linked
```
(The Phase-0 harness binary keeps its "with debug_info, not stripped" suffix;
the stage binaries are the stripped deliverables.)

(b) C16, stage0 regression (tail):
```
[PASS] canonical HMAC key hex absent from binary
[PASS] flag plaintext absent (masked blob only)
[PASS] no debug paths / compiler strings in binary
[PASS] stage-0 flag matches canonical format (CARTO{[a-z0-9_]{8,64}})
[PASS] package left pristine (test state removed)

== 36 tests run, 0 failed ==
ALL TESTS PASSED
```

(c) C17, the Phase 2 verification (build lines + both suites):

```
mkdir -p ../../cartographer/stage1_vm
musl-gcc -O2 -Wall -Wextra -std=c11 -static -fno-ident -I../state stage1_vm.c vm.c ../state/libstate.a -o ../../cartographer/stage1_vm/stage1_vm
strip --strip-all ../../cartographer/stage1_vm/stage1_vm
objcopy --remove-section .comment ../../cartographer/stage1_vm/stage1_vm 2>/dev/null || true
musl-gcc -O0 -g -Wall -Wextra -std=c11 -static -fno-ident -I../state stage1_vm.c vm.c ../state/libstate.a -o stage1_vm.dbg
./test_detect
== vm_debug timing-verdict unit tests ==
== 8 checks, 0 failed ==
ALL CHECKS PASSED
./test_stage1.sh
== stage1_vm end-to-end verification ==
[PASS] binary exists and is executable
[PASS] binary statically linked (musl)
[PASS] binary stripped (no symtab)
[PASS] no debug paths / compiler strings in binary
[PASS] model: no VM fault in any of the four runs
[PASS] model: both variants yield the same key
[PASS] model key matches the key recorded in the build tables
[PASS] model: detected path yields a different (corrupted) key
[PASS] model detected key matches the recorded debug constant
[PASS] clean run exits 0
[PASS] clean run: stderr silent
[PASS] clean run serves the standard variant (coastal)
[PASS] engine steps == python model (4083)
[PASS] clean run prints the real Stage 2 key material
[PASS] token is minted from the first half of the key
[PASS] token matches the canonical flag format (D11)
[PASS] engine ledger matches the python model (r1/r2/r6/r7)
[PASS] state file is exactly 352 bytes
[PASS] state HMAC valid (independent python check)
[PASS] attempt_count[1] == 1 after first run
[PASS] interaction ring extended (8 forged + 1 recorded)
[PASS] debugger_detected stays 0 on a clean run
[PASS] second run reproduces key and steps exactly
[PASS] attempt_count[1] == 2 after second run
[PASS] first_run_ms is preserved
[PASS] no .tmp residue after runs
[PASS] uniform interaction timing selects the escalated variant
[PASS] escalated variant steps == model (7266)
[PASS] escalated variant yields the identical key
[PASS] fast arrival selects the escalated variant
[PASS] fast-arrival variant matches the uniform-timing variant exactly
[PASS] persisted debugger flag escalates the variant
[PASS] persisted debugger flag alone does NOT corrupt the key
[PASS] decoy submission exits 0 (no error path)
[PASS] decoy submission: stderr silent
[PASS] decoy route re-inks the decoy checkpoint key
[PASS] decoy token equals the registered policy.h entry
[PASS] decoy route is framed as new information, not failure
[PASS] decoy route does not leak the real key
[PASS] decoy bit 0 persisted in the state file
[PASS] state HMAC valid after decoy routing
[PASS] unknown token still runs the engine normally
[PASS] unknown token gets a neutral reply
[PASS] unknown token sets no decoy bit
[PASS] the engine recognises its own token
[PASS] token self-check does not disturb the key
[PASS] debugger run exits 0 (detection stays silent)
[PASS] debugger run serves the corrupted constant (same shape, wrong value)
[PASS] debugger key differs from the real key
[PASS] debugger run executes the detection branch (4081 steps)
[PASS] debugger run still mints a well-formed token
[PASS] debugger_detected flag persisted to the state file
[PASS] state HMAC valid after the debugger run
[PASS] timing-path run exits 0
[PASS] single-stepped trace serves the corrupted constant
[PASS] timing detection persisted the debugger flag
[PASS] decoy constant present in the shipped binary (.rodata)
[PASS] decoy lure string present (forgotten-debug framing)
[PASS] registered decoy token is findable in the binary
[PASS] real key material absent from the binary
[PASS] real token absent from the binary
[PASS] canonical HMAC key hex absent from binary
[PASS] debug-path key is not stored in the binary
[PASS] no writes outside the working directory
[PASS] package left pristine (test state removed)

== 65 tests run, 0 failed ==
ALL TESTS PASSED
```

(d) `file` + hashes + scrub + regeneration + model:

```
../../cartographer/stage1_vm/stage1_vm: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), statically linked, stripped
317d4a846af9168ed34b1283ae05bccdebb659ade342343d63a16fcc99f49e1a  ../../cartographer/stage1_vm/stage1_vm
f2d1e064554ed7bafa8beb8deaf9bf4887bd9d857b9c745b68678e6ee1d2486f  ../../cartographer/stage0_start/stage0_start
scrub grep count: 0
REGEN-DETERMINISTIC-OK
profile0: steps=4083 key=fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f
profile1: steps=7266 key=fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f
detect=1: steps=4081 key=fb48aecdda0e960831b16d45c7efbe485d69b61bda262b5c72af18d9b88d1621
SELFTEST OK
```

The stripped C deliverable and the independent python model agree
bit-exactly on ledger, step count and key for every profile/detect
combination — the cross-implementation check this phase was built around.
stage0_start's hash changed from bb06ad49... to f2d1e064... purely because
it was relinked against the -fno-ident library (same size, 66,840 bytes;
36/36 after the relink).

## 6. Solver-visible output (verbatim, four variants)

Fresh state, no arguments (CARTO_ESC_TIME_FAST fires -> "interior"):
```
======================================================================
  THE CARTOGRAPHER'S GHOST
  Stage 1 -- The Survey Engine
======================================================================

Past the ledger's first page there is no map at all -- only an
engine: a survey instrument the old man built to keep drawing
after his hand stopped. Its rules are not written down anywhere;
it re-inks them itself as it turns, so no reading of it can be
taken from a standing start.

A second hand, in the margin -- smaller, and not the keeper's:
  "The true figure lies not on the coast but at the third survey
   mark, westward; count them and the ledger will open."

  engine variant : interior
  engine steps   : 7266
  engine ledger  : r1=6e595f2b1b6fd6a5 r2=0f012442cf11814c r6=2ec3dfdf49803efd r7=c0b8223882fe22fe

The engine finishes its circuit and sets down the key material for
the interior survey:

    fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f

Stage 1 token -- bank it, it is yours:

    CARTO{fd3e8049dfdfc32efe22fe823822b8c0}

Carry it forward. The interior is not surveyed by daylight.
======================================================================
```
(rc=0, stderr silent; the "coastal" variant differs only in variant name and
step count 4083 — identical ledger, key and token.)

Decoy token submitted (`./stage1_vm/stage1_vm 'CARTO{12f8a367b772817e805725e7292acfb6}'`):
```
The margin note matches the ink you carried in. The survey
engine accepts it as a corroborated reading and re-inks the
checkpoint the old man left behind for the 0.4 survey:

  engine variant : interior
  corroborated key material:
    12f8a367b772817e805725e7292acfb694501c4f16c17ed09d614022e0be7ced

  confirmed token:
    CARTO{12f8a367b772817e805725e7292acfb6}

Take it into the interior. Nothing here needs re-drawing.
======================================================================
```
(rc=0, stderr silent, decoy bit 0 persisted, real key never printed.)

Debugger attached (gdb -batch -ex run): identical layout, but
```
  engine variant : interior
  engine steps   : 7264
  engine ledger  : r1=5c2b26da1bb6695d r2=21168db8d918af72 r6=08960edacdae48fb r7=48beefc7456db131

    fb48aecdda0e960831b16d45c7efbe485d69b61bda262b5c72af18d9b88d1621

Stage 1 token -- bank it, it is yours:

    CARTO{fb48aecdda0e960831b16d45c7efbe48}
```
(same shape, wrong value; no error, no hint; debugger_detected=1 persisted.)

## 7. Bugs found and fixed DURING Phase 2

1. vm_spec.py assembly: two editor inserts landed by line number inside the
   Asm class and scrambled the emit() body, fused _program_tail/_hex_rows and
   duplicated three lines at EOF. Symptom: Python IndentationError. Fix:
   re-spliced the three bodies by anchor-based edits. WORKFLOW LESSON: the
   editor's insert_line is only safe at EOF; prefer anchor-based old_text
   edits (used for everything afterwards).
2. Assembler operand order for the irregular form: _encode() expected
   (imm, reg) for "i32r" while every call site passes (reg, imm) with the
   form chosen per build, so every flexible op with the i32r layout decoded
   the wrong register (the model crashed with IndexError on R[rd] = imm).
   Fix: normalise in _encode (source order is always (reg, imm); the
   encoder emits imm-then-reg for i32r).
3. Python model CREAD: read self.code[ip] (the CREAD's own opcode byte)
   instead of the byte after the instruction. Fix: read code[end] and set
   ip = end + 1; semantics documented as "read the bytes that follow as
   data and consume the byte read".
4. Variant invariance violated: NOISE_ITERS and MUT_PASSES were per-profile
   AND the pad0 sweep folds into the ledger, so profile 0 and profile 1
   produced DIFFERENT keys. Fix: both loops now use identical counts in both
   profiles (single constants) and all profile-1-only work (HN_ITERS loop +
   pad1 sweep) is confined to R0/R8..R11 and pad1, which are excluded from
   the packing.
5. decoy_blob.h generator emitted a malformed brace-initialiser macro (the
   closing brace on its own line, unescaped) -> C syntax error in
   stage1_vm.c. Fix: the last data row closes the brace on the same line.
6. Test-harness bugs found while getting to 65/65:
   a) model values parsed with 's/^R1=//' but the model prints "R1=0x..."
      -> ledger comparison always failed. Fix: strip the 0x.
   b) forge_state() anchored the ring timestamps at first_run; the stage
      records its own interaction BEFORE evaluating the timing reasons, so
      the freshly appended delta (~570 s) destroyed the forged uniformity
      and the escalated variant was never selected. Fix: ring timestamps are
      anchored to now (last entry ~now).
   c) the timing-path gdb script kept breakpoint 2 active, so the
      detection-triggered SECOND vm_run stopped and -batch quit before the
      output was printed (that hit with detect_flag=1 was itself proof the
      timing verdict had fired). Fix: stepi 4000, `delete 2`, continue.
7. Concurrency hazard (not a product bug): test_stage0.sh and
   test_stage1.sh both operate on cartographer/.cartographer_state; run in
   parallel they delete/tamper each other's state and report spurious
   failures. Serial execution is required (documented with C15-C17).
8. Build-order hazard: `make test` in src/stage1_vm requires
   ../state/libstate.a; after `make clean` in src/state the stage build
   fails with "No rule to make target '../state/libstate.a'". Documented in
   C15 (build the library first); deliberately not auto-built, to keep the
   Phase-0 library an explicit, separate artifact.

## 8. Explicitly NOT done / deferred

- Phase 3 (Stage 2 stego: decoy LSB layer, stride from Stage 1's real
  output, custom zlib dictionary, WAV metadata, manual-step trap), Phase 4
  (Feistel oracle), Phase 5 (assembly riddle + validator), Phase 6
  (calibration + self-testing + SOLVE_PATH_PRIVATE.md), Phase 7 (packaging,
  README_FOR_SOLVER.txt, HINTS.md, TRYHACKME_ROOM_TEXT.md).
- The "interior + detected" combination is verified only via the python
  model (steps 7264, key fb48aecd...1621) and an ad-hoc gdb run, not
  asserted by the suite (the suite asserts coastal+detected).
- Solver-facing documentation of the token CLI is deferred to Phase 7 (the
  CLI exists and is tested: no arg / decoy token / own token / unknown).
- No threshold calibration: CARTO_VM_DEBUG_RATIO_LIMIT (20.0) and all
  Phase-0 policy constants remain uncalibrated per D10.
- The decoy's downstream effect ("fails at Stage 3 in a non-obvious way")
  cannot be demonstrated until Stage 2 exists (Phase 3); the Phase 2
  evidence is that the decoy value is wrong, plausible and reachable only by
  static reading (no clean trace ever produces it).
- Assumed-but-unverified: NOTHING in Phase 2 scope -- every claim above was
  produced by a command and its real output is pasted in section 5.

## 9. Open questions / judgment calls for the next session

1. SCORING (D18 trade-off): decide in Phase 7 whether the Stage-1 token (and
   Stage-0's flag) become TryHackMe answers. Recommendation: score only the
   Stage-0 flag and the final assembled flag, so a decoy/wrong token cannot
   be rejected instantly by the room and the 1-1.5 hr decoy budget holds.
2. PHASE 5 ASSEMBLY INPUT: define the "transformed Stage 1 real output"
   (proposal: bytes 16..23 of the real key as 16 lowercase hex chars, or a
   key rotation that is NOT the token content). Must be decided in Phase 5
   and validated there; do not reuse the token substring.
3. PHASE 6 CALIBRATION: (a) CARTO_VM_DEBUG_RATIO_LIMIT 20.0 -- measure a
   real single-step slowdown on the target machine and confirm the margin;
   (b) whether to mask the printed step-count delta (4083 vs 4081) --
   recommendation: KEEP it, it is a fair, cheap anti-debug discovery route;
   (c) confirm the fresh-state "interior" escalation is acceptable pacing
   (Phase-0 CARTO_T_FAST_SEC_DEFAULT 90 s does the selecting).
4. DECOY VISIBILITY: the registered decoy token appears in `strings` of
   every stage binary (policy.h is linked in). Accepted deliberately
   (findable decoys, expensive confirmation). Phase 3-4 should keep new
   decoys D11-conforming and register them the same way.
5. PTrace AVAILABILITY (important fairness risk): the deliverable has only
   been exercised on Ubuntu-24.04 WSL2 (kernel 6.6.87.2) where
   PTRACE_TRACEME succeeds. Under a seccomp/policy that BLOCKS ptrace the
   call could fail with EPERM/ENOSYS on a perfectly clean run, which the
   current code would read as "debugger detected" and corrupt the constant.
   Recommend, in Phase 6, either (a) requiring BOTH a ptrace failure AND a
   timing-ratio breach, or (b) checking errno and only treating EPERM as a
   tracer, before the challenge is shipped.

## 10. Git commit for Phase 2

Single commit on `main`, subject:

    phase2: stage1_vm custom VM (86 opcodes, seeded per-build mapping,
    self-modifying bytecode) + 65-test suite; real/decoy/debug candidate
    constants

containing src/stage1_vm/* (generated headers and listings included),
cartographer/stage1_vm/stage1_vm (the deliverable binary), the three
src/state edits (policy.h, test_part2.c, Makefile), the relinked
cartographer/stage0_start/stage0_start, .gitignore additions, and both
protocol logs. The hash is intentionally not hardcoded here (amending this
log would change it); run `git -C /home/manish/cartographer-build log
--oneline` for the authoritative list (the Phase-1 commit is 8c3ec8f, the
Phase-2 commit is its child).

## Appendix A -- generated opcode mapping

Seed 0xCA4705E1. Form ids: none, i8, i16, i32, i64, r, rr, r3, ri8, ri32, i32r, ri64, rel8, rel16, rrel16, a8. Endian column applies only to the
16/32-bit immediate and relative forms (0 = little, 1 = big).
Regenerate with: cd src/stage1_vm && python3 vm_spec.py --listing

idx opcode form     end  mnemonic
--- ------ -------- ---  --------------------
  0  0x34  none     0    NOP
  1  0x82  none     0    HALT
  2  0xe5  i8       0    NOPA
  3  0xea  i16      1    NOPB
  4  0x45  r        0    ENC
  5  0x88  rr       0    ENCS
  6  0xd5  rr       0    MOV
  7  0x4a  ri8      0    MOVI8
  8  0x08  i32r     1    MOVI32
  9  0x20  ri64     0    MOVI64
 10  0x07  rr       0    XCHG
 11  0x49  r3       0    MOVM
 12  0x2f  r3       0    MOVL
 13  0x10  r3       0    MOVB
 14  0xfa  r3       0    STOREB
 15  0xfc  rr       0    CLOAD
 16  0x7d  rr       0    CSTORE
 17  0x1a  rr       0    CXOR
 18  0x61  ri8      0    CADD
 19  0xdc  r        0    CREAD
 20  0x8c  i8       0    SKIPC
 21  0x59  rr       0    ADD
 22  0xdb  i32r     0    ADDI
 23  0x3b  rr       0    SUB
 24  0x52  i32r     0    SUBI
 25  0x94  rr       0    MUL
 26  0x7f  i32r     0    MULI
 27  0x42  rr       0    UMULH
 28  0xb6  rr       0    DIV
 29  0xcb  rr       0    MOD
 30  0x79  rr       0    AND
 31  0x09  i32r     0    ANDI
 32  0xeb  rr       0    OR
 33  0x74  i32r     0    ORI
 34  0x2c  rr       0    XOR
 35  0xbb  i32r     1    XORI
 36  0xa2  rr       0    SHL
 37  0xe1  ri8      0    SHLI
 38  0xe6  rr       0    SHR
 39  0x99  ri8      0    SHRI
 40  0xf4  rr       0    SAR
 41  0x66  rr       0    ROTL
 42  0xce  ri8      0    ROTLI
 43  0x5d  rr       0    ROTR
 44  0xd0  r        0    NOT
 45  0x44  r        0    NEG
 46  0xc8  r        0    INC
 47  0x25  r        0    DEC
 48  0xd6  r3       0    MULMOD
 49  0x01  r3       0    ADDMM
 50  0x1c  r3       0    SUBMM
 51  0xdd  r3       0    POWM
 52  0xbf  rr       0    CMP
 53  0x8b  i32r     1    CMPI
 54  0xa3  rr       0    TEST
 55  0x96  r3       0    SEL
 56  0x2e  r        0    ACC
 57  0xa9  r        0    ACCC
 58  0xa7  r        0    ACRM
 59  0x80  r        0    ACCS
 60  0x4c  rel16    1    JMP
 61  0xb8  rel8     0    JMP8
 62  0xf7  r        0    JMPR
 63  0x0f  rel16    1    JZ
 64  0x54  rel16    1    JNZ
 65  0xc0  rel16    0    JL
 66  0xba  rel16    1    JGE
 67  0x3d  rel16    1    JGT
 68  0xf3  rel16    0    JLE
 69  0xa4  rel16    1    JC
 70  0x53  rel16    1    JNC
 71  0xe3  rel16    1    JOV
 72  0xda  rel16    1    CALL
 73  0x6b  r        0    CALLR
 74  0x83  none     0    RET
 75  0x50  rrel16   1    LOOP
 76  0xec  r        0    PUSH
 77  0x73  r        0    POP
 78  0x23  i32      0    PUSHI
 79  0x13  none     0    DUP
 80  0x9d  none     0    SWAP
 81  0xc3  r        0    PICK
 82  0xb0  none     0    DROP
 83  0x1f  none     0    OPAQUE
 84  0x89  r        0    POKE
 85  0xab  r        0    PEEK

Program sizes: profile 0 = 692 bytes, profile 1 = 759 bytes.
Mnemonic meanings: see D19-D22 and vm.c; per-instruction disassembly of both profiles: src/stage1_vm/listings/.
