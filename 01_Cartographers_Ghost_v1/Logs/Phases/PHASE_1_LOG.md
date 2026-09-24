# PHASE 1 LOG — Stage 0: Orientation + Immediate Real Reward

Status: COMPLETE — all verifications passing (36/36 stage0 end-to-end tests,
26/26 Phase-0 state-library regression tests, static+stripped+scrub checks,
independent python HMAC verification of the state file). Repo:
/home/manish/cartographer-build (git branch `main`). Date of session: 2026-09-18.

## 0. Protocol confirmation (Session Continuity Protocol)

Before writing any code or running any build command, this session:

1. READ the full build spec start to end:
   d:\gandu\01_BUILD_PROMPT_FOR_CLAUDE_CODE.md (all 164 lines, in chunks;
   identical copy exists at /home/manish/cartographer-build/docs/BUILD_SPEC.md).
2. READ /home/manish/cartographer-build/logs/PHASE_0_LOG.md IN FULL (all 295 lines).
3. INDEPENDENTLY re-verified Phase 0 — reproduced, did not trust the log.

Command: wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/state && make clean && make test && file test_state'

Real output (abridged ONLY in the per-test [PASS] lines — all 26 names listed):

```
rm -f *.o libstate.a test_state
musl-gcc -O2 -Wall -Wextra -std=c11 -static -c carto_sha256.c -o carto_sha256.o
musl-gcc -O2 -Wall -Wextra -std=c11 -static -c state_core.c -o state_core.o
musl-gcc -O2 -Wall -Wextra -std=c11 -static -c state_policy.c -o state_policy.o
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
test_state: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), statically linked, with debug_info, not stripped
```

Plus C3 key-not-in-binary check re-run: `strings test_state | grep -q f03ea6b5`
→ NOT-IN-BINARY-OK. Foundation verified; Phase 1 build proceeded.

## 1. What was built (exact paths, all in /home/manish/cartographer-build)

- src/stage0/stage0.c        — stage0_start main (94 lines): state init via shared
                               library, flavor text, flag handout, timestamp print
- src/stage0/gen_flag_blob.py — build-time flag-mask generator (internal, not
                               shipped; 70 lines). Regenerates flag_blob.h.
- src/stage0/flag_blob.h     — GENERATED + committed: masked Stage-0 flag + raw mask
- src/stage0/Makefile        — musl static build + strip + scrub; test target (30 lines)
- src/stage0/test_stage0.sh  — 36-check end-to-end verification suite (169 lines)
- cartographer/stage0_start/stage0_start — THE DELIVERABLE BINARY (66,840 bytes;
  sha256 bb06ad495b28a0893a8180a065097d4d533e8b9d43fac76c813e2759005341f7)
- cartographer/              — solver package root created (spec "Overall
  Architecture" tree; stage1_vm/.. arrive in later phases)
- .gitignore                 — += .cartographer_state, .cartographer_state.tmp
- logs/PHASE_1_LOG.md, logs/KICKOFF_PHASE_2.md — this phase's protocol artifacts

Package layout decision: the binary lives at cartographer/stage0_start/stage0_start
(stage dirs per spec tree); the solver runs it FROM the cartographer/ package root
(`./stage0_start/stage0_start`), and the binary passes "./.cartographer_state"
explicitly (Phase-0 log convention), so the state file lands at the package root
next to the stage dirs — exactly the spec tree. Runtime state files are gitignored;
the built binary IS committed (deliverable artifact, small, reproducible; rollback
safety across sessions).

## 2. Design decisions and why

D11. CANONICAL FLAG FORMAT (finalized; supersedes Phase-0 "tentative CARTO{...}"):
     regex  ^CARTO\{[a-z0-9_]{8,64}\}$
     i.e. literal uppercase prefix CARTO{, contents only lowercase a-z / digits /
     underscore, 8..64 chars, closing }. Rationale: (a) prefix distinct from common
     CTF formats (flag{, HTB{, THM{); (b) single-case contents make flags
     transcription-robust (no case ambiguity — deliberate, because Stage 3's
     oracle help text will tax hex transcription and the flag itself must not);
     (c) machine-checkable for Stage 4's format check and TryHackMe multi-flag
     submission (Phase 7). ENFORCED from this phase on: gen_flag_blob.py refuses
     to mint non-conforming flags; test_stage0.sh re-checks the format.
     NOTE: policy.h placeholder decoy "CARTO{phase0-placeholder-decoy}" contains
     hyphens and therefore does NOT match the final format — it is a mechanism-test
     placeholder that Phases 2-4 replace; its REPLACEMENTS must match the regex.
     policy.h was NOT modified this phase (left for Phases 2-4/6).

D12. STAGE-0 REAL FLAG MINT: CARTO{first_ink_in_the_ledger} (30 bytes; contents 23
     chars). Thematic: .cartographer_state is the surveyor's ledger; the solver's
     first run is the ledger's first ink. Storage: XOR-masked blob, mask stored RAW
     (32 bytes) beside it — NO seed string in the binary, mask derivation happens
     only inside gen_flag_blob.py at build time. Runtime: stage0.c unmasks into a
     stack buffer, prints, wipes. Why masked at all: keeps `strings` scraping from
     yielding the flag without running the binary (the intended path stays trivial
     and ungated); why a SINGLE masked copy (unlike the two-copy HMAC key): the
     flag's correctness is externally observable — the test suite byte-exactly
     compares the printed flag against the python-minted value, so a transcription
     drop fails loudly (the two-copy idiom was needed only where round-trip tests
     could not see the truth). Why this remains "a genuine ungated win, not a
     trick": the binary hands over the flag on EVERY correct run per README
     instructions; no state, no gating, no decoy logic touches it.

D13. KEY POLICY (answers PHASE_0_LOG open question #2, DECIDED): ONE canonical HMAC
     key shared by all stage binaries —
     f03ea6b5c1b869482723c0d11d635f8e9966c43a0a8def87fd1e2e950c10a7de
     (= SHA-256("cartographer-ghost:phase0 dev key:do-not-ship"); ships only in the
     two masked forms already in state_core.c). No per-binary key variation. Any
     future phase needing a different secret uses a DIFFERENT constant, never a
     second state-key.

D14. STAGE-0 SEMANTICS versus the state library (consumed AS-IS; zero library
     changes): load("./.cartographer_state", &st, carto_now_ms()); fresh :=
     (rc != CARTO_LOAD_OK) — so CREATED and TAMPERED are treated identically at
     runtime (Phase-0 runtime rule; a tampered ledger silently restarts and the
     flavor honestly shows first-visit text). Then bump attempt_count[0], record
     interaction (same `now` used for load — invariant: ring_ts[0] == first_run_ms
     on a fresh create), save. Flag handout is unconditional.

D15. Escalation/decoy machinery is deliberately NOT wired into Stage 0: it is the
     ungated orientation stage. carto_should_escalate() and carto_lookup_decoy()
     remain available to Stages 1-3 (Phases 2-4). Stage 0 never prints state
     diagnostics of any kind (stderr stays empty in every scenario — tested).

D16. FLAVOR TEXT (written fresh; theme: the vanished surveyor and his ledger): a
     dead cartographer's final survey, an open ledger that "accepts your hand."
     One forward-looking sentence ("He drew in order, coast first, interior
     last") foreshadows stage ordering WITHOUT being a mechanical clue — kept
     deliberately vague (no coordinates, no names, no numbers) so Phase 2's
     narrative-misdirection trap can be planted on clean ground.

D17. BUILD PIPELINE per spec (musl static -> strip --strip-all -> scrub):
     musl-gcc -O2 -Wall -Wextra -std=c11 -static -fno-ident, then
     strip --strip-all, then objcopy --remove-section .comment.
     BUG FOUND AND FIXED during this phase: first build's binary still contained
     "GCC: (Ubuntu 13.2.0...) 13.2.0" + "GCC: (Ubuntu 13.3.0...) 13.3.0" strings —
     NOT from stage0.c (compiled with -fno-ident) but from the Phase-0 state
     library's committed .o members (built without -fno-ident). Root-cause fix
     (rebuild libstate .o with -fno-ident) belongs to the state Makefile; chosen
     interim fix: explicit .comment-section removal in the stage Makefile —
     works regardless of how the library was compiled, and future phases inherit
     the same recipe. (The Phase-0 library is untouched per D14; consider folding
     -fno-ident into src/state/Makefile in Phase 2.)

## 3. Every constant introduced (exact values + location)

- CANONICAL FLAG FORMAT (decision D11): ^CARTO\{[a-z0-9_]{8,64}\}$
  (documented here and enforced in src/stage0/gen_flag_blob.py + test_stage0.sh)
- STAGE-0 REAL FLAG (D12): CARTO{first_ink_in_the_ledger}
  - length 30 bytes; plaintext exists ONLY: (a) in this log (internal),
    (b) on the solver's stdout at runtime. NEVER in any shipped binary.
  - lives in src/stage0/gen_flag_blob.py as the mint source
- flag XOR-mask (raw, 32 bytes, in flag_blob.h kCartoS0FlagMask):
    93438e2a8b381953706eb23fdbc5de3ea19dc88f942c7272dd4e1adf74c2bd86
  = SHA-256("cartographer-flag-mask-stage0")  [seed string NOT in any binary;
    recorded here (internal) + gen_flag_blob.py]
- masked flag blob (30 bytes, in flag_blob.h kCartoS0MaskedFlag):
    d002dc7ec4437f3a021dc660b2abb561c8f397fbfc492d1eb82a7dba06bf
- STATE PATH: literal "./.cartographer_state" (state.c, STATE_PATH macro)
- CFLAGS for stage binaries (src/stage0/Makefile):
    -O2 -Wall -Wextra -std=c11 -static -fno-ident
- No changes to: policy.h thresholds, HMAC key/masks, state file format,
  state library API (all Phase-0 values stand unchanged).

## 4. Exact commands (runnable verbatim)

C7. Build stage0_start (regenerates flag_blob.h deterministically):
wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/stage0 && make'

C8. THE stage0 verification (36 checks; expect ALL TESTS PASSED):
wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/stage0 && ./test_stage0.sh'

C9. State-library regression (Phase-0 suite; expect 26/26):
wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/state && make clean && make test && file test_state'

C10. Key/flag/mask derivation one-liner (mask + masked blob, matches flag_blob.h):
wsl.exe bash -lc 'python3 -c "import hashlib; flag=b\"CARTO{first_ink_in_the_ledger}\"; mask=hashlib.sha256(b\"cartographer-flag-mask-stage0\").digest(); print(mask.hex()); print(bytes(a^b for a,b in zip(flag,mask)).hex())"'

C11. Manual smoke run (from the package root, as a solver would):
wsl.exe bash -lc 'cd /home/manish/cartographer-build/cartographer && rm -f .cartographer_state && ./stage0_start/stage0_start && ./stage0_start/stage0_start'

C12. Scrub spot-check (expect empty output):
wsl.exe bash -lc 'strings -n 4 /home/manish/cartographer-build/cartographer/stage0_start/stage0_start | grep -Ei "(GCC|clang|musl|/home/manish|cartographer-build)" ; true'

## 5. Verification run — full real output (C8, after the D17 fix)

```
== stage0_start end-to-end verification ==
[PASS] binary exists and is executable
[PASS] binary statically linked (musl)
[PASS] binary stripped (no symtab)
[PASS] first run exits 0
[PASS] first run: stderr silent
[PASS] first run prints exact flag line once
[PASS] first-entry timestamp printed
[PASS] .cartographer_state created
[PASS] state file is exactly 352 bytes
[PASS] state HMAC valid (independent python check)
[PASS] first_run_ms ~= wall clock at creation
[PASS] attempt_count[0] == 1 after first run
[PASS] interaction ring: 1 entry, head=1
[PASS] debugger flag is 0
[PASS] ring_ts[0] == first_run_ms (same clock read)
[PASS] no decoy bits on stage 0
[PASS] second run exits 0
[PASS] second run: stderr silent
[PASS] second run prints flag (ungated every run)
[PASS] attempt_count[0] == 2 after second run
[PASS] ring: 2 entries, head=2
[PASS] first_run_ms stable across runs
[PASS] ring timestamps monotonic
[PASS] no .tmp residue
[PASS] run after tamper exits 0 (no error path)
[PASS] tampered run: stderr silent (no diagnostics)
[PASS] flag still handed over after tamper reset
[PASS] state rewritten valid after tamper
[PASS] first_run_ms reset (tamper was self-defeating)
[PASS] counters reset to fresh defaults
[PASS] reset first_run_ms ~= now
[PASS] canonical HMAC key hex absent from binary
[PASS] flag plaintext absent (masked blob only)
[PASS] no debug paths / compiler strings in binary
[PASS] stage-0 flag matches canonical format (CARTO{[a-z0-9_]{8,64}})
[PASS] package left pristine (test state removed)

== 36 tests run, 0 failed ==
ALL TESTS PASSED
```

`file` on the deliverable:
cartographer/stage0_start/stage0_start: ELF 64-bit LSB executable, x86-64,
version 1 (SYSV), statically linked, stripped

C9 regression (tail): == 26 tests run, 0 failed == / ALL TESTS PASSED
(27 including file(1) reporting the static binary).

## 6. Solver-visible output (verbatim, both variants)

First run (rm .cartographer_state first):
```
======================================================================
  THE CARTOGRAPHER'S GHOST
  Stage 0 -- Orientation: The Surveyor's Ledger
======================================================================

They say the old surveyor drew his final map the night the fog
took him: no body, no farewell. Only his study, still warm, and a
ledger lying open on the desk, a page waiting for a hand.

You take up the pen. The ledger accepts yours as the keeper's
hand and yields the first token of his survey:

    CARTO{first_ink_in_the_ledger}

Bank it -- it is yours, and it is real. He drew in order, coast
first, interior last. So, it appears, shall you.

  First entry inked: 2026-09-18 17:49:14 UTC
======================================================================
```
Second run: same banner; body replaced by:
"The ledger already knows your hand. The first token stands:" — flag identical,
"First entry inked" timestamp UNCHANGED (17:49:14, proving persistence), rc=0.

## 7. Bugs found and fixed DURING Phase 1

1. GCC ident strings ("GCC: (Ubuntu 13.2.0-6ubuntu1) 13.2.0" and 13.3.0) in the
   first built binary — source: state library .o members compiled without
   -fno-ident (stage0.c itself had it). Fixed via objcopy --remove-section
   .comment in the stage Makefile (D17); test went 35/36 -> 36/36.
2. pwsh->bash multi-line python one-liners broke again (confirmed Phase-0
   quirk); use C5/C10-style single-line semicolon form with pwsh single quotes
   around the whole bash command and \" escapes for python string literals.

## 8. Explicitly NOT done / deferred (per spec phases)

- README_FOR_SOLVER.txt (Phase 7 deliverable; the run instructions referenced
  by D12 exist as C11 for now).
- Stage 1 VM (Phase 2), Stage 2 stego (Phase 3), Stage 3 oracle (Phase 4),
  Stage 4 riddle+validator (Phase 5), calibration+self-test (Phase 6),
  packaging/HINTS/room text (Phase 7).
- Real decoy entries in policy.h (Phases 2-4; placeholder entry does NOT match
  the canonical format — its replacement must, see D11).
- Optional: folding -fno-ident into src/state/Makefile (see D17 note).

## 9. Open questions / judgment calls for the next session

1. Stage 1's deliverable per spec is KEY MATERIAL (Stage 2 key) computed by the
   VM, with the final flag assembled only in Stage 4. Decide in Phase 2 whether
   Stage 1 also prints an intermediate submittable string (must follow D11
   format if so) or nothing but the key material.
2. Opcode mapping seed (Phase 2): keep it OUT of solver-facing files entirely;
   it MAY live in PHASE_2_LOG.md (internal) per the kickoff constraint.
3. State-file runtime rule restated for every future binary: treat
   CARTO_LOAD_CREATED and CARTO_LOAD_TAMPERED identically (silent fresh start).
4. Timestamps: wall clock (CLOCK_REALTIME via carto_now_ms) is correct for the
   interaction ring (deltas must span process restarts) — do not switch to
   CLOCK_MONOTONIC.
5. d:\gandu\_stage: Phase-1 staged files are s0_*.c/.py/Makefile/.sh and
   PHASE_1_LOG.md / KICKOFF_PHASE_2.md; Phase-0 *.part2 chunks remain untouched.

Git commits for Phase 1: single commit on main, subject "phase1: stage0_start
(state init, ungated Stage-0 flag, flavor) + 36-test suite; canonical flag
format finalized", containing src/stage0/*, cartographer/stage0_start/stage0_start,
the .gitignore update, and both protocol logs. The hash is intentionally not
hardcoded here (amending this log changes it); run
git -C /home/manish/cartographer-build log --oneline for the authoritative list.
