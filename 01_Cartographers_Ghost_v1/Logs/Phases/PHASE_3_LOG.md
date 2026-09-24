# PHASE 3 LOG — Stage 2: The Interior Sheet (nested steganography)

Status: COMPLETE — all verifications passing (71/71 stage-2 end-to-end checks,
58/58 differential inflate vectors vs python zlib, 27/27 state-library
regression, 36/36 stage-0 regression, 65/65 stage-1 regression, carrier
regeneration and binary reproducibility confirmed). Repo:
/home/manish/cartographer-build (git branch `main`). Session date: 2026-09-19.

## 0. Protocol confirmation (Session Continuity Protocol)

Before writing any code or running any build command, this session:

1. READ the full build spec start to end: d:\gandu\01_BUILD_PROMPT_FOR_CLAUDE_CODE.md
   (all 164 lines, in chunks; identical copy at
   /home/manish/cartographer-build/docs/BUILD_SPEC.md).
2. READ /home/manish/cartographer-build/logs/PHASE_0_LOG.md,
   PHASE_1_LOG.md and PHASE_2_LOG.md IN FULL, in order (the Phase-2 log is 890
   lines and was read in chunks: design decisions D18-D30, constants, section 9
   open questions).
3. INDEPENDENTLY re-verified Phases 0, 1 and 2 — reproduced, did not trust the
   logs. Real output in section 5. Both SHA-256 anchors matched exactly
   (stage1_vm 317d4a84...99f49e1a, stage0_start f2d1e064...1d2486f) and every
   suite passed on the first run, so no repair work was needed before Phase 3
   began. Suites were run SERIALLY (they share cartographer/.cartographer_state).

## 1. What was built (exact paths, all in /home/manish/cartographer-build)

Authoring pipeline: the editor wrote staging files d:\gandu\_stage\s2_*; a
one-shot copy script (d:\gandu\_stage\s2_sync.sh, run verbatim as
`wsl.exe bash -lc 'tr -d "\r" < /mnt/d/gandu/_stage/s2_sync.sh | bash'`)
copied them into the repo with CRLF->LF normalisation. Repo copies are
canonical; staged copies are the editable source of record for Windows.

- src/stage2_stego/gen_carriers.py  — GENERATOR (INTERNAL, not shipped): builds
  both carriers + stage2_blob.h deterministically, with in-memory self-checks
  of BOTH layers before writing anything (see D32/D33/D34)
- src/stage2_stego/stage2_blob.h    — GENERATED + committed: expected-reading
  digest + length, the two carrier fingerprints, the spent-press advertisement
- src/stage2_stego/s2_inflate.h/.c  — hand-rolled zlib-format inflate with
  preset-dictionary (FDICT) support + adler32 verification (RFC 1950/1951).
  Hand-rolled for the same reason carto_sha256.c is: the deliverable stays
  fully static under musl with no external dependency (a system libz.a is
  glibc-built and NOT usable from musl-gcc — verified and rejected, see 8.11)
- src/stage2_stego/stage2_stego.c   — THE DELIVERABLE MAIN (verifier + press;
  holds no means of derivation — see D38)
- src/stage2_stego/test_inflate.c   — internal differential unit test (C vs
  python zlib over a generated vector file)
- src/stage2_stego/mkvec.py         — internal vector generator (INTERNAL)
- src/stage2_stego/test_stage2.sh   — 71-check end-to-end verification suite
- src/stage2_stego/verify.sh        — internal clean-room verification driver
  (runs every phase's suite serially + determinism/reproducibility/hygiene)
- src/stage2_stego/Makefile         — musl static build + strip + scrub; test,
  test_inflate, clean targets; carriers are made by the generator
- cartographer/stage2_stego/stage2_stego      — THE DELIVERABLE BINARY
  (62,728 bytes; sha256
  5058a901eddbd9bc539ba27168c401fbdffd49409d6a82e4bfecd080438a8e4e;
  reproducible: identical hash across three builds)
- cartographer/stage2_stego/survey_frame.png  — THE SHEET CARRIER
  (46,258 bytes; sha256
  81b630a8d9cf0a7a85ac2fd99e352d6a4a3b432f568900a7ab9da5e88712d23c)
- cartographer/stage2_stego/survey_tape.wav   — THE TAPE CARRIER
  (8,152 bytes; sha256
  17bb6addf71803ebf13864fde2c96c9a28927180b9fa4074697b67e2201d29f6)
- src/state/policy.h                — stage-2 decoy row added (D41); mechanism
  untouched
- src/state/test_part2.c            — test_decoy_lookup now table-driven over
  every row + new test_decoy_count (26 -> 27 tests; D43)
- .gitignore                        — += src/stage2_stego/test_inflate,
  src/stage2_stego/vectors.txt
- logs/PHASE_3_LOG.md, logs/KICKOFF_PHASE_4.md — this phase's artifacts

Solver package layout: the binary lives at cartographer/stage2_stego/ and is
run FROM the cartographer/ package root (same convention as Stages 0-1); it
reads "./.cartographer_state" and audits "./stage2_stego/survey_frame.png" and
"./stage2_stego/survey_tape.wav", so nothing depends on the caller's cwd
beyond the documented package-root convention.
## 2. Design decisions and why

D31. STAGE-1 -> STAGE-2 HAND-OFF (implements the spec sentence "a pixel stride
     derived from Stage 1's real (not decoy) output"): the Stage 2 key material
     is exactly the 32-byte Stage 1 REAL key of PHASE_2_LOG D23
     (fd3e8049...4224010f), and the sweep is derived from its first two
     little-endian 64-bit words:
         R6 = LE64(K[0:8]) = 0x2ec3dfdf49803efd
         R7 = LE64(K[8:16]) = 0xc0b8223882fe22fe
         STRIDE = 3 + (R6 % 61) = 46
         START  = 512 + (R7 % 9000) = 5070
     The token is NOT used (it is only 16 of the 32 key bytes, and PHASE_2_LOG
     open question #2 reserves "the transformed Stage 1 real output" for Phase
     5). Why these shapes: (a) both are cheap to compute from a key the solver
     already has, (b) START >= 512 keeps the sweep out of the decoy region
     (D33) for every possible key, and (c) the alternatives were checked for
     real — the Stage-1 DECOY key gives stride 39 / start 1512 and the
     DEBUGGER-path key gives stride 6 / start 1601, so all three candidates
     draw different sweeps and only the real one parses (verified, section 5).

D32. SHEET CARRIER FORMAT: a hand-written 512x512, 8-bit RGB PNG (colour type
     2, filter type 0 on every row, IHDR + tEXt("Comment") + tEXt("FieldNote")
     + one IDAT + IEND, CRC32 on every chunk). No image library is used, so the
     generator is reproducible anywhere and the carrier is byte-identical on
     every run (verified: REGEN-DETERMINISTIC-OK). A plausible graticule
     background (paper grain + rule lines + faint contours) is drawn so a
     casual look shows a survey sheet, not a payload carrier.

D33. LAYER SEPARATION (the fix for the first real bug of this phase): the DECOY
     layer is confined to the OPENING DECOY_MARKS = 512 marks, and the real
     sweep always begins at mark >= 512. Bit k of the decoy stream is the LSB
     of channel (k mod 3) of mark (k div 3) — i.e. R,G,B in order for the first
     512 marks — MSB-first, which is exactly what a naive "read the LSBs of
     every pixel" tool does first. Capacity 512*3 = 1536 bits = 192 bytes. The
     real layer (D34) writes only bit 0 of the BLUE channel of marks >= 512, so
     the two layers share a bit plane but can never touch the same bit, which
     makes both layers deterministic and tool-independently readable. The first
     version embedded the real layer across the WHOLE sheet and the decoy layer
     into the opening marks, so for small strides the real bits overwrote decoy
     bits and the naive read decoded garbage for exactly the solvers who took
     the trap.

D34. REAL LAYER ENCODING: blue-channel bit 0 of every STRIDE-th mark from START
     to the far edge; the drawn bits are MSB-first bytes of
     LE16(len(zblob)) || zblob. capacity = (262144 - START)/STRIDE = 5588 bits
     (698 bytes) and the payload uses 400 bits (50 bytes: 2 length + 48 zlib),
     so there is ~14x headroom: the sweep never runs off the end of the sheet
     (a fairness property — no truncation class of failure).

D35. THE PRESS (custom zlib preset dictionary, per spec "compressed with a zlib
     custom preset dictionary ... so naive decompression fails until the solver
     notices and supplies it"): the 56-byte dictionary is stored RAW in the
     tape's RIFF INFO/ICMT chunk, and zlib sets FDICT in the zlib header, so
     (a) a bare zlib.decompress()/inflate fails on the header, and (b) a raw
     inflate fails on the first dictionary-distance match — both verified.
     The first 22 bytes are the ASCII prefix "interior-ink-formula-v1:" so the
     chunk reads as plausible text under `strings`/exiftool while the 32-byte
     binary tail is the real dictionary. It NEVER touches any binary (verified:
     the press formula is not in the shipped binary).

D36. TAPE CARRIER FORMAT: a hand-written 8,152-byte RIFF/WAVE — PCM, 16-bit,
     mono, 8000 Hz, 4,000 samples (0.5 s of a smooth tone), LIST/INFO with
     INAM ("interior survey tape 2") and ICMT (the press), every chunk
     word-aligned with strict sizes. INAM's payload is odd so it carries a pad
     byte, which makes a naive chunk walk (ignoring the pad) mis-parse the
     following chunk — a real, cheap hazard that the solver's own tooling
     exposes immediately as garbage. The samples' LSBs carry an irrelevant
     44-char message ("the tape hums; the figure is not in the sound") as the
     cheap secondary micro-distraction the spec asks for.

D37. THE MANUAL-STEP TRAP (spec Phase 3: "a specific ImageMagick/exiftool flag
     combination that must be discovered by reading tool documentation, because
     the default output of common stego tools silently mangles the exact byte
     range that matters"). VERIFIED, NOT ASSUMED, on this machine (exiftool
     12.76):
       - `exiftool survey_tape.wav` prints Comment as MOJIBAKE (the binary
         dictionary rendered as latin-1 characters) — useless;
       - `exiftool -b -Comment survey_tape.wav` prints 70 bytes for a 56-byte
         tag: it silently RE-ENCODES the binary run, so a solver who trusts the
         convenient flag silently corrupts the exact bytes that matter;
D38. THE TOOL HOLDS NO MEANS OF DERIVATION (deliberate strengthening over
     Phase 2). stage2_stego contains: the expected reading's SHA-256 digest and
     length (constant-time compare), the two carriers' SHA-256 fingerprints
     (verifier evidence, derivable by anyone from the shipped files), the
     registered decoy flag (via policy.h) and the spent-press advertisement.
     It contains NO stride/start constant, NO sweep arithmetic, NO press
     formula, NO reading. Rationale: Stage 2's derivation is two lines of
     arithmetic anybody can re-derive, so a shipped extractor would hand the
     puzzle over; instead the tool VERIFIES a claimed reading and PRESSES a
     re-supplied ink (D39). "The verifier knows the answer only as a digest" is
     also exactly the pattern Phase 5's final validator needs, so this design is
     reused there.

D39. CLI CONTRACT (every path exits 0; stderr is ALWAYS silent):
       ./stage2_stego/stage2_stego                     -> usage
       ./stage2_stego/stage2_stego -c '<reading>'      -> verdict on a claim
       ./stage2_stego/stage2_stego -p <mark|mark-file> -R <ink-file>
                                                       -> press the ink, then verdict
     The press mark may be given as raw bytes in a file or as hex letters (a
     solver may legitimately prefer hex; the raw form is what the tape holds).
     The ink file is the framed ink exactly as drawn from the sheet (LE16 length
     + zlib bytes), which is what any sweep implementation produces naturally.
     A wrong mark is refused AT THE HEAD (the DICTID check of 8.8) — no partial
     decode, no diagnosis of which side was wrong.

D40. VERDICT DISCIPLINE (spec: "no partial-match feedback of any kind"): the
     digest comparison is constant time, the length test is evaluated
     unconditionally, and every refusal prints identical text. The suite proves
     it: a claim of the stage-1 decoy token and a claim of an arbitrary wrong
     string produce byte-identical output.

D41. DECOY ROUTING (spec: "Submitting it routes into the extended dead-end
     branch via state-file logic, framed as new information, never as an
     error"): the naive-LSB decoy is registered in src/state/policy.h as
     { stage 2, CARTO{twice_over_the_coast_before_the_interior}, branch 1 } and
     a claim matching it routes into the extended branch ("the ledger knows
     this ink ... re-inks the checkpoint the old man left for the coast
     survey ... this mark was struck from the coast press, not the interior
     one"), persists bit 0 (1u << (branch-1), the PHASE_2_LOG D26 convention)
     and NEVER prints the real reading. The DEPTH of that extended branch — the
     dead end that must read as progress for ~1-1.5 h — is Phase 6 calibration
     work (it needs the later stages to exist), so the routing and the checkpoints
     are built and tested now and the extension is deepened in Phase 6.

D42. CHECKPOINT TOKEN: CARTO{sha256(reading)[0:16] as hex} (D11-conforming,
     38 chars). Minted from the EXPECTED digest, so it is stable across runs,
     and the reading itself is never stored in the binary, so the token is a
     one-way checkpoint (no leak). Same grammar as Stage 0's ungated win and
     Stage 1's token.

D43. STATE-LIBRARY CHANGES (mechanism untouched, per PHASE_0 D10/D14): (1)
     policy.h gains the stage-2 decoy row, CARTO_DECOY_TABLE_LEN 1 -> 2; (2)
     test_part2.c's test_decoy_lookup now iterates EVERY row (so Phases 4-5
     registrations keep the mechanism test exhaustive) and a new
     test_decoy_count asserts table-macro agreement; 26 -> 27 tests. No
     threshold was tuned (calibration is Phase 6).

D44. ESCALATION VARIANTS: ONE binary, two PRE-BUILT branches (spec: "pre-compiled
     branches already embedded in its own data section"): "plain audit" vs
     "extended audit", selected by carto_should_escalate(CARTO_STAGE2, now)
     (fast arrival / uniform timing / persisted debugger flag). Both accept the
     identical reading (the figure is never corrupted — fairness), and the
     extended branch additionally reports the cross-check ("the second pass
     agrees with the first; sheet and tape were struck from the same press")
     and, for decoys, the coast-press framing. HONEST LIMITATION: for a pure
     verifier there is no way to make the escalated branch mechanically harder
     without either breaking fairness or hiding the answer, so the escalation
     here is presentation/verification-depth only; the machinery (reasons
     computed, variant selected, state persisted) is exercised and Phase 6 can
     revisit. Recorded as an open question.

D45. FAIRNESS / DETERMINISM: no clock and no RNG affect any value; the sheet,
     the tape, the digest and the token are byte-reproducible. Every trap has a
     deterministic resolution: (a) the sheet's own FieldNote chunk spells the
     sweep rule in plain words, (b) the tape holds the press in a documented
     container, (c) exiftool -v3 / raw bytes recover it exactly, (d) the tool's
     own -p/-R mode verifies a hand-drawn sweep, (e) the decoy is falsifiable by
     the tool's refusal without any downstream round trip. Nothing requires a
     guess outside the puzzle's own logic, and nothing on the real path is
     luck-based.
       - `exiftool -v3 survey_tape.wav` prints the tag with its length
         ("Tag 'ICMT' (56 bytes)") and hex rows of the exact bytes — the
         documented, honest route (asserted in the suite);
       - raw reads (xxd/python) obviously work, and ImageMagick reads the sheet.
## 3. Every constant introduced (exact values + location)

DIGEST SEED STRINGS (INTERNAL: gen_carriers.py + this log ONLY; never compiled
into any binary — verified by the suite):
- press formula seed: "cartographer-ghost:stage2:ink-formula:v1"
  -> tail = SHA-256(seed) =
     2e032c75bee2b9952d0c6b93c77bb72b1339b377480c6a5f4e425aa36cfd7695
- spent-press (decoy advertisement) seed:
  "cartographer-ghost:stage2:decoy:spent-press:v1"
  -> 893c70442fdfc9e05aa8ec4434413a2bc1a9a63f31d4a8a60c06905dd2ec26b7
  (THIS digest is compiled into the binary: it is a decoy advertisement.)

THE PRESS (56 bytes, stored RAW in the tape's INFO/ICMT chunk; in
src/stage2_stego/gen_carriers.py as DICT = name + SHA-256(seed)):
  696e746572696f722d696e6b2d666f726d756c612d76313a2e032c75bee2b9952d0c6b93c77bb72b1339b377480c6a5f4e425aa36cfd7695
  = ASCII "interior-ink-formula-v1:" + the 32-byte tail above
  tape offset of the ICMT payload: 8096 (0x1FA0); chunk id at offset 8088

THE READING (Stage 2 real payload; exists ONLY inside the carrier bytes):
  CARTO{no_figure_sits_in_every_pixel}   (36 bytes)
  SHA-256 = b27692a0d5f63d4f1a0c3fb79afbf81b3f9385db66c057655b8f07d2ea0550a3
  (the digest, and only the digest, is compiled into the binary;
   CARTO_S2_EXPECTED_LEN = 36u, kStage2ExpectedDigest[32])

CHECKPOINT TOKEN (minted at runtime from the digest, D42):
  CARTO{b27692a0d5f63d4f1a0c3fb79afbf81b}

THE DECOY (naive whole-image LSB layer, marks 0..511; registered in policy.h):
  CARTO{twice_over_the_coast_before_the_interior}
  (D11-conforming; the opening 192-byte LSB stream is zero-padded after it)

SWEEP (derived at RUNTIME from the Stage 1 real key; NO such constant exists in
any binary — asserted by the suite):
  STRIDE = 46            (3 + (LE64(K[0:8]) % 61))
  START  = 5070          (512 + (LE64(K[8:16]) % 9000))
  capacity = 5588 bits; payload drawn = 400 bits (LE16 48 + 48 zlib bytes)
  wrong-key sweeps (verified): decoy key -> stride 39 / start 1512;
  debugger-path key -> stride 6 / start 1601 (both unparseable garbage)

STRUCTURAL CONSTANTS
- sheet: 512x512 RGB8; marks 0..511 = decoy region; 512*3 = 1536 decoy bits;
  PNG filter type 0 on every row; chunk order IHDR, tEXt, tEXt, IDAT, IEND
- tape: RIFF/WAVE, PCM 16-bit mono 8000 Hz, 4,000 samples, chunks fmt(16),
  data(8000), LIST(INFO{INAM, ICMT}); sizes strictly honoured (INAM padded)
- sample-LSB micro-distraction message: "the tape hums; the figure is not in
  the sound" (44 bytes)
- shipped carrier fingerprints (compiled in, as verifier evidence):
  sheet 81b630a8d9cf0a7a85ac2fd99e352d6a4a3b432f568900a7ab9da5e88712d23c
  tape  17bb6addf71803ebf13864fde2c96c9a28927180b9fa4074697b67e2201d29f6
- spent-press lure string (in .rodata): "stage2_key_checkpoint (pre-interior)
  -- the press this sheet was struck from; do not re-cut"
- CLI: -c <claim>, -p <mark|mark-file>, -R <ink-file>; caps CLAIM_MAX 512,
  FILE_MAX 1 MiB, MARK_MAX 64 KiB, OUT_MAX 64 KiB

FLAG-FORMAT / KEY POLICY (unchanged from Phases 1-2): every minted string is
^CARTO\{[a-z0-9_]{8,64}\}$ (D11); ONE canonical HMAC key shared by all stage
binaries (PHASE_1_LOG D13); no threshold in policy.h was touched (Phase 6
calibrates CARTO_T_FAST_SEC_DEFAULT 90s, CARTO_STDDEV_LOW_MS 1500ms,
CARTO_MIN_TIMING_DELTAS 4).

## 4. Exact commands (runnable verbatim)

C22. Sync the staged Phase 3 sources into the repo (CRLF->LF normalised):
wsl.exe bash -lc 'tr -d "\r" < /mnt/d/gandu/_stage/s2_sync.sh | bash'

C23. One-shot state-library edits (idempotent; both already applied; the first
     version of the policy edit was buggy — see 8.5 — and s2_fix_policy.py
     repaired the repo file. Prefer re-running the fixed s2_policy.py):
wsl.exe bash -lc 'tr -d "\r" < /mnt/d/gandu/_stage/s2_policy.py > /tmp/s2_policy.py && python3 /tmp/s2_policy.py'
wsl.exe bash -lc 'tr -d "\r" < /mnt/d/gandu/_stage/s2_test_part2.py > /tmp/s2_tp2.py && python3 /tmp/s2_tp2.py'

C24. State-library regression (27 checks; MUST precede the stage builds):
wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/state && make clean && make test'

C25. Stage-0 regression (36 checks):
wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/stage0 && make && ./test_stage0.sh'

C26. Stage-1 regression (65 checks + 8 verdict checks; relinks against the
     updated library, so re-run it after any state-library change):
wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/stage1_vm && make test'

C27. THE Phase 3 build + verification (regenerates both carriers and
     stage2_blob.h, builds test_inflate, runs the differential vectors and then
     the 71 end-to-end checks):
wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/stage2_stego && make test'

C28. THE whole clean-room verification (all four suites SERIALLY + carrier
     regeneration determinism + three-build binary reproducibility + scrub +
     solver-eye smoke run). This is what produced section 5:
wsl.exe bash -lc 'bash /home/manish/cartographer-build/src/stage2_stego/verify.sh'

C29. Manual solver-eye run (from the package root):
wsl.exe bash -lc 'cd /home/manish/cartographer-build/cartographer && rm -f .cartographer_state && ./stage2_stego/stage2_stego && ./stage2_stego/stage2_stego -c "CARTO{no_figure_sits_in_every_pixel}"'

C30. Verify a hand-drawn sweep through the tool's press mode (the independent
     route a solver would take; -R takes the ink file as drawn):
wsl.exe bash -lc 'cd /home/manish/cartographer-build/cartographer && python3 -c "b=open(\"stage2_stego/survey_tape.wav\",\"rb\").read(); i=b.find(b\"ICMT\"); open(\"/home/manish/press.bin\",\"wb\").write(b[i+8:i+8+56]); print(\"press written\")" && ./stage2_stego/stage2_stego -p /home/manish/press.bin -R /home/manish/ink.bin'
## 5. Verification run — full real output (C28, verbatim from the run)

Sections 1-3 (regressions; tails):
```
############ 1. state library (Phase 0) ############
[PASS] test_decoy_lookup
[PASS] test_decoy_count
[PASS] test_decoy_persist
[PASS] test_attempts_persist
[PASS] test_debugger_persist
[PASS] test_hmac_differential
== 27 tests run, 0 failed ==
ALL TESTS PASSED
test_state: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), statically linked, with debug_info, not stripped

############ 2. stage0_start (Phase 1) ############
== 36 tests run, 0 failed ==
ALL TESTS PASSED

############ 3. stage1_vm (Phase 2) ############
== 8 checks, 0 failed ==
ALL CHECKS PASSED
== 65 tests run, 0 failed ==
ALL TESTS PASSED
```
(The state suite went 26 -> 27 because of the Phase 3 additions of D43; every
pre-existing test still passes, including test_decoy_lookup, now exhaustive.)

Section 4 — the hand-rolled inflate vs python zlib, then the 71 stage-2 checks:
```
############ 4. stage2_stego (Phase 3) ############
musl-gcc -O2 -Wall -Wextra -std=c11 -static -fno-ident -I../state stage2_stego.c s2_inflate.c ../state/libstate.a -o ../../cartographer/stage2_stego/stage2_stego
strip --strip-all ../../cartographer/stage2_stego/stage2_stego
objcopy --remove-section .comment ../../cartographer/stage2_stego/stage2_stego 2>/dev/null || true
./test_stage2.sh
== stage2_stego end-to-end verification ==
== s2_inflate differential unit tests (C vs python zlib) ==
== 58 vectors run, 0 failed ==
ALL TESTS PASSED
[PASS] hand-rolled s2_inflate agrees with python zlib on 58 vectors, refuses all bad streams
[PASS] binary exists and is executable
[PASS] binary statically linked (musl)
[PASS] binary stripped (no symtab)
[PASS] no debug paths / compiler strings in binary
[PASS] sheet carrier present
[PASS] tape carrier present
[PASS] sheet verified independently as a 512x512 PNG
[PASS] naive whole-image LSB layer carries the registered decoy at the head
[PASS] real sweep derives stride 46 / start mark 5070 from the Stage 1 real key
[PASS] blue-channel layer decompresses to the interior reading
[PASS] naive zlib decompression of the ink is refused (the press mark is required)
[PASS] debugger-path key draws a different sweep (stride 6, start 1601)
[PASS] stage-1 decoy key draws a different sweep (stride 39, start 1512)
[PASS] a wrong Stage 1 key yields garbage that does not parse and does not error
[PASS] the debugger-path key's sweep also yields unparseable garbage
[PASS] tape carries INAM + ICMT metadata
[PASS] the press mark extracted from the tape's metadata decrypts the ink
[PASS] tape sample LSBs carry the irrelevant pattern (not the figure)
[PASS] sheet carries the field note and the (flavor-only) comment
[PASS] exiftool default output mangles the binary press mark (text-habit shortcut fails)
[PASS] exiftool -b -Comment silently re-encodes the mark (70 bytes for 56)
[PASS] exiftool -v3 prints the exact mark bytes (documented, fair resolution)
[PASS] the mark is recoverable byte-exactly from the raw file
[PASS] ImageMagick can read the sheet (a tool route exists as well)
[PASS] clean run exits 0
[PASS] clean run: stderr silent
[PASS] claim mode accepts the real reading
[PASS] acceptance echoes the reading
[PASS] stage 2 checkpoint token minted from the reading digest
[PASS] carrier audit recognises the shipped sheet and tape
[PASS] human-paced ledger serves the plain audit variant
[PASS] stage 2 attempt counter bumped
[PASS] no decoy bit set by the real reading
[PASS] state HMAC valid (independent python check)
[PASS] state file is exactly 352 bytes
[PASS] attempt counter advances across runs
[PASS] checkpoint token is stable across runs
[PASS] debugger flag stays 0 on clean runs
[PASS] press mode exits 0
[PASS] press mode accepts the ink with the tape's mark
[PASS] the pressed reading verifies against the ledger
[PASS] a wrong press mark is refused at the head (DICTID), without diagnosing
[PASS] wrong press mark never leaks the real reading
[PASS] a missing ink is reported plainly, not as an error
[PASS] decoy claim exits 0 (no error path)
[PASS] decoy claim: stderr silent
[PASS] decoy claim routes into the extended branch
[PASS] decoy branch is framed as new information, not failure
[PASS] decoy branch never leaks the real reading
[PASS] stage 2 decoy bit 0 persisted (branch 1 -> 1u<<0)
[PASS] state HMAC valid after decoy routing
[PASS] decoy claim also selects the extended audit variant
[PASS] refusals are textually identical: no partial-match feedback
[PASS] the stage-1 decoy token gets only a plain refusal (no oracle)
[PASS] uniform interaction timing selects the extended audit variant
[PASS] escalated variant still accepts the real reading
Sections 5-7 (regeneration determinism, three-build reproducibility, artifacts):
```
############ 5. carrier regeneration determinism ############
REGEN-DETERMINISTIC-OK
HEADER-DETERMINISTIC-OK

############ 6. binary reproducibility (two clean rebuilds) ############
5058a901eddbd9bc539ba27168c401fbdffd49409d6a82e4bfecd080438a8e4e  .../stage2_stego
5058a901eddbd9bc539ba27168c401fbdffd49409d6a82e4bfecd080438a8e4e  .../stage2_stego
5058a901eddbd9bc539ba27168c401fbdffd49409d6a82e4bfecd080438a8e4e  .../stage2_stego

############ 7. artifact inventory ############
total 120
-rwxr-xr-x 1 manish manish 62728 Sep 19 15:26 stage2_stego
-rw-r--r-- 1 manish manish 46258 Sep 19 15:26 survey_frame.png
-rw-r--r-- 1 manish manish  8152 Sep 19 15:26 survey_tape.wav
stage2_stego: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), statically linked, stripped
62728 /home/manish/cartographer-build/cartographer/stage2_stego/stage2_stego
SCRUB-CLEAN
```

Section 8 (solver-eye smoke run; banner repetitions elided with "..."):

```
############ 8. solver-eye smoke run ############
======================================================================
  THE CARTOGRAPHER'S GHOST
  Stage 2 -- The Interior Sheet
======================================================================

The coast is behind you. This is the interior: a sheet of survey
marks, and the tape the old man spoke his field note onto. Neither
of them is a map with the figure drawn on it plainly.

  sheet : ./stage2_stego/survey_frame.png -- the ledger knows this one
  tape : ./stage2_stego/survey_tape.wav -- the ledger knows this one
  ledger mode : extended audit

The ledger will take a reading, or press an ink.

    ./stage2_stego/stage2_stego -c '<reading>'
        hand over what you read out of the sheet

    ./stage2_stego/stage2_stego -p <mark|mark-file> -R <ink-file>
        hand over the sheet's press mark (raw bytes in a file, or as
        hex letters) and the ink drawn from the sheet, packed eight
        marks to a letter as it came

Nothing about a wrong reading is an error -- the ledger says plainly
that it does not know it, and keeps no grudge.
  the ledger does not know that reading: it is not the interior figure.
  Nothing about a wrong reading is an error. Keep the mark; the sweep is
  somewhere on the sheet, and the press is on the tape.
======================================================================
--- claim of the real reading ---
...
  the ledger takes this reading:

    CARTO{no_figure_sits_in_every_pixel}

  the interior figure stands. Stage 2 checkpoint token -- bank it:

    CARTO{b27692a0d5f63d4f1a0c3fb79afbf81b}

  extended audit: the second pass agrees with the first; sheet and
  tape were struck from the same press.

  Carry it to the oracle. It answers in figures, not in ink.
======================================================================
--- decoy claim ---
...
  the ledger knows this ink. It accepts it as a corroborated reading
  and re-inks the checkpoint the old man left for the coast survey:

    CARTO{twice_over_the_coast_before_the_interior}

  extended audit: this mark was struck from the coast press, not the
  interior one.

  Nothing here needs re-drawing.
======================================================================
```
(The smoke run reads "extended audit" because a fresh state triggers
CARTO_ESC_TIME_FAST — the same harmless behaviour PHASE_2_LOG D25 recorded for
Stage 1: the variant never changes the verdict, only the presentation.)

## 6. Additional verifications performed this session

- s2_inflate differential: 58 vectors (payload sizes 1..120,000 bytes; zlib
  levels 0/1/6/9; with and without the preset dictionary; multi-block streams;
  repetitive text for long matches) — the C implementation matched python's zlib
  byte for byte on all valid streams and refused all 12 malformed ones
  (truncated, wrong dictionary, missing dictionary, garbage header, reserved
  block type).
- Wrong-Stage-1-key behaviour measured for BOTH wrong candidates: the decoy key
  sweeps stride 39/start 1512 and the debugger-path key stride 6/start 1601;
  neither yields bytes containing "CARTO{" and neither inflates — i.e. garbage
  that does not parse and does not error, exactly as the spec requires.
- The manual-step trap was measured, not assumed: default exiftool output
  differs from the true bytes; `-b -Comment` returns 70 bytes for a 56-byte tag;
  `-v3` prints the exact bytes (all three asserted in the suite).
- RELINK NOTE (expected, verified): adding the stage-2 decoy row to policy.h
  changes libstate.a, so the Stage 0 and Stage 1 binaries were relinked (same
  sizes: 66,840 and 62,728 bytes) and BOTH suites were re-run against the new
  library: 36/36 and 8/8 + 65/65. Their sha256s changed accordingly:
    stage0_start f2d1e064554ed7bafa8beb8deaf9bf4887bd9d857b9c745b68678e6ee1d2486f
              -> d3b23eb286c8bf66ef03a478603f57dd3737b9b8e5bc4b750fa80721aeb42a06
    stage1_vm    317d4a846af9168ed34b1283ae05bccdebb659ade342343d63a16fcc99f49e1a
              -> 3f302ef8dddda227cbd488d185148e7725c0ceea1c34a902cc810e98d63389b5
  behaviour is unchanged (their own suites prove it); the decoy table inside
  them now also exposes the stage-2 decoy flag, which is the accepted D29-style
  "findable decoys" trade-off. Any future log that pins stage0/stage1 hashes
  must use these new values.
- Carrier regeneration is byte-identical (sheet, tape and the generated header
## 7. Bugs found and fixed DURING Phase 3

1. LAYER COLLISION (design bug, caught by reasoning before shipping): the first
   generator wrote the decoy layer into the opening marks AND the real layer
   across the whole sheet. For stride <= 3 the real bits overwrote decoy bits,
   so the naive read decoded garbage for exactly the solver who fell for the
   trap (an unfair, self-defeating poison). Fix: the real sweep is confined to
   marks >= START >= 512 by construction (D33/D31).
2. GENERATOR SELF-CHECK ORDER: gen_carriers.py checked the real layer by
   re-reading the sheet image BEFORE the real bits were embedded, so the check
   read the bare base sheet and zlib refused it ("unknown compression method").
   Fix: embed the real layer first, then self-check both layers in memory
   (nothing is written until both layers verify).
3. CHUNK-SPLICE TRUNCATION (write_wav): an editor insert landed mid-function and
   the function's final `path.write_bytes(...)` was lost, so the tape was never
   written (FileNotFoundError on the tape) and a duplicate copy of that
   statement stranded at module level caused a second failure
   (NameError: name 'path'). Fix: re-anchored the statement inside write_wav and
   deleted the stray copy.
4. CHUNK-SPLICE SCRAMBLE (stage2_stego.c): the same hazard put usage()'s tail,
   report_decoy()'s tail and the whole report_unknown() AFTER main(), producing
   implicit-declaration errors and a duplicate-main cascade. Fix: s2_fix_stego.py
   reorders the line blocks with every boundary asserted before splicing.
   WORKFLOW LESSON (repeat of PHASE_2_LOG #1): the editor is only safe when
   edits are anchored on old_text; line-number inserts must be treated as
   suspect and every generated file re-read before building.
5. POLICY PATCH DESTROYED A ROW: the first s2_policy.py used a
   `(?:.*?\n)*?` regex over the whole table and deleted the Stage-1 decoy row
   (and duplicated a doc-comment line). The state suite caught it immediately —
   test_decoy_lookup failed with "wrong stage matched" (the "other stage"
   variant became the same stage) and test_decoy_count failed with "table
   length macro disagrees". Fix: s2_fix_policy.py restored row 1, and
   s2_policy.py now INSERTS the new row before the closing brace and never
   rewrites existing rows. The two new tests earned their keep on their first
   run.
6. INFLATE: PRESET-DICTIONARY WINDOW SEEDING. Seeding the window at win[0..take)
   while leaving win_pos = 0 broke the history ring's invariant (the newest byte
   must sit at win_pos-1), so every dictionary stream was refused. Fix: seed the
   END of the window (win[WINSIZE-take .. WINSIZE)) with win_pos = 0, so the
   first output byte lands at ring position 0 and back-references resolve into
   the dictionary tail.
7. INFLATE: ADLER32 ACCUMULATOR OVERFLOW. `b` (the running sum of `a`) could
   wrap the 32-bit accumulator for outputs of a few hundred bytes, so large
   streams failed their checksum. Diagnosis: the traced copy printed
   "expected == got" for small streams while large ones refused. Fix: the
   standard deferred-reduction form (reduce a and b whenever they pass
   5552*65521), verified to produce adler32("A") = 0x00420042 and to match
   python on 120 KB outputs.
8. INFLATE: MISSING RFC 1950 DICTID. When FDICT is set the zlib header is
   followed by a 4-byte big-endian DICTID before the deflate data; the parser
   started at offset 2 and read the DICTID as compressed data, refusing every
   dictionary stream. Fix: validate the DICTID against adler32(dictionary tail)
   and begin the deflate parse at offset 6. Side benefit: a wrong press mark is
   now refused at the head instead of after a partial decode (D39).
  all re-hash to the same digests) and the deliverable binary is identical
  across three clean rebuilds.
- Scrub: `strings` shows no GCC/clang/musl/compiler-path residue; the binary is
  static (musl) and stripped; the canonical HMAC key, the reading, the Stage 1
  real key and the press formula are all absent.
- Carriers contain neither the reading nor the sweep constants nor any seed
  string (asserted).
9. TEST-HARNESS BUGS (all found while driving the suite to green):
   a) `zlib.decompress(ink, -15)` — a NEGATIVE wbits means RAW deflate, not
      "zlib stream with a dictionary", so the vector generator refused streams
      for the wrong reason. Fixed to wbits 15 with a zdict (or a plain
      compressobj when there is no dictionary).
   b) The reader printed a python bytes repr (`b'CARTO{...}'`) into a shell
      variable; twelve assertions compared against the repr. Fixed by decoding
      to latin-1.
   c) The token grep `CARTO{[a-z0-9_]{1,}}` matched the echoed READING rather
      than the minted token; tightened to `CARTO\{[0-9a-f]{32}\}`.
   d) The exiftool -v3 assertion took an odd-length tail (33 hex chars), so the
      spaced-hex grep could never match; fixed to tail -c 32.
   e) The "wrong press mark" fixture (`rev | cut -c1-112 | rev` on a 112-char
      hex string) was a NO-OP, so the test compared the correct mark and
      expected a refusal; replaced with a real one-nibble mutation plus a
      length assertion.
   f) The ink fixture was written without its LE16 length prefix, so press mode
      correctly reported "too few marks"; the reader now writes the framed ink
      file itself (one source of truth).
   g) The decoy/extended-variant assertions ran on a forged HUMAN-paced state,
      where no escalation reason fires; re-forged with the fast mode.
   h) The "trap material" assertion required the literal dictionary prefix in
      the binary — but D35/D38 keep the press bytes in the tape, so only a
      prefix of the prefix survives in .rodata (compiler string folding); the
      assertion was corrected to accept any of three true variants.
10. RETAINING THE DECOY ADVERTISEMENT: `keep_decoy` must be `volatile` (as
    PHASE_2_LOG's Stage 1 did) or GCC 13 -O2 drops the never-taken branch and
    the spent-press note vanishes from .rodata — the suite's trap-visibility
    check caught exactly that.
11. ENVIRONMENT (worth repeating for future sessions): a system libz.a is
    glibc-built and `musl-gcc` cannot see /usr/include/zlib.h, so linking the
    system zlib into a musl-static deliverable was rejected outright (missing
    headers plus mixed C runtimes). Hand-rolling inflate (the "no external deps"
    convention of carto_sha256.c) was the right call. Also: /tmp is tmpfs and
    was wiped twice mid-session by WSL idle restarts, and the pwsh->bash
    quoting quirk ate shell variables (both documented in PHASE_0_LOG section 6)
    — all verification logic now lives in script files inside the repo.

## 8. Explicitly NOT done / deferred

- Phase 4 (Stage 3 Feistel oracle: hand-rolled network, deliberate round-function
  bias, chosen-plaintext differential attack, near-uniform-timing automation
  detection with poisoned ciphertext, the misreadable help-text human trap),
  Phase 5 (assembly riddle + constant-time validator), Phase 6 (calibration +
  self-testing + SOLVE_PATH_PRIVATE.md), Phase 7 (packaging, README_FOR_SOLVER,
  HINTS, room text).
- DEEPENED DECOY DEAD END (D41): the routing, the state bit and the framing are
  built and tested, but the extended branch that must read as progress for
  ~1-1.5 h is Phase 6 work — it needs the downstream stages to exist to be a
  dead end at all. FLAGGED: this is the one Phase-3 spec element that is only
  partially satisfied right now, deliberately, with the mechanism in place.
- Escalation for a pure verifier is presentation-depth only (D44): an escalated
  VERDICT cannot be made mechanically harder without unfairness, so the
  machinery is exercised but its gameplay value is unproven. Phase 6 judgement
  call.
- No threshold calibration: CARTO_T_FAST_SEC_DEFAULT (90 s), CARTO_STDDEV_LOW_MS
  (1500 ms), CARTO_MIN_TIMING_DELTAS (4) and CARTO_VM_DEBUG_RATIO_LIMIT (20.0)
  remain Phase-0/Phase-2 placeholders per D10/D43.
- Solver-facing documentation of the Stage-2 CLI is deferred to Phase 7 (the CLI
  exists, is described in the tool's own usage text, and is fully tested).
- Public-tool coverage of the decoy layer: the suite proves the naive R,G,B-LSB
  read yields the decoy flag, but it does NOT install an external stego tool
  (zsteg is a ruby gem and is not installed); the naive reader is implemented in
  the suite instead. If Phase 6 wants literal tool coverage, apt can supply
  steghide/pngcheck or ruby+zsteg.
- Assumed-but-unverified: NOTHING in Phase 3 scope — every claim above was
  produced by a command whose real output is pasted in section 5 or summarised
  in section 6 with its exact command in section 4.
## 9. Open questions / judgment calls for the next session

1. STAGE 2 -> STAGE 3 HAND-OFF (the most important decision for Phase 4): the
   spec says the oracle is a local rate-limited chosen-plaintext cipher and the
   final flag needs "Stage 3 cipher key". Proposal (decide and log in
   PHASE_4_LOG): the oracle's Feistel key derives from the Stage 2 READING
   (e.g. sha256(reading) or its byte tail) — NOT from the Stage 2 token and NOT
   from the Stage 1 token, so no submittable string doubles as key material
   (PHASE_2_LOG open question #2 wants the "transformed Stage 1 real output"
   reserved for Phase 5's assembly). Gate the oracle on nothing (it must run for
   anyone: the spec's fairness rule forbids error-framed gating); let a wrong
   Stage 2 reading simply produce a wrong Stage 3 answer that fails at Phase 5's
   validator — the same "garbage, not an error" shape Stage 2 uses.
2. RATE LIMITING / AUTOMATION DETECTION (spec Phase 4): "near-uniform call
   spacing (read from shared state) triggers silent poisoned-ciphertext
   responses". The ring is CARTO_RING_SIZE = 32 with a 1500 ms stddev threshold
   placeholder; decide in Phase 4 whether that window is the right length for
   the poison to become detectable by comparing scripted vs manual queries, and
   whether the poison should key off the Stage-2 escalation path (it already
   persists debugger_detected). Do NOT tune the threshold — Phase 6 calibrates.
3. DECOY DEPTH (D41) is the Phase-3 element carried forward: the extended-branch
   dead end needs the downstream stages (Phase 4-5) to be a real detour, and its
   ~1-1.5 h budget is Phase 6's calibration target.
4. VERIFIER-ONLY ESCALATION (D44): decide in Phase 6 whether Stage 2's
   escalation should instead gate a HARDER-but-fair extra artifact (e.g. only
   the extended branch exposes the full press-vs-sheet cross-check, and the
   plain branch asks for a second confirmation run). Any change must keep the
   verdict invariant.
5. PTRACE/SECCOMP FAIRNESS (PHASE_2_LOG open question #5) still open: Stage 1's
   anti-debug could mis-read a blocked ptrace as "debugger detected". Stage 2
   never tripped it (it only reads the persisted flag), but the recommendation
   stands: require BOTH a ptrace failure AND a timing breach, or check errno for
   EPERM specifically, before shipping.
6. SCORING (PHASE_2_LOG open question #1, unchanged): score only the Stage-0
   flag and the final assembled flag; treat Stage 1's token and Stage 2's
   reading/token as in-challenge checkpoints. Phase 7 decides.
7. PACKAGE NAMING for Phase 4: cartographer/stage3_oracle/ (per the spec tree),
   with the binary self-auditing any carrier it needs; keep the "verifier holds
   only a digest / never the derivation" pattern (D38) unless the oracle's
   chosen-plaintext interface makes it impossible (it should not: the key can be
   derived at runtime from the Stage 2 reading passed in).

## 10. Git commit for Phase 3

Single commit on `main`, subject:

    phase3: stage2_stego (PNG+WAV nested stego, derived sweep, preset-dict
    press), hand-rolled inflate, 71-test suite; stage-2 decoy registered

containing src/stage2_stego/* (generator, generated header, inflate, tool,
tests, Makefile, verify.sh), cartographer/stage2_stego/ (binary + both
carriers), the two src/state edits (policy.h, test_part2.c), .gitignore, and
both protocol logs. The hash is not hardcoded here (amending this log would
change it); run `git -C /home/manish/cartographer-build log --oneline` for the
authoritative list (the Phase-2 commit is 0a7664c; the Phase-3 commit is its
child).
[PASS] escalation does not touch the debugger flag
[PASS] a persisted debugger flag selects the extended audit variant
[PASS] a persisted debugger flag does NOT corrupt the real verdict
[PASS] debugger flag is preserved across the stage 2 run
[PASS] shipped binary carries the decoy flag, the spent-press note, the audit text and the mark prefix
[PASS] real reading absent from the binary
[PASS] stage 1 real key absent from the binary
[PASS] press formula is not in the binary (tape only)
[PASS] canonical HMAC key hex absent from binary
[PASS] no sweep constants or pixel-stride logic are compiled into the binary
[PASS] carriers leak neither the reading nor the sweep constants
[PASS] the sheet's own field note spells the sweep rule (deterministic resolution)
[PASS] package left pristine (test state removed)
[PASS] no writes outside the working directory

== 71 tests run, 0 failed ==
ALL TESTS PASSED
```