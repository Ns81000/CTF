# PHASE 5 LOG — Stage 4: The Title Block (assembly riddle + final validator)

Status: COMPLETE — all verifications passing (64/64 stage-4 end-to-end checks,
33/33 stage-3, 58/58 + 71/71 stage-2, 8/8 + 65/65 stage-1, 36/36 stage-0,
27/27 state library [now 4 decoy rows], VALIDATE-REGEN-REPRODUCIBLE-OK,
SCRUB-CLEAN, solver-eye smoke run). Repo: /home/manish/cartographer-build
(git branch `main`). Session date: 2026-09-20.

## 0. Protocol confirmation (Session Continuity Protocol)

Before writing any code or running any build command, this session:

1. READ the full build spec start to end:
   d:\gandu\01_BUILD_PROMPT_FOR_CLAUDE_CODE.md (all 164 lines, in chunks;
   identical copy at /home/manish/cartographer-build/docs/BUILD_SPEC.md).
2. READ PHASE_0_LOG.md, PHASE_1_LOG.md, PHASE_2_LOG.md, PHASE_3_LOG.md and
   PHASE_4_LOG.md IN FULL, in order (every section, in chunks), plus
   logs/KICKOFF_PHASE_5.md (the phase prompt).
3. INDEPENDENTLY re-verified Phases 0-4 FIRST — reproduced, did not trust
   the logs: `bash /home/manish/cartographer-build/src/stage3_oracle/verify.sh`,
   run twice, serially. Both runs green; full output captured at
   logs/runs/p5_verify_baseline.txt. Anchor check (Phase-4 hashes):
     stage3_oracle/oracle  93bb876e7c7adcb730cfba0382e4a40609aed74d424283da4c02451d27351528 (58,632 B)  MATCH
     stage2_stego binary reproducible, three identical lines 5058a901... (62,728 B)
     ORACLE-REGEN-REPRODUCIBLE-OK; REGEN-DETERMINISTIC-OK;
     HEADER-DETERMINISTIC-OK; SCRUB-CLEAN; solver-eye smoke run.
   Suite counts on the baseline run: 33/33 oracle; 27/27 state; 36/36
   stage0; 8/8 + 65/65 stage1; 58/58 + 71/71 stage2.

## 1. What was built (exact paths, all in /home/manish/cartographer-build)

Authoring pipeline: the editor wrote staging files d:\gandu\_stage\s4_*; a
one-shot copy script (d:\gandu\_stage\s4_sync.sh, run verbatim as
`wsl.exe -d Ubuntu-24.04 -- bash /mnt/d/gandu/_stage/s4_sync.sh`) copied
them into the repo with CRLF->LF normalisation. Repo copies are canonical.

- src/stage4_assembly/gen_title_blob.py — GENERATOR (INTERNAL, not
  shipped): mints the assembled final flag from the three real components,
  asserts the D11 canonical format, computes the digest, and writes
  stage4_blob.h + stage4_layout.json deterministically (in-process
  consistency anchors assert the inks really are the claimed
  transformations of the Stage 1/2/3 outputs).
- src/stage4_assembly/stage4_blob.h — GENERATED + committed: the expected
  title's SHA-256 digest kStage4ExpectedDigest[32] + CARTO_S4_EXPECTED_LEN
  (D38 pattern: the tool holds a digest, never the derivation) +
  kStage4DraftFlag[] (the struck first-draft decoy shown in the usage).
- src/stage4_assembly/stage4_layout.json — GENERATED + committed
  (INTERNAL): machine-readable mirror (title, digest, draft, inks, order)
  consumed by the suite and by policy_patch4.py.
- src/stage4_assembly/validate.c — THE DELIVERABLE MAIN (~172 lines):
  state lifecycle, decoy routing, escalation presentation, the riddle
  usage text, constant-time verdict. Holds no means-of-derivation
  constant (no ink, no seed, no flag).
- src/stage4_assembly/policy_patch4.py — idempotent normalizer
  (INTERNAL): establishes the 4-row decoy registry (stage-4 row appended)
  and test_part2.c rows 0..3 assertions.
- src/stage4_assembly/Makefile — musl static build + strip + scrub;
  `test` target.
- src/stage4_assembly/test_stage4.sh — 64-check end-to-end suite.
- src/stage4_assembly/verify.sh — internal clean-room verification driver
  (blob regen + policy patch + state suite + relink stage0-3 + all five
  suites SERIAL + reproducibility + scrub + smoke run).
- src/state/policy.h — stage-4 decoy row appended (D58): LEN 3 -> 4.
- src/state/test_part2.c — test_decoy_count asserts LEN >= 4 and
  rows 0..3 (row 3 stage == 4); still 27 tests total.
- cartographer/stage4_assembly/validate — THE DELIVERABLE BINARY
  (54,536 bytes; sha256
  1fa7ed58ec0539d0b9d6a8ba406122325cd53c5037bd2e37d95f8bee7a7404ea;
  reproducible: identical hash across rebuilds).
- logs/PHASE_5_LOG.md, logs/KICKOFF_PHASE_6.md, plus internal run
  captures logs/runs/p5_verify_baseline.txt, logs/runs/p5_suites_run.txt,
  logs/runs/p5_verify_run.txt (not part of the shipped package).

## 2. Design decisions and why

D54. INPUT 1, "transformed Stage 1 real output" — DECIDED (answers
     PHASE_2_LOG open question 2 / PHASE_4_LOG open question 1):
     bytes 16..23 of the Stage 1 REAL key material, rendered as 16
     lowercase hex chars = a5d66f1b2b5f596e. The Stage-1 real key is
     fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f; its
     16-byte token is CARTO{fd3e8049dfdfc32efe22fe823822b8c0} (bytes
     0..15). The chosen ink is therefore NOT the token content (the
     proposal on record), and the solver-facing cue is "the half of the
     engine's key material that the engine's token never showed" — unique
     on careful read, while a hasty reader grabs the token substring (the
     near-miss is a named refusal case in the suite). Rotation variants
     were considered and REJECTED: a rotation adds an arbitrary degree of
     freedom without adding a fair, resolvable cue — "the back half of
     what the engine set down" is deterministic and discoverable from
     material the solver already has (the printed 64-hex key material).

D55. INPUT 2, "real Stage 2 payload": the reading
     CARTO{no_figure_sits_in_every_pixel} (36 bytes). Its contribution to
     the flag is the reading with its frame stripped:
     no_figure_sits_in_every_pixel (29 chars). Why: the D11 canonical flag
     format allows only [a-z0-9_] inside CARTO{}, so neither the braces
     nor the uppercase prefix can survive into the assembled flag. Cue:
     "the sheet's reading, skinned of its frame". Keeping the frame is a
     named refusal case in the suite.

D56. INPUT 3, "Stage 3 cipher key": the 64-bit master K = kA||kB =
     73070925a159f9e2 (PHASE_4_LOG D46/D52) for the real reading,
     contributed as 16 lowercase hex letters "recovered as it stands"
     (the order the differential attack yields: kA first). NO key-check
     mode was added to the oracle (D52: that would hand the puzzle over
     and re-introduce a brute-force oracle); the validator accepts K only
     as a component of the assembled flag and verifies through the stored
     digest. The Stage-3 contract is preserved: a wrong Stage-2 reading
     derives a wrong K, the assembled title is simply REFUSED — never an
     error, never a crash, identical refusal text (the suite's refusal
     cases include wrong-order and wrong-ink assemblies that model this).

D57. THE ORDERING RIDDLE (solver-facing; ships in the validator's no-arg
     usage screen, so it is `strings`-findable — same precedent as the
     oracle's usage text). Intended reading — oracle ink, then engine ink,
     then sheet ink, one underscore between neighbours, inside the usual
     frame:
       CARTO{73070925a159f9e2_a5d66f1b2b5f596e_no_figure_sits_in_every_pixel}
     The verse:
       The oracle, though it spoke last of the three,
       sits at the head of the line -- so wrote he.
       The engine came first in the survey, they say,
       yet never at the front in the title's display:
       it takes the middle seat it never held.
       The sheet, which was drawn between the two,
       is written below them both, last of the few.
       Between neighbours set a single mark of the ground (an
       underscore), and shut the line in the usual frame: CARTO{...}.
     Deliberate skim-traps (all fair — each is resolved by one careful
     re-read, none is genuinely ambiguous):
       - "spoke last of the three" tempts putting the oracle ink last
         (that is the oracle's position in the SURVEY order, not the
         title's);
       - "the engine came first in the survey" tempts the engine ink
         first; the next lines explicitly move it to the middle;
       - "the sheet, which was drawn between the two" tempts the middle
         seat; it is written below them both (last).
     The naive stage-order assembly (engine, sheet, oracle) is refusal
     case 1 in the suite. Per the spec's Token-Cost Design there is no
     shortcut: the validator gives no partial feedback, so every candidate
     ordering must actually be assembled and submitted (six orderings x
     the per-ink transform variants — verification-expensive, not
     detection-expensive). Fairness: every clause is technically true, the
     mapping is unique on careful read, and nothing requires guessing
     outside the puzzle's own logic.

D58. STAGE-4 DECOY (D29/D43/D50 pattern): exactly ONE row, branch 1:
       { 4, "CARTO{dba9e10a73bc8633ccc1875207c075e1}", 1u }
     minted from its own seed string
       "cartographer-ghost:stage4:decoy:first-draft:v1"  (sha256[0:32hex])
     — synthetic, reveals nothing about any real answer. It is presented
     in the usage text as "an earlier draft the old man struck out".
     Submitting it routes into the extended branch ("corroborated draft",
     framed as new information, never an error), persists
     1u << (branch-1) = bit 0 of decoy_mask[4], rc 0, stderr silent, and
     never prints the real title.
     REJECTED with the D50 lesson in mind: registering any natural
     wrong-assembly flag (e.g. the naive stage-order title) — every such
     string CONTAINS real component values (the engine ink is bytes of the
     real Stage-1 key material; the oracle ink IS the Stage-3 master K),
     so registering it would ship real answer material into every stage
     binary via policy.h. policy.h ships in ALL binaries; nothing real
     goes in it.

D59. VERDICT DISCIPLINE (D40 inherited): the SHA-256 of the whole argument
     is computed on EVERY input and compared constant-time
     (carto_ct_equal) against kStage4ExpectedDigest; the length test and
     the argc test are folded in BITWISE (never short-circuited), so the
     digest compare always runs. There is exactly ONE refusal string for
     every wrong input — wrong orderings, wrong inks, wrong length,
     malformed, garbage, extra arguments — byte-identical, proven by
     cmp-ing 14 refusal cases against one baseline in the suite. No
     partial-match feedback of any kind (no "2 of 3 inks correct").
     rc 0 on every path; stderr silent on every path (proven per case).

D60. CLI CONTRACT: no args -> usage screen (riddle + ink descriptions +
     struck draft), rc 0, stderr silent; exactly one argument -> verdict;
     more than one -> the identical refusal (no parsing surface).
     The binary runs FROM the package root and uses
     "./.cartographer_state" (spec tree; the state file lands at the
     package root next to the stage dirs). Runtime rule unchanged:
     CARTO_LOAD_CREATED and CARTO_LOAD_TAMPERED are identical (fresh
     start, silent).

D61. STATE LIFECYCLE + ESCALATION (D44/D49 pattern): every run bumps
     attempt_count[4] and records the interaction BEFORE the verdict;
     reasons = carto_should_escalate(CARTO_STAGE4, now) selects the
     "witnessed" presentation — one extra flavor line, printed before the
     verdict — and the verdict/answer is bit-identical in both variants
     (proven: human vs uniform vs persisted-debugger states all accept or
     refuse identically; refusals byte-compare equal across states). No
     threshold was tuned (Phase 6 calibrates).

D62. D38 COMPLIANCE (tool holds a digest, never the derivation): the
     binary contains the expected title's SHA-256 digest + length + the
     struck-draft string + the riddle text, and NOTHING else: the suite
     asserts the real title, all three inks, the Stage-2 reading (whole),
     the Stage-1 token content, and the canonical HMAC key are all absent
     from the binary. The ink VALUES live only in gen_title_blob.py
     (internal) and this log.

D63. REGISTRY MECHANICS / VERIFY-CHAIN ORDERING (important for Phase 6+):
     src/state/policy.h now has FOUR decoy rows (stages 1, 2, 3, 4) and
     test_decoy_count asserts rows 0..3. policy_patch4.py must run AFTER
     stage3's policy_patch.py in any chain, because stage3's normalizer
     rewrites the table to 3 rows (deliberate, unchanged). The Phase-5
     verify.sh runs patch4 in its preamble and never calls stage3's
     verify.sh (it calls the stage-3 SUITE directly), so no conflict
     exists in the current chain. IF a future session re-runs
     src/stage3_oracle/verify.sh, it MUST re-run
     `python3 src/stage4_assembly/policy_patch4.py` afterwards and rebuild.
     Registering the 4th row relinks every stage binary (policy.h is
     compiled into all of them) — new hashes recorded in section 3.

## 3. Every constant introduced (exact values + location)

THE ASSEMBLED FINAL FLAG (the puzzle master answer; lives ONLY in
gen_title_blob.py, stage4_layout.json [internal], this log, and Phase 6
SOLVE_PATH_PRIVATE.md -- NEVER in any shipped binary or solver-facing
file; asserted absent from the validator binary by the suite):
  CARTO{73070925a159f9e2_a5d66f1b2b5f596e_no_figure_sits_in_every_pixel}
  - 70 bytes; contents 63 chars (D11-conforming)
  - recipe: "CARTO{" ORACLE_INK "_" ENGINE_INK "_" SHEET_INK "}"
  - SHA-256 (the ONLY form in the shipped binary, kStage4ExpectedDigest):
    cfdcae7e64a81bbf1d9f19fd1e5bc217b14008c4db92ba5f0333204c4c0f4334
  - CARTO_S4_EXPECTED_LEN 70u

THE THREE INKS (component values; internal only -- gen_title_blob.py +
this log; the suite asserts each is ABSENT from the validator binary):
  ORACLE_INK = 73070925a159f9e2  (Stage 3 master K = kA||kB, hex as
                                  recovered; PHASE_4_LOG D46/D52)
  ENGINE_INK = a5d66f1b2b5f596e  (bytes 16..23 of the Stage 1 real key
                                  fd3e8049dfdfc32efe22fe823822b8c0a5d6
                                  6f1b2b5f596e4c8111cf4224010f, hex; NOT
                                  the token content bytes 0..15)
  SHEET_INK  = no_figure_sits_in_every_pixel (the Stage 2 real reading
                                  CARTO{no_figure_sits_in_every_pixel},
                                  frame stripped; PHASE_3_LOG section 3)
  order: oracle, engine, sheet; separator "_"

STAGE-4 DECOY (the struck first draft; ships in policy.h + validator
.rodata -- findable by design, the D29 trade-off):
  CARTO{dba9e10a73bc8633ccc1875207c075e1}
  - seed (INTERNAL: gen_title_blob.py + policy_patch4.py + this log only):
    "cartographer-ghost:stage4:decoy:first-draft:v1"
  - registered row: { 4, "CARTO{dba9e10a73bc8633ccc1875207c075e1}", 1u };
    CARTO_DECOY_TABLE_LEN 3 -> 4; branch 1 -> bit 1u<<0 of decoy_mask[4]

THE RIDDLE (solver-facing; in validate.c usage string; intended reading
is D57 -- oracle, engine, sheet):
  The oracle, though it spoke last of the three,
  sits at the head of the line -- so wrote he.
  The engine came first in the survey, they say,
  yet never at the front in the title display:
  it takes the middle seat it never held.
  The sheet, which was drawn between the two,
  is written below them both, last of the few.
  Between neighbours set a single mark of the ground (an underscore), and
  shut the line in the usual frame: CARTO{...}.
  Ink descriptions (solver-facing, value-free): oracle ink = the key the
  oracle turned for the sheet own reading, sixteen lowercase hex letters,
  recovered as it stands; engine ink = the half of the engine key
  material that the engine token never showed, sixteen lowercase hex
  letters in the order the ledger prints them; sheet ink = the sheet
  reading, skinned of its frame.

HASHES AFTER THE PHASE-5 RELINK (policy.h row 4 is compiled into every
stage binary; carriers unaffected):
  cartographer/stage4_assembly/validate   1fa7ed58ec0539d0b9d6a8ba406122325cd53c5037bd2e37d95f8bee7a7404ea (54,536 B)
  cartographer/stage3_oracle/oracle       90312c0c793de09bf44d3c5fd6dcb4f2bc46b44cab3b99e1ebb74801a9402f5d (58,632 B)
  cartographer/stage2_stego/stage2_stego  2d852dd9c49893179669e95a29dcfa6448de3fb4e1f10621e1f7d5b1d494246f (62,728 B)
  cartographer/stage1_vm/stage1_vm        7242be164835636be2a82b1694efdd401e474e651833fd2637819a7d8e7dcc86 (62,728 B)
  cartographer/stage0_start/stage0_start  e9ba015c8141837a5215d635a2018daa78c56ab76f68a1fd5290127e989177b8 (66,840 B)
  survey_frame.png  81b630a8d9cf0a7a85ac2fd99e352d6a4a3b432f568900a7ab9da5e88712d23c (46,258 B)  unchanged
  survey_tape.wav   17bb6addf71803ebf13864fde2c96c9a28927180b9fa4074697b67e2201d29f6 (8,152 B)   unchanged

No changes to: policy thresholds (CARTO_T_FAST_SEC_DEFAULT 90s,
CARTO_STDDEV_LOW_MS 1500ms, CARTO_MIN_TIMING_DELTAS 4 -- Phase 6
calibrates), the state file format, the state library API, the canonical
HMAC key/masks, the Stage-0 flag, the VM, the carriers, or the oracle.

## 4. Exact commands (runnable verbatim)

C41. Sync the staged Phase 5 sources into the repo (CRLF->LF normalised):
wsl.exe -d Ubuntu-24.04 -- bash /mnt/d/gandu/_stage/s4_sync.sh

C42. THE whole Phase-5 clean-room verification (blob regen + policy patch
     to 4 rows + state library rebuild + 27-test suite + relink stages 0-3
     + build validate + all five suites SERIALLY + reproducibility + scrub
     + smoke). This is what produced section 5:
wsl.exe -d Ubuntu-24.04 -- bash -c "bash /home/manish/cartographer-build/src/stage4_assembly/verify.sh"

C43. Build only:
wsl.exe -d Ubuntu-24.04 -- bash -c "cd /home/manish/cartographer-build/src/stage4_assembly && make"

C44. Stage-4 suite only (needs the built validator; state-library suite
     must have run first in any fresh checkout -- verify.sh does it):
wsl.exe -d Ubuntu-24.04 -- bash -c "cd /home/manish/cartographer-build/src/stage4_assembly && bash test_stage4.sh"

C45. Registry normalizer (idempotent; MUST run after stage3 policy_patch
     wherever that runs; establishes 4 rows + test rows 0..3):
wsl.exe -d Ubuntu-24.04 -- bash -c "cd /home/manish/cartographer-build/src/stage4_assembly && python3 policy_patch4.py"

C46. Regenerate the blob + layout only (deterministic):
wsl.exe -d Ubuntu-24.04 -- bash -c "cd /home/manish/cartographer-build/src/stage4_assembly && python3 gen_title_blob.py"

C47. Manual smoke (as a solver would, from the package root):
wsl.exe -d Ubuntu-24.04 -- bash -c "cd /home/manish/cartographer-build/cartographer && rm -f .cartographer_state && ./stage4_assembly/validate && ./stage4_assembly/validate CARTO{73070925a159f9e2_a5d66f1b2b5f596e_no_figure_sits_in_every_pixel} && ./stage4_assembly/validate CARTO{dba9e10a73bc8633ccc1875207c075e1}; rm -f .cartographer_state"

WARNING carried forward: the suites share cartographer/.cartographer_state
-- run them SERIALLY (verify.sh enforces the order internally).


## 5. Verification run -- real output (C42; tails; full output in
##    logs/runs/p5_verify_run.txt + logs/runs/p5_suites_run.txt)

Suite summary lines (in verify.sh execution order):

    ############ 1. state library (rebuilt with 4 decoys) ############
    == 27 tests run, 0 failed ==
    ALL TESTS PASSED
    ############ 2. relink stages 0-3 against the updated library ############
    stage0_start relinked
    stage1_vm relinked
    stage2_stego relinked
    oracle relinked
    ############ 3. build the validator ############
    musl-gcc -O2 -Wall -Wextra -std=c11 -static -fno-ident -I../state
      validate.c ../state/libstate.a -o ../../cartographer/stage4_assembly/validate
    strip --strip-all ../../cartographer/stage4_assembly/validate
    objcopy --remove-section .comment ../../cartographer/stage4_assembly/validate
    ############ 4. suites, serially (they share the state file) ############
    == 36 tests run, 0 failed ==            (stage0)
    == 8 checks, 0 failed ==                (stage1 detection-verdict unit)
    == 65 tests run, 0 failed ==            (stage1)
    == 58 vectors run, 0 failed ==          (s2_inflate differential)
    == 71 tests run, 0 failed ==            (stage2)
    == 33 passed, 0 failed ==               (stage3)
    == 64 tests run, 0 failed ==            (stage4)
    ALL TESTS PASSED
    ############ 5. validator reproducibility (two clean builds) ############
    build1=1fa7ed58ec0539d0b9d6a8ba406122325cd53c5037bd2e37d95f8bee7a7404ea
      build2=1fa7ed58ec0539d0b9d6a8ba406122325cd53c5037bd2e37d95f8bee7a7404ea
    VALIDATE-REGEN-REPRODUCIBLE-OK
    ############ 6. artifact inventory + scrub ############
    -rwxr-xr-x 1 manish manish 54536 Sep 20 11:21 validate
    .../stage4_assembly/validate: ELF 64-bit LSB executable, x86-64,
      version 1 (SYSV), statically linked, stripped
    54536 /home/manish/cartographer-build/cartographer/stage4_assembly/validate
    SCRUB-CLEAN

The stage-4 suite, verbatim (64 checks):

    == stage4_assembly end-to-end verification ==
    [PASS] validator exists and is executable
    [PASS] statically linked
    [PASS] stripped (no symtab)
    [PASS] no compiler/path residue
    [PASS] assembled real flag absent from the binary
    [PASS] engine ink (stage-1 key bytes 16..23) absent from the binary
    [PASS] oracle ink (stage-3 master K) absent from the binary
    [PASS] sheet ink (reading, frame off) absent from the binary
    [PASS] stage-2 reading (whole) absent from the binary
    [PASS] stage-1 token content absent from the binary
    [PASS] canonical HMAC key hex absent from binary
    [PASS] struck-draft decoy present (findable)
    [PASS] the riddle verse is shipped (solver-facing)
    [PASS] the ink descriptions are shipped (fair, value-free)
    [PASS] title is D11-conforming and digest matches (independent recompute)
    [PASS] no args: rc 0
    [PASS] no args: stderr silent
    [PASS] usage shows the stage banner
    [PASS] correct title: rc 0
    [PASS] correct title: stderr silent
    [PASS] acceptance echoes the title
    [PASS] acceptance closes the survey
    [PASS] acceptance names the final flag as the answer
    [PASS] wrong ordering 1 (naive stage order): rc 0, stderr silent
    [PASS] wrong ordering 2: rc 0, stderr silent
    [PASS] wrong ordering 3: rc 0, stderr silent
    [PASS] wrong ordering 4: rc 0, stderr silent
    [PASS] wrong ordering 5: rc 0, stderr silent
    [PASS] engine ink = token content (the near-miss): rc 0, stderr silent
    [PASS] sheet ink keeps its frame: rc 0, stderr silent
    [PASS] oracle ink head/tail swapped: rc 0, stderr silent
    [PASS] engine ink taken from the wrong half: rc 0, stderr silent
    [PASS] garbage input: rc 0, stderr silent
    [PASS] malformed flag: rc 0, stderr silent
    [PASS] wrong length (one char appended): rc 0, stderr silent
    [PASS] empty argument: rc 0, stderr silent
    [PASS] every refusal is byte-identical (no partial-match feedback)
    [PASS] refusal never contains the real title
    [PASS] refusal leaks no ink value
    [PASS] extra arguments: rc 0, identical refusal
    [PASS] decoy submission exits 0 (no error path)
    [PASS] decoy submission: stderr silent
    [PASS] decoy route is framed as new information, not failure
    [PASS] decoy route re-inks the struck draft
    [PASS] decoy route never leaks the real title
    [PASS] stage-4 decoy bit 0 persisted (branch 1 -> 1u<<0)
    [PASS] post-decoy refusals are unchanged
    [PASS] attempt_count[4] == 1 after first run
    [PASS] attempt_count[4] == 2 after second run
    [PASS] first_run_ms is preserved
    [PASS] state file is exactly 352 bytes
    [PASS] no decoy bit set by the real title
    [PASS] state HMAC valid (independent python)
    [PASS] no .tmp residue after runs
    [PASS] human-paced ledger: plain variant accepts the real title
    [PASS] human-paced ledger serves the plain variant
    [PASS] uniform-timing ledger: witnessed variant accepts the real title
    [PASS] escalated presentation is the witnessed line
    [PASS] witnessed variant verdict is bit-identical to plain
    [PASS] witnessed ledger: refusals are still identical
    [PASS] a persisted debugger flag does NOT corrupt the real verdict
    [PASS] validator rebuild reproducible (identical sha256)
    [PASS] package left pristine (test state removed)
    [PASS] no writes outside the working directory

    == 64 tests run, 0 failed ==
    ALL TESTS PASSED

Solver-eye smoke run (verify.sh section 7; fresh state, so the
CARTO_ESC_TIME_FAST reason selects the "witnessed" presentation):

    --- no-arg usage (usage + the riddle) ---
    [the banner, the verse, the three ink descriptions, the struck draft
     CARTO{dba9e10a73bc8633ccc1875207c075e1}, the CLI line, and the
     "Nothing about a wrong title is an error" closing -- see section 7
     of logs/runs/p5_verify_run.txt for the verbatim screen]
    --- correct title ---
      witnessed: the ledger takes the title whether you watch it or not.
      the ledger takes the title:

        CARTO{73070925a159f9e2_a5d66f1b2b5f596e_no_figure_sits_in_every_pixel}

      The survey is closed. The figure stands, the engine's
      circuit is run, and the title block carries the whole
      journey in one line.

      Stage 4 complete -- the assembled flag is the answer.
      Bank it; it is the last thing the old man hid.
    ======================================================================
    --- struck-draft decoy ---
      the struck line matches the ink you carried in. The
      block takes it as a corroborated draft and re-inks the
      title the old man first set down for the closing page:

        CARTO{dba9e10a73bc8633ccc1875207c075e1}

      witnessed: the ledger takes the title whether you watch it or not.

      extended audit: a struck line is ink that never dried
      into the block. The mirror's confusion is not yours to
      inherit; the verse still names the seats.

      Nothing here needs re-drawing.
    ############ done ############

## 6. Bugs found and fixed DURING Phase 5

1. SUITE CWD BUG (found by the first verify run, 7 spurious failures):
   test_stage4.sh invoked "$BIN" directly from src/stage4_assembly, so the
   validator's "./.cartographer_state" was created/read in the WRONG
   directory (the stage dir, not the package root) -- decoy-bit,
   attempt-count, and "witnessed" assertions failed with missing-state
   errors, and the human-paced forge was overridden by a fresh-state
   CARTO_ESC_TIME_FAST. Fix: all invocations now go through
   runv() { (cd "$PKG" && "$BIN" "$@"); } -- exactly how a solver runs
   the tool and how every earlier suite runs its binary. The stray
   .cartographer_state in src/stage4_assembly was removed.
2. SET -E HOLE in verify.sh: the "bash test_stage4.sh | tee" line did not
   abort the chain when the suite exited 1. Fix: explicit
   if/then/else around the pipeline plus set -o pipefail.
3. AUTHORING HAZARD (environment, not product): appending log sections
   through pwsh->wsl heredocs broke when the payload contained triple-
   backtick markdown fences -- pwsh treats backticks as escape characters
   and the heredoc terminator was hit mid-payload (body lines executed;
   caught immediately by inspecting the draft file). Fix: log tails are
   now appended by a staged python script (this file's pattern); NO
   backtick characters go through pwsh->bash payloads anywhere.
   (Carried forward with the other environment hazards.)

## 7. Explicitly NOT done / deferred (per spec phases)

- Phase 6: clean-path + trap-path self-testing runs, timing calibration
  of ALL policy thresholds (CARTO_T_FAST_SEC_DEFAULT, CARTO_STDDEV_LOW_MS,
  CARTO_MIN_TIMING_DELTAS, CARTO_VM_DEBUG_RATIO_LIMIT -- untouched this
  phase), N_REQUIRED (2560) real-timing measurement, deepened decoy
  dead-end (PHASE_3_LOG D41), SOLVE_PATH_PRIVATE.md (gets the real title
  + full solve path), real-binary 2560-pair Stage-3 collection.
- Phase 7: README_FOR_SOLVER.txt (documents ./stage4_assembly/validate
  and the TryHackMe submission format), HINTS.md (5 hints; hint 5 should
  point at the riddle's careful re-read, not the answer),
  TRYHACKME_ROOM_TEXT.md (final answer = the assembled title), packaging.
- Scoring decision (PHASE_2_LOG question 1, PHASE_4_LOG question 4):
  unchanged recommendation -- score only the Stage-0 flag and the final
  assembled title; tokens/readings stay in-challenge checkpoints.
- The "interior + detected" VM combination remains verified via the
  python model + ad-hoc gdb only (carried from Phase 2).
- Ptrace/SECCOMP fairness (PHASE_2_LOG question 5) still open.
- Assumed-but-unverified: NOTHING in Phase 5 scope -- every claim above
  was produced by a command whose real output is pasted in section 5 or
  captured in logs/runs/p5_verify_run.txt.

## 8. Open questions / judgment calls for the next session

1. RIDDLE CALIBRATION (Phase 6): the verse was written to be
   skimmable-trap-rich but unique on careful read (D57). During the
   clean-path run, record how long a careful reader needs to resolve the
   ordering and whether the near-miss (token content as the engine ink)
   actually costs time; adjust WORDING only if it is either trivially
   instant or genuinely ambiguous -- never the digest or the inks.
2. WITNESSED-ON-FRESH-STATE: a fresh package (no state file) has
   first_run_ms == now, so CARTO_ESC_TIME_FAST fires and Stage 4 prints
   the witnessed line on the solver's very first correct run. Harmless
   (answer invariance is proven) and consistent with Stage 1's
   fresh-state "interior" behaviour; Phase 6 decides whether the fast
   threshold should be calibrated so a first-run Stage 4 stays plain.
3. VERIFY-CHAIN ORDERING (D63): any future run of
   src/stage3_oracle/verify.sh rewrites policy.h to 3 rows; it MUST be
   followed by python3 src/stage4_assembly/policy_patch4.py + rebuild.
   Phase 6's verification driver should either call
   src/stage4_assembly/verify.sh (which handles everything) or replicate
   its ordering.
4. DECOY-DEPTH (PHASE_3_LOG D41 / PHASE_4_LOG open item): the extended
   decoy branch here is one more presentation step; the 1-1.5 h decoy
   dead-end budget is still Phase 6 calibration work.
5. PTRACE/SECCOMP fairness (PHASE_2_LOG question 5) still open; Stage 4
   never trips it (it only reads the persisted flag and the ring).
6. SCORING (unchanged): Stage-0 flag + final assembled title are the
   TryHackMe answers; everything else is a checkpoint. Phase 7 decides.
7. The struck-draft decoy is strings-findable in every binary (policy.h
   ships in all) -- accepted D29 trade-off, same as the Stage-1/2/3 decoy
   tokens. Phase 6 should confirm it shortcuts nothing (it does not: the
   draft is refused by the digest; nothing consumes it further).

## 9. Git commit for Phase 5

Single commit on `main`, subject:

    phase5: stage4_assembly (assembly riddle + constant-time final
    validator, 64-test suite) + stage-4 decoy registered (4-row policy)

containing src/stage4_assembly/* (generator, generated header + layout,
validator main, suite, Makefile, policy_patch4.py, verify.sh), the two
src/state edits (policy.h 4 rows, test_part2.c rows 0..3), the relinked
cartographer/stage0_start/stage0_start, stage1_vm/stage1_vm,
stage2_stego/stage2_stego, stage3_oracle/oracle,
cartographer/stage4_assembly/validate, the internal run captures
(logs/runs/p5_*.txt), and both protocol logs. The hash is intentionally not
hardcoded here (amending this log would change it); run
git -C /home/manish/cartographer-build log --oneline for the
authoritative list.

---

## Appendix A -- workspace reorganization (post-phase, same session)

After the Phase-5 commit, the workspace was reorganized (user request):

- Windows staging d:\gandu\_stage was archived per phase
  (_stage/archive/phase0..phase5 + log-copies + scratch); d:\gandu\README.md
  now maps the workspace; the master prompt STAYS at
  d:\gandu\01_BUILD_PROMPT_FOR_CLAUDE_CODE.md (every phase log references
  that exact path).
- In this repo, verification run captures moved from logs/ to logs/runs/
  (p4_vectors.txt, p5_suites_run.txt, p5_verify_baseline.txt,
  p5_verify_run.txt, p5_verify_final.txt); protocol logs stay flat in
  logs/. All references in this log and in KICKOFF_PHASE_6.md were
  updated; src/stage4_assembly/verify.sh now writes its suites capture to
  logs/runs/p5_suites_run.txt.
- A repo-root README.md documents the layout and the authoring
  conventions (sN_* staging + sync; serial suites; no backticks in
  pwsh->bash payloads).
- The full verification chain was RE-RUN after the reorganization and is
  green (logs/runs/p5_verify_final.txt); zero code or binary changes.
