# PHASE FINAL-2 LOG — Pacing Fix, Full Source Audit, Repackage, WSL Archive

Status: COMPLETE. Repo: `/home/manish/cartographer-build` (branch `main`).
Session date: 2026-09-21. Executed against the Phase FINAL-2 kickoff prompt
("Pacing Fix, Full Corner-Sweep Audit, Repackage, WSL Archive") — the last
session before the hackathon.

## 0. Protocol confirmation (Session Continuity Protocol)

Before writing any code or running any build command, this session:

1. READ `docs/BUILD_SPEC.md` IN FULL, and `logs/PHASE_0_LOG.md` …
   `logs/PHASE_5_LOG.md` plus `logs/PHASE_FINAL_LOG.md` (the previous final
   session's report) IN ORDER, IN FULL.
2. INDEPENDENTLY re-verified the previous phase FIRST, before touching
   anything: `bash src/stage4_assembly/verify.sh` (the full clean-room chain:
   state 27/27, stage0 36/36, stage1 8/8 + 65/65, stage2 58/58 + 71/71,
   stage3 33/33, stage4 64/64, regen deterministic, scrub clean) — all green
   on the pre-FINAL-2 build, so the foundation was sound before the pacing
   work started.

## 1. What was built / changed (exact paths)

Section 1 — the pacing fix (internal tooling + docs; **no shipped binary
changes**):

- src/final/cartosolve.py       — `N_REQUIRED = 260` documented constant with
                                   its rationale; `parse_pace` / `pace_stats`
                                   / `pace_draw`: the pacing model now
                                   supports both the old alternating pair and
                                   a per-query jittered draw
                                   ("jitter:lo,hi"), which is what the
                                   cautious-edge run uses
- src/final/run_clean_path.py   — default `PER_WINDOW` =
                                   `cartosolve.N_REQUIRED` (260); default
                                   pace `jitter:0.6,3.4`; accepts both pace
                                   spec forms
- src/final/trial_attack.py     — NEW: the reliability-trial harness (section
                                   1 of the kickoff): N candidates x T
                                   independent trials, fresh random figures
                                   per trial, two data sources (real binary /
                                   model), per-trial dataset verification
                                   against the real key
- src/final/pf2_report.py       — NEW: aggregates the trial JSONL into the
                                   per-N failure table
- src/final/probe_ring.py       — NEW: diagnostic that proves the sampled
                                   ciphertexts are the clean-key ones and
                                   dumps the ring deltas / poison floor
- src/final/build_testbuild.sh  — doc only (PER_WINDOW 320 -> 260)
- src/stage3_oracle/test_stage3.sh — the attack proof now runs at the
                                   calibrated N=2080 pairs AND keeps the
                                   N=2560 control (33 -> 34 checks)

Section 2 — the audit fix (the only shipped-source change of this phase):

- src/stage1_vm/vm.c            — the code image now carries an 8-byte pad
                                   (`VM_CODE_PAD`): `vm_decode()` can be
                                   entered with `ip` within 8 bytes of the end
                                   of a 1024-byte image and reads up to 9 bytes
                                   (widest operand form), which ran past the
                                   end of the array. See section 6.

Section 4 — packaging:

- drive-upload/cartographer.zip — rebuilt from the new binaries (9 entries)
- organizer-private/            — this log, the updated
                                   SOLVE_PATH_PRIVATE.md, all run captures

Deliverable files:

- SOLVE_PATH_PRIVATE.md         — sections 2, 4.4, 4.6 (new), 5.1, 5.5 (new),
                                   8 updated
- README_FOR_SOLVER.txt         — one light paragraph added (section 4 of the
                                   kickoff): vary your gaps; a perfectly even
                                   loop is not a person. No mechanism named.
- logs/PHASE_FINAL_2_LOG.md     — this file
- logs/runs/pf2_trials_model.jsonl   — first sweep (300 trials x 11 N)
- logs/runs/pf2_model_sweep.txt      — its console log
- logs/runs/pf2_trials_model2.jsonl  — the recorded sweep (1500 trials x 6 N)
- logs/runs/pf2_model_sweep2.txt     — its console log
- logs/runs/pf2_trials_real.jsonl    — real-binary trials (5 x 6 N)
- logs/runs/pf2_real_sweep.txt       — its console log
- logs/runs/pf2_confirm_upper.log/.stdout — cautious-edge confirmation run
- logs/runs/pf2_confirm_lower.log/.stdout — fast-edge confirmation run
- logs/runs/pf2_cppcheck.txt         — the static-analysis pass (section 6)
- logs/runs/pf2_verify_chain.txt     — the clean rebuild + all suites
- logs/runs/pf2_adversarial.txt      — the 107-check adversarial suite

## 2. Design decisions and why

D71. **The pacing fix is a solver-side sample-size change, not a binary
     change.** `N_REQUIRED` never lived in any shipped artifact (grep proves
     it: 320/2560/5120 appear only in internal tooling and one suite). The
     challenge imposes no query budget; the budget is what the attack needs.
     So the fix is: recalibrate the documented budget from measured attack
     reliability, keep the cipher and the trap untouched, and re-measure the
     clean path at a realistic cadence. Shipped binaries are unchanged except
     the one audit fix (D74).

D72. **260 pairs/window, chosen from a sweep, not from one lucky run.** 1500
     independent trials per candidate (fresh random figures every trial,
     `logs/runs/pf2_trials_model2.jsonl`) plus 5 real-binary trials per
     candidate against the actual oracle (`logs/runs/pf2_trials_real.jsonl`).
     Full table and reasoning: SOLVE_PATH_PRIVATE.md section 4.6. Summary:

     | N | calls | model trials | single-pass failures | real trials |
     |---|---|---|---|---|
     | 200 | 3200 | 1500 | 108 (7.2%) | 5/5 |
     | 220 | 3520 | 1500 | 75 (5.0%) | - |
     | 240 | 3840 | 1500 | 29 (1.9%) | 5/5 |
     | **260** | **4160** | **1500** | **20 (1.3%)** | **5/5** |
     | 280 | 4480 | 1500 | 9 (0.6%) | 5/5 |
     | 320 (control) | 5120 | 1500 | 4 (0.27%) | 5/5 |

     260 is the smallest candidate whose single-pass rate stays within a
     small factor of the 320 control while cutting the budget 19%; 200 is the
     cliff and was rejected. Every residual failure is deterministically
     recoverable (the attack report names the short window; ~80 extra calls
     fix it; the acceptance test is exhaustive verification against every
     collected pair, so a wrong key is never accepted).

D73. **Pacing bounds were measured, not projected.** Both confirmation runs
     are real, unscaled, full clean paths at N=260 in isolated package copies
     (`/tmp/carto_confirm_upper`, `/tmp/carto_confirm_lower`), driven by
     `src/final/run_clean_path.py` against the shipped binaries:

     * **Cautious (upper) edge** — `jitter:0.6,3.4`: a fresh uniform draw per
       query, mean **2.000 s**, stddev **0.808 s** (5.4x the 150 ms poison
       floor). Projected 138.7 min. **Measured: 147.84 min** (ring stddev
       812.0 ms).
     * **Fast edge** — `jitter:0.1,1.1`: mean **0.600 s**, stddev **0.289 s**
       (1.9x the floor). Projected 41.6 min. **Measured: 41.42 min**
       (ring stddev 282.5 ms). This is the fastest cadence this phase
       is willing to call "comfortably above" the floor; anything tighter
       (e.g. `jitter:0.1,0.5`, stddev ~115 ms) is *inside* the floor and gets
       poisoned — measured on purpose, see D75.

     So the whole normal human range (0.6 s - 2.0 s mean, jittered) fits the
     window: the fix does not work at only one specific pace.

D74. **vm.c decode over-read (the one shipped-source fix).** `vm_decode()`
     reads up to 9 bytes from `g_code[]` at `ip`, and every `ip` is only ever
     masked with `VM_CODE_MASK`; a decode entered in the last 8 bytes of the
     1024-byte image therefore read past the end of the array (UB, and a hard
     error under ASan). The embedded bytecode never does it, so no output
     changes — the fix is an 8-byte pad the VM itself can never address.
     stage1_vm is the only binary whose hash moves because of it.

D75. **A trial-harness bug became the best evidence in the phase.** The first
     real-binary trial sweep poisoned *every* dataset, because the harness
     scaled its own sleeps by 60 but did not export `CARTO_TEST_TIME_SCALE`,
     so the test-build oracle still used the *unscaled* 150 ms floor against
     5-34 ms deltas. `probe_ring.py` pinned it exactly: with the floor
     unscaled, 4/10 answers were the real key and 6/10 the poison key, the
     flip happening at the 5th query — precisely when the ring first holds
     `CARTO_MIN_TIMING_DELTAS` (4) deltas. With the env var exported, the
     same probe reads 10/10 real key. Two consequences: every trial now
     re-verifies its dataset against the real key and refuses to report a
     poisoned one, and the floor's teeth were demonstrated on a *jittered*
     loop (`jitter:0.1,0.5`, stddev ~115 ms < 150 ms) — the trap is a stddev
     trap, not a "perfectly uniform" trap, which the solver-facing hint had
     always implied.

D76. **The trap was re-proved at the NEW call volume.** `probe_poison_volume.py`
     drives the real shipped oracle through the whole recalibrated budget
     (8 x 260 pairs = 4160 calls) at a machine-uniform fixed 0.1 s spacing —
     the thing a scripted loop naturally does. Result
     (`logs/runs/pf2_poison_volume.txt`): ring stddev **0.82 ms** against the
     150 ms floor, the dataset mixes the couple of clean answers that precede
     the first `CARTO_MIN_TIMING_DELTAS` deltas with poison-key answers after
     it, and the reference attack returns **NO-CONSENSUS** — the scripted
     solver gets nothing at all, silently, and no error is ever printed. (A
     dataset collected entirely under the poison key still converges on
     `0fab297110c73e9f`, which `test_stage3.sh --poison-converges` asserts:
     both outcomes are the trap working.) The new budget therefore does not
     weaken the anti-automation tell.

## 3. Every constant introduced or changed

- cartosolve.N_REQUIRED          260   (was a bare 320 in three tool files;
                                        8 x 260 = 2080 pairs = 4160 calls)
- run_clean_path pace default    "jitter:0.6,3.4"  (mean 2.000 s, sd 0.808 s)
- fast-edge pace                 "jitter:0.1,1.1"  (mean 0.600 s, sd 0.289 s)
- vm.c VM_CODE_PAD               8     (compile-time constant, new)
- carto_t_fast_sec[], CARTO_STDDEV_LOW_MS, CARTO_MIN_TIMING_DELTAS,
  CARTO_VM_DEBUG_RATIO_LIMIT, the cipher, the fold tables, the poison
  derivation and the decoy table — all UNCHANGED from Phase FINAL.

## 4. Exact commands (runnable verbatim)

C60. Reliability sweep, model side (1500 trials per candidate):
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /home/manish/cartographer-build && python3 src/final/trial_attack.py --mode model --candidates 200,220,240,260,280,320 --trials 1500 --jobs 6 --out logs/runs/pf2_trials_model2.jsonl"

C61. Reliability sweep, real binary (scaled test build; 5 trials per
candidate, fresh random figures each trial, isolated package per trial):
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /home/manish/cartographer-build && CARTO_TEST_TIME_SCALE=60 bash src/final/build_testbuild.sh && CARTO_FINAL_TSCALE=60 python3 src/final/trial_attack.py --mode real --candidates 160,200,240,260,280,320 --trials 5 --jobs 3 --out logs/runs/pf2_trials_real.jsonl && bash src/stage4_assembly/verify.sh"

C62. Clean rebuild + every suite on the new build:
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /home/manish/cartographer-build && bash src/stage4_assembly/verify.sh > logs/runs/pf2_verify_chain.txt 2>&1"

C63. The 107-check adversarial suite (anti-debug, anti-automation, tamper):
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /home/manish/cartographer-build && bash src/final/verify_adversarial.sh > logs/runs/pf2_adversarial.txt 2>&1"

C64. Cautious-edge confirmation run (real, unscaled, isolated package copy):
wsl.exe -d Ubuntu-24.04 -- bash -lc "cp -r /home/manish/cartographer-build/cartographer /tmp/carto_confirm_upper && CARTO_PKG=/tmp/carto_confirm_upper CARTO_FINAL_LOG=/home/manish/cartographer-build/logs/runs/pf2_confirm_upper.log python3 /home/manish/cartographer-build/src/final/run_clean_path.py"

C65. Fast-edge confirmation run (same, at the fast pace):
wsl.exe -d Ubuntu-24.04 -- bash -lc "cp -r /home/manish/cartographer-build/cartographer /tmp/carto_confirm_lower && CARTO_PKG=/tmp/carto_confirm_lower CARTO_FINAL_PACE=jitter:0.1,1.1 CARTO_FINAL_LOG=/home/manish/cartographer-build/logs/runs/pf2_confirm_lower.log python3 /home/manish/cartographer-build/src/final/run_clean_path.py"

C66. Static analysis (cppcheck, installed this session via apt):
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /home/manish/cartographer-build && cppcheck --enable=all --inconclusive --std=c11 --force --inline-suppr -I src/state -I src/stage0 -I src/stage1_vm -I src/stage2_stego -I src/stage3_oracle -I src/stage4_assembly src/state/carto_sha256.c src/state/state_core.c src/state/state_policy.c src/stage0/stage0.c src/stage1_vm/stage1_vm.c src/stage1_vm/vm.c src/stage2_stego/stage2_stego.c src/stage2_stego/s2_inflate.c src/stage3_oracle/oracle.c src/stage4_assembly/validate.c > logs/runs/pf2_cppcheck.txt 2>&1"

C67. Packaging + isolated re-verification + Windows copy + hash tables:
build_package.sh, verify_isolated.sh, finalize_windows.sh, report_windows.sh
— outputs captured in logs/runs/pf2_package.txt, pf2_isolated.txt,
pf2_windows_report.txt.

## 5. Verification evidence

(a) Clean rebuild + every suite on the new build (C62,
`logs/runs/pf2_verify_chain.txt`):
```
== 27 tests run, 0 failed ==        (state library)
== 36 tests run, 0 failed ==        (stage0)
== 8 checks, 0 failed ==            (stage1 detection unit)
== 65 tests run, 0 failed ==        (stage1 end-to-end)
== 58 vectors run, 0 failed ==      (stage2 vectors)
== 71 tests run, 0 failed ==        (stage2 end-to-end)
== 34 passed, 0 failed ==           (stage3; 33 + the new N=2080 proof)
== 64 tests run, 0 failed ==        (stage4)
VALIDATE-REGEN-REPRODUCIBLE-OK / SCRUB-CLEAN / solver-eye smoke run
```

(b) The 107-check adversarial suite on the new build (C63,
`logs/runs/pf2_adversarial.txt`): `== 107 checks passed, 0 failed ==`,
including, on the new build:
```
[PASS] real gdb attach: the corrupted constant is served (trap intact)
[PASS] scripted-uniform spacing: the poison is self-consistent (0adb9b08b2e01566)
[PASS] poison is falsifiable: same figure, two states, two answers
[PASS] human spacing: clean answer is self-consistent (2a7479540c7163e3)
```
and the state-file tamper-resistance section re-run at every documented
offset of the 352-byte ledger (magic, version, flags, first_run_ms,
attempt_count, decoy_mask, ring_count, ring_head, debugger flag, reserved,
ring timestamp, HMAC bit, truncate, extend) — 14/14 silent-reset-and-re-sign.

(c) Reliability sweeps: section 2, D72.

(d) Pacing bounds: section 2, D73.

(e) Static analysis (C66): 14 style-level notes, 0 errors, 0 warnings, 0 performance findings (38 informational include notes); every style note is triaged in section 6 (triaged file by file in
section 6).

(f) Clean rebuild from scratch (every stage `make clean && make`) and the
reproducibility compare against the pre-FINAL-2 commit
(`logs/runs/pf2_clean_rebuild.txt`, `logs/runs/pf2_binaries_diff.txt`):
four of the five shipped binaries are byte-identical to the previous
session's build; only `stage1_vm` moved, and only because of the audit fix
(D74):
```
unchanged  stage0_start  ebce5c7f9012021ab6de1d770f28bf34f938ac11d38fb99022082899042766b9
CHANGED    stage1_vm     5574b14a3e9ccb9b1b55abef422eb0d52c3b565bb942d6e674b3b3389cbc5752
                        -> 53f891d669b2475305aef929c7ec7d9c3c73f9ab73ffdab0bf0a19bacd4fdc13
unchanged  stage2_stego  64e9d123b52082fd56e8612f712efdef70f7e7b743032418f27e69b27bbc1a73
unchanged  oracle        2bc24a4a70fd4b22d6962aabd820b1255f793b37b47b6c9ed998ceaf07a3ab8e
unchanged  validate      4715ee4633cdb4614fa8860a12ee6a275a914c919e25e2d6cf22783a3090e637
```

(g) The anti-automation trap at the new call volume (D76): a full-budget
machine-uniform scripted collection (4160 calls, fixed 0.1 s spacing) yields
ring stddev 0.82 ms and a dataset the reference attack cannot converge on at
all — `logs/runs/pf2_poison_volume.txt`.

## 6. Section-2 audit — every file, findings and dispositions

Method: `grep -rn` sweeps per bug class across the whole tree first (unchecked
`malloc/fopen/fread/fwrite/open/read/write`; `strcpy/strcat/sprintf/memcpy/
strlen`; `printf`-family with non-literal formats; `getenv/#ifdef/#if`;
`TODO/FIXME/debug`; `argv/argc`; `eval/exec/shell=True/rm -rf`), then every
hit read individually; every shipped .c/.h read end to end; cppcheck
`--enable=all --inconclusive --std=c11 --force` over all ten shipped
translation units as the automated pass (logs/runs/pf2_cppcheck.txt, 185 lines).

Findings that were real and are FIXED:

1. `src/stage1_vm/vm.c` — out-of-bounds read: `vm_decode()` may read up to 9
   bytes at an `ip` within 8 bytes of the end of the 1024-byte image (D74).
   Fixed with an 8-byte pad; stage1_vm rebuilt; every suite re-run.

Findings examined and NOT defects (with the reason, so nothing is silently
ignored):

- `src/stage2_stego/s2_inflate.c:168` (cppcheck: "`idx<0` is always false") —
  true, and deliberate: `sym` is already known >= 257 there, the test is
  defence in depth on the decoder's only untrusted index. Left as is.
- `src/stage4_assembly/validate.c:145` (cppcheck inconclusive: bitwise on
  booleans) — deliberate constant-time style (D40): `eq & len_ok & (argc==2)`
  must not short-circuit. The suite asserts the byte-identical refusal.
- `src/state/state_policy.c` "function never used" x5 — the selftests and
  accessors are the library's public API, consumed by `test_state` and the
  stage binaries; cppcheck only sees one translation unit.
- cppcheck "Include file not found" for the standard headers — informational;
  the headers come from the compiler and musl. No action.
- `src/state/carto_sha256.c:116` `malloc(64+msg_len)` — msg_len is bounded by
  the callers (state file 320 B, reading <= 512 B, argv <= MAX_ARG_STRLEN), so
  the addition cannot wrap; on failure the HMAC returns a fixed all-zero mac,
  which the state load treats as tampered (fail-closed), never as valid.
- `src/state/state_core.c` `carto_state_save` — `malloc` checked, `.tmp` +
  `rename` atomic, `fwrite` result compared to the full size before the swap,
  `.tmp` removed on failure.
- `src/state/state_core.c` `carto_state_load` — reads exactly 352 bytes and
  demands EOF after them (truncation and extension both detected), verifies
  magic + version + HMAC, and `deserialize` re-validates flags, reserved
  bytes, ring_count and ring_head range before use. Every index into the ring
  is therefore bounded.
- `src/stage2_stego/stage2_stego.c` — every fixed buffer that receives
  variable-length input is length-checked before use: `verdict()` copies into
  `claim[CLAIM_MAX+1]` only under `len <= CLAIM_MAX`; `load_mark()` bounds the
  hex path with `n > cap`; `read_file()` caps at FILE_MAX; `press_mode()`
  checks `framed + 2 > ink_len` before slicing; `mint_token` writes exactly
  TOKEN_LEN into a TOKEN_LEN buffer.
- `src/stage2_stego/s2_inflate.c` — the RFC 1951 tables are indexed only
  after range checks (`idx >= 29`, `dsym >= 30`), the repeat loop is bounded
  by `n + rep > hlit + hdist`, distances are bounded by `win_len`, the
  history window is a ring with mask arithmetic, `s2_put` bounds the output
  against `out_cap`, and the trailing adler32 read is bounds-checked.
- `src/stage1_vm/stage1_vm.c` — `tracer_pid_from_proc` uses
  `fgets(line, sizeof line, f)` with a 256-byte line and `strtol`; the token
  compare is length-gated before `memcmp`; the decoy key is wiped after use.
- `src/stage3_oracle/oracle.c` — the reading is refused above
  `READING_MAX=512` with a spoken refusal (never an error); `buf[32 +
  READING_MAX]` cannot overflow; the figure parse requires exactly 16 hex
  letters before shifting; the key material is memset after use.
- `src/state/state_policy.c` — `carto_timing_stddev_ms` bounds every index by
  `ring_count <= CARTO_RING_SIZE` (validated on load) and clamps negative
  clock glitches to 0; the test-scale hook is entirely inside `#ifdef`.
- Format strings: no `printf`-family call anywhere in shipped code takes a
  non-literal format (the sweep returns zero hits outside the test suites);
  solver-supplied strings are always passed as `%s` arguments.
- Hidden flags: the whole-tree `getenv`/`#ifdef` sweep returns exactly one
  runtime env read in shipped code — `CARTO_TEST_TIME_SCALE` inside
  `#ifdef CARTO_TEST_TIME_SCALE_ENABLE` (state_policy.c) — plus the build-time
  `CARTO_TEST_BUILD=1` Makefile switch. No second debug hook exists. The
  shipped binaries' `.rodata` is audited for the name by the adversarial
  suite (section 1) and by the isolated-package check.
- Leftover `TODO/FIXME/debug`: zero hits in shipped sources; the word "debug"
  appears only in the intentional decoy framing ("forgotten debug checkpoint")
  and in the state field name `debugger_detected`.
- Stage-to-stage input-validation consistency: all five binaries follow the
  same discipline (a wrong input is never an error: it is refused with a
  spoken, non-diagnosing message, rc 0, silent stderr). Stage 1 gates its
  token compare on length, Stage 2 gates its decoy copy on `CLAIM_MAX`, and
  Stage 3 gates its reading at `READING_MAX`; the Stage-3 cap is the only
  *stated* cap because it is the only stage that holds its input in a fixed
  buffer. Verified consistent rather than assumed.

Internal tooling (`src/final/*`, the generators, the suites) was swept with
the same patterns: no `eval`/`exec` outside the adversarial suite's own
state-mutation helper (`tamper_case`, which executes a python snippet against
the state file by design), no `shell=True`, and no unquoted `rm -rf`
variables. The generators' `print` calls are build-time progress output and
reach no shipped artifact.

## 7. Bugs found and fixed DURING Phase FINAL-2

1. `vm.c` decode over-read (D74) — the phase's only shipped-source defect.
2. `trial_attack.py` harness: the first real-binary sweep ran with the poison
   floor unscaled against scaled pacing (D75) — a harness defect, caught
   because the harness re-verifies its data; fixed by exporting the env var
   and by adding the per-trial dataset assertion.
3. `trial_attack.py --one-trial` argument plumbing passed one token too many,
   so the first sweep's children all aborted (argparse error). Caught by the
   report showing 0 successes at 0.0 s/trial; fixed.
4. `cartosolve.parse_pace` rejected an already-parsed plan tuple, which killed
   both confirmation runs at the first collection step (ValueError). Caught
   from the runs' `.stdout` tracebacks; fixed, then the driver was
   smoke-tested end to end before relaunch.
5. Launching background runs from the Windows shell needs absolute paths for
   their redirects: the launcher shell's cwd is not the repo, so a relative
   redirect silently aborted one launch (no traceback anywhere). Recorded
   here because it is exactly the kind of failure that looks like a hang.

## 8. Explicitly NOT done / deferred

- No change to the cipher, the fold tables, the decoys, the carriers, or the
  state-library policy: the pacing problem was solved on the sample size, as
  the previous session's own open question said it should be.
- The reference attack is deliberately left as the naive per-byte score-vote
  plus exhaustive verification. A candidate-enumeration resolver would cut
  the 1.3% single-pass failure further at zero query cost, but it would also
  blur the documented "mixed dataset fails to converge" property, so it is
  recorded as an option, not shipped.
- The 107-check adversarial suite count is unchanged: the new stage-3 attack
  check lives in the stage-3 suite (33 -> 34 checks), not in the adversarial
  suite.

## 9. Open questions / judgement calls for any future session

1. If the 165-min ceiling is ever hardened further, the next lever is the
   candidate-enumeration resolver (section 8), not the pacing.
2. The fast edge is defined here as "stddev ~1.9x the floor". A more
   aggressive definition (1.1x) also works but leaves no room for a slow
   machine; the floor comparison happens per query, so a burst of fast deltas
   can momentarily pull the ring stddev near it.
3. The repo's WSL working tree was deleted at the end of this phase after the
   archive was verified; the archive in `D:\gandu\wsl-archive\` is the only
   copy of the full build history (see section 10).

## 10. Archive and deletion record

After both Windows folders were rebuilt and hash-verified in place, the WSL
working tree was archived and deleted — in that order, with the verification
between:

1. `bash pf2_archive.sh` creates
   `/tmp/cartographer-build-archive-<UTC timestamp>.zip` from
   `/home/manish/cartographer-build` (whole tree, `.git` history included).
2. It extracts the archive to `/tmp/pf2_archive_check` and refuses to proceed
   unless **every** check passes:
   * file count identical (live vs extracted, `.git` included);
   * manifest diff identical (every path and every size);
   * **full sha256 comparison of every file** — no sampling;
   * `.git log` readable from the extracted copy with the same commit count;
   * `git fsck` clean on the extracted copy.
3. Only then `rm -rf /home/manish/cartographer-build`, followed by a
   post-condition check that the path is really gone.
4. The zip is moved to `D:\gandu\wsl-archive\` and its sha256 is written to a
   `.sha256` sidecar file beside it (the sidecar cannot live inside the
   archive, since it hashes the archive).

The verification output is in `logs/runs/pf2_archive.txt`; the authoritative
hash is in `D:\gandu\wsl-archive\cartographer-build-archive-<timestamp>.zip.sha256`
and is quoted in the Phase FINAL-2 report. The three remaining copies of this
project are: that archive, `D:\gandu\drive-upload\`, and
`D:\gandu\organizer-private\`.
