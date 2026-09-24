# PRAMBH v3 - KEYS (organizer-private)

Full seed -> value -> location table (spec 5).

| label / seed | value | location |
| --- | --- | --- |
| SHA256("prambh:archive:root:v3") | ca21a27efa07e39b8d97d944d39451384c9bcb6af38251c9c310cc5237b37925 | derivation root (public, deterministic) |
| SHA256("prambh:stage0:token:v1") | PRAMBH{zero_b8c1d72c} | stage0_milestone/milestone (.rodata), printed every run |
| SHA256("prambh:canary:token:v1") | PRAMBH{canary_87eefe3e} | HUMAN_OPERATOR_NOTICE.txt, usage screens, PNG Notice chunks |
| SHA256("prambh:launch:phrase:v1") -> 6 words | fable coil autumn coast reed zinc | LAUNCH.txt (package root, ARCHIVE mode) |
| SHA256("prambh:capsule:content:v1") | 96415166fc01091e7bce5b43d36a5d491cb6591f0471415e5f670535c7856392 | nowhere in the clear; = capsule.bin XOR SHA256ctr(SHA256(phrase)) |
| capsule.bin | e1cbbd2f51685fb35a0e0fa991a9580a7fe579e486007086dc6c1c3570531954 | capsule.bin (package root) |
| SHA256("prambh:loom:seed:v1" || capsule_content) | 4668e434c5ea0e9b249cae68c6ecc81e1ad79afaa4f0aefef0661b72746045c7 | nowhere; derived by the loom from the opened capsule (chain #1 seed) |
| SHA256("prambh:loom:model:v1") | MERU-8 | needle folio 338 only (flood corpus) |
| SHA256("prambh:doors:numbers:v1") -> 8 hall numbers | 761, 268, 787, 451, 215, 338, 834, 756 | door folios (P6); needle/decoy folios name one each |
| SHA256("prambh:doors:real:v1") -> real hall | 761 (index 0 of 8) | needle folio 325; the real chamber (P6) |
| flood needle folios | folio_265, folio_338, folio_325, folio_108, folio_020 | field-notes/; order: capsule, loom, hall, mirror, plates |
| flood decoy folios | folio_386, folio_364, folio_192, folio_237, folio_374 | field-notes/; contradict needles 1:1 |
| decoy plate codes | 21b3edf867f4117638, 808db61e567e04f811, d52cba0a2ab5931b34, 67ad16b261c459305e, 1b6778cc6225d5afd4, 8c83b6e330f1a51b0d | plates/decoy_plate_0..5.png (rendered pixels) |
| SHA256("prambh:loom:decoy:v1"||LE32(0)) -> cartridge pan | f610054b36efc2750701f0f4383df620077a9cbc8de3d8177a74d8817124e48f | roms/tide_merc6.rom CART window, written by gen_rom.py |
| D-ROM-1 chain seed = SHA256("prambh:loom:seed:v1"||pan) | a1c3110b71a474135e5c10684c33988c6955f1ec141a2d06cfc8670203eb82cd | walked by roms/tide_merc6.rom (harvested, runs/p5_decoy_tokens.txt) |
| D-ROM-1 field token (chain engine, production T) | PRAMBH{21200db398a8c416} | printed by roms/tide_merc6.rom; registered decoy, accepted nowhere |
| SHA256("prambh:loom:decoy:v1"||LE32(1)) -> cartridge pan | dd63121505be80688949b2ce21675cb52ae3af672d2c50dc5f8c55f704a36045 | roms/star_merc3.rom CART window, written by gen_rom.py |
| D-ROM-2 chain seed = SHA256("prambh:loom:seed:v1"||pan) | 7cdc4ce68030cdb09fd9e045b846f83e76966d09ea8105528f853ed5ba60f00d | walked by roms/star_merc3.rom (harvested, runs/p5_decoy_tokens.txt) |
| D-ROM-2 field token (chain engine, production T) | PRAMBH{dfc675e0d58fb83a} | printed by roms/star_merc3.rom; registered decoy, accepted nowhere |
| SHA256("prambh:loom:decoy:v1"||LE32(2)) -> cartridge pan | 05681112d51e280bd40063927768215d753586ed3ba1b7a8f43d3fcd2e12c531 | roms/grav_merc9.rom CART window, written by gen_rom.py |
| D-ROM-3 chain seed = SHA256("prambh:loom:seed:v1"||pan) | 61873e446a17c0711175ff317cb9a92b66a727214a4e5ec7c1b9ec0edbe32d7d | walked by roms/grav_merc9.rom (harvested, runs/p5_decoy_tokens.txt) |
| D-ROM-3 field token (chain engine, production T) | PRAMBH{188517ddd668f209} | printed by roms/grav_merc9.rom; registered decoy, accepted nowhere |
| SHA256("prambh:loom:debug:v1") -> diagnostic pan | ae90adc9741cf1cb58aa7e530ccdc3e10baafc07c185c1a1397c0c8c2f76d6ac | diagnostic cartridge .rodata (the anti-debug lane) |
| D-DBG calibration token | PRAMBH{3d406bb2fcb99dfa} | printed by the diagnostic cartridge under a tracer; registered decoy (independently re-derived in the P5 suite from its pan) |
| zip seal words (SHA256("prambh:release:zip:v1") -> 4 words) | gate hearth zinc field | password for the distributed prambh.zip.enc; the room description hides it as the Keeper's 4-station perimeter landmark riddle (Station North=gate, Center=hearth, West=zinc, South=field) |
| SHA256("prambh:mirror:token:v1") -> survey mark | PRAMBH{dup_c61d246a} | printed by mirror/mirror_milestone; registered decoy |
| mirror stage A output (own walk, 2-stage) | 5855a5099d47510a590b13a9afa94432cbd9c4768403e29faa3737f7ef493665 | mirror_milestone walk; token PRAMBH{5855a5099d47510a} |
| mirror stage B output (chained) | 5e7a0768329a6bbb62a3e88d2942a263741f3385c5747a68c1c5a13657bcd2fd | mirror_milestone seal; token PRAMBH{5e7a0768329a6bbb} |
| mirror dead-end title | PRAMBH{mirror_5e7a0768329a6bbb} | the ONE title mirror_validate accepts (registered decoy) |
| real eye ink | Y22RGQ_9NK3HT_9UJYNG | three plates, normative order |
| real eye codes | Y22RGQ, 9NK3HT, 9UJYNG | plates/depth.png, hue.png, sheet_a+sheet_b.png |
| decoy eye codes | 7HX5YC, FKWQXA, CF59LP | carried INSIDE the same plates (second plane, luminance, reciprocal bearing) |
| door ink | 66cb77c72ed791a7 | the real chamber's plate fragment |
| real door phrase (the verse answer) | kiln weir sapling mantle hollow lunar | read from riddle.bin with K_loom only |
| chain #2 load vector (real chamber handover) | 83687190e2798db9283c55e0658ac7eb262a51b185dd5ea44987380108f4317a | printed inside the real chamber |
| real chamber hall | 761 (index 0) | decoy chambers cite the other seven halls |
| chain #1 out (loom ink) | de918c455c4b1d42 | output of production T walk (runs/chain1_walk.txt) |
| chain #1 checkpoint | PRAMBH{ec5ba654fe8e606a} | intermediate claim checkpoint minted by loom |
| chain #2 out (seal ink) | 43560fb33c8d0924 | output of production T walk (runs/chain2_walk.txt) |
| chain #2 checkpoint | PRAMBH{d4802d644703f98a} | seal chain intermediate checkpoint |
| final capstone title | PRAMBH{43560fb33c8d0924_de918c455c4b1d42_66cb77c72ed791a7_Y22RGQ_9NK3HT_9UJYNG} | verified and accepted by stage5_eyes/validate |
