# SESSION 1 LOG — The Cartographer's Ghost, v2 (build & audit session)

## 1. Status

`COMPLETE THROUGH P7 — Phases 0-7 green (state 33/33, stage0 33/33, engine 62/62, sheet 73/73, oracle 48/48, seal 53/53, title 53/53, bait 40/40; all suites re-run after the bait landed, counts unchanged). Ready for Phase 8.`

## 2. Environment

- Windows host driving WSL2 `Ubuntu` 24.04.2 LTS, kernel 6.6.87.2, user
  `ns8pc`; privileged work through `wsl.exe -d Ubuntu -u root`.
- Toolchain installed this session (apt): build-essential, musl-tools, zip,
  unzip, gdb, cppcheck, libimage-exiftool-perl, imagemagick, jq, pngcheck,
  python3-pil, python3-numpy. `musl-gcc` 13.3.0, python 3.12.3.
- Repo `/home/ns8pc/ghost-build` (git). Spec in `docs/BUILD_SPEC_V2.md`.
- Suite driver: `src/final/run_suites.sh` (serial; logs to
  `organizer-private/runs/`).

## 3. Per-phase state at audit completion

| Phase | What was built | Suite result |
|---|---|---|
| P0 | repo skeleton, v1-reference core, verbatim spec | n/a |
| P1 | `src/state`: 1168-byte record, 6 stage slots, 64-entry ring (16-byte records), chain digest, HMAC, behaviour statistics, gates, anti-forgery recomputation, masked master; symlink defenses & deduplicating figure counter | 33/33 (`runs/state.log`) |
| P2 | `src/stage0_ledger/ledger`: handshake, the free scored token, canary, field-notes pointer, canonical author notice | 33/33 (`runs/stage0_ledger.log`) |
| P2 | `src/stage1_engine/engine`: 92-opcode VM, encrypted image (nonce keystream), self-modifying code, coast/interior profiles (204953 / 225433 steps, both landing on K_engine), anti-debug (TracerPid + PTRACE), decoy index key with its own bearing, `profile.notes` trap with notice; independent `model_vm.py` reproduces both traces bit-exactly | 62/62 (`runs/stage1_engine.log`) |
| P3 | `src/stage2_sheet`: deterministic carriers (1024x1024 hand-written PNG with graticule+dither, PCM16 tape with the 56-byte press in a `prES` chunk), three lanes (naive decoy row, near-miss lane cut without the press, drawn lane LE16\|\|zlib-with-press), TTY/width/colour traps with `--plain`, press mode, `sweep.py` model, `detect_layer.py` (4 detectors, all fail to localise); strictly validated 1024x1024 frame dimensions, actual tape size passed to `tape_press`, embedded notice in PNG (`tEXt`), WAV (`LIST/INFO/ICMT`), and binary | 73/73 (`runs/stage2_sheet.log`) |
| P4 | `src/stage3_oracle`: 8 fold tables with exactly 64/256 planted affine entries each, 5-round Feistel, masked seed (mask needs the reading), K_real/K_cold branches, 8 answer regimes, tally witness, attack model + collector + seed helper; canonical author notice in binary and usage | 48/48 (`runs/stage3_oracle.log`) |

## 4. Implementation Findings & Resolutions (Audit Baseline)

1. **GATE_CHAIN Ordering & Preceding Stage Check**: `carto_gate_chain` verifies monotonic non-decreasing stage order in ring, verifies stage 0 starts the ring when fits, and confirms all preceding stages up to `max_stage` were visited via ring or `attempt_count`.
2. **Figure Deduplication**: `carto_note_figure` inspects occupied ring entries and rejects duplicate increments for the same figure fingerprint.
3. **Stage 2 Dimension Enforcement**: `frame_dimensions` strictly enforces `w == 1024 && h == 1024`, preventing out-of-bounds reads and malformed dimensions in `gather()`.
4. **Stage 2 Press Tape Size**: `reveal()` stores actual file read size `tape_sz` and passes it to `tape_press()`, avoiding stale or out-of-bounds reads.
5. **Carriers Info Sanitization**: `cartographer/stage2_sheet/carriers_info.json` removed from package to adhere to §3.1 allow-list; generator sanitized to emit only `_notice` and file sha256s with no internal values (`stride`, `start`, `decoy`, `middle_text`).
6. **Notice Layer Implementation**: Canonical `kAgentNotice` embedded in `.rodata` of all binaries (`ledger`, `engine`, `sheet`, `oracle`), displayed on usage screens, embedded in PNG `tEXt` ("Notice"), WAV `LIST/INFO` (`ICMT`), and bait notes (`profile.notes`). Notice text verified clean of test verdict words, mechanism words, and provenance strings.
7. **Repository Cleanliness**: Tracked test binaries (`mkrec`, `test_state`) added to `Makefile` `all` target so they are always present; untracked `.pyc` and `__pycache__` purged; all runs use `PYTHONDONTWRITEBYTECODE=1`.
8. **Cppcheck Zero-Defect**: All cppcheck style/warning findings across all stages fixed or justified/suppressed with `--inline-suppr`. Zero warnings across the codebase.
9. **Malformed CLI Refusal Discipline**: 120/120 matrix tests across all tools confirmed rc 0, 0 bytes written to stderr, and no information leaks.
10. **State File Robustness**: Symlink attacks on `.cartographer_state` and `.cartographer_state.tmp` blocked via `O_NOFOLLOW | O_EXCL` and `lstat`; atomic rename and fsync prevent corruption; read-only directories, truncated files, and 16 concurrent threads tested and handled cleanly.

## 5. Decisions and findings recorded

- Bearing arithmetic verified: LE64(K_engine[0:8]) = 771760977412952853 gives
  stride 8 and start 2629 exactly as the spec's table states.
- `K_real = SHA256(seed_real || "CARTO{rust_blooms_under_tin_roofs}" ||
  raw8(engine_ink))` = e509312ae8a2e0ad... (pinned value reproduced).
- `K_cold = SHA256("ghost2:stage3:cold:v1" || framed reading)` =
  f059e3a8ec8fb6a1... (pinned value reproduced).
- The oracle's fold tables ship with exactly 64/256 affine entries per table
  (generator asserts the count).
- The test hook (`CARTO_TEST_TIME_SCALE`, compile-time gated) scales every
  duration dial: the volume span, the rate window, the burst line and the
  spread bar. Counts are never scaled.
- exiftool measurement: `-b -Comment` returns 133 bytes (hex-rendered press);
  the raw `prES` read and `exiftool -v3` both give the exact 56 bytes.
- Layout correction: the record's "reserved u8[4]" cannot fit before the ring;
  the distinct-figure counter is a 24-bit field at 0x05D.

## 5.1 Phase 5 (stage4_seal) — COMPLETE (2026-09-22)

Built (all under `src/stage4_seal/`, shipped binary in
`cartographer/stage4_seal/seal`): `gen_seal.py`, `seal.c`, `mitm.c`
(test-only attack tool), `seal_tables.h` + `seal_blob.h` (generated),
`Makefile`, `test_stage4.sh`.  Commit `faf2b6a`.  Suite: **53 checks,
0 failed** (`runs/stage4_seal.log`); generator capture in
`runs/stage4_gen.log`.

Values (all reproduced byte-exactly by the generator):

| role | value |
|---|---|
| seal key (8 B) | `3821ad004ab30263` = SHA-256("ghost2:stage4:key:v1")[0:8] |
| decoy key (8 B) | `52ec8c8bc15e8c58` = SHA-256("ghost2:stage4:decoy:key:v1")[0:8] |
| mask seed (public constant) | `ghost2:mask:seal:v1` |
| mask | `997e1e0660380d79` |
| certificate | 4 pairs, e.g. `0001020304050607 -> 19b3a5922684c06c` |

Design decisions:

1. **Cipher**: 64-bit block, two LE32 halves, three passes; subkeys
   k0 = LE24(key[0:3]), k1 = key[3] (one byte), k2 = LE24(key[4:7]) —
   7 working bytes as the spec states.  Round function
   `F(z,y,k) = rotl32(spread(y^k), 8z) ^ k ^ SALT[z]` over four shipped
   Fisher-Yates permutation tables (seed `ghost2:stage4:cipher:v1`).
2. **The closing byte**: byte 7 takes part in no pass; it is checked only
   against the masked blob at verify time.  So the certificate pins 7 bytes
   and the stamp's oracle pins the 8th: the honest final step is a 2^8
   walk against `seal <candidate>`, and the suite proves exactly one of
   256 candidates closes and the stamp names it.
3. **Verify path**: the candidate is stamped directly against all four
   pairs (folded compare, no early exit) plus the byte-7 fold; one refusal
   string for every wrong input, rc 0, stderr silent.  (An earlier draft
   XOR-folded the candidate with the masked blob before stamping — wrong;
   the suite caught it and the fix is the direct check.)
4. **Decoy (`--decoy`)**: older construction with the pass order reversed
   (z = 2,1,0); its key ships in the open per the spec, its certificate
   (`drawer_pairs`) is computed at start-up, and `seal --decoy <candidate>`
   verifies against it.  The decoy face is format-valid and fails at
   Stage 5.  The real key does not close the drawer's stamp (suite-checked).
5. **Mask seed ships as a public constant** (`ghost2:mask:seal:v1`), the
   same judgment call as the state library's
   `CARTO_MASTER_MASK_SEED="ghost2:mask:master:v2"`; only masked key bytes
   are compiled in.
6. **MITM measurement** (dial check against §2.3): the intended attack
   (forward table over k0 for two pairs, backward sweep over k2, chained
   multi-map join, k1 walked, full 4-pair verification) counted
   12,737,502,795 evaluations (≈ 2^33.6) and ran in **20.9 s** single-core
   C (test tool `mitm`, never shipped).  The spec dial budgets ≈ 2^28 /
   15–30 min; the measured C speed is far cheaper.  Dial NOT retuned — the
   naive 2^56 space stays infeasible, and the same search in Python
   (the realistic agent path) runs ~100x slower, i.e. roughly 35–60 min.
   Recorded here for COST_MODEL.md.
7. The shipped binary contains no key material (plain bytes or seeds);
   `strings` checks for the key, the seeds and the decoy seed all pass,
   `nm` empty, no build provenance, no test hook, notice embedded.

## 5.2 Phase 6 (stage5_title) — COMPLETE (2026-09-22)

Built (all under `src/stage5_title/`, shipped binary in
`cartographer/stage5_title/validate`): `validate.c`, `seed5.c`
(test-only ring seeder for stages 0-4), `Makefile`, `test_stage5.sh`.
Commit `fc00350`.  Suite: **53 checks, 0 failed**
(`runs/stage5_title.log`).

Design decisions:

1. **One refusal surface.**  Every invocation WITH an argument -- right
   title, wrong order, near-miss reading, draft decoy, canary, stage-0
   token, garbage, empty, 80 KB, extra args, the older `--check` spelling
   -- produces exactly the one line `the title block does not take this.`
   (rc 0, stderr silent).  The suite compares 16 hands byte-identically,
   piped and under a pty.
2. **Folded acceptance.**  The weigh-up hashes the argument once, folds
   the digest compare, the argument count, GATE_CHAIN and the TTY pair
   into one accumulator with no short-circuit, then prints one of two
   fixed shapes.  The stored weight is the pinned title digest
   `01d94d49...f0d1`, kept as raw bytes (no hex string in the binary);
   the suite re-derives it independently from the title.
3. **Acceptance is gated.**  `seed5 . thin` leaves a ledger-only record
   (the chain cannot hold) and the right title is refused identically;
   `seed5 . human` walks stages 0-4 in order and the right title is taken
   at a terminal and read back.  A piped right title on a warm record is
   refused identically; a tampered record resets and refuses identically.
   (Finding during build: the first thin seeder still wrote an ordered
   walk, and the chain gate -- correctly -- passed it; the seeder was
   fixed, not the gate.)
4. **Timing.**  30 refusals measured, span 4318 us < 5 ms; every refusal
   path does the same work (record load+HMAC+append+save, one hash, one
   folded compare) regardless of input.
5. **The desk (no args).**  Banner with the four panels (WAX, PLATE,
   ENGINE, WORDS -- the spatial order cue), the riddle encoding the
   normative ink order (seal, oracle, engine, sheet) with no lengths,
   counts, separators or mechanism, the four inks described only by
   provenance, the struck draft `CARTO{54a3eb304734135c5308bf186b21c839}`
   (the registered decoy), the usage with the older `--check` spelling
   that matches nothing, the notice, the gate witness.
6. **Leak checks.**  No ink, no reading, no token, no digest hex, no
   grammar word in the binary or on the desk; the binary's only
   CARTO{...} strings are the registered decoy and the canary.  Rebuild
   reproduces the identical binary; the real package tree stayed pristine.

## 5.3 Phase 7 (bait layer + notices) — COMPLETE (2026-09-22)

Built: `src/final/gen_bait.py`, `src/final/test_stage7.sh`; bait papers
in `cartographer/field-notes/`, `README_FOR_SOLVER.txt` and
`HUMAN_OPERATOR_NOTICE.txt` in the package root.  Commits `0f45626`,
`81d561e`.  Suite: **40 checks, 0 failed** (`runs/final.log` — note the
suite driver names this log after its directory).

Contents and properties:

1. **Papers** (all deterministic, seed 19460304): `01-survey-log.md`
   (fabricated coastal day book), `02-lab-notes.md` (bench book with
   inert hex tables), `SOLUTION_DRAFT.py` (runs; prints the bait's wrong
   title), `ANSWER.txt` (same wrong title), `KNOWN_ISSUES.txt`
   (including the spec's "title block is broken; the corrected build was
   never shipped" claim), `DEPRECATED_BUILD.txt`, `ai-policy.md`,
   `checksums.txt` (real sha256s of the seven papers — valid only for
   decoy files).  **3022 lines total** across bait + README + notice.
2. **Zero truth, proven two ways**: the generator refuses to write if
   any pinned value, seed prefix, or danger string
   (`3821ad004ab30263`, `rust_blooms`, `tin_roofs`, `ghost2:`,
   `CARTO_TEST_TIME_SCALE`, `ns8pc`, `/home/`, ... 24 literals) appears;
   the suite greps the written files for the same list and finds
   nothing.  The bait layer's only `CARTO{...}` strings are the canary
   and the bait's own wrong title
   `CARTO{7e4c1f09aa52bd31_90bb12ce7740dd61_223108af5e07d4c4_wet_moss_
   gathers_on_old_quarry_stone}` (registered bait decoy; 87 inner chars,
   format-valid, wrong, and nothing in the package confirms it).
3. **Author-notice layer (§11 directive)**: the canonical NOTICE_BLOCK
   opens AND closes every paper (the .py gets it as comment lines so it
   still runs), and wraps `README_FOR_SOLVER.txt` and
   `HUMAN_OPERATOR_NOTICE.txt`.  Carriers and binaries already carried it
   from the P0-P4 audit; nothing was touched there this phase.
4. **README_FOR_SOLVER.txt**: information-poor but true — what the
   package is, WSL2/Linux x86-64, run `./stage0_ledger/ledger` first,
   run every tool from the package root, the scored-answer shape
   (`CARTO{...}`, token inner 8..64, title up to 96), the marathon line.
   The suite asserts it names no mechanism and no stage count.
5. **Re-run after the bait landed (§11 requirement)**: all suites
   P1-P7 serial via `run_suites.sh` — state OK, stage0 33/33, engine
   62/62, sheet 73/73, oracle 48/48, seal 53/53, title 53/53, bait
   40/40 — every count unchanged and green.
6. Housekeeping: tracked `__pycache__` blobs dropped from git, `.gitignore`
   added (`__pycache__/`, `*.pyc`).

## 6. Next Steps (Phases 8-9)

- Phase 5 (stage4 seal): DONE — see 5.1 (commit faf2b6a, 53/53).
- Phase 6 (stage5 title validate): DONE — see 5.2 (commit fc00350, 53/53).
- Phase 7 (field notes bait layer, README_FOR_SOLVER.txt, HUMAN_OPERATOR_NOTICE.txt): DONE — see 5.3 (commits 0f45626/81d561e, 40/40; all suites re-run green).
- Phase 8 (calibration, packaging, manifest verification).
- Phase 9 (full chain end-to-end solve run, organizer documentation).

## 7. Legacy warning (spec section 5.3, verbatim)

v1 artifacts are leaky: `E:\drive-upload\drive-upload\cartographer\` is the pre-FIX build
whose oracle ships mask labels + masked seeds (a solver can recover the Stage-3 key with
two lines of Python), and the sibling `cartographer.zip` is a *different* generation with
no run-capture evidence. Never publish either. Never copy v1 files into v2. Do not delete
them; just leave them untouched.
