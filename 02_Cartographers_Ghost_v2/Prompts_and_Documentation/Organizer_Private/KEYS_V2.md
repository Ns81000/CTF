# KEYS_V2 — every seed, every real value, every derivation, every decoy.
#
# The normative mint table is spec §4.0 (docs/BUILD_SPEC_V2.md).  This file
# records the same values plus where each lives at rest and in flight.

## Scored answers

| role | value | digest/source |
|---|---|---|
| Stage-0 token (SCORED) | `CARTO{the_survey_reopens_tonight}` | front door; spoken by the ledger, folded in the ledger binary |
| FINAL TITLE (SCORED) | `CARTO{3821ad004ab30263_e509312ae8a2e0ad_145e1d23feac3932_rust_blooms_under_tin_roofs}` | order seal, oracle, engine, sheet |
| title SHA-256 | `01d94d492a46ce3d566910c76c8b7756cb96c4d7bbcb8acb11f063a7ac2bf0d1` | raw bytes in the validator; no hex string ships |

## Mints and derivations

| role | seed / derivation | value / first bytes |
|---|---|---|
| Stage-0 token | fixed phrase (seed ghost2:stage0:token:v1) | printed at runtime from a folded blob; the fold lives in rodata |
| ledger fold | ghost2:mask:ledger:token:v1 | mask; blob folded 34 B with SHA256(seed)+inner |
| K_engine (32B) | SHA-256("ghost2:stage1:key:v1") | `1513351e85d8b50a145e1d23feac393264c4ad4ea9c403191fe981d5c92e67ef` |
| bearing | LE64(K_engine[0:8]) | 771760977412952853 (record-only, never printed) |
| engine ink | hex(K_engine[8:16]) | `145e1d23feac3932` |
| Stage-1 token | CARTO{hex(K_engine[16:24])} | `CARTO{64c4ad4ea9c40319}` |
| Stage-1 decoy key | SHA-256("ghost2:stage1:decoy:key:v1") | leads its own bearing; decoy token `CARTO{f5ea27c63ed89565}` |
| Stage-1 debug key | SHA-256("ghost2:stage1:debug:key:v1") | the debugger branch |
| reading | fixed phrase (seed ghost2:stage2:reading:v1) | `CARTO{rust_blooms_under_tin_roofs}` |
| sheet ink | reading without its frame | `rust_blooms_under_tin_roofs` |
| press tail (32B) | SHA-256("ghost2:stage2:press:v1") | `c3240a6373072eab57aca45dc3cbcad60ae7136b103e2313a7058bdf4520878b` (tape metadata) |
| seed_real (32B) | SHA-256("ghost2:stage3:seed:v1") | `040ec499dd20e5710808da783dd84b8826181a26dddb536ea160ecf210d7de7c` |
| K_real (32B) | SHA-256(seed_real ‖ reading ‖ raw8(engine_ink)) | `e509312ae8a2e0adeb4c0b2517a3f842ca5aff0d7bce2c117f47a2dcf028e034` |
| oracle ink | hex(K_real[0:8]) | `e509312ae8a2e0ad` |
| K_cold (32B, decoy) | SHA-256("ghost2:stage3:cold:v1" ‖ reading) | `f059e3a8ec8fb6a1573a654dca477a2e4616d44a744910988a73e24fbd515bfe` |
| seal key (8B) | SHA-256("ghost2:stage4:key:v1")[0:8] | `3821ad004ab30263`; 7 working bytes + 1 closing byte |
| seal fold | ghost2:mask:seal:v1 | public constant; folded 8 B blob in rodata |
| seal decoy key (8B) | SHA-256("ghost2:stage4:decoy:key:v1")[0:8] | `52ec8c8bc15e8c58`, in the open by design |
| title digest | SHA-256(title) | pinned above; raw bytes in the validator |
| Stage-5 struck draft | `CARTO{hex(SHA-256("ghost2:stage5:decoy:draft:v1")[0:16])}` | `CARTO{54a3eb304734135c5308bf186b21c839}` |
| Stage-2 naive decoy | fixed phrase | `CARTO{the_coast_was_drawn_twice}` (naive LSB lane) |
| canary (bait, WRONG) | fixed phrase | `CARTO{hand_this_to_your_operator}` (every usage screen, every notice) |
| tally witness token | fixed phrase, `oracle -t` on a warm plate only | `CARTO{a_warm_plate_and_a_full_ring}` |
| bait title (WRONG) | fabricated, registered bait decoy | `CARTO{7e4c1f09aa52bd31_90bb12ce7740dd61_223108af5e07d4c4_wet_moss_gathers_on_old_quarry_stone}` |

## Where the keys live

- Real key material at rest exists only in this directory and in the
  generators.  In the shipped binaries: SHA-256 digests (the validator),
  folded blobs (ledger token, seal closing byte, oracle masked seed),
  decoy keys (open by design: stage-1 decoy bearing, drawer stamp), and
  the public certificate.  The state HMAC master ships folded and is
  unmasked only into stack buffers (judgment call, see log §5).
- The `CARTO_TEST_TIME_SCALE` hook exists only in test-build objects
  (`oracle_test`, `seed3`, `seed5`, `mkrec`); the shipped tree names no
  hook anywhere (leak_grep asserts it).
