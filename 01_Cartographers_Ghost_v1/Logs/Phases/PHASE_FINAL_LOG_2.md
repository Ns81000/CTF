# PHASE FINAL LOG — Calibration, Deep Verification & Split Deliverables

Status: COMPLETE. Repo: `/home/manish/cartographer-build` (branch `main`).
Session date: 2026-09-20. Executed against `logs/KICKOFF_PHASE_FINAL.md`
(the restructured revision with `CARTO_TEST_TIME_SCALE` and split
`drive-upload/` / `organizer-private/` deliverables).

## 0. Protocol confirmation (Session Continuity Protocol)

Before writing any code or running any build command, this session:

1. READ `docs/BUILD_SPEC.md` IN FULL (all 170 lines, in chunks, including the
   merged Phase FINAL section and the constraints section).
2. READ `logs/PHASE_0_LOG.md` through `logs/PHASE_5_LOG.md` IN ORDER, IN FULL
   (295 + 314 + 907 + 749 + 668 + 577 = 3504 lines, in chunks), plus
   `logs/KICKOFF_PHASE_FINAL.md`.
3. INDEPENDENTLY re-verified Phases 0-5 FIRST — reproduced, did not trust the
   logs:
   * `cd src/state && make clean && make test` → **27/27 ALL TESTS PASSED**
   * `bash src/stage4_assembly/verify.sh` → 27 state, 36 stage0, 8+65 stage1,
     58+71 stage2, 33 stage3, 64 stage4, all 0 failed; all seven artifact
     SHA-256s matched PHASE_5_LOG section 3 exactly.
   * Swept the whole `src/` tree for `__pycache__`/`*.pyc` (one stale
     `src/stage3_oracle/__pycache__/model_oracle.cpython-312.pyc` found and
     removed; re-count = 0).

## 1. What was built (exact paths, all in /home/manish/cartographer-build)

Internal verification and calibration drivers (never shipped):

- src/final/cartosolve.py        — solver-side toolkit for the calibration
                                   runs (Stage-2 sweep/press reader, oracle
                                   driver + 8-experiment collector, assembly);
                                   package root overridable via CARTO_PKG
- src/final/run_clean_path.py    — Run A driver (clean path, per-stage timing)
- src/final/run_decoy_segment.py — Run B driver (decoy detour + recovery only)
- src/final/run_isolated_solve.py— section-7 driver (solves a re-pointed,
                                   extracted package standing alone)
- src/final/verify_adversarial.sh— section-4 adversarial suite (107 checks)
- src/final/verify_isolated.sh   — section-7 isolated-package verification
- src/final/build_package.sh     — section-6 split packaging
- src/final/build_testbuild.sh   — builds the scaled test build
- src/final/probe_scale.c        — behavioural proof of the time-scale hook
- src/final/README_FOR_SOLVER.txt— the one shipped text file (canonical copy)

Repository sources changed:

- src/state/state_policy.c       — CARTO_TEST_TIME_SCALE hook (compile-time
                                   gated) + CARTO_STDDEV_LOW_MS_EFF
- src/state/Makefile             — `make CARTO_TEST_BUILD=1` opt-in
- src/state/policy.h             — calibrated thresholds + CALIBRATED comments
- src/state/test_part2.c         — test_escalate_fast made boundary-driven
- src/stage1_vm/stage1_vm.c      — debugger-detection fairness fix
                                   (/proc TracerPid authoritative)
- src/stage1_vm/test_stage1.sh   — "fast" forge age made calibration-proof
- src/stage2_stego/test_stage2.sh— same

Deliverables:

- SOLVE_PATH_PRIVATE.md          — the internal writeup (NEVER shipped)
- HINTS.md                       — exactly 5 hints (organizer copy)
- TRYHACKME_ROOM_TEXT.md         — room text + the two scored answers
- drive-upload/cartographer.zip  — the solver package (9 files)
- organizer-private/             — everything internal, never shipped
- logs/PHASE_FINAL_LOG.md        — this file
- logs/runs/final_clean_path.log{,.stdout,.started}
- logs/runs/final_decoy_segment.log
- logs/runs/scale60_clean.log{,.stdout}   (scaled cross-check)
- logs/runs/final_adversarial.txt          (107-check adversarial suite)


## 2. Design decisions and why

D64. **No in-binary waits exist** (found first, governs everything else).
     Searched the whole tree: `grep -rn 'sleep\|usleep\|nanosleep' src/`
     returns hits ONLY in `src/stage3_oracle/solve_attack.py` (internal
     tooling, not shipped). Every stage binary is a deterministic finite
     computation; the only wall-clock cost a solver controls is the Stage-3
     query budget and its pacing. The kickoff's section-2/3 premise ("a
     60-minute mandatory wait", "sleep/rate-limit/escalation-timer check")
     therefore does not describe this build, and `CARTO_TEST_TIME_SCALE` was
     implemented where the real time-dependent logic actually lives: the
     escalation thresholds in the shared state library, plus the internal
     query driver's pacing. Recorded honestly rather than inventing a wait
     that does not exist.

D65. **CARTO_TEST_TIME_SCALE is compile-time gated in the library.** The
     escalation logic lives in `state_policy.o` (inside `libstate.a`), so one
     define is enough for every stage binary that links it:
     `make CARTO_TEST_BUILD=1` → `-DCARTO_TEST_TIME_SCALE_ENABLE`. Shipped
     builds define nothing. It divides BOTH the elapsed-time thresholds and
     the inter-arrival uniformity floor — scaling both is required, because
     compressing time shrinks the ring's inter-arrival deltas by the same
     factor, so scaling only one side would make a compressed paced loop look
     scripted-uniform and get poisoned (the first version of the probe got
     this wrong and the test caught it). Proven two ways:
       * `strings` on all 5 shipped binaries → name absent; on the test
         build's objects → name present.
       * `src/final/probe_scale.c`: shipped answers identically at scale 1
         and 60; test build at scale 60 suppresses both; test build at scale 1
         is identical to shipped; a non-numeric value falls back to 1.

D66. **CALIBRATION FINDING — the Stage-3 budget was costed wrong.**
     `PHASE_4_LOG` D52 recorded "2560 pairs ~ 85 min at 2 s spacing", but each
     pair is TWO oracle calls, so 5120 queries at 2 s is ~171 min — past the
     165-min ceiling before any other stage runs. Separately, the Phase-0
     placeholder `CARTO_STDDEV_LOW_MS = 1500.0` imposed a hard floor on any
     clean paced query loop (alternating sleeps give stddev = (b-a)/2, so
     staying clean required b-a > 3000 ms, i.e. a >= 1.5 s mean spacing), a
     minimum of ~128 min on the query stage alone. Both targets were
     unreachable. This is exactly the class of defect Phase FINAL exists to
     find, and it was found by arithmetic before any long run was started.

D67. **CARTO_STDDEV_LOW_MS 1500.0 → 150.0.** The one calibration that changes
     measured behaviour (it also gates the Stage-3 poison). 150 ms keeps the
     trap's intent: a fixed `sleep(0.05)` loop has stddev ~4 ms and is still
     poisoned; a fixed `sleep(1)` loop ~10 ms, still poisoned; while anything
     whose spacing varies with thinking time is far above it. The calibrated
     run's pacing (alternating 0.15 s / 1.85 s) measures ~850 ms = 5.7x
     margin. Cadence band restored: 0.19 s minimum clean mean (was 1.5 s),
     and the measured 1.00 s mean lands the whole clean path at ~84 min.

D68. **carto_t_fast_sec[] {90,90,90,90,90} → {3, 3, 20, 60, 300} s.**
     "Reached this stage this soon after the very first run." Set well below

## 3. Every constant introduced (exact values + locations)

Calibrated policy (src/state/policy.h; was Phase-0 placeholder):

- CARTO_STDDEV_LOW_MS  1500.0 -> 150.0   (D67; also gates the Stage-3 poison)
- carto_t_fast_sec[5]  {90,90,90,90,90} -> {3, 3, 20, 60, 300}  (D68)
- CARTO_T_FAST_SEC_DEFAULT  90u -> 3u
- CARTO_MIN_TIMING_DELTAS  4  (UNCHANGED: a count, not a time)
- CARTO_VM_DEBUG_RATIO_LIMIT  20.0  (UNCHANGED; re-measured, margin comfortable)
- CARTO_DECOY_TABLE_LEN  4  (UNCHANGED; the four registered decoys stand)

Time-scale hook (src/state/state_policy.c, guarded by
`#ifdef CARTO_TEST_TIME_SCALE_ENABLE`):

- env var CARTO_TEST_TIME_SCALE, integer, default 1, valid range 1..1000000,
  non-numeric/negative falls back to 1
- divides carto_t_fast_sec[stage] (clamped to a 1 s minimum)
- divides CARTO_STDDEV_LOW_MS via the CARTO_STDDEV_LOW_MS_EFF macro
  (shipped build: expands to the plain constant, so shipped codegen and
  behaviour are unchanged)

Stage-1 detection order (src/stage1_vm/stage1_vm.c, D69):

- /proc/self/status "TracerPid:"  > 0 -> detected;  == 0 -> clean
- fallback: ptrace(PTRACE_TRACEME) < 0 -> detected iff errno == EPERM
- #include <stdlib.h> added for strtol

Stage-3 query budget (UNCHANGED, now costed correctly):

- 8 experiments x 320 pairs = 2560 pairs = 5120 oracle invocations
- calibrated clean-path pacing: alternating 0.15 s / 1.85 s
  (mean 1.000 s, stddev 0.850 s = 5.7x the 150 ms poison floor)
- scaled-build pacing used for iteration only: the same pair divided by
  CARTO_TEST_TIME_SCALE

Internal tooling knobs (src/final/*, env, default in parentheses):

- CARTO_FINAL_PER_WINDOW (320)   pairs per experiment
- CARTO_FINAL_PACE ("0.15,1.85") alternating inter-query sleeps, seconds
- CARTO_FINAL_LOG                run log path
- CARTO_PKG                      package root (isolated verification)

Files shipped (drive-upload/cartographer.zip, 9 entries):

- cartographer/README_FOR_SOLVER.txt
- cartographer/stage0_start/stage0_start
- cartographer/stage1_vm/stage1_vm
- cartographer/stage2_stego/stage2_stego
- cartographer/stage2_stego/survey_frame.png   (byte-identical to Phase 3)
- cartographer/stage2_stego/survey_tape.wav    (byte-identical to Phase 3)
- cartographer/stage3_oracle/oracle
- cartographer/stage4_assembly/validate

Nothing else. No markdown, no logs, no source, no .git, no build artifacts,
and `CARTO_TEST_TIME_SCALE` in none of the five binaries.

## 4. Exact commands (runnable verbatim)

C48. Re-verify the whole baseline (Phases 0-5) before touching anything:
wsl.exe -d Ubuntu-24.04 -- bash -c "cd /home/manish/cartographer-build && cd src/state && make clean && make test && bash ../stage4_assembly/verify.sh"

C49. Apply the Phase FINAL patches (idempotent) and prove both builds:
wsl.exe -d Ubuntu-24.04 -- bash -c "tr -d '\r' < /mnt/d/gandu/_stage/s5_final/apply.sh | bash"
  (runs p1..p6, then `make CARTO_TEST_BUILD=1 test` -> 27/27 + the hook
   present, then `make test` -> 27/27 + the hook absent)

C50. Sync the Phase FINAL tooling + documents into the repo:
wsl.exe -d Ubuntu-24.04 -- bash -c "tr -d '\r' < /mnt/d/gandu/_stage/s5_final/sync_all.sh | bash"

C51. The scaled test build (iteration speed-up only):
wsl.exe -d Ubuntu-24.04 -- bash -c "CARTO_TEST_TIME_SCALE=60 bash /home/manish/cartographer-build/src/final/build_testbuild.sh && cd /home/manish/cartographer-build && CARTO_TEST_TIME_SCALE=60 CARTO_FINAL_PER_WINDOW=320 CARTO_FINAL_LOG=logs/runs/scale60_clean.log python3 src/final/run_clean_path.py"
  (restore the shipped build afterwards with C48's verify.sh)

C52. Run A — the real, unscaled clean-path measurement:
wsl.exe -d Ubuntu-24.04 -- bash -c "cd /home/manish/cartographer-build && date -u > logs/runs/final_clean_path.started && setsid env -u CARTO_TEST_TIME_SCALE CARTO_FINAL_PER_WINDOW=320 CARTO_FINAL_PACE=0.15,1.85 CARTO_FINAL_LOG=/home/manish/cartographer-build/logs/runs/final_clean_path.log python3 src/final/run_clean_path.py > logs/runs/final_clean_path.stdout 2>&1 < /dev/null &"
  (~85 min; poll with `tail logs/runs/final_clean_path.log`)


## 5. Verification run — real output

(a) C48, the independent baseline re-verification (tails):
```
== 27 tests run, 0 failed ==            (state library)
ALL TESTS PASSED
== 36 tests run, 0 failed ==            (stage0)
== 8 checks, 0 failed ==                (stage1 detection-verdict unit)
== 65 tests run, 0 failed ==            (stage1)
== 58 vectors run, 0 failed ==          (s2_inflate differential)
== 71 tests run, 0 failed ==            (stage2)
== 33 passed, 0 failed ==               (stage3)
== 64 tests run, 0 failed ==            (stage4)
```
All seven artifact hashes matched PHASE_5_LOG section 3 exactly before any
change was made (the carriers are still byte-identical after it).

(b) C49, both library builds after the patches:
```
test build (CARTO_TEST_BUILD=1)
== 27 tests run, 0 failed == ALL TESTS PASSED
  TEST-BUILD-CARRIES-SCALE-OK
shipped build (default)
== 27 tests run, 0 failed == ALL TESTS PASSED
  SHIPPED-BUILD-SCALE-ABSENT-OK
```

(c) C48 re-run after the patches, full chain green:
```
== 27 tests run, 0 failed ==   == 36 tests run, 0 failed ==
== 8 checks, 0 failed ==       == 65 tests run, 0 failed ==
== 58 vectors run, 0 failed == == 71 tests run, 0 failed ==
== 33 passed, 0 failed ==      == 64 tests run, 0 failed ==
```
Two of those runs initially FAILED and both failures were real
test-harness defects (D70), not product defects:
`[FAIL] test_escalate_fast` and `[FAIL] extended variant not selected`.

(d) C54, the adversarial suite:
```
== 107 checks passed, 0 failed ==
probe_scale: elapsed_fast=FIRES (raw=0x1) uniform=FIRES (raw=0x3) ring_stddev_ms=3.959   [shipped, scale=1]
probe_scale: elapsed_fast=FIRES (raw=0x1) uniform=FIRES (raw=0x3) ring_stddev_ms=3.959   [shipped, scale=60]
probe_scale: elapsed_fast=FIRES (raw=0x1) uniform=FIRES (raw=0x3) ring_stddev_ms=3.959   [test build, scale=1]
probe_scale: elapsed_fast=quiet (raw=0x0) uniform=quiet (raw=0x1) ring_stddev_ms=3.959   [test build, scale=60]
```
That table is the whole argument for D65 in four lines: the shipped build
cannot be triggered by the variable at all, the test build can, and the test
build at scale 1 is indistinguishable from shipped.

(e) Run B (C53, real, unscaled):
```
RESULT: detour segment complete; real path resumed at the START of Stage 3
ADDED DETOUR COST: 0.02 s (0.00 min)
```
Every decoy branch fired as designed (decoy key re-inked; decoy sweep
stride 39 / start 1512 -> unparseable; naive LSB -> the coast flag accepted
into the extended branch; checkpoint token -> re-inked-checkpoint branch;
struck draft -> corroborated draft), and the recovery re-derived the real
reading. Full log: logs/runs/final_decoy_segment.log.

(f) The scaled cross-check (C51, test build, scale 60):
```
RESULT: CLEAN-PATH SOLVE COMPLETE, deterministically
TOTAL 91.46s (1.52 min)
attack recovered K = 73070925a159f9e2
./stage4_assembly/validate accepted the title -- SURVEY CLOSED
```

(g) Run A (C52, real, unscaled): see section 6 below for the final numbers
and the log path.

C53. Run B — the real, unscaled decoy-detour-segment measurement:
wsl.exe -d Ubuntu-24.04 -- bash -c "cd /home/manish/cartographer-build && env -u CARTO_TEST_TIME_SCALE CARTO_FINAL_LOG=/home/manish/cartographer-build/logs/runs/final_decoy_segment.log python3 src/final/run_decoy_segment.py"

C54. Section 4 — the deep adversarial verification (107 checks):
wsl.exe -d Ubuntu-24.04 -- bash -c "cd /home/manish/cartographer-build && bash src/final/verify_adversarial.sh > logs/runs/final_adversarial.txt 2>&1"

C55. Section 6 — the split packaging:
wsl.exe -d Ubuntu-24.04 -- bash -c "bash /home/manish/cartographer-build/src/final/build_package.sh"

C56. Section 7 — the isolated-package re-verification:
wsl.exe -d Ubuntu-24.04 -- bash -c "bash /home/manish/cartographer-build/src/final/verify_isolated.sh"

     the legitimate arrival time at each stage so it fires only for scripted
     play-through. These thresholds select a PRESENTATION variant only —
     every stage suite proves the key/verdict is bit-identical across
     escalated and plain states — so they cannot change any measured solve

## 6. Calibration results (the numbers this phase exists to produce)

Run A — clean path, no detours, real wall clock, unscaled:

| quantity | value |
|---|---|
| started / completed | 2026-09-20T18:26:17Z / 19:50:46Z |
| budget | 8 x 320 pairs = 2560 pairs = 5120 oracle calls |
| pacing (requested) | alternating 0.15 s / 1.85 s (mean 1.000 s, stddev 0.850 s) |
| pacing (measured) | **0.989 s per query**; ring stddev after collection **850.2 ms** (5.7x the 150 ms poison floor) |
| **measured clean-path time** | **5066.07 s = 84.43 min** (Stage-3 collection 84.43 min; stages 0/1/2/4 are 0.00-0.01 s) |
| target 60–90 min | **PASS** |
| recovered K | 73070925a159f9e2 (hits A = 24/28/15/16, B = 24/23/26/32) |
| title accepted | yes — `CARTO{73070925a159f9e2_a5d66f1b2b5f596e_no_figure_sits_in_every_pixel}` |

Run B — decoy-detour segment only, real wall clock, unscaled:

| quantity | value |
|---|---|
| **measured added machine cost** | **0.02 s** |
| human analysis cost (modelled, per step) | ~65–130 min (SOLVE_PATH_PRIVATE.md 5.2) |
| worst-case estimate (clean + full detour) | ~149–165 min at the calibrated cadence |

Both targets are met at the calibrated cadence, with the honest caveat that a
deliberately unhurried solver can exceed the ceiling (section 9, item 1).

## 7. Bugs found and fixed DURING Phase FINAL

1. p1_time_scale: the helper's insertion was guarded on
   `"carto_test_time_scale" not in src`, but the escalation-block replacement
   had already introduced that symbol, so the guard and the
   `CARTO_STDDEV_LOW_MS_EFF` macro were never emitted and the file did not
   compile. Caught immediately by the C49 build; fixed by guarding on the
   `#ifdef` line itself.
2. p4_calibrate_policy: the `carto_t_fast_sec` regex did not anchor the
   `static const uint32_t ` prefix, so the replacement doubled it. Caught by
   the same build. Fixed by anchoring the whole declaration.
3. `[FAIL] test_escalate_fast` after calibration: the test hard-coded the
   Phase-0 placeholder ("30 s < 90 s placeholder"). Product code was correct.
   Fixed by deriving the boundary from `carto_t_fast_sec[]` (D70).
4. `[FAIL] extended variant not selected` after calibration:
   `test_stage2.sh` forged "fast arrival" as 60 s, which the new 20 s stage-2
   threshold no longer considers fast. Product code was correct. Fixed by
   forging 1 ms (D70); `test_stage1.sh` hardened the same way.
5. probe_scale.c scenario B used a CONSTANT inter-arrival spacing, whose
   stddev is 0 and therefore fires the uniformity reason under BOTH floors,
   proving nothing. Caught by the suite's own output. Fixed by using deltas
   1,9,1,9,1,9,1 ms (stddev 3.96 ms, between the scaled 2.5 ms and the
   unscaled 150 ms floors) and printing the measured stddev.
6. verify_adversarial.sh: `hmac_ok` was called without its `$STATE` argument
   at three call sites (`set -u` then aborted the script mid-suite). Fixed.
7. verify_adversarial.sh: the oversized-argument case used a 200 KB single
   argv, which fails with E2BIG at the OS level (`MAX_ARG_STRLEN` = 128 KB)
   and returned rc 126 for every binary — a harness bug, not a binary bug.
   Fixed to 120 KB and the OS limit is documented in the suite.
8. verify_adversarial.sh: a section-4 insert split a multi-line `chk` call in
   half, leaving it with one argument. Caught by `set -u`. Fixed.
9. cartosolve.py: the checkpoint-token grep expected a 38-character line
   because PHASE_2_LOG D18 says "38 chars"; the real length is 39
   (6 + 32 + 1). The tool now matches `CARTO{[0-9a-f]{32}}` exactly.
10. cartosolve.py: the ink framing was read as a big-endian 16-bit length.
    The framing is `LE16(len(zblob))` while the bit stream is MSB-first per
    byte, so reading it big-endian yields 0x3000 instead of 48 and the real
    sweep looks empty. Fixed (and the decoy sweep correctly still yields 0).

## 8. Explicitly NOT done / deferred

- `CARTO_TEST_TIME_SCALE` is NOT in any shipped artifact (asserted twice:
  once against the repo package, once against the extracted zip). It is a
  throwaway iteration aid and is documented as such.
- The Stage-3 differential attack is NOT re-paid in the isolated-package
  verification (that would double the 85-minute cost); the isolated oracle is
  instead proven to be the identical cipher by bit-exact agreement with the
  model on chosen figures, and the full-budget attack was measured once in
  Run A.
- No change to `N_REQUIRED` (320/window), the 4-round cipher, the decoy table
  or the carrier files.
- The "interior + detected" VM combination is still only verified via the
  python model and an ad-hoc gdb run (carried from Phase 2; the suite asserts
  coastal+detected).

## 9. Open questions / judgement calls for any future session

1. If the 165-min ceiling is ever hardened into a hard requirement, the lever
   is `N_REQUIRED` (fewer pairs per experiment, re-proving the attack at that
   sample size), not the pacing: pacing is solver behaviour, not a property of
   the challenge.
2. `CARTO_T_FAST_SEC_DEFAULT` is 3 s, so the first stages flag
   `CARTO_ESC_TIME_FAST` on a legitimate fast start. Harmless by construction
   (presentation only) and intended; lowering it further would make the tell
   meaningless.
3. The four decoy tokens remain `strings`-findable in every binary via
   policy.h. Accepted D29/D50 trade-off, re-confirmed this phase to shortcut
   nothing.
4. The Windows-side staging for this phase is `d:\gandu\_stage\s5_final\`
   (patches p1..p6, the drivers, and the documents). Repo copies are
   canonical.

     time or any answer. Data-driven from Run A's measured arrival times.
