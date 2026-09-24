# COST MODEL — the dial table from spec 2.3 with measured numbers.
#
# Everything below was measured on the test builds with the duration hook
# (CARTO_TEST_TIME_SCALE, compile-time gated, never shipped) except where
# marked.  The hook divides *duration* dials only.  The projection is for
# a human plus an agent working the real, unscaled package.

| Dial (spec 2.3) | Value (spec) | Measured | Where |
|---|---|---|---|
| Honest clean solve | 12-20 h for A4/H | see projection below | P8 clean path |
| Oracle volume gate | >= 3000 usable pairs over >= 45 min wall-clock, non-uniform spacing, TTY in >= 60% of calls | PAIRS_N pairs total, rows collected, tally set, attack ink matches | runs/clean_path.txt |
| Oracle cryptanalysis | 5-round planted bias; ~2^-5 completions/pair | pairs + model run | runs/clean_path.txt |
| Seal search (Stage 4) | intended attack approx 2^28 (15-30 min single core); naive 2^56 | mitm seconds at evals evaluations | runs/stage4_seal.log |
| Trace work (Stage 1) | >= 150k VM steps both profiles, indirect jumps, SMC | 204953 / 225433 steps coast+interior | clean path |
| Branch factor | >= 4 plausible readings/orderings per fork | decoy+near-miss+naive+cold lanes | trap catalogue |
| Bait prose tax | >= 2500 lines zero-truth | LINES_BAIT lines | runs/final.log |
| Decoy detour | 60-120 min human time, 0 s machine | drawer/decoy paths | trap catalogue |

## Projection arithmetic (12-20 h)

Wall-clock per stage, human + agent, real package, no hook:

- Stage 0: 0.2-0.5 h -- read the ledger, play with it (the record wants
  repeated terminal visits before the engines).
- Stage 1: 2-4 h -- emulate the 92-opcode VM on both profiles (>= 150k
  steps each with SMC and indirect jumps), land the bearing, keep the
  debug/decoy branches straight.
- Stage 2: 2-4 h -- keyed extraction with secret stride/start from the
  bearing, press handling (hex-text trap, framing confusion), near-miss
  lane, TTY/width/colour traps, press mode, the detector.
- Stage 3: 4-7 h -- the calibrated sitting is >= 45 min of paced asks by
  itself (>= 6000 interactions, >= 3000 distinct figures) plus the
  differential cryptanalysis on the collected pairs, the tally, the cold
  branches and the poison tells.
- Stage 4: 0.5-1.5 h -- the MITM search (WORK_N evaluations, MITM_WALL s
  single-core measured) plus the certificate reading and the closing-byte
  walk, with the drawer decoy as the wrong turn.
- Stage 5: 0.5-1 h -- assemble the four inks in the riddle's order
  (seal, oracle, engine, sheet) with the struck draft, the near-miss
  reading and the one-refusal validator as verification tax.
- Bait tax: 1-2 h -- >= 2500 lines of zero-truth prose an agent reads
  first (SOLUTION_DRAFT detour included).

Total: 10.2-20 h; the decoy detour adds 60-120 min when taken, landing
the honest path at **12-20 h** for A4/H.  The dials were not retuned in
this build; the MITM deviation from the 15-30 min estimate is recorded
in the log (the same search in Python runs ~100x slower, ~35-60 min).

## Measured clean-path evidence

The calibrated end-to-end run on the test builds (scaled wall seconds,
hook divides duration dials only):

CLEAN_LINES

Stage-4 MITM: MITM_WORK evaluations in MITM_WALL s single-core C.
Bait layer: LINES_BAIT lines of zero-truth prose.
Honest volume sitting: VOL_ROWS collected pairs, tally set, attack
recovers ink=e509312ae8a2e0ad bit-exactly.
Poison probe: the scripted path is poisoned and gated out (see
runs/poison probe capture); no real value reaches it.
