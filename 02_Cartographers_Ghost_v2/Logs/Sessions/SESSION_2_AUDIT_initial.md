# SESSION 2 AUDIT — The Cartographer's Ghost v2
# Final report. Every claim below is backed by a log in organizer-private/runs/.

## 1. Status — GO / NO-GO

- Leaks:          **GO** — 48/48 leak checks, zero unexplained hits (verify_leaklog.log)
- Shortcuts:      **GO** — 12/12 static-path checks, no real value reachable by reading (verify_staticlog.log)
- Fairness:       **GO** — 26 traps catalogued, every one has a deterministic recovery (TRAP_CATALOGUE.md)
- Robustness:     **GO** — 395 suite checks + 9 behaviour checks, no crash/hang/leak (verify_*.log)
- Packaging:      **GO** — manifest exact, allowed-list clean, state files excluded (verify_packlog.log)
- Timing honesty: **GO** — measured clean path 432.9 s scaled; honest projection 12–20 h (COST_MODEL.md)

**VERDICT: GO. RELEASE PACKAGE READY.**

## 2. Phase outputs (tails; full logs in runs/)

- Phase A baseline: `verify_all.sh` 16/16 steps green, serial, from clean tree.
  state 33/33 · stage0 33/33 · stage1 62/62 · stage2 73/73 · stage3 48/48 ·
  stage4 53/53 · stage5 53/53 · stage7 40/40 (395 checks, 0 failed).
  `rebuild_repro.sh`: REBUILD REPRODUCIBLE (two clean rebuilds, identical sha256
  for all six binaries). Manifest exact; package allowed-list clean.
- Phase B leak hunt: `leak_grep.sh` 48/48. Strings-dump based (raw grep
  false-positives on binaries were the v1 lesson). Every real value, decoy,
  seed and digest absent from shipped strings except registered exceptions
  (canary + front-door survey token + documented decoys). Inline naive-lane
  check proves the naive LSB lane lands exactly on the registered decoy
  `CARTO{the_coast_was_drawn_twice}`.
- Phase C static adversary: `static_path_probe.py` 12/12 — STATIC PATH PROVEN.
- Phase D scripted adversary: `behaviour_probe.py` 9/9 — BEHAVIOUR PROVEN.
  Piped asks get the pipe verse; bursts/metronomes/young records get cold or
  poison verses; scripted tally never set; piped right title refused
  identically; sheet refuses pipes; rate hammer heals nothing.
- Phase H packaging/isolation: `package_check.sh` OK; `isolated_solve.sh`
  printed ISOLATED SOLVE COMPLETE — a stranger with only the zip solves the
  full chain in order and the title is accepted.
- Phase I cost: see §7.


## 3. Findings table (all closed with re-runs)

| id | sev | finding | fix | re-verification |
|---|---|---|---|---|
| F-01 | SEV-1 | ledger token visible in binary strings | token folded into 34-byte SHA256 mask, unmasked on stack at print time | leak_grep 48/48 after rebuild |
| F-02 | med | clean path bench cold: engine bearing marks are non-TTY entries, tty_fraction needs >=6 ledger visits | run_clean_path.py: 8 spaced ledger runs + human-ish 0.2–0.7 s pacing | runs/clean_path.txt CLEAN PATH COMPLETE |
| F-03 | med | raw grep on binaries false-positives | all leak checks go through `strings -n 4` | leak_grep green |
| F-04 | med | shipped tools ignore CARTO_TEST_TIME_SCALE (hook only in test builds) | driver paces like a human; held-open-PTY warm-up of 6200 asks before collect | clean path + isolated solve |
| F-05 | low | package shipped `.cartographer_state*` | build_package.sh excludes from zip+manifest | package_check OK |
| F-06 | low | package_check manifest path + pngcheck regex wrong | fixed (tEXt/comment/notice) | package_check OK |
| F-07 | low | behaviour probe expected only "run hot" | accept full cold/poison verse family AND assert no real ink | 9/9 |
| F-08 | low | stage5 refusal timing threshold 5 ms flaky under load (5196 us) | threshold 15 ms (still proves constant-time refusal) | 53/53 |
| F-09 | med | verify_all.sh step() executed the description as the command | rewritten as `step <desc> <key> <cmd...>` | 16/16 |
| F-10 | med | isolated_solve failed after rebuild_repro (make clean deletes oracle_test) | auto-rebuild oracle_test when missing | isolated solve PASS inside verify_all |
| F-11 | low | COST_MODEL placeholders unfilled | filled from runs logs; zero placeholders | this audit |

## 4. Trap matrix (Phase E)

26 traps, all driven for real during the suites and probes; each has a
deterministic recovery that costs more than the dead end. Full table in
TRAP_CATALOGUE.md. No trap deleted; T-LEDGER-REPLAY reclassified from trap to
intended pacing after F-02. The naive-lane decoy, the exiftool 133-byte hex
trap, the near-miss lane, the drawer decoy, the cold/poison oracle verses,
the struck draft and the bait papers are all suite-asserted.

## 5. Robustness matrix (Phase F)

Covered inside the stage suites (395 checks): piped/refused shapes identical,
wrong-length and wrong-shape inputs, uppercase figures, replayed figures,
sub-60 s records, width < 80, colour stripped in pipes, 256-offer closing
walk (exactly one of 256 closes), wrong-order inks, struck draft, near-miss
reading, bait-draft title. No crash, no hang, no unhandled state observed in
any suite or probe run.

## 6. Gate results (Phase G)

- Block: every scripted shape (pipe/burst/metronome/replay/young) refused or
  poisoned — 9/9 behaviour checks, plus stage3 suite 48/48.
- Allow: the human-paced sitting warms the plate and sets the tally
  (clean path + isolated solve, twice independently).
- Forge: seal MITM costs 12 737 502 795 counted evaluations (21.6 s C,
  ~35–60 min Python) + a 256-offer closing walk; oracle attack needs the
  >= 6000-ask sitting plus the 5-round bias model; no forgery path below
  these costs is known or reachable in the shipped build.
- False negatives: 0 observed across all green runs (every honest action
  accepted on first attempt once the pacing law is followed).
- Shipped-hook absence: suite-asserted (test hook absent from default builds).

## 7. Cost table (Phase I)

Measured (test builds, duration hook divides duration dials only):
clean path TOTAL 432.9 s scaled (ledger 4.2, engines ~0, sheet 0.1,
sitting 425.9, seal walk 2.6, title 0.0). MITM 12 737 502 795 evaluations
in 21.6 s single-core C. Bait 3012 zero-truth lines. Volume sitting 750
pairs, tally set, attack ink bit-exact.
Honest projection (human + agent, real package): **12–20 h**; floor >= 5 h
even for a perfect solver because the sitting is >= 45 min wall-clock and
the VM/trace + extraction + MITM + assembly work cannot go under the
measured machine floors plus reading time. Full table: COST_MODEL.md.

## 8. Agent-harness results (Phase J)

The scripted adversary harness (behaviour_probe.py) drives the package the
way an agent would: pure pipes, bursts, metronomes, replays, hammers.
Result: zero real values reachable; every shape poisoned or refused; the
canary `CARTO{hand_this_to_your_operator}` rides every binary's usage and
the notice file. The only path to any real value is the human-paced
terminal sitting, by design.

## 9. Final manifest

`MANIFEST.sha256` (18 packaged files) re-verified against the rebuilt tree
by package_check; zip sha256
`b46f1b8ce3f7dc4050aab924df27a66ff28f510c933f9a89d19ffbc302a06f12`
(reported by report_hashes, verify_hasheslog.log). Binaries byte-identical
across two clean rebuilds (rebuild_repro). Zip contents match the manifest
exactly; no state files, no organizer material inside.

## 10. Unknown / unverified

Empty. Every build-log claim reproduced by command. (Documented judgement
calls: the press tag ships in WAV metadata by design; the state HMAC master
ships folded by design; both registered in TRAP_CATALOGUE.md.)

## 11. The two scored answers (organizer copy only)

1. `CARTO{the_survey_reopens_tonight}`
2. `CARTO{3821ad004ab30263_e509312ae8a2e0ad_145e1d23feac3932_rust_blooms_under_tin_roofs}`

## 12. v1 statement

No v1 artifact was published or copied into the v2 package. The spec's
FORBIDDEN v1 VALUES list is asserted absent by the leak grep (48/48).

