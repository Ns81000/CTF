# SOLVE_PATH_PRIVATE.md — "The Cartographer's Ghost"

**ORGANIZER-PRIVATE. NEVER SHIPPED, NEVER COMMITTED TO THE DRIVE PACKAGE.**

This is the complete internal record of the finished challenge: the full solve
path with every real value, every decoy and its recovery, the final calibrated
constants with their rationale, and the two measured calibration runs of Phase
FINAL. Anything a solver could use is in here on purpose — this file is the
reason the organizer bundle must never be mixed with the Drive zip.

Repo of record: `/home/manish/cartographer-build` (WSL2, branch `main`).
Solver package: `cartographer/` → zipped as `drive-upload/cartographer.zip`.

---

## 1. The real answer set (complete)

| # | What | Value | Where it can appear |
|---|------|-------|---------------------|
| 1 | **Stage-0 flag (scored)** | `CARTO{first_ink_in_the_ledger}` | `stage0_start` stdout, every run, ungated |
| 2 | Stage-1 key material (Stage-2 sweep input) | `fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f` | `stage1_vm` stdout, clean trace only |
| 3 | Stage-1 token (checkpoint) | `CARTO{fd3e8049dfdfc32efe22fe823822b8c0}` | minted at runtime from key bytes 0..15 |
| 4 | **Stage-2 reading** | `CARTO{no_figure_sits_in_every_pixel}` | only inside the carrier bytes |
| 5 | Stage-2 checkpoint token (checkpoint) | `CARTO{b27692a0d5f63d4f1a0c3fb79afbf81b}` | minted at runtime = sha256(reading)[0:16] |
| 6 | **Stage-3 master key K** (the attack target) | `73070925a159f9e2` (`kA`=0x73070925, `kB`=0xa159f9e2) | only after the differential attack |
| 7 | **Final title (scored)** | `CARTO{73070925a159f9e2_a5d66f1b2b5f596e_no_figure_sits_in_every_pixel}` | `validate` argv, accepted |

**Scored answers are #1 and #7 only** (rationale in section 6). Everything else
is an in-challenge checkpoint the challenge itself validates.

### The three inks of the title block (Stage 4)

`CARTO{ oracle_ink _ engine_ink _ sheet_ink }`

* **oracle ink** = the Stage-3 master K recovered as it stands: `73070925a159f9e2`
* **engine ink** = key material bytes **16..23** as 16 lowercase hex letters:
  `a5d66f1b2b5f596e` — deliberately *not* the token content (bytes 0..15),
  and the near-miss is asserted as a refusal case in the suite
* **sheet ink** = the Stage-2 reading with its frame stripped:
  `no_figure_sits_in_every_pixel`

Separator: a single underscore between neighbours. Frame: `CARTO{...}`.

### Wrong-but-well-formed keys (never stored in any binary)

| Key | Produced by | Token it mints |
|-----|-------------|----------------|
| `12f8a367b772817e805725e7292acfb694501c4f16c17ed09d614022e0be7ced` | the Stage-1 **decoy** (`.rodata` "forgotten debug constant") | `CARTO{12f8a367b772817e805725e7292acfb6}` |
| `fb48aecdda0e960831b16d45c7efbe485d69b61bda262b5c72af18d9b88d1621` | a **debugger-detected** run (steps 4081/7264 vs 4083/7266) | `CARTO{fb48aecdda0e960831b16d45c7efbe48}` |

Both are the same length and shape as the real key. Only a clean run produces
the real one, and only the Stage-2 round trip can tell the three apart.


## 2. The clean solve, step by step

Everything below is real and was executed end to end by
`src/final/run_clean_path.py` (see section 5 for the measured run).

### Stage 0 — the ledger

```bash
cd <package root>          # the folder containing README_FOR_SOLVER.txt
./stage0_start/stage0_start
```
Prints `CARTO{first_ink_in_the_ledger}` and creates `./.cartographer_state`
(352 bytes, HMAC-SHA256 signed, first_run_ms recorded). Ungated, repeatable,
no arguments.

### Stage 1 — the survey engine

```bash
./stage1_vm/stage1_vm
```
Prints `engine variant` (`coastal`/`interior`), `engine steps` (4083/7266),
`engine ledger r1 r2 r6 r7`, then the 64-hex **key material** and the
checkpoint token. On a fresh state the `CARTO_ESC_TIME_FAST` reason selects
`interior`; that is presentation only and the key is identical in both variants
(asserted by the suite).

`r6` and `r7` of the printed ledger are exactly the first two 8-byte words of
the key material read little-endian — a deliberate, free consistency check for
a solver who emulates rather than runs.

### Stage 2 — the interior sheet

Derive the sweep from the **first 16 bytes** of the key material
(`src/stage2_stego/gen_carriers.py derive()`, PHASE_3_LOG D31):


The **press** is the 56-byte raw dictionary inside the tape's `LIST/INFO/ICMT`
chunk: ASCII `interior-ink-formula-v1:` followed by the 32-byte tail
`2e032c75bee2b9952d0c6b93c77bb72b1339b377480c6a5f4e425aa36cfd7695`
(= SHA-256 of the internal seed string; the seed itself is in no binary and no
carrier). Extract it byte-exactly:

```bash
python3 -c 'b=open("stage2_stego/survey_tape.wav","rb").read(); \
i=b.find(b"ICMT"); open("press.bin","wb").write(b[i+8:i+8+56])'
```

**Do not use `exiftool -b -Comment`** — it re-encodes the binary tail and
returns 70 bytes for a 56-byte tag. `exiftool -v3 survey_tape.wav` prints the
exact bytes; a raw read obviously does too. That is the manual-step trap.

Inflate the 48-byte zlib stream with that 56-byte press as the **preset
dictionary** (`zlib.decompressobj(15, press)`), which yields

```
CARTO{no_figure_sits_in_every_pixel}
```

Hand it to the verifier, which answers and mints the checkpoint token:

```bash
./stage2_stego/stage2_stego -c 'CARTO{no_figure_sits_in_every_pixel}'
```

A solver who prefers the tool's own press mode can instead run
`./stage2_stego/stage2_stego -p press.bin -R ink.bin`, where `ink.bin` is the
framed ink exactly as drawn; the verdict is the same.

### Stage 3 — the cipher oracle

The oracle derives its cipher key **at runtime** from the reading handed in
with `-r` (never from a token):

```
digest = SHA-256(seed_real || reading_bytes)
kA = BE32(digest[0:4])   kB = BE32(digest[4:8])   ->  73070925a159f9e2
```

`K` is never stored or printed and there is deliberately **no key-check mode**;
it is recovered by differential cryptanalysis against the planted bias.

*Cipher shape*: 64-bit block, two 32-bit halves, 4 rounds, alternating round
functions, no final swap. `G_A` at rounds 1/3 with subkey `kA`, `G_B` at rounds
2/4 with subkey `kB`; `G_Z(y) = M_Z(y ^ fold_Z(y))` with eight shipped 256-byte
fold tables. For each `(Z,j)` exactly 64 of 256 table entries `W` satisfy
`T[W] ^ T[W ^ dw] == dw` for the planted byte difference `dw` (density 2^-2).

**The attack.** Eight experiments: for `Z in {A,B}` and window byte `j in 0..3`,
perturb figure byte `j` of half `Z` by the planted delta `DELTA[Z][j]` (A:
`0x1,0x200,0x40000,0x8000000`; B: `0x10,0x2000,0x400000,0x80000000`, the last
applied to the *left* half in the figure). Each experiment collects **260
pairs** (Phase FINAL-2 calibration, section 4.6), i.e. two oracle calls per
pair: `P` and `P ^ delta`.

**Total budget: 8 x 260 = 2080 pairs = 4160 oracle invocations.**
(The pre-FINAL-2 budget was 8 x 320 = 2560 pairs = 5120 calls, which at a
cautious ~2 s/query costs ~171 min — past the 180-min CTF window before any
other stage runs. That is what the FINAL-2 recalibration fixed.)

A difference confined to window byte `j` cancels the whole round-function
output difference with probability 2^-2, so the 4-round iterative
characteristic completes at 2^-4 → ~1 hit per 16 pairs → ~17 hits per window at
260 pairs. Per byte the attack score-votes over the completions (tolerance 3,
minimum score 4), keeps the `{b, b ^ dw}` twin pairs a collision plant forces,
and finishes offline over at most 2^8 candidates.

Recovered: `K = 73070925a159f9e2`. Verified bit-exactly against the independent
python model (`model_oracle.py`) in the suite.

**The poison (and how to survive it).** If the interaction ring's inter-arrival
stddev falls at or below `CARTO_STDDEV_LOW_MS`, the oracle silently switches to
a second key derived from the *same* real digest —
`K_poison = 0fab297110c73e9f` — and answers every figure under it. The poisoned
dataset is self-consistent and recovers the **poison** key, which simply fails
the Stage-4 validator. It is never an error and never a coin flip; it is
falsifiable by asking the same figure twice, once paced and once in a tight
loop, and comparing. Survival is therefore not luck: vary the inter-query

## 3. Every decoy: trigger, dead end, recovery

Four decoys are registered in `src/state/policy.h` (which is compiled into
**every** stage binary, so all four are `strings`-findable in all five binaries
— an accepted design trade-off: finding them is cheap, *confirming* which is
real is what costs). Submitting one never errors: it routes into an extended
branch, is framed as new information, persists a per-stage bit, and never
prints a real answer. Every case was driven for real by
`src/final/run_decoy_segment.py` (section 5).

### 3.1 Stage 1 — the "forgotten debug constant" (the main 1–1.5 h trap)

* **Trigger.** A `.rodata` record in `stage1_vm`, sitting next to the lure
  string *"stage2_key_checkpoint (pre-rekey) -- kept for the 0.4 survey; do not
  ship"*, holding
  `12f8a367b772817e805725e7292acfb694501c4f16c17ed09d614022e0be7ced`. It looks
  exactly like a plausible early key material. Submitting the token
  `CARTO{12f8a367b772817e805725e7292acfb6}` to `stage1_vm` routes into the
  extended branch: *"the margin note matches the ink you carried in …
  corroborated key material"* and **re-inks the decoy key as if it were the
  answer**.
* **Dead end.** The decoy key derives a *different* sweep —
  `stride 39, start 1512` (the real one is `46 / 5070`). Those 400 bits neither
  parse as a framing nor inflate: **garbage that does not parse and does not
  error**, exactly as the spec requires. Handing the swept bytes to
  `stage2_stego` gets only *"the ledger does not know that reading"* with no
  diagnosis. The solver has burned the time on Stage 2's derivation before
  realising.
* **Recovery.** Re-run `stage1_vm` with no argument. The real key is produced
  by a clean trace; the decoy value is reachable only by static reading, so no
  amount of re-running "fixes" it — the contrast is the lesson. The decoy bit
  stays set and changes nothing downstream.

### 3.2 Stage 2 — the naive whole-image LSB layer

* **Trigger.** Read the LSBs of the opening 512 marks of `survey_frame.png`
  across R,G,B (what any standard LSB tool does first) →
  `CARTO{twice_over_the_coast_before_the_interior}`.
  Submitting it to `stage2_stego -c` routes into the extended branch: *"the
  ledger knows this ink … this mark was struck from the coast press, not the
  interior one."*
* **Dead end.** It is a valid D11 flag and *not* the reading. Nothing
  downstream consumes it; the verifier accepts it into a branch and moves on.
* **Recovery.** The real layer is confined to blue-channel bit 0 at
  marks >= START >= 512 by construction, so the two layers can never collide
  (the Phase-3 layer-collision bug was found and fixed for exactly this
  reason).

### 3.3 Stage 3 — the checkpoint token fed back

* **Trigger.** Hand `stage2_stego`'s checkpoint token
  `CARTO{b27692a0d5f63d4f1a0c3fb79afbf81b}` to the oracle as the reading
  (`-r`). It routes into the extended branch: *"this ink is a checkpoint, not a
  reading … the oracle will still turn figures for it, but under the ink you
  handed over, not under the sheet's."*
* **Dead end.** The oracle then derives a different well-formed key and answers
  every figure under it — self-consistent, plausible, and simply wrong. Only
  the Stage-4 validator's refusal reveals it.
* **Recovery.** Feed the **reading**, not the token. Registering the Stage-1
  token as a second Stage-3 decoy was **rejected**: policy.h ships in every
  binary and the Stage-1 token *is* half of the real key material, so it would
  have leaked a real answer into all five binaries. The Stage-2 checkpoint
  token is safe because it is a one-way digest.
* **Related (Stage 3).** The scripted-uniform **poison** is the fourth
  "looks like progress" state: a wholly poisoned dataset recovers
  `0fab297110c73e9f` cleanly and only fails at the validator.

### 3.4 Stage 4 — the struck first draft


## 4. Calibration — final constants and rationale

### 4.1 The problem the calibration had to solve

(Phase FINAL context — the *sample size* half of this problem was finished by
the Phase FINAL-2 recalibration in section 4.6.)

Stage 3's query budget is **8 experiments x 320 pairs = 2560 pairs**, and each
pair costs **two** oracle invocations, so the budget is **5120 oracle calls**.
`PHASE_4_LOG` D52 recorded the cost as *"at a human-plausible ~2 s average
spacing that is ~85 min of queries"* — that arithmetic used 2560 where it
needed 5120, so the true figure at 2 s/query is **~171 min**, already past the
165-min worst-case ceiling before any other stage runs. Worse, the Phase-0
placeholder `CARTO_STDDEV_LOW_MS = 1500.0` imposed a *hard floor* on any clean
paced query loop: with alternating sleeps the inter-arrival stddev is
`(b - a) / 2`, so staying clean required `b - a > 3000 ms`, i.e. a **minimum
average spacing of ~1.5 s**, i.e. 5120 x 1.5 s = **~128 min on the query stage
alone**. Both the target band (60–90 min clean) and the ceiling were
unreachable. That is what Phase FINAL had to calibrate.

### 4.2 `CARTO_STDDEV_LOW_MS`: 1500.0 → **150.0**  (real lever, not presentation)

This constant also gates the Stage-3 poison, so it is the one calibration that
actually changes measured behaviour. 150 ms keeps the trap's intent intact and
restores a workable cadence band:

| Query cadence | inter-arrival stddev | under 150.0 | under old 1500.0 | 5120 queries cost |
|---|---|---|---|---|
| tight loop, `sleep(0.05)` fixed | ~4 ms | **poisoned** | poisoned | n/a (wrong key) |
| polite loop, `sleep(1)` fixed | ~10 ms | **poisoned** | poisoned | n/a (wrong key) |
| alternating 0.02 s / 0.36 s | ~170 ms | **clean** | poisoned | ~16 min |
| alternating 0.15 s / 1.85 s (**measured**) | ~850 ms | **clean** | clean | **~85 min** |
| alternating 0.4 s / 3.6 s (Phase-4 default) | ~1.6 s | clean | clean | ~102 min |
| unhurried human, ~2 s mean | ~1 s+ | clean | clean | ~171 min |

The point of the trap survives: anything a machine does on a *constant*
interval (4 ms, 10 ms) is still flagged, while anything whose spacing varies
with thinking time — a human, or an agent that writes a jittered loop — is far
above 150 ms. What changed is only that a brisk jittered loop is no longer
forced to be slow. Measured margin for the calibrated run: **5.7x**.

### 4.3 `carto_t_fast_sec[]`: `{90,90,90,90,90}` → `{3, 3, 20, 60, 300}` s

"This stage was reached this soon after the very first run." Set to well below
the legitimate arrival time at each stage, so it fires only for scripted
play-through. These thresholds select a **presentation variant only** — every
stage suite proves the key/verdict is bit-identical across escalated and plain
states — so they cannot change any measured solve time or answer. They are
data-driven from Run A's measured arrival times (section 5). Stage 4's 300 s
means "reached the title block within five minutes", i.e. skipped the oracle
work; a legitimate solver arrives at ~5100 s or later.

### 4.4 Deliberately **not** changed

* `CARTO_MIN_TIMING_DELTAS = 4` — a count, not a time; "insufficient evidence"
  must keep reading as "not suspicious".
* `CARTO_VM_DEBUG_RATIO_LIMIT = 20.0` — re-measured, not retuned. A real
  single-stepped trace is orders of magnitude above it while a slow machine
  (which slows the calibration loop and the trace together) keeps the ratio
  near 1; the margin is comfortable, so 20.0 stands.
* The 4-round cipher, the eight fold tables, the planted deltas, the poison
  derivation and `CARTO_STDDEV_LOW_MS = 150.0` — FINAL-2 changed only the
  *sample size a solver needs* (4.6); nothing about the cipher or the trap
  moved, which is why every shipped binary is unchanged by it except the one
  audit fix in section 2 of the FINAL-2 log.

### 4.6 `N_REQUIRED`: 320 → **260** pairs/window (Phase FINAL-2)

Why it had to move: the FINAL budget 8 x 320 = 2560 pairs is **5120 oracle
calls** (two per pair), which at the cautious ~2 s/query cadence this phase
targets costs ~171 min — the clean path alone blew the 180-min CTF window. At
260 pairs/window the budget is **8 x 260 = 2080 pairs = 4160 calls**, ~139 min
at 2.0 s/query, i.e. inside the 165-min ceiling with real margin at a cadence
a normal human actually uses.

Evidence, not arithmetic: the reference attack (`model_oracle.attack`, the
same code the suites prove) was run on fresh random figures, 1500 independent
trials per candidate (`logs/runs/pf2_trials_model2.jsonl`, driver
`src/final/trial_attack.py`), plus 5 real-binary trials per candidate against
the actual oracle at scaled pacing with fresh seeds every trial
(`logs/runs/pf2_trials_real.jsonl`; every trial re-verifies its dataset against
the real key and asserts zero poison contamination):

| N (pairs/window) | oracle calls | model trials | single-pass failures | real-binary trials |
|---|---|---|---|---|
| 200 | 3200 | 1500 | 108 (7.2%) | 5/5 |
| 220 | 3520 | 1500 | 75 (5.0%) | — |
| 240 | 3840 | 1500 | 29 (1.9%) | 5/5 |
| **260** | **4160** | **1500** | **20 (1.3%)** | **5/5** |
| 280 | 4480 | 1500 | 9 (0.6%) | 5/5 |
| 320 (control) | 5120 | 1500 | 4 (0.27%) | 5/5 |

260 is the smallest candidate whose single-pass rate is within a small factor
of the old 320 control while the budget drops 19%; it is **not** the knee
(200 is), so the choice has margin on both sides. Every failure in the table
is *recoverable, deterministically*: the attack report names the window that
lacked evidence (`B1:insufficient`, ...), and a solver collects another
handful of pairs for that window (80 calls ≈ 2.7 min at 2 s) and re-runs the
offline attack — the acceptance test is exhaustive verification against every
collected pair, so a wrong key can never be accepted. Nothing about the
challenge forces a particular sample size on a solver; 260 is the documented
reference budget that a normal cadence can afford.


## 5. The measured calibration runs (Phase FINAL)

Both runs are driven by `src/final/run_clean_path.py` and
`src/final/run_decoy_segment.py` against the **real, unscaled shipped
binaries** in the package root. Logs: `logs/runs/final_clean_path.log`,
`logs/runs/final_decoy_segment.log`.

### 5.1 Run A — clean path, no detours (real wall clock)

(Phase FINAL run at the pre-FINAL-2 budget of 5120 calls; the FINAL-2 runs at
the recalibrated 4160-call budget are in section 5.5.)

* Started `2026-09-20T18:26:17Z`, completed `19:50:46Z`
  (see `logs/runs/final_clean_path.started` and the log).
* Unscaled: `CARTO_TEST_TIME_SCALE` unset; pacing requested alternates
  **0.15 s / 1.85 s** (mean 1.00 s, stddev 0.85 s = 5.7x the calibrated poison
  floor); **measured 0.989 s per query**, ring stddev after collection
  **850.2 ms**.
* Budget: 8 x 320 pairs = 2560 pairs = **5120 oracle invocations**.
* Stages 0, 1, 2 and 4 are machine-instant (0.00-0.01 s in the same run);
  **the entire clean-path cost is the Stage-3 query budget**, as designed.
* **Measured clean-path time: 5066.07 s = 84.43 min** (all of it the Stage-3
  collection).
* Recovered `K = 73070925a159f9e2` from the real collected dataset
  (hits A = 24/28/15/16, B = 24/23/26/32); the assembled title was accepted by
  the real validator.
* **Target check: 60–90 min — PASS** (84.43 min, upper half of the band by
  design, because the run was deliberately taken at the slowest cadence that
  still fits the band: ~1.0 s per query).

Cadence sensitivity of the same budget (arithmetic on the measured 5120-query
budget, all points inside the poison-safe band):

| mean cadence | Stage-3 query time | clean-path total |
|---|---|---|
| 0.25 s | 21 min | ~21 min |
| 0.50 s | 43 min | ~43 min |
| **1.00 s (measured)** | **84 min** | **84 min** |
| 1.50 s | 128 min | ~128 min |

### 5.2 Run B — decoy detour segment only (added cost)

Run A already covers the earlier portion of the chain, so Run B starts from a
ledger already at Stage 1 (Stage 0 is run only to mint a valid ledger and is
excluded from the timing), then walks the whole detour and stops the clock the
moment the real reading is accepted — i.e. back on the real path at the start
of Stage 3. Steps taken, in order:

1. submit the Stage-1 decoy token → decoy branch, decoy key re-inked;
2. sweep with the decoy key (stride 39 / start 1512) → garbage, refused by
   `stage2_stego` with no diagnosis → **dead end confirmed**;
3. trigger the Stage-2 naive-LSB bait → `twice_over_the_coast…` accepted into
   the extended branch → **reads as progress**;
4. feed the Stage-2 checkpoint token to the oracle → re-inked-checkpoint
   branch → **detour deepens one stage**;
5. submit the Stage-4 struck draft → corroborated-draft branch;
6. recover: re-run the engine cleanly → real key → real sweep (46/5070) →
   real press → real reading → **accepted**.

* **Measured added machine cost of the entire detour + recovery: 0.02 s.**

  re-proving the attack at a lower sample size for no pacing benefit.

### 4.5 `CARTO_TEST_TIME_SCALE` (throwaway iteration speed-up, never shipped)

Compile-time gated: compiled into the library only when

### 5.3 Cross-check: the scaled test build

To make every fix-test-fix cycle cost seconds instead of hours, the same clean
path was run on the **scaled test build** at `CARTO_TEST_TIME_SCALE=60`
(`logs/runs/scale60_clean.log`): the full chain — real binaries, real
collection, real attack — completed in **91.46 s** (Stage-3 91.44 s) and
recovered the same `K = 73070925a159f9e2`, with the assembled title accepted.
That is a 55x wall-clock speedup with an identical result, which is what the
hook exists for. It is **not** a reported calibration number.

### 5.4 Deterministic-solvability confirmation

* Stage 0: ungated, prints the flag on every run.
* Stage 1: no clock, no RNG, no environment input; the C binary and the
  independent python model agree bit-exactly on ledger, step count and key for
  all four profile/detect combinations. All three candidate constants are
  reproducible.
* Stage 2: the sweep, the framing and the press are all deterministic
  functions of the real key and the carrier bytes; carrier regeneration is
  byte-identical (REGEN-DETERMINISTIC-OK).
* Stage 3: the cipher is deterministic; the attack is a fixed, finite procedure
  at a fixed budget and recovers K from the real collected dataset.
* Stage 4: one constant-time digest compare.
* No step anywhere on the real path requires luck, a guess outside the
  puzzle's own logic, or an infeasible brute force (2^64 offline is out of
  reach, and there is no key-check oracle to brute force against).

### 5.5 Phase FINAL-2 — the recalibrated budget, measured at both ends

Both runs below are full clean paths at `N_REQUIRED = 260` (2080 pairs = 4160
oracle calls) against the real, unscaled shipped binaries, in isolated package
copies, driven by `src/final/run_clean_path.py`. The pacing is a **per-query
uniform jitter draw**, not an alternating pair, so nothing about the ring is
machine-uniform by construction.

| quantity | fast edge (`jitter:0.1,1.1`) | cautious edge (`jitter:0.6,3.4`) |
|---|---|---|
| mean spacing (requested) | 0.600 s | 2.000 s |
| spacing stddev (requested) | 0.289 s = **1.9x** the 150 ms floor | 0.808 s = **5.4x** |
| projected Stage-3 time | 41.6 min | 138.7 min |
| **measured clean-path total** | 41.42 | 147.84 |
| measured s/query | 0.597 | 2.132 |
| ring stddev after collection | 282.5 ms | 812.0 ms |
| recovered K | `73070925a159f9e2` | `73070925a159f9e2` |
| title accepted | yes | yes |
| target | fits with huge margin | **<=150 min target met; 165-min ceiling cleared with margin** |

Logs: `logs/runs/pf2_confirm_lower.log`, `logs/runs/pf2_confirm_upper.log`.

Cadence sensitivity of the new budget (arithmetic on 4160 calls; every point
inside the poison-safe band):

| mean cadence | Stage-3 query time | note |
|---|---|---|
| 0.6 s | ~42 min | **fast edge, measured** (stddev 1.9x floor) |
| 1.0 s | ~69 min | the FINAL run's cadence, now 19% cheaper |
| 1.5 s | ~104 min | |
| 2.0 s | **~139 min** | **cautious edge, measured** |
| 2.5 s | ~173 min | past the ceiling: a deliberately glacial solver |

For contrast, the pre-FINAL-2 budget (5120 calls) at the same cautious 2.0 s
cadence was ~171 min — the clean path alone blew the window. That is the
defect this phase fixed.

The poison keeps its teeth at the new budget: a scripted uniform loop still
gets a self-consistent dataset under the poison key (adversarial suite section
5, re-run on the new build), and a *jittered* loop whose spacing stddev lands
inside the floor is poisoned too (`jitter:0.1,0.5`, stddev ~115 ms — measured
in `src/final/probe_ring.py` runs during this phase). What a solver must do is
what a person does anyway: vary the gaps.

## 6. Scoring decision

Only the **Stage-0 flag** and the **assembled Stage-4 title** are TryHackMe
answers. Everything else (Stage-1 token, Stage-2 reading and its checkpoint
token) is an in-challenge checkpoint.

Rationale, carried from PHASE_2_LOG D18 and PHASE_4_LOG open question 4 and now
decided: the intermediate tokens are **format-valid on the decoy and debugger
paths too** — `CARTO{12f8a367b772817e805725e7292acfb6}` and
`CARTO{fb48aecdda0e960831b16d45c7efbe48}` are both well-formed `CARTO{…}`
strings. Scoring them would let the room reject a decoy instantly, which
collapses the 1–1.5 h trap budget to zero. The Stage-0 flag is ungated and the
Stage-4 title is only producible from the three real inks, so those two are the
right pair to score. `TRYHACKME_ROOM_TEXT.md` reflects exactly this.

## 7. Package contents and verification

* `drive-upload/cartographer.zip` — exactly 9 files: the 5 binaries, the 2
  carriers, `README_FOR_SOLVER.txt`. Nothing else. Zero `.md`, zero `.git`,
  zero source, zero logs, zero build artifacts.
* `organizer-private/` — `SOLVE_PATH_PRIVATE.md`, `HINTS.md` (exactly 5),
  `TRYHACKME_ROOM_TEXT.md`, `docs/BUILD_SPEC.md`, the complete `logs/` tree,
  and a copy of the solver README for reference. Never mixed with the zip.
* `src/final/verify_isolated.sh` extracts the zip into a clean directory,
  re-audits its contents and its binaries' symbols/strings there (including
  `CARTO_TEST_TIME_SCALE` absence), and solves the extracted copy standing
  alone with `src/final/run_isolated_solve.py`.

## 8. Residual issues, stated plainly

1. **No in-binary waits exist.** The kickoff's section-2/3 premise ("a
   60-minute mandatory wait", "sleep/rate-limit/escalation-timer check") does
   not describe this build: no shipped binary sleeps, rate-limits or waits.
   The only real wall-clock cost is solver-side pacing against the Stage-3
   query budget, and the only real thresholds are the escalation thresholds in
   the shared state library. `CARTO_TEST_TIME_SCALE` is therefore implemented
   where the real time-dependent logic lives (library thresholds) plus the
   internal query driver, and the measured runs reflect that.
2. **Run B's detour cost is analysis time, not machine time.** The measured
   machine cost is 0.02 s. The 1–1.5 h figure is an analysis-cost estimate
   (section 5.2), documented per step, not a stopwatch measurement. This is
   unavoidable: the detour's cost is human cognition, and faking a wall-clock
   number would be dishonest.
3. **Pacing is a solver-side model.** The clean-path time is dominated by the
   Stage-3 query budget at a chosen cadence. Phase FINAL-2 recalibrated that
   budget to 4160 calls (section 4.6) and measured both ends of the realistic
   cadence range (section 5.5): ~42 min at the fast edge (0.6 s mean, jittered)
   and 147.84 at the cautious edge (2.0 s mean, jittered), both clean.
   A *slower* solver still legitimately takes longer — at 3 s/query the same
   budget is ~208 min — but the design target (a normal human pace inside the
   180-min window with margin) is now met by measurement, not by hope. If the
   ceiling were ever hardened further, the remaining levers are the
   candidate-enumeration resolver (zero query cost) or a lower N, not the
   pacing.
4. **Two arithmetic slips in the older phase logs** (recorded here because
   this phase found them): `PHASE_2_LOG` D18 calls the 32-hex token "38 chars"
   (it is 39), and `PHASE_4_LOG` D52 costs the Stage-3 budget at "2560 pairs
   ~ 85 min" (it is 5120 queries). Neither affected any shipped artifact; both
   are corrected in this file's sections 1 and 4.1.
5. **`CARTO_T_FAST_SEC_DEFAULT` is 3 s**, so a Stage-0 run followed immediately
   by anything else flags `CARTO_ESC_TIME_FAST` for the first stages. Harmless
   by construction (presentation only, proven answer-invariant) and intended:
   it is the "you got here impossibly fast" tell.

`make CARTO_TEST_BUILD=1` passes `-DCARTO_TEST_TIME_SCALE_ENABLE`
(`src/state/Makefile`). It divides **both** elapsed-time thresholds and the
inter-arrival uniformity floor by `$CARTO_TEST_TIME_SCALE` (scaling both is
required: compressing time shrinks the ring's deltas by the same factor, so
scaling only one side would make a compressed paced loop look scripted-uniform
and get poisoned). Shipped builds define nothing, so the name is absent from
their `.rodata` — proven two ways: `strings` on all five shipped binaries
(107-check adversarial suite, section 4 audit) and the behavioural probe
`src/final/probe_scale.c`, which shows the shipped build answering **identically**
at scale 1 and scale 60 while the test build at scale 60 suppresses both
thresholds.

Used for every fix-test-fix cycle in this phase; **not** used for any reported
number (all reported numbers below are from the unscaled build).

* **Trigger.** The validator's usage screen presents
  `CARTO{dba9e10a73bc8633ccc1875207c075e1}` as *"an earlier draft the old man
  struck out"*. Submitting it routes into the extended branch (*"corroborated
  draft"*, *"a struck line is ink that never dried into the block"*).
* **Dead end.** Synthetic seed, reveals nothing about any real answer.
* **Recovery.** Assemble per the verse. Registering any *natural wrong
  assembly* as the Stage-4 decoy was **rejected** for the same leak reason:
  every such string contains real component values (the engine ink is real key
  bytes; the oracle ink **is** the Stage-3 master K).

### 3.5 The anti-debug traps (Stage 1)

* `ptrace(PTRACE_TRACEME)` self-attach plus a timing ratio
  (`CARTO_VM_DEBUG_RATIO_LIMIT` 20.0). On detection the binary does **not**
  error: it sets `debugger_detected`, re-runs the engine with the detection
  gate `R10=1`, and prints the corrupted constant `fb48aecd…1621` (steps
  4081/7264 instead of 4083/7266).
* **Fairness (fixed in Phase FINAL).** PHASE_2_LOG open question 5 — a seccomp
  policy or a ptrace-less kernel would have been misread as "debugger
  detected", corrupting the constant on a *clean* run. Stage 1 now reads
  `/proc/self/status TracerPid` as the authority (non-zero ⇒ a real tracer),
  and the ptrace probe is only a fallback where `EPERM` means "already traced"
  while `ENOSYS` means "no ptrace here". Verified: a real `gdb` attach still
  serves the corrupted constant (the trap keeps its teeth), and a clean run
  leaves the flag at 0. See `verify_adversarial.sh` section 5.
* A persisted debugger flag **escalates** the variant (harder trace) but never
  corrupts a later clean run's key — asserted by the suite.

spacing so the ring's stddev stays well above the floor. (The poison keys off
`CARTO_ESC_TIMING_UNIFORM` **only** — a fresh-state solver is never poisoned,
and a one-time debugger visit is not punished twice.)

### Stage 4 — the title block

```bash
./stage4_assembly/validate 'CARTO{73070925a159f9e2_a5d66f1b2b5f596e_no_figure_sits_in_every_pixel}'
```
Constant-time SHA-256 compare against a stored digest, no partial-match
feedback of any kind, rc 0 on every path, stderr silent on every path. The
ordering verse ships in the no-argument usage screen.

```
R6     = LE64(K[0:8])   = 0x2ec3dfdf49803efd
R7     = LE64(K[8:16])  = 0xc0b8223882fe22fe
STRIDE = 3  + (R6 % 61) = 46
START  = 512 + (R7 % 9000) = 5070
```

Read the **blue** channel, bit 0, of every `STRIDE`-th mark from `START` to the
far edge, packed **MSB-first**, 8 marks to a byte. The first two bytes are the
framing `LE16(len(zblob))` — note the byte order: the length is little-endian
while the bits inside each byte are big-endian-first (getting this backwards
yields 0x3000 instead of 48). Here the framing is 48, so the ink is
`LE16(48) || 48 zlib bytes` = 50 bytes, 400 bits.


---

## 6. Phase FIX — Closing Shortcut Leaks (Post-Audit Hardening)

### 6.1 Confirmed Shortcuts, Root Causes, and Fixes

1. **Stage 1 (`stage1_vm`) Unstripped Key Material:**
   - *Shortcut:* Running `./stage1_vm` without arguments printed the full internal register state (`engine ledger: r1=... r2=...`) and the 64-hex key material with label `key material: ...`, allowing solvers to bypass VM disassembly and extract the engine ink component directly.
   - *Root Cause:* Development/debugging print statements in `stage1_vm.c` that were left active.
   - *Fix:* Stripped `hex_line(key, KEY_LEN)` and register ledger prints from `stage1_vm.c`. A plain run now outputs only the engine variant, step count, and the Stage 0-style 32-hex checkpoint token (`CARTO{fd3e8049dfdfc32efe22fe823822b8c0}`). The second 16 bytes (`R1`) required for Stage 4 must be obtained by reversing the VM bytecode.

2. **Stage 2 (`survey_frame.png` & `survey_tape.wav`) Carrier Metadata Formulas:**
   - *Shortcut:* The `Comment` and `FieldNote` tEXt chunks in `survey_frame.png` gave the exact offset and stride math formulas (`mod 61`, `mod 9000`, `stride = 3 + ...`) in plain English, and `survey_tape.wav` had its `ICMT` chunk labeled `interior-ink-formula-v1:`.
   - *Root Cause:* Dev-convenience text notes embedded in the PNG/WAV generator.
   - *Fix:* In `gen_carriers.py`, stripped the math formulas from `Comment` and `FieldNote` (retaining thematic surveyor clues). Renamed the dictionary prefix to `interior-survey-mark-v1:`. Embedded the sweep derivation arithmetic (`carto_s2_derive_sweep`: `stride = 3 + (r6 % 61)`, `start = 512 + (r7 % 9000)`) directly into `stage2_stego.c` compiled machine code (kept live via volatile gate) so solvers must reverse the binary rather than reading plain text in metadata.

3. **Stage 3 (`stage3_oracle`) Identifiable Mask String in `.rodata`:**
   - *Shortcut:* `.rodata` in `oracle` contained the identifiable plaintext string `cartographer-mask-stage3-real`, allowing solvers to compute `SHA-256("cartographer-mask-stage3-real")` and unmask `kMaskedSeedReal` to derive the master key without querying the oracle.
   - *Root Cause:* Mask seed string from `gen_oracle_constants.py` embedded in `oracle_blob.h` under the assumption that a mask string alone reveals nothing.
   - *Fix:* Removed `kMaskSeedRealStr` and `kMaskSeedPoisonStr` from `oracle_blob.h` and `gen_oracle_constants.py`. Derived the masks dynamically from the cipher's own round fold tables (`kFoldA0..B3`). No human-readable mask string or label is compiled into the binary.

### 6.2 Verification and Invariance
- All intermediate key materials, cipher outputs, and the final flag (`CARTO{73070925a159f9e2_a5d66f1b2b5f596e_no_figure_sits_in_every_pixel}`) remain 100% invariant.
- Naive recon (no-arg runs, `--help`, strings regex scan for keys/formulas/masks, carrier metadata dumps) confirms zero leaks.
- Legitimate solve path verified end-to-end via `run_isolated_solve.py` and stage test suites.
