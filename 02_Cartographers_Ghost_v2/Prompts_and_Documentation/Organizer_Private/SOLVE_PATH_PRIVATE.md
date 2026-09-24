# SOLVE PATH (organiser only) — the full honest solve, with timings.

Values are in KEYS_V2.md.  Timings are the calibrated end-to-end run on
the test builds (runs/clean_path.txt, scaled wall) unless marked; the
projection row is the honest human+agent real-package range from
COST_MODEL.md.

## 0. The desk (0.2-0.5 h)

Run `./stage0_ledger/ledger` from the package root, then again, and
again.  The ledger's line `first entry:
CARTO{the_survey_reopens_tonight}` is the first scored answer and costs
nothing beyond the sitting: the record needs repeated terminal visits
(about eight ledger runs) before the engines, or the engine's bearing
marks drag the tty fraction under the bench's bar.  The chain gate then
reads: 0,0,0,0,0,0,0,0 then forward, never backwards.

## 1. The machine (2-4 h)

Run `./stage1_engine/engine -p coast` and `-p interior` (204953 /
225433 steps).  Both end at the same ink (`145e1d23feac3932`); the
machine never writes it down -- the traces do, if you emulate the
92-opcode VM with its self-modifying code and indirect jumps.  The
bearing rides on the record for the sheet to read; it is never printed.
Dead ends on this bench: the debug branch (needs the ptrace shape), the
decoy branch (the older index key with its own bearing, verified by the
older certificate), the profile.notes arithmetic.

## 2. The frame (2-4 h)

Run `./stage2_sheet/sheet` (audit), then `./stage2_sheet/sheet -r
--plain` on a warm bench at a terminal.  The bearing off the record
gives stride 8, start 2629; the drawn lane is blue bit 0, every 8th
mark, MSB-first, `LE16(len) ‖ zlib_deflate(reading, dict=press)`;
the press comes off the tape raw (56 bytes: 24-byte tag + 32-byte tail)
-- `exiftool -b -Comment` re-renders it as 133 bytes of hex text, which
is the documented trap.  The reading is
`CARTO{rust_blooms_under_tin_roofs}`.  Decoys on this frame: the naive
row (`CARTO{the_coast_was_drawn_twice}`), the near-miss lane (one
parameter off, readable, plausible, never a flag), the exact-LC-vs-LE16
confusion (0x3000).  Fair exit: `--plain` says the colour bit as a word.

## 3. The plate (4-7 h, including the ≥45 min sitting)

At least 6000 paced asks with at least 3000 distinct figures over at
least 45 minutes, non-uniform, terminal-shaped, TTY in ≥ 60% of calls.
Run `./stage3_oracle/oracle -r <reading> -i <engine-ink> <figure>` and
pace: any scripted uniform/burst/piped/replayed/too-young sitting is
answered off one of the poison keys with its own tell, and mixed data
yields NO-CONSENSUS from any solver.  The attack is the 5-round planted
bias: ~2^-5 completions per pair, recover kA=2a3109e5 kB=ade0a2e8
bit-exactly, ink=e509312ae8a2e0ad.  `./stage3_oracle/oracle -t` on the
warm plate prints the tally `CARTO{a_warm_plate_and_a_full_ring}`.
Omitting the engine ink (or handing the stage-1 token as -i) is the
decoy derivation: K_cold, plausible, format-valid, wrong.  Uppercase
figures are a different (also wrong) key.  Repeating a figure twice in
a row replays the ring cache.  Measured at scale: the calibrated
sitting (750 pairs, 6064 answers) clears volume and the model matches
the ink bit-exactly.

## 4. The stamp (0.5-1.5 h)

Run `./stage4_seal/seal` for the certificate: four pairs, the block
rules, the closing rule.  The intended attack is meet-in-the-middle on
the outer passes against the middle byte: ~2^33.6 counted evaluations,
20.9 s single-core C at full size (the same search in Python runs
~100x slower).  It recovers the 7 working bytes; byte 8 is the closing
byte, found only by offering candidates to the stamp (exactly one of
256 closes).  The face reads `3821ad004ab30263`.  The drawer
(`--decoy`) is the older reversed construction with its open key
`52ec8c8bc15e8c58`; its face is valid-looking and fails at the block.

## 5. The title (0.5-1 h)

Run `./stage5_title/validate` for the desk, the riddle, the provenance
lines and the struck draft.  Assemble the four inks in the riddle's
order -- seal, oracle, engine, sheet:
`CARTO{3821ad004ab30263_e509312ae8a2e0ad_145e1d23feac3932_rust_blooms_under_tin_roofs}`,
digest `01d94d49...f0d1`.  The block weighs it once: the refusal is one
line for every wrong hand and a right hand taken only with the chain
and a terminal.  Detours with measured cost: the struck draft, a
reading one character off, the bait's drafted title, the decoy faces.

## Traps and their recoveries (summary; the catalogue is normative)

Every trap in §5 of the build log has a deterministic resolution that
costs more than the dead end: the exiftool hex text (raw read / -v3),
the near-miss lane (re-derive with the press), the cold plate (sit),
the poison verses (pace, vary, space), the cache trap (don't repeat),
the case trap (lowercase), the drawer (the older round order), the
closing byte (the 256-offer walk), the struck draft (downstream round
trip to disprove), the bait papers (zero truth; the draft prints a
registered wrong title).
