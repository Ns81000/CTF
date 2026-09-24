# PRAMBH v3 - SESSION 1 LOG (build session, resumed at P5)

## 1. Status

P0-P4 were complete when this session began (commits: spec, p0, p1, p2 x2,
p3, p4, p5-wip).  This session finished P5 and built P6-P10.  Suite
verdicts live in organizer-private/runs/ (each file ends with its own
"n PASS, m FAIL" line):

| suite | file |
| --- | --- |
| state (P1) | runs/suite_state.txt |
| chain (P2) | runs/suite_chain.txt |
| stage0 (P3) | runs/suite_stage0.txt |
| flood (P4) | runs/suite_flood.txt |
| loom (P5, >=60) | runs/p5_loom.txt |
| doors (P6, >=40) | runs/suite_doors.txt |
| mirror (P7, >=35) | runs/p7_mirror.txt |
| eyes (P8, >=45) | runs/suite_eyes.txt |
| server (P9, >=35) | runs/p9_server.txt |
| eventgen (P9, >=20) | runs/p9_eventgen.txt |

## 2. Environment

- Ubuntu 24.04 (WSL2), kernel 6.6.87.2-microsoft-standard-WSL2, 12 cores,
  7.6 GB RAM, x86-64; repo /home/ns8pc/prambh-build, Windows mirror
  /mnt/e/drive-upload.
- toolchain: musl-gcc (musl 1.2), gcc 13.3, python3 3.12 with PIL + numpy.
- method: wsl.exe from PowerShell; long jobs launched with the
  Start-Process recipe of the contract's Appendix B.2.

## 3. P5 - loom emulator, cartridges, decoy registry (finished here)

- src/loom/test_loom.sh: the phase suite - build hygiene, selftest
  bit-equality C-vs-Python across all 96 opcodes, real / decoy /
  diagnostic-lane parity, registry-vs-harvest equality, leak and behaviour
  lanes, and the reduced-T wall-clock projection.
- src/gen/loom_decoys.py: harvest-only registry of the four registered
  loom decoy lanes; the diagnostic lane's token is re-derived independently
  from its pan and the suite asserts the two agree.
- src/loom/project_wallclock.py: the Appendix C.2 projection (per-step cost
  at three reduced T, cache-resident probe, emulated route, arithmetic) ->
  runs/p5_projection.{txt,json}.
- src/gen/gen_canary.py -> src/core/canary.h: the minted canary, printed on
  every shipped tool's usage screen (spec 4.10).
- production src/loom/params.h: T = 7,705,630,875, S = 536,870,912.
- Two real defects found by the new suite and fixed:
  1. the anti-debug lane read /proc/self/TracerPid, which does not exist on
     Linux, so gdb was never detected; loom.c now parses the TracerPid
     field of /proc/self/status (gdb and strace lanes are green);
  2. the datasheet claimed "64 operations" while opcodes.py defines 96; the
     count is now generated from the ISA table.
- Also fixed: every tool now returns rc 0 for every abuse input (spec 7.6).

## 4. P6 - Hall of Doors (spec 4.5)

- src/doors/verse_gen.py: the verse generator.  Eight designed readings of
  the same six field-note lines each yield one designed phrase: the real
  answer (the line-final "settling" word) plus the seven misreadings (the
  word after each of past/by/at/near/under/through/toward).  The generator
  self-checks every mapping.
- src/doors/chambers_gen.py: the real chamber (hall 761: hall ink + chain
  #2's handover vector) and seven decoy chambers, each with its own
  12-minute walk, its harvested field token, a decoy folio, a decoy plate
  id, a decoy cartridge and the Duplicate Survey pointer.
- src/doors/doors_build.py: doors.bin (eight fixed-size
  seed(32) || ciphertext(2048) records, raw XOR, no marker in ciphertext)
  and riddle.bin (the verse XOR SHA256ctr(K_loom)).
- src/doors/doors.c: the shipped tool - open <phrase> (answer as key, one
  fixed line for every failure) and riddle <K_loom> (opens the verse,
  records the stage bit).  rc 0, silent stderr, state-only writes.
- src/doors/test_doors.sh: >=40 checks.
- src/gen/trap_attraction.py -> organizer-private/TRAP_ATTRACTION.md
  (Appendix C.3): the dominant misreadings mapped to decoy chambers and
  mirror threads, with the cross-corroboration matrix.

## 5. P7 - Mirror Room (spec 4.6)

- src/mirror/mirror_milestone.c (own marker; walk and seal settle its own
  two-stage chain) and src/mirror/mirror_validate.c (accepts exactly one
  registered decoy title, one non-committal line, constant-time compare).
- src/mirror/mirror_chain.py: the two-stage walk, harvested to
  runs/mirror_chain.txt (stage A 575.7 s, stage B 574.0 s under load).
- src/mirror/gen_mirror.py: the campaign constants and the six
  Duplicate-Survey folios (generated, dated 1981, citing plate ids that do
  not exist in plates/).
- src/mirror/test_mirror.sh: >=35 checks including a scripted full mirror
  solve to its honest dead end.

## 6. P8 - Surveyor's Eyes (spec 4.7)

- src/eyes/plate_gen.py: the three human gates as deterministic numpy/PIL
  artifacts - depth (two planes: the survey's code cut nearest, the depot's
  deeper, repeat period jittered per band), hue (hue-difference code at
  matched luminance plus a luminance-channel decoy), and the two line
  screens (fine modulation = survey code, coarse = depot code; two
  alignment maxima).
- src/eyes/gen_eyes.py: chain #2 dials, SHA-256 of the assembled title
  (the only thing the validator stores) and the sealed viewing notes.
- src/eyes/eyes.c (seal, gated on the real chamber) and
  src/eyes/validate.c (the final record: state gates, pacing, one
  acceptance line, one refusal line for every failure class, digest-only
  storage).
- src/eyes/decode_lanes.py: the three automation lanes with measured costs
  (spec 7.4).
- src/eyes/test_eyes.sh: >=45 checks.

## 7. P9 - server (4.8) and EVENT generator (3)

- src/server/checker.py: stdlib-only ThreadingHTTPServer - /register,
  /checkpoint (ordered, stalls counted silently), /submit (the
  proof-of-journey flag gated on the player's own title digest, ordered
  checkpoints and MIN_JOURNEY), /board.  JSON state with HMAC records only,
  per-IP pacing.
- src/server/test_server.sh: >=35 checks driving the real server with curl.
- src/gen/player_gen.py plus the PRAMBH_PLAYER_HEX player context in
  mint.py: EVENT mode regenerates the whole package from
  seed = SHA-256(master_secret || "prambh:player:v1" || callsign); ARCHIVE
  mode (no context) stays bit-identical to the archived package.
- src/gen/test_eventgen.sh: >=20 checks (determinism x2, three callsigns,
  cross-contamination, per-player answers, ARCHIVE regression).

## 8. P10 - calibration, packaging, adversarial quick pass

- src/final/: build_package.py, make_release.sh (clamped mtimes, sorted
  staging, TZ=UTC zip -X -@, MANIFEST.sha256, copy to
  /mnt/e/drive-upload/prambh/RELEASE/), verify_all.sh, package_check.sh,
  rebuild_repro.sh, isolated_solve.sh, leak_grep.sh, attack_static.py,
  attack_scripted.py, floor_proof.py, p5_loom.sh.
  Package release includes `prambh.zip.enc` (AES-256-CBC PBKDF2 200k iter,
  passphrase `gate hearth zinc field` per KEYS / THM briefing).
- src/gen/chain_jobs.py: the deterministic emitter for every organizer-side
  chain walk, so any run reproduces the values bit-for-bit.
- src/gen/docs_gen.py -> COST_MODEL.md, SOLVE_PATH_PRIVATE.md, HINTS.md,
  TRYHACKME_ROOM_TEXT.md.

## 9. Chain work this session

Launched in parallel (Windows-side Start-Process, Appendix B.2):

- chain #1 (loom seed, T = 7,705,630,875) -> runs/chain1_walk.txt
- chain #2 (eyes seal seed) -> runs/chain2_walk.txt
- seven decoy-chamber walks (T = 1,232,900,940 each) -> runs/door{1..7}_walk.txt
- the mirror campaign's two stages -> runs/mirror_chain.txt (done: 575.7 s
  and 574.0 s under load)

Nine 512 MiB walks ran concurrently on a 12-core/7.6 GB machine, so every
measured wall-clock is contention-inflated; the design numbers are the
projected ones in runs/p5_projection.txt.

## 10. Timings (PROJECTED per Appendix C.2)

See runs/p5_projection.txt for the raw numbers and the full arithmetic, and
runs/floor_proof.txt for the floor statement.  Summary: native ~0.58
us/step -> chain #1 ~75 min; emulated ~11 us/step -> chain #1 ~23.5 h;
cache-resident ~0.2-0.3 us and the rest of each step is a DRAM round-trip,
so a 4x faster core buys ~1.1x, not 4x - the walk is one sequential
SHA-256 dependency chain and nothing in it parallelises.  Honest ARCHIVE
path: two chains (~2.5 h) plus the seven 12-minute decoy walks a wrong
reading invites, the plate gates and the paper record.  EVENT mode adds the
server's 4 h MIN_JOURNEY gate as a backstop, never as the floor.

NOT measured here (audit, Appendix C.2a): the full REAL-T emulated
cartridge run, the full REAL-T native walk, the hours-long honest
REAL-paced solve, the isolated stranger solve at production T, and the
reduced-table attack at production T.

## 11. NOT-DONE / DEFERRED

Every deferred item is listed with its exact command in
organizer-private/HANDOFF.md.  Nothing was silently dropped.

## 12. Judgment calls and deviations

1. /proc/self/TracerPid does not exist on Linux; the authoritative detector
   is the TracerPid field of /proc/self/status (fixed).
2. The shipped machine is the minted model MERU-8 in every generated
   artifact, while the contract prose calls the emulator MERU-1 and names
   the datasheet field-notes/meru1_datasheet.txt.  The datasheet carries
   the valley-vs-coast tell that resolves the near-miss.
3. Spec 4.6's mirror tell references an epoch printed by milestone;
   milestone prints no date, so the contradiction is carried against the
   datasheet's 1983 valley issue (recorded in TRAP_CATALOGUE.md).
4. Suites run the chains at reduced T wherever the contract allows it
   (Appendix C.2); every production-T run is listed in HANDOFF.md.
5. Tracked organizer binaries (src/chain/prambh_chain, chain_dbg,
   src/state/test_state) are deliberate; none enters the zip.

