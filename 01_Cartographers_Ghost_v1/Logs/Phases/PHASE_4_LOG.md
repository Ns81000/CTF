# PHASE 4 LOG — Stage 3: The Cipher Oracle (local rate-limited chosen-plaintext cipher)

Status: COMPLETE — all verifications passing (33/33 stage-3 end-to-end checks,
27/27 state-library regression, 36/36 stage-0 regression, 8/8 + 65/65 stage-1
regression, 58/58 + 71/71 stage-2 regression, REGEN-DETERMINISTIC-OK,
HEADER-DETERMINISTIC-OK, ORACLE-REGEN-REPRODUCIBLE-OK, SCRUB-CLEAN, solver-eye
smoke run). Repo: /home/manish/cartographer-build (git branch `main`).
Session date: 2026-09-19/20.

## 0. Protocol confirmation (Session Continuity Protocol)

Before writing any code or running any build command, this session:

1. READ the full build spec start to end: d:\gandu\01_BUILD_PROMPT_FOR_CLAUDE_CODE.md
   (all 164 lines, in chunks; identical copy at
   /home/manish/cartographer-build/docs/BUILD_SPEC.md).
2. READ PHASE_0_LOG.md, PHASE_1_LOG.md, PHASE_2_LOG.md and PHASE_3_LOG.md IN
   FULL, in order (every section, in chunks).
3. INDEPENDENTLY re-verified Phases 0-3 FIRST — reproduced, did not trust the
   logs: `bash /home/manish/cartographer-build/src/stage2_stego/verify.sh`
   (run twice, serially). First run: state 27/27; stage0 36/36; stage1 8/8 +
   65/65; stage2 58/58 + 71/71; REGEN-DETERMINISTIC-OK;
   HEADER-DETERMINISTIC-OK; three identical stage2_stego sha256 lines
   (5058a901eddbd9bc539ba27168c401fbdffd49409d6a82e4bfecd080438a8e4e,
   62,728 B); SCRUB-CLEAN; solver-eye smoke run. All anchors matched, so no
   repair work was needed before Phase 4 began. Suites ran SERIALLY (they
   share cartographer/.cartographer_state).

## 1. What was built (exact paths, all in /home/manish/cartographer-build)

Authoring pipeline: the editor wrote staging files d:\gandu\_stage\s3_*; a
one-shot copy script (d:\gandu\_stage\s3_sync.sh, run as
`tr -d "\r" < /mnt/d/gandu/_stage/s3_sync.sh | bash`) copied them into the
repo with CRLF->LF normalisation. Repo copies are canonical.

- src/stage3_oracle/gen_oracle_constants.py — GENERATOR (INTERNAL, not
  shipped): deterministically builds both masked KDF seeds, the two round
  functions' fold tables (with planted 2^-2 collision sets), the mix
  constants and oracle_layout.json. In-memory self-checks BEFORE writing:
  (a) each table's accept set is exactly 64 of 256 values for its planted
  difference and its fix-up converges, (b) accidental same-window collision
  counts stay < 24 for all non-planted differences, (c) mix bijection probe,
  (d) empirical characteristic check — 30,000 pairs per (round-function,
  window): completions at 2^-4 within 4 sigma for all 8 planted deltas, and
  round-1 predicate equivalence over 4,000 probes. Runtime ~8 s;
  byte-reproducible.
- src/stage3_oracle/oracle_blob.h — GENERATED + committed: the two masked KDF
  seeds (kMaskedSeedReal / kMaskedSeedPoison), the two mask seed STRINGS
  (D4 convention: a mask alone reveals nothing), and the eight 256-byte fold
  tables kFold{A,B}{0..3}. The ACCEPT sets are NOT shipped (derivable from
  the shipped tables by anyone who reverses the round function; kept in
  oracle_layout.json for internal tooling).
- src/stage3_oracle/oracle_layout.json — GENERATED + committed (INTERNAL):
  machine-readable mirror (tables, accepts, planted bits/deltas, mix
  description, KDF seed digests) used by the model, the attack driver and
  the suite.
- src/stage3_oracle/oracle.c — THE DELIVERABLE MAIN (~341 lines): CLI, KDF,
  poison key derivation, the 4-round alternating Feistel-ish cipher, decoy
  routing, escalation presentation, usage text with the deliberate
  byte-order ambiguity (D51).
- src/stage3_oracle/model_oracle.py — INDEPENDENT python implementation of
  the cipher (INTERNAL, not shipped): --selftest, --keys, --enc,
  --poison-enc, --stats, --attack-json. Carries the differential attack
  (per-byte score voting + twin-pair resolution + offline finish).
- src/stage3_oracle/solve_attack.py — attack driver (INTERNAL): --model,
  --model-true, --mixed, --poison-converges, --bin (real-binary collection
  with alternating 0.4/3.6 s pacing), --fast-demo (scripted-fast poison
  exposure).
- src/stage3_oracle/test_stage3.sh — 33-check end-to-end verification suite.
- src/stage3_oracle/verify.sh — Phase 4 clean-room verification driver
  (normalizes the registry, rebuilds the state library, regenerates
  constants, builds the oracle, runs the stage-3 suite, then runs the Phase
  0-3 clean-room verification SERIALLY, then reproducibility + scrub +
  inventory + solver-eye smoke run).
- src/stage3_oracle/policy_patch.py — idempotent normalizer for the state
  library's decoy registry (see D50; repairs any earlier 4-row attempt).
- src/stage3_oracle/Makefile — musl static build + strip + scrub; test target.
- src/state/policy.h — stage-3 decoy row added (D50); mechanism untouched;
  CARTO_DECOY_TABLE_LEN 2 -> 3.
- src/state/test_part2.c — test_decoy_count extended (LEN >= 3, row 2
  stage == 3); test_decoy_lookup unchanged (already table-driven, D43).
- cartographer/stage3_oracle/oracle — THE DELIVERABLE BINARY (58,632 bytes;
  sha256 93bb876e7c7adcb730cfba0382e4a40609aed74d424283da4c02451d27351528;
  reproducible across clean rebuilds).
- logs/PHASE_4_LOG.md, logs/KICKOFF_PHASE_5.md, logs/p4_vectors.txt (cipher
  test vectors; internal).

Solver package layout: the binary lives at cartographer/stage3_oracle/oracle
and is run FROM the cartographer/ package root (same convention as Stages
0-2); it passes "./.cartographer_state" explicitly, so the state file stays
at the package root (spec tree).

Relink note (expected, verified): adding the stage-3 decoy row to policy.h
changed libstate.a, so Stage 0/1/2 were relinked (sizes unchanged: 66,840 /
62,728 / 62,728 bytes) and ALL their suites were re-run green. New sha256s:
  stage0_start 2d5ce3c15eca52d496d59b9c863034bb77daef7c02b6d514fdb5a40ec311fa7c
  stage1_vm    d56725ef995c66418c77ad3eddd82aed1c088755a467f834aa0d442cc355eb91
  stage2_stego 18043e634bf55305425db15551aa89d9a6565b0cf18d4e9dca533f476070b7db
Carriers are byte-identical (survey_frame.png 46,258 B; survey_tape.wav
8,152 B; regeneration still byte-deterministic). Any future log that pins
stage0/1/2 hashes must use these new values.

## 2. Design decisions and why

D46. STAGE 2 -> STAGE 3 HAND-OFF (answers PHASE_3_LOG section 9 question 1,
     DECIDED): the oracle's cipher key derives at RUNTIME from the Stage 2
     READING handed in with -r, NEVER from a submittable token.
       digest = SHA-256(seed_real || reading_bytes)             (32 bytes)
       kA = BE32(digest[0..3]);  kB = BE32(digest[4..7])        (64-bit key)
     Rationale: (a) the reading is what the solver physically extracted from
     the sheet — the thing the chain of custody actually turns on; (b) no
     submittable string doubles as key material (PHASE_2_LOG open question #2
     reserves the "transformed Stage 1 real output" for Phase 5; the Stage-2
     checkpoint token stays a checkpoint); (c) a WRONG reading yields a
     DIFFERENT well-formed key, so every oracle answer stays well-formed and
     self-consistent, and the mistake surfaces only when the Phase-5 validator
     refuses the assembled flag — the same "garbage, not an error" shape Stage
     2 uses. The oracle is gated on NOTHING: it answers for any reading, any
     figure, any state (fresh/human/uniform/debugger/tampered). A missing -r
     prints usage (rc 0, stderr silent) — a missing argument, not a dead end.


D47. THE CIPHER (hand-rolled, NOT textbook): 64-bit block, two 32-bit halves
     (L high, R low); 4 rounds; alternating round functions; NO final swap.
       round r: (L,R) -> (R, L ^ G_{r&1}(R ^ k_{r&1}))
       G_A used at rounds 1,3 (subkey kA);  G_B at rounds 2,4 (subkey kB)
       G_Z(y) = M_Z( y ^ fold_Z(y) )
       fold_Z(y) = T_Z0[(y>>0)&0xFF] ^ T_Z1[(y>>8)&0xFF] << 8
                 ^ T_Z2[(y>>16)&0xFF] << 16 ^ T_Z3[(y>>24)&0xFF] << 24
     T_{Z,j} are eight 256-byte tables (shipped in oracle_blob.h; the whole
     point is that a solver CAN reverse them); M_A/M_B are strong 32-bit
     bijections (xorshift / odd-multiply / rotate; distinct constants).
     PLANTED BIAS: for each (Z,j) exactly 64 of 256 table values W satisfy
     T[W] ^ T[W^dw] == dw for the planted byte-difference dw = 1<<b_Zj
     (density 2^-2). A difference confined to window byte j therefore cancels
     the fold — and so the whole round-function output difference — with
     probability 2^-2, while nonzero difference is spread by M and hides any
     other structure at ~2^-32.
     WHY 4 ROUNDS: the two iterative characteristics
        (0,delta) <-> (delta,0)  for delta = delta_{A,j}  (hits at r1,r3)
        (delta,0) <-> (0,delta)  for delta = delta_{B,j}  (hits at r2,r4)
     complete at 2^-4 (two 2^-2 F-hits). That gives ~1 completion per 16
     pairs, so the recorded N_REQUIRED stays ~2560 pairs. A 6-round variant
     was built and measured first: at 2^-6 completions the per-window hit
     count over a feasible query budget was too small for reliable byte
     recovery (~8000 pairs, ~2-4 h of paced queries) — rejected as
     disproportionate to the 2-3 h whole-puzzle budget. 4 rounds also keeps
     the puzzle honest: with alternating keyed round functions there is no
     MITM split (forward 2 rounds needs BOTH subkeys; backward 2 likewise),
     and 2^64 offline brute force is out of reach, so the differential attack
     is the economical path. (Recorded as a known, documented limitation for
     Phase 6 to re-examine — see open question 2.)

D48. AUTOMATION DETECTION / POISON (spec Phase 4): per invocation the oracle
     computes reasons = carto_should_escalate(CARTO_STAGE3, now) from the
     shared ring and poisons iff (reasons & CARTO_ESC_TIMING_UNIFORM) — the
     scripted-uniform-spacing tell — and NOTHING else.
       K_poison:  pdigest = SHA-256(seed_poison || real_digest)
                  kA' = BE32(pdigest[0..3]); kB' = BE32(pdigest[4..7])
     Poisoned answers are produced by encrypting with (kA',kB') through the
     SAME public cipher: well-formed, same shape, rc 0, stderr silent,
     deterministic, and self-consistent (same figure -> same poisoned answer).
     It is NEVER a coin flip and it is falsifiable three ways: (a) the same
     figure asked under a human-paced state answers differently; (b) a
     dataset that mixes clean and poisoned pairs does not converge (the attack
     reports NO-CONSENSUS); (c) a wholly poisoned dataset still yields a
     consistent key — the POISON key — that simply fails at the Phase-5
     validator. Crucially, poison deliberately does NOT key off
     CARTO_ESC_TIME_FAST (a fresh-state solver would otherwise be poisoned
     from the start — unfair) nor off the persisted debugger flag (already
     punished in Stage 1). The three escalation reasons still select the
     presentation variant (D49).

D49. ESCALATION VARIANTS (D44 pattern): reasons != 0 selects the "witnessed"
     presentation (one extra flavor line); the answer is BIT-IDENTICAL to the
     "plain" variant. Verdict/answer invariance is proven by the suite
     (human state -> plain, real key; uniform state -> witnessed, poison;
     the key choice depends only on TIMING_UNIFORM).


D50. DECOY REGISTRATION (D29/D43 pattern) — and one REJECTION worth recording.
     REGISTERED: one stage-3 row, branch 1:
       { 3, "CARTO{b27692a0d5f63d4f1a0c3fb79afbf81b}", 1u }
     i.e. the Stage-2 checkpoint token fed back as the oracle reading — the
     most natural lazy path ("Carry it to the oracle" -> hand the checkpoint
     straight back). Feeding it as -r routes into the extended decoy branch
     ("this ink is a checkpoint, not a reading ... the oracle will still turn
     figures for it, but under the ink you handed over, not under the sheet's"),
     persists bit 1<<(branch-1) in the state file, and STILL ANSWERS every
     figure — never an error, and never a gate. CARTO_DECOY_TABLE_LEN 2 -> 3.
     REJECTED (with evidence): registering the Stage-1 token
     (CARTO{fd3e8049dfdfc32efe22fe823822b8c0}) as a second stage-3 decoy. A
     first attempt did register it (LEN 4, branches 1-2) and it was caught by
     the pre-existing Phase-1/Phase-2 absence assertions: policy.h rows are
     compiled into EVERY stage binary, and the Stage-1 token's content is the
     first 16 bytes of the REAL Stage-1 key material, so registering it leaks
     half of a real answer into solver-facing material (stage1's own suite
     failed "real key material leaked into the binary" / "real token leaked
     into the binary"; stage2's failed "stage 1 real key leaked into the
     binary"). The Stage-2 checkpoint token is safe by contrast: it is a
     one-way digest checkpoint (PHASE_3_LOG D42) that reveals nothing about
     the reading. Net effect: exactly one stage-3 decoy, no cross-stage answer
     leakage, zero changes needed to Phases 1-3 test suites. policy_patch.py
     is an idempotent normalizer that establishes (and can repair) this end
     state.

D51. HUMAN TRAP (spec Phase 4: help text that is technically true but easy to
     misread). The usage text describes the input as "sixteen hex letters,
     eight bytes to the block, one byte to a pair as the sheet wrote them.
     Hand them over as they stand -- the head pair opens the block. The ledger
     files every figure under the tail it came in with, and the oracle does
     not swap your letters: it answers in the same order you handed them
     over." Every clause is true: the parse is strictly as-written (first hex
     pair = most significant byte of the 64-bit block), the answer is printed
     in the same order, and the oracle never byte-swaps. The trap is the
     adjacent phrasing ("tail it came in with", "head pair opens the block")
     tempting a hasty reader to transpose byte order while transcribing;
     the failure is consistent-looking (every answer off) and resolves on one
     careful test — a real tax on careless reading, not a coin flip. Two
     suite checks pin the intended semantics (zero-padded 16-hex figure
     parses == model; the oracle never swaps).

D52. THE ATTACK, ITS SAMPLE SIZE, AND A STRUCTURAL FINDING.
     Characteristics: exp-A plaintext difference (0, delta_{A,j}); exp-B
     (delta_{B,j}, 0), delta_{Z,j} = 1 << (8j + b_{Zj}); b_{Aj} = j
     (block bits 0,9,18,27); b_{Bj} = (j+4)%8 (bits 4,13,22,31).
     Hit predicate (round 1 for A, round 2 for B): W_j(x ^ k_Z) in ACCEPT_Zj,
     where x is the known right half (A) or the computable x = R1 =
     L0 ^ G_A(R0 ^ kA) (B, once kA is known — the sequential structure the
     two experiments exploit).
     STRUCTURAL FINDING (found while driving the suite green): a
     zero-difference (collision) plant is INHERENTLY PAIRING-SYMMETRIC — if W
     is accepted then so is W^dw — so every honest hit set contains BOTH the
     true byte and its dw-twin, and no number of hits resolves the last bit of
     any byte. Correct engineering: recover each byte as a {b, b^dw} PAIR
     (score-voting with a tolerance for stray alternative-path completions),
     then finish OFFLINE by enumerating the 2^4 kA twins x 2^4 kB twins = 256
     candidates against collected pairs (no further queries). Verification of
     a candidate key is purely offline (reproduce the oracle's own answers) —
     there is deliberately NO key-check mode in the binary, so brute force
     cannot feed on cheap yes/no feedback.
     N_REQUIRED = 2560 chosen-plaintext pairs = 8 experiments x 320 pairs.
     Derivation: per-window completions = pairs/16 (2^-4); 320 pairs -> ~20
     hits/window (score vote needs >= 4 and >= hits-3); 4 windows x 2 subkeys
     = 8 experiments. At a human-plausible ~2 s average spacing that is ~85 min
     of queries; a scripted uniform loop is silently poisoned (D48). The
     suite proves recovery end-to-end on the model at exactly this budget
     (true key AND poison key), plus NO-CONSENSUS on mixed data. Real-binary
     2560-pair collection is deferred to Phase 6 (timing calibration).


D53. BUILD PIPELINE + VERIFICATION (per spec, same recipe as Stages 0-2):
     musl-gcc -O2 -Wall -Wextra -std=c11 -static -fno-ident (oracle.c +
     ../state/libstate.a) -> strip --strip-all -> objcopy --remove-section
     .comment. Deliverable reproducible: clean rebuilds produce the identical
     sha256 93bb876e...351528 (58,632 B). D38 PATTERN COMPLIANCE: the binary
     carries the MASKED KDF seeds (obfuscated, never plaintext), the public
     fold tables, and the decoy row via policy.h — but NO derivation seed
     strings ("cartographer-ghost:stage3:*" are absent, asserted), no
     key-check mode, and no readable reading. The KDF seeds ship only masked;
     the mask seed STRINGS ship (D4 convention: a mask alone reveals nothing).
     The 33-check suite covers: binary hygiene (static/stripped/scrub/key-and-
     seed absence/masked-seed presence by byte match), CLI discipline (9 paths,
     all rc 0 + stderr silent, including the poison path), human/trap semantics
     (zero-padded figure == model), the poison triad (poison == model
     poison-enc; poison != real; poison self-consistent), the state lifecycle
     (352 B, independent HMAC, attempt_count[3] 1 then 2, decoy bit 0), the
     model cross-check (bit-exact on 4 figures), the three attack proofs
     (N=2560 true-key recovery; poison-dataset recovery; mixed NO-CONSENSUS),
     and reproducibility.

## 3. Every constant introduced (exact values + locations)

KDF / mask material (gen_oracle_constants.py; masked forms in oracle_blob.h):
- KDF derivation seeds (NEVER compiled into any binary; asserted absent):
    seed_real   = SHA-256("cartographer-ghost:stage3:cipher-key:v1")
                = 6c6468b68883d18610b74f23a5127c325cd676874ee2ce5853843701a10d8f1f
    seed_poison = SHA-256("cartographer-ghost:stage3:poison-key:v1")
                = cfa0a5e87807fae28f0f1a95d3e160f26e82064d9d4dd7c879c334558a8b221d
- Mask seed strings (DO ship; D4 convention):
    "cartographer-mask-stage3-real", "cartographer-mask-stage3-poison"
    mask_real   = SHA-256("cartographer-mask-stage3-real")
    mask_poison = SHA-256("cartographer-mask-stage3-poison")
- Masked seeds as shipped in oracle_blob.h:
    kMaskedSeedReal   = 4496ad38044364c0b01831c50bc9774fad1d2964c286bb5720234afb16ebb439
    kMaskedSeedPoison = 74b965966f097b1161038e05e03f176f52b307f7615da98c65bde9c136ba2314
- Fold-table seed (generator + this log only):
    "cartographer-ghost:stage3:fold-tables:v1"
- Mix constants: M_A = (x^=x>>16; x*=0x85EBCA6B; x^=x>>13; x*=0xC2B2AE35;
    x^=x>>16; rotl(x,7)); M_B = (rotl(x,17); x^=x>>15; x*=0x2545F491;
    x^=x>>14; x*=0x9E3779B1; x^=x>>16).
- Cipher shape: BLOCK 64 bits; ROUNDS 4; WINDOWS 4 (byte j of the 32-bit
    F-input); T tables 8 x 256 bytes; ACCEPT size 64/256 per table (p = 2^-2);
    planted bits b_{Zj} = j for A, (j+4)%8 for B.
- Planted deltas: A = 0x1, 0x200, 0x40000, 0x8000000 (block bits 0,9,18,27);
    B = 0x10, 0x2000, 0x400000, 0x80000000 (bits 4,13,22,31; the last is the
    high bit of the low 32-bit half, applied to the LEFT half in the figure).
- N_REQUIRED = 2560 pairs (8 experiments x 320); completions/pair = 2^-4;
    offline finish = <= 2^8 candidates.
- Attack thresholds (model_oracle.py): TOLERANCE = 3, MIN_SCORE = 4.
- CLI: -r <reading> (<= 512 bytes) + 16-hex <figure>; rc 0 always; stderr
    always silent.

KDF worked example (reading = CARTO{no_figure_sits_in_every_pixel}):
    real:   kA = 0x73070925,  kB = 0xa159f9e2   (master K = 73070925a159f9e2)
    poison: kA = 0x0fab2971,  kB = 0x10c73e9f
    (kB=0x10c73e9f ... note the poison subkeys are derived from the REAL digest.)

Cipher test vectors (real key / poison key), also in logs/p4_vectors.txt:
    0123456789abcdef  real 2a7479540c7163e3   poison 0adb9b08b2e01566
    ffffffffffffffff  real 50175fafe8292077   poison 069b3aa438ddce7a
    0000000000000000  real aad1a962b4e66bf8   poison 9237bb2735b4bdcf
    123456789abcdef0  real 4629fae7c6ee6bba   poison 9db6674f210a6fa7
    00000000000000ff  real c4faca6134049afb   poison de70072e2be2adda
    deadbeefcafebabe  real cc634fb39d0b7105   poison 64c8fc37a7076047

Stage-3 decoy (registered, policy.h): { 3, "CARTO{b27692a0d5f63d4f1a0c3fb79afbf81b}", 1u }
    (the Stage-2 checkpoint token; persisted bit 1<<(1-1) = bit 0.)

FLAG-FORMAT / KEY POLICY (unchanged from Phases 1-3): every minted string is
^CARTO\{[a-z0-9_]{8,64}\}$ (D11); ONE canonical HMAC key shared by all stage
binaries (D13); CREATED == TAMPERED at runtime (D14); no threshold in
policy.h was touched (CARTO_T_FAST_SEC_DEFAULT 90 s, CARTO_STDDEV_LOW_MS
1500 ms, CARTO_MIN_TIMING_DELTAS 4 remain Phase-0 placeholders — Phase 6
calibrates).


## 4. Exact commands (runnable verbatim)

C31. Sync the staged Phase 4 sources into the repo (CRLF->LF normalised):
wsl.exe -d Ubuntu-24.04 -- bash -c 'tr -d "\r" < /mnt/d/gandu/_stage/s3_sync.sh | bash'

C32. Normalize the decoy registry (idempotent; sets 3 rows + LEN 3):
wsl.exe -d Ubuntu-24.04 -- bash -c 'cd /home/manish/cartographer-build/src/stage3_oracle && python3 policy_patch.py'

C33. State-library regression (27 checks; MUST precede the stage builds):
wsl.exe -d Ubuntu-24.04 -- bash -c 'cd /home/manish/cartographer-build/src/state && make clean && make test'

C34. Regenerate the constants and build the oracle:
wsl.exe -d Ubuntu-24.04 -- bash -c 'cd /home/manish/cartographer-build/src/stage3_oracle && python3 gen_oracle_constants.py && make'

C35. THE Phase 4 build + verification (33 end-to-end checks):
wsl.exe -d Ubuntu-24.04 -- bash -c 'cd /home/manish/cartographer-build/src/stage3_oracle && bash test_stage3.sh'

C36. THE whole clean-room verification (stage-3 suite, then Phases 0-3
     serially, then reproducibility + scrub + smoke). This is what produced
     section 5:
wsl.exe -d Ubuntu-24.04 -- bash -c 'bash /home/manish/cartographer-build/src/stage3_oracle/verify.sh'

C37. Manual solver-eye smoke (from the package root):
wsl.exe -d Ubuntu-24.04 -- bash -c 'cd /home/manish/cartographer-build/cartographer && rm -f .cartographer_state && ./stage3_oracle/oracle && ./stage3_oracle/oracle -r "CARTO{no_figure_sits_in_every_pixel}" 0123456789abcdef && ./stage3_oracle/oracle -r "CARTO{b27692a0d5f63d4f1a0c3fb79afbf81b}" 0123456789abcdef'

C38. The three attack proofs (standalone; model-side):
wsl.exe -d Ubuntu-24.04 -- bash -c 'cd /home/manish/cartographer-build/src/stage3_oracle && python3 solve_attack.py --model-true --pairs-per-window 320 && python3 solve_attack.py --poison-converges && python3 solve_attack.py --mixed'

C39. Model self-checks and bias measurement:
wsl.exe -d Ubuntu-24.04 -- bash -c 'cd /home/manish/cartographer-build/src/stage3_oracle && python3 model_oracle.py --selftest && python3 model_oracle.py --stats'

C40. Real-binary poison exposure (12 identical scripted-fast queries) and the
     paced real-vs-model cross-check (Phase 6 timing work uses these):
wsl.exe -d Ubuntu-24.04 -- bash -c 'cd /home/manish/cartographer-build/src/stage3_oracle && python3 solve_attack.py --fast-demo 12'
wsl.exe -d Ubuntu-24.04 -- bash -c 'cd /home/manish/cartographer-build/src/stage3_oracle && python3 solve_attack.py --bin --pairs 8'

## 5. Verification run — full real output

(a) C35, the stage-3 suite (verbatim, 33/33):

```
== stage3_oracle end-to-end verification ==
[PASS] oracle exists and is executable
[PASS] statically linked
[PASS] stripped (no symtab)
[PASS] no compiler/path residue
[PASS] canonical HMAC key absent
[PASS] KDF derivation seeds absent
[PASS] masked KDF seed present in binary
[PASS] no args: rc 0, stderr silent
[PASS] -r only: rc 0, stderr silent
[PASS] figure only: rc 0, stderr silent
[PASS] malformed figure: rc 0, stderr silent
[PASS] too-long figure: rc 0, stderr silent
[PASS] clean query: rc 0, stderr silent
[PASS] human state: oracle == model on 0123456789abcdef
[PASS] human state: oracle == model on ffffffffffffffff
[PASS] human state: oracle == model on 0000000000000000
[PASS] human state: oracle == model on 123456789abcdef0
[PASS] zero-padded 16-hex figure parses == model
[PASS] uniform state: poison key served (== model poison-enc)
[PASS] poison answer differs from the real-key answer
[PASS] poison is self-consistent (same figure -> same answer)
[PASS] stage-2 token as reading: rc 0 silent
[PASS] stage-1 token as reading: rc 0 silent
[PASS] wrong reading: rc 0 silent
[PASS] state file created (352 bytes)
[PASS] state HMAC valid (independent python)
[PASS] attempt_count[3] == 1
[PASS] attempt_count[3] == 2 after second run
[PASS] stage-3 decoy bit 0 persisted
[PASS] attack recovers true key (N=2560)
[PASS] poisoned dataset self-consistent (wrong key)
[PASS] mixed dataset fails to converge (falsifiable)
[PASS] oracle rebuild reproducible (identical sha256)

== 33 passed, 0 failed ==
ALL TESTS PASSED
```


(b) C36, the aggregated clean-room output (anchor lines):

```
== 33 passed, 0 failed ==            (stage3_oracle)
ALL TESTS PASSED
== 27 tests run, 0 failed ==         (state library, 3 decoy rows)
ALL TESTS PASSED
== 36 tests run, 0 failed ==         (stage0_start)
ALL TESTS PASSED
== 65 tests run, 0 failed ==         (stage1_vm; the 8/8 verdict checks run first)
ALL TESTS PASSED
== 58 vectors run, 0 failed ==       (s2_inflate differential)
ALL TESTS PASSED
== 71 tests run, 0 failed ==         (stage2_stego)
ALL TESTS PASSED
REGEN-DETERMINISTIC-OK
HEADER-DETERMINISTIC-OK
SCRUB-CLEAN
############ done ############
ORACLE-REGEN-REPRODUCIBLE-OK
SCORE: build1=93bb876e7c7adcb730cfba0382e4a40609aed74d424283da4c02451d27351528 build2=<same>
############ done ############
```

(c) C38, the three attack proofs (verbatim):

```
model key   : 73070925a159f9e2
pairs used  : 2560 (320 per experiment)
hits A      : [18, 17, 18, 17]
recovered   : 73070925a159f9e2
hits B      : [22, 23, 32, 24]
cands       : {'A0': [36, 37], 'A1': [9, 11], 'A2': [3, 7], 'A3': [115, 123],
               'B0': [226, 242], 'B1': [217, 249], 'B2': [25, 89], 'B3': [33, 161]}
VERIFIED
poisoned dataset -> KEY=0fab297110c73e9f
POISON-KEY-RECOVERED (self-consistent wrong dataset)
mixed dataset: 48 clean + 48 poisoned pairs
NO-CONSENSUS (mixed data falsifies deterministically)
```
(note: the 'cands' entries are exactly the {b, b^dw} twin pairs of D52.)

(d) C39, model self-checks and measured bias:

```
SELFTEST OK (accept sets, mix injectivity, kdf anchor)
planted delta 00000001: 1872 completions in 30000 pairs (want 1875 +- 168)
non-planted delta 00000002: 2 completions in 20000 pairs (want ~0)
STATS OK
```

(e) generator self-checks (C34, verbatim):

```
tables built; self-checks passed
planted deltas A: ['0x1', '0x200', '0x40000', '0x8000000']
planted deltas B: ['0x10', '0x2000', '0x400000', '0x80000000']
demo reading kdf: kA=73070925 kB=a159f9e2
demo poison keys: kA=0fab2971 kB=10c73e9f
oracle_blob.h + oracle_layout.json written
```

(f) artifact inventory + reproducibility (verbatim):

```
-rwxr-xr-x 1 manish manish 58632 Sep 20 01:05 oracle
cartographer/stage3_oracle/oracle: ELF 64-bit LSB executable, x86-64,
  version 1 (SYSV), statically linked, stripped
93bb876e7c7adcb730cfba0382e4a40609aed74d424283da4c02451d27351528  oracle
SCRUB-CLEAN
```


(g) solver-visible output (verbatim, three variants; fresh state so the
    CARTO_ESC_TIME_FAST reason selects the "witnessed" presentation):

```
===USAGE===
======================================================================
  THE CARTOGRAPHER'S GHOST
  Stage 3 -- The Cipher Oracle
======================================================================

Past the sheet, the survey turns to figures. Somewhere in
the dark of the map room an engine answers every figure with
a figure, and keeps its own counsel about what they mean.

  oracle mode : witnessed

  the oracle answers only what is handed a reading.

The oracle answers figures with figures. Hand it a reading and
a figure:

    ./stage3_oracle/oracle -r '<reading>' <figure>

  <reading>  what the interior sheet yielded, handed over whole.
             The oracle keeps no reading of its own; the reading
             you carry in is the one it works from.

  <figure>   sixteen hex letters, eight bytes to the block, one
             byte to a pair as the sheet wrote them. Hand them
             over as they stand -- the head pair opens the block.
             The ledger files every figure under the tail it came
             in with, and the oracle does not swap your letters:
             it answers in the same order you handed them over.

Every figure receives an answer, and no answer is ever refused;
nothing about a wrong reading is an error here. The oracle only
turns figures. What an answer is worth is decided further up the
survey, where figures are read.
===CLEAN (real reading, human-paced)===
  witnessed: the engine turns whether you watch it or
  not.

  the oracle answers:

    2a7479540c7163e3
===DECOY (stage-2 checkpoint token as reading)===
  re-inked checkpoint (branch 1):

    CARTO{b27692a0d5f63d4f1a0c3fb79afbf81b}

  witnessed: the engine turns whether you watch it or
  not.

  the oracle answers:

    8e7737de894ee908
```
(a white reading is never an error: an unknown reading simply yields the
answer for the key it derives; a malformed figure gets a plain
"the figure does not read" line; all rc 0, stderr silent.)

## 6. Bugs found and fixed DURING Phase 4

1. SIX-ROUND DESIGN REVISITED (design bug, caught by measurement): the first
   cipher was 6 rounds, giving 2^-6 completions (1 per 64 pairs). Measured
   with the real attack at 320 pairs/window: hits per window 1-8, and whole
   windows failed to resolve, so recovery needed ~8000 pairs. Replaced with
   the 4-round alternating scheme (2^-4 completions) so N_REQUIRED stays
   2560; recorded in D47 with the reasoning, and flagged for Phase 6.
2. PAIRING-SYMMETRY DEADLOCK (structural bug, found by driving the suite
   green): strict per-byte intersection always returned EMPTY (later,
   ambiguous) because a collision plant accepts W and W^dw together, so the
   true byte's last bit is never constrained. Fixed by score-voting (tolerant
   of stray alternative-path completions) + explicit {b, b^dw} twin pairs +
   a <=2^8 offline finish. See D52.
3. TEST-SUITE FALSE FAILURES FROM THE POISON ITSELF (harness bug): the first
   suite run showed "oracle != model" on 3 of 4 figures. Diagnosis: the
   suite's own rapid-fire queries drove the ring uniform, so the oracle was
   correctly serving the POISON key. Confirmed by comparing the oracle's
   answer (069b3aa438ddce7a) against the model's poison-enc (match) and
   real-enc (no match). Fixed by forging a HUMAN-paced state before each
   real-key comparison and adding explicit poison assertions. This was the
   automation detection working exactly as specified.
4. DECOY REGISTRATION LEAK (design bug, caught by the earlier phases' own
   assertions): registering the Stage-1 token as a stage-3 decoy shipped the
   first half of the REAL Stage-1 key material into every binary via
   policy.h; stage1 and stage2 suites failed their absence assertions.
   Fixed by registering ONLY the one-way Stage-2 checkpoint token; documented
   in D50 and enforced by the idempotent policy_patch.py normalizer.
5. MAKEFILE STALE TARGET: the first Makefile copied a "stage3_oracle_blob.h"
   that the generator never writes (it writes oracle_blob.h), so `make` built
   the binary then failed on the copy. Fixed by dropping the redundant copy
   target and making oracle_blob.h the dependency of the binary.
6. TEST-HARNESS STALENESS: the suite's "static/musl" check grepped for the
   string "musl" (absent from a stripped static ELF) and its
   fold-table/masked-seed presence checks grepped for SYMBOL NAMES (removed
   by strip). Fixed: grep "statically linked"; verify the masked seed by
   comparing its 32 bytes (extracted from oracle_blob.h) against the binary.
7. EDITOR/CRLF AUTHORING HAZARDS (environment; repeats PHASE_2/PHASE_3
   lessons): the editor writes CRLF, so every staged shell script must be
   normalised before running (s3_sync.sh does it; scripts that run directly
   from /mnt/d must go through `tr -d "\r"`). One large editor write produced
   a truncated/escaped s3_test_stage3.sh; it was deleted and rebuilt in small
   anchored chunks, then syntax-checked (`bash -n`) and byte-inspected before
   use. WSL /tmp was wiped mid-session again (use $HOME or the repo for
   anything worth keeping).



## 7. Explicitly NOT done / deferred

- Phase 5 (Stage 4 assembly riddle + constant-time validator), Phase 6
  (calibration + self-testing + SOLVE_PATH_PRIVATE.md), Phase 7 (packaging,
  README_FOR_SOLVER, HINTS, room text).
- REAL-BINARY 2560-pair collection is NOT exercised end-to-end: the attack is
  proven at exactly N=2560 against the model (which is cross-checked
  bit-exactly against the shipped binary on live queries), and the real
  binary is exercised for the poison triad and the paced cross-check
  (--bin --pairs 8). Running the full 2560-pair paced attack against the
  binary takes ~85 min and is Phase 6's timing-calibration job (C40 with
  --pairs 2560 and a real reader).
- No threshold calibration: CARTO_T_FAST_SEC_DEFAULT (90 s),
  CARTO_STDDEV_LOW_MS (1500 ms), CARTO_MIN_TIMING_DELTAS (4) remain Phase-0
  placeholders per D10/D43. The poison's false-negative/positive edges (a
  genuinely human solver's spacing distribution vs a jittering script) are
  Phase 6 measurements.
- Solver-facing documentation of the Stage-3 CLI is deferred to Phase 7 (the
  CLI is described in the tool's own usage text and fully tested here).
- The DEEPENED DECOY DEAD END (PHASE_3_LOG D41) remains Phase 6 work; Stage 3
  adds one more discoverable decoy step to that chain but does not deepen it.
- The 4-round cipher's MITM/brute-force margin is argued (alternating keyed
  rounds defeat forward/backward splitting; 2^64 infeasible) but NOT proven
  against a determined offline attacker; Phase 6 may revisit (open question 2).
- Assumed-but-unverified: NOTHING in Phase 4 scope — every claim above was
  produced by a command whose real output is pasted in section 5 (or
  summarised in section 6 with its exact command in section 4).

## 8. Open questions / judgment calls for the next session

1. PHASE 5 ASSEMBLY INPUTS (must be decided and validated in Phase 5):
     - "transformed Stage 1 real output": still reserved per PHASE_2_LOG
       question 2; proposal remains bytes 16..23 of the real key as 16 hex
       chars, or a rotation that is NOT the Stage-1 token content.
     - "real Stage 2 payload": the reading CARTO{no_figure_sits_in_every_pixel}.
     - "Stage 3 cipher key": the 64-bit master K = 73070925a159f9e2 (kA||kB).
       NOTE the oracle never stores or prints K, there is no key-check mode,
       and K is recovered only by the differential attack. Phase 5 must
       therefore accept K as an INPUT (like Stage 2 accepts the reading) and
       verify the assembly through the final validator's stored hash — do NOT
       add an oracle mode that reveals or checks K (that would hand the puzzle
       over and re-introduce a brute-force oracle).
2. PHASE 6 CALIBRATION of N_REQUIRED (2560) against real timing: measure the
   actual human/jitter spacing distribution, confirm a jittering script can
   survive CARTO_STDDEV_LOW_MS without a multi-hour query budget, and decide
   whether the 4-round choice should be re-tuned (or the poison threshold
   widened) so a clean solver's Stage-3 cost lands in the 1-2 h band.
3. PHASE 6: does the poison's TIMING_UNIFORM-only trigger need the
   CARTO_MIN_TIMING_DELTAS (4) figure revisited? A solver whose first few
   queries are clean then poisons is the designed experience; confirm the
   observable "scripted vs manually-timed" mismatch is cheap enough to
   discover (it is: same figure, two states, two answers).
4. PHASE 6/7: SCORING — unchanged recommendation (score only the Stage-0 flag
   and the final assembled flag; tokens/readings are in-challenge checkpoints).
5. PTRACE/SECCOMP fairness (PHASE_2_LOG question 5) still open; Stage 3 never
   trips it (it only reads the persisted flag and the ring).
6. The registered Stage-2 checkpoint token is now findable via `strings` in
   every stage binary (accepted D29/D50 trade-off). Phase 6 should confirm it
   does not shortcut any stage (it does not: nothing consumes the token; the
   oracle consumes the READING).

## 9. Git commit for Phase 4

Single commit on `main`, subject:

    phase4: stage3_oracle (4-round alternating Feistel-ish oracle, planted
    2^-2 fold-table bias, runtime reading-derived key, silent uniform-timing
    poison, decoy routing) + 33-test suite; stage-3 decoy registered

containing src/stage3_oracle/* (generator, generated header + layout, oracle
main, python model + attack driver, test + verify drivers, Makefile, registry
normalizer), cartographer/stage3_oracle/oracle (the deliverable binary), the
two src/state edits (policy.h, test_part2.c), the relinked
cartographer/stage0_start/stage0_start, cartographer/stage1_vm/stage1_vm,
cartographer/stage2_stego/stage2_stego, logs/p4_vectors.txt, and both protocol
logs. The hash is intentionally not hardcoded here (amending this log would
change it); run `git -C /home/manish/cartographer-build log --oneline` for the
authoritative list (the Phase-3 commit is its parent).
