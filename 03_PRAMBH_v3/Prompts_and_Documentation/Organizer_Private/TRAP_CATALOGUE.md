# PRAMBH v3 - TRAP CATALOGUE (organizer-private)

Every decoy/bait value, where it lives, and what it costs.


## Outer Encrypted Distribution Package (Stage -1 / M0)

Distribution file: `prambh.zip.enc` with OpenSSL AES-256-CBC PBKDF2 (200k iter).

- Passphrase: `gate hearth zinc field` (derived from the Keeper's 4-station perimeter landmark riddle: Station North = `gate`, Station Center = `hearth`, Station West = `zinc`, Station South = `field`).
- Decoy behavior: any wrong passphrase or naive `unzip` without OpenSSL yields `bad decrypt` or invalid zip header; provides zero archive access.


## Canary

- CANARY-1: `PRAMBH{canary_87eefe3e}` - printed in HUMAN_OPERATOR_NOTICE.txt, on every tool usage screen, and in PNG Notice chunks. Planted to trace AI-solver writeups. Never accepted anywhere; not the final title's shape.


## Capsule wrong-phrase lanes (Stage 0 -> Mirror Room)

Real launch phrase: `fable coil autumn coast reed zinc` (ships in LAUNCH.txt, ARCHIVE mode).

Real load vector: `96415166fc01091e7bce5b43d36a5d491cb6591f0471415e5f670535c7856392`

- D-CAP-1: phrase `zinc reed coast autumn coil fable` -> load vector `c0816a2ec4a6cf374983952bf16c8a80e847fc2ceafb2e07dc186f3bf5ca03ad` -> loom walks it, output mismatches the loom verifier, routes to the Mirror Room campaign (P5/P7).

- D-CAP-2: phrase `coil autumn coast reed zinc fable` -> load vector `d678bc50e5bf221de99ee71cc6f6a7341aea28503ca8c877941ce80119da9803` -> loom walks it, output mismatches the loom verifier, routes to the Mirror Room campaign (P5/P7).

- D-CAP-3: phrase `sand coil autumn coast reed zinc` -> load vector `9952abf0a57b75c36cca829476eb15e1eb06ab38c6920edf25644eaa10634a80` -> loom walks it, output mismatches the loom verifier, routes to the Mirror Room campaign (P5/P7).

- D-CAP-4: phrase `fable coil autumn coast reed delta` -> load vector `21014158cc88a7447485f4ac692c1fae645eafe13ddb01d7f4982a5c16b0d95f` -> loom walks it, output mismatches the loom verifier, routes to the Mirror Room campaign (P5/P7).

- D-CAP-U: any other phrase yields an unregistered but format-valid load vector; it fails the loom verifier and routes to the Mirror Room like the designed lanes.


## Flood corpus decoy folios (P4)

Needle folios (stitched originals): folio_265, folio_338, folio_325, folio_108, folio_020

- D-FLOOD-1: folio_386 - format-valid decoy, contradicts needle #0; feeds wrong loom model / wrong hall number / wrong plate method to skimmers.

- D-FLOOD-2: folio_364 - format-valid decoy, contradicts needle #1; feeds wrong loom model / wrong hall number / wrong plate method to skimmers.

- D-FLOOD-3: folio_192 - format-valid decoy, contradicts needle #2; feeds wrong loom model / wrong hall number / wrong plate method to skimmers.

- D-FLOOD-4: folio_237 - format-valid decoy, contradicts needle #3; feeds wrong loom model / wrong hall number / wrong plate method to skimmers.

- D-FLOOD-5: folio_374 - format-valid decoy, contradicts needle #4; feeds wrong loom model / wrong hall number / wrong plate method to skimmers.

- D-FLOOD-L: every flood lane (any token, 8 pages) is plausible generated chaff; wrong tokens are indistinguishable in form.


## Decoy survey plates (P4)

- D-PLATE-1: plates/decoy_plate_0.png, code `21b3edf867f4117638` - format-valid eye-plate decoy; the stage-4 validator must treat it as an ordinary wrong answer.

- D-PLATE-2: plates/decoy_plate_1.png, code `808db61e567e04f811` - format-valid eye-plate decoy; the stage-4 validator must treat it as an ordinary wrong answer.

- D-PLATE-3: plates/decoy_plate_2.png, code `d52cba0a2ab5931b34` - format-valid eye-plate decoy; the stage-4 validator must treat it as an ordinary wrong answer.

- D-PLATE-4: plates/decoy_plate_3.png, code `67ad16b261c459305e` - format-valid eye-plate decoy; the stage-4 validator must treat it as an ordinary wrong answer.

- D-PLATE-5: plates/decoy_plate_4.png, code `1b6778cc6225d5afd4` - format-valid eye-plate decoy; the stage-4 validator must treat it as an ordinary wrong answer.

- D-PLATE-6: plates/decoy_plate_5.png, code `8c83b6e330f1a51b0d` - format-valid eye-plate decoy; the stage-4 validator must treat it as an ordinary wrong answer.


## Loom decoy cartridges + the diagnostic lane (P5 - spec 4.4)

Registry source: `organizer-private/runs/p5_decoy_tokens.txt` (harvested once against the production parameters; never recomputed).  All four lanes print in the same teleprinter voice as the real cartridge, lodge a claim of the same shape, and exit clean; nothing in the package labels them.

- D-ROM-1 (MERC-6 tide recorder), `roms/tide_merc6.rom`

  - cartridge pan (mint-derived, CART window): `f610054b36efc2750701f0f4383df620077a9cbc8de3d8177a74d8817124e48f`
  - chain seed (harvested): `a1c3110b71a474135e5c10684c33988c6955f1ec141a2d06cfc8670203eb82cd`

  - token: `PRAMBH{21200db398a8c416}`

  - trigger: running the cartridge (`./loom run roms/tide_merc6.rom` / `./loom claim roms/tide_merc6.rom`) or any all-ROM sweep of the instrument collection

  - dead end: the token is accepted nowhere - no chamber, no eye-plate, no validator, no server record - and it contradicts a needle folio 1:1 (D-FLOOD-1..5)

  - recovery (documented observation): the needle folio names the one program cartridge (the survey stitch cartridge) and the datasheet's valley-vs-coast tell separates MERU from MERC

  - fairness: same build recipe, same size class and same output framing as the real cartridge; registered here before the package was built

  - wasted cost (PROJECTED - audit must confirm with the full REAL run): 290 s (5 min) under the shipped emulator, 237 s (4 min) for a native re-implementation

- D-ROM-2 (MERC-3 star camera), `roms/star_merc3.rom`

  - cartridge pan (mint-derived, CART window): `dd63121505be80688949b2ce21675cb52ae3af672d2c50dc5f8c55f704a36045`
  - chain seed (harvested): `7cdc4ce68030cdb09fd9e045b846f83e76966d09ea8105528f853ed5ba60f00d`

  - token: `PRAMBH{dfc675e0d58fb83a}`

  - trigger: running the cartridge (`./loom run roms/star_merc3.rom` / `./loom claim roms/star_merc3.rom`) or any all-ROM sweep of the instrument collection

  - dead end: the token is accepted nowhere - no chamber, no eye-plate, no validator, no server record - and it contradicts a needle folio 1:1 (D-FLOOD-1..5)

  - recovery (documented observation): the needle folio names the one program cartridge (the survey stitch cartridge) and the datasheet's valley-vs-coast tell separates MERU from MERC

  - fairness: same build recipe, same size class and same output framing as the real cartridge; registered here before the package was built

  - wasted cost (PROJECTED - audit must confirm with the full REAL run): 290 s (5 min) under the shipped emulator, 237 s (4 min) for a native re-implementation

- D-ROM-3 (MERC-9 gravimeter), `roms/grav_merc9.rom`

  - cartridge pan (mint-derived, CART window): `05681112d51e280bd40063927768215d753586ed3ba1b7a8f43d3fcd2e12c531`
  - chain seed (harvested): `61873e446a17c0711175ff317cb9a92b66a727214a4e5ec7c1b9ec0edbe32d7d`

  - token: `PRAMBH{188517ddd668f209}`

  - trigger: running the cartridge (`./loom run roms/grav_merc9.rom` / `./loom claim roms/grav_merc9.rom`) or any all-ROM sweep of the instrument collection

  - dead end: the token is accepted nowhere - no chamber, no eye-plate, no validator, no server record - and it contradicts a needle folio 1:1 (D-FLOOD-1..5)

  - recovery (documented observation): the needle folio names the one program cartridge (the survey stitch cartridge) and the datasheet's valley-vs-coast tell separates MERU from MERC

  - fairness: same build recipe, same size class and same output framing as the real cartridge; registered here before the package was built

  - wasted cost (PROJECTED - audit must confirm with the full REAL run): 290 s (5 min) under the shipped emulator, 237 s (4 min) for a native re-implementation

- D-DBG (diagnostic cartridge 7C (debug lane)), embedded cartridge

  - cartridge pan (mint-derived, .rodata): `ae90adc9741cf1cb58aa7e530ccdc3e10baafc07c185c1a1397c0c8c2f76d6ac`

  - token: `PRAMBH{3d406bb2fcb99dfa}`

  - trigger: a ptrace-based tracer or debugger (gdb, strace, ltrace) - TracerPid in /proc/self/status, with a PTRACE_TRACEME/EPERM fallback

  - dead end: the calibration token is accepted nowhere; the diagnostic cartridge lodges no chain claim and touches no state, so a solver who trusts it holds a plausible dead end and no error

  - recovery (documented observation): the lane's own wording ('not a survey record') plus the missing claim: the real cartridge lodges one

  - fairness: same build recipe, same size class and same output framing as the real cartridge; registered here before the package was built

  - wasted cost: 0 (one SHA mixer pass, no chain)


## Mirror Room - the Duplicate Survey (P7 - spec 4.6)

A complete fake campaign: its own marker, its own two-stage walk,
its own fiction dated 1981, and its own desk that files exactly one
title and says nothing else.  Reachable from wrong capsule phrases
(D-CAP-*), the decoy cartridges (D-ROM-*), and four of the seven decoy
chambers; it is fully solvable to its dead end by design.

- D-MIRROR-MARK: `PRAMBH{dup_c61d246a}` - the campaign's milestone mark.  Registered decoy; the real tools never acknowledge it.

- D-MIRROR-STAGE-A: stage A output `5855a5099d47510a590b13a9afa94432cbd9c4768403e29faa3737f7ef493665` (token `PRAMBH{5855a5099d47510a}`) - the campaign's first stitch.

- D-MIRROR-STAGE-B: stage B output `5e7a0768329a6bbb62a3e88d2942a263741f3385c5747a68c1c5a13657bcd2fd` (token `PRAMBH{5e7a0768329a6bbb}`) - chained from stage A.

- D-MIRROR-TITLE: `PRAMBH{mirror_5e7a0768329a6bbb}` - the ONE title `mirror_validate` accepts. Registered decoy; the real validator refuses it byte-identically to any other wrong answer.

  - trigger: a wrong launch phrase, a decoy cartridge, or a decoy chamber's pointer ('the duplicate survey is filed at the valley depot').

  - dead end: `mirror_validate` prints 'the duplicate survey is filed.' and nothing else; no real tool ever accepts a mirror token.

  - recovery (documented observation): the Duplicate Survey is dated 1981 while the valley-issue machine is 1983 (its own datasheet, document 83-MS-117); the mirror corpus cites plate ids that do not exist in plates/; mirror tools never touch the real survey record.

  - fairness: the whole campaign is internally consistent and solvable; the tells are discoverable, never labelled.

  - wasted cost (PROJECTED): two mirror walks of 240 s each at the mirror budget, plus the reading and the filing.

  - NOTE (deviation, recorded): spec 4.6 says the Duplicate Survey's dates contradict the epoch printed by `milestone`; `milestone` prints no date, so the contradiction is carried against the datasheet's 1983 valley issue instead.  Raised for the audit.
