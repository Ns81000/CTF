# KICKOFF — Phase 3 (Stage 2: Nested Steganography)

You are starting Phase 3 of "The Cartographer's Ghost" build. Work strictly in order:

1. READ THE FULL BUILD SPEC first, start to end, in chunks if needed (do NOT skim,
   do NOT jump to the relevant section — phases depend on cumulative context):
   Windows: d:\gandu\01_BUILD_PROMPT_FOR_CLAUDE_CODE.md
   WSL2 (identical copy): /home/manish/cartographer-build/docs/BUILD_SPEC.md

2. READ EVERY PHASE LOG IN ORDER, IN FULL, before writing any code:
   /home/manish/cartographer-build/logs/PHASE_0_LOG.md
   /home/manish/cartographer-build/logs/PHASE_1_LOG.md
   /home/manish/cartographer-build/logs/PHASE_2_LOG.md   (890 lines; read it all)
   Pay special attention to:
     - PHASE_1_LOG D11 canonical flag format ^CARTO\{[a-z0-9_]{8,64}\}$ — every
       future mint MUST conform; D13 single canonical HMAC key; D14 runtime rule
       CREATED==TAMPERED; D17 build pipeline (incl. objcopy --remove-section .comment).
     - PHASE_2_LOG D18 (Stage 1 emits key material AND a token; Phase 7 scoring
       decision), D23 (Stage 2 key material = LE64(R6)||LE64(R7)||LE64(R1)||LE64(R2),
       32 bytes), D26 (decoy routing: branch B -> state bit 1u<<(B-1)), D27 (the
       real/decoy/debug candidates), D29 (policy.h decoy registry is now real),
       section 9 open questions (esp. #2: Phase 5 owns the "transformed Stage 1
       real output" decision, and #5: ptrace-availability fairness risk).

3. INDEPENDENTLY RE-VERIFY Phases 0, 1 and 2 — never trust the logs; reproduce.
   RUN THE SUITES SERIALLY (they share cartographer/.cartographer_state and
   interfere if run concurrently — this actually happened in Phase 2):

     wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/state && make clean && make test && file test_state'
   Expect: 26 tests run, 0 failed, ALL TESTS PASSED, statically linked.

     wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/stage0 && make && ./test_stage0.sh'
   Expect: 36 tests run, 0 failed, ALL TESTS PASSED.

     wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/stage1_vm && make test'
   Expect: "8 checks, 0 failed / ALL CHECKS PASSED" then
           "65 tests run, 0 failed / ALL TESTS PASSED" (gdb must be installed; it is).

     wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/stage1_vm && python3 model_vm.py --selftest'
   Expect: profile0/profile1 same key, detect=1 a different key, SELFTEST OK
           (key fd3e8049...4010f; debug key fb48aecd...1621).

   Sanity anchors: stage1_vm sha256 317d4a846af9168ed34b1283ae05bccdebb659ade342343d63a16fcc99f49e1a;
   stage0_start sha256 f2d1e064554ed7bafa8beb8deaf9bf4887bd9d857b9c745b68678e6ee1d2486f.
   If anything fails: STOP, fix it, re-verify before adding anything new.

4. Only then build Phase 3 per the spec (Phase 3 — Stage 2: Nested Steganography):
   - Decoy layer: naive full-image LSB in a PNG, findable by any standard tool,
     decoding to a flag-shaped string that PASSES the Stage 4 checksum/format check
     (D11). Submitting it must route into the extended dead-end branch via the
     state-file logic (carto_lookup_decoy + carto_mark_decoy, branch B -> bit
     1u<<(B-1)), framed as new information, never as an error.
   - Real layer: blue-channel-only LSB at a PIXEL STRIDE DERIVED FROM STAGE 1'S
     REAL KEY MATERIAL (see PHASE_2_LOG D23/D27 — use the real 32-byte key, not the
     token and not the decoy; document the exact derivation), compressed with zlib
     using a CUSTOM PRESET DICTIONARY derived from a constant elsewhere in the
     package, so naive decompression fails until the dictionary is supplied.
   - WAV carrier: real content in RIFF metadata padding (not audio samples), plus an
     obvious-but-irrelevant LSB pattern in the samples as a cheap secondary
     micro-distraction.
   - Human trap: at least one piece requires a fiddly MANUAL step discovered by
     reading tool help output (e.g. an ImageMagick/exiftool flag combination whose
     default output silently mangles the exact byte range that matters).
   - The stage must link the shared state library (attempts, interaction ring,
     escalation variants, decoy routing) and record its interactions. If the stage
     ships a binary, it must be musl-static/stripped/scrubbed per PHASE_2_LOG D30
     and land in cartographer/stage2_stego/.
   - State semantics for the wrong-Stage-1-key case: wrong key -> wrong stride ->
     garbage extraction that does NOT parse and does NOT error (spec).
   - Register every new discoverable decoy in src/state/policy.h (D29 pattern) and
     keep it D11-conforming; update src/state/test_part2.c only if the mechanism
     (not merely the data) changes — the decoy test is already table-driven.
   - Calibration is Phase 6's job: do NOT tune policy.h thresholds.

5. End of phase per the Session Continuity Protocol: run every relevant verification
   and paste REAL output into logs/PHASE_3_LOG.md (complete and standalone: what was
   built, every design decision, every constant including stride/dictionary/pixel
   derivations and carrier checksums, exact commands, full test output, not-yet-done
   list, open questions); write logs/KICKOFF_PHASE_4.md; git commit.

Constraints reminder: fully offline; no writes outside the working directory; every
trap has a fair deterministic resolution; keep means-of-derivation constants,
seeds and private write-ups OUT of solver-facing material (cartographer/ ships;
logs/ and src/ are internal). Author via
d:\gandu\_stage\s2_* + `tr -d "\r" < /mnt/d/gandu/_stage/s2_sync.sh | bash`
(the Phase 2 pattern; s1_sync.sh is the template), or edit repo files directly in
WSL. Keep the suites serial.
