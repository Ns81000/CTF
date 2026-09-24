# PHASE 0 LOG — Bootstrap Session (Environment + Shared State Library)

Status: COMPLETE — all verifications passing (26/26 unit tests, clean-room re-run,
static-link check, key-not-in-binary check). Repo: /home/manish/cartographer-build
(git branch `main`). Date of session: 2026-09-18.

## 0. Scope ruling for this phase (judgment call, flagged)

The spec defines Phases 1-7 as build phases and treats "Phase 0" as the session that
starts from a fresh paste of the spec (Session Continuity Protocol). Phase 0 scope
chosen here:

- Full WSL2 environment audit; install anything missing via apt (spec says don't ask).
- git-init of ~/cartographer-build with repo-local identity.
- The shared state library (`state.c`/`state.h`) from the spec's "Overall Architecture"
  section: fully implemented + unit-tested. Rationale: the spec says EVERY stage binary
  links it and Phase 1's Stage 0 must initialize `.cartographer_state` on first run;
  building it now de-risks every later phase. PHASE 1 CONSUMES THIS API AS-IS — do not
  redesign it (extend via policy.h and stage code, not by changing the core).
- Protocol artifacts: this log + KICKOFF_PHASE_1.md.

NOT built this session (by design): no stage binaries, no real flags, no decoy
content, no stego carriers, no oracle, no validator, no calibration, no packaging.

## 1. What was built (exact paths, all in /home/manish/cartographer-build)

- docs/BUILD_SPEC.md          — copy of the full build spec (from Windows-side
                                d:\gandu\01_BUILD_PROMPT_FOR_CLAUDE_CODE.md), LF-normalized
- .gitignore                  — repo root: *.o *.a test_state .probe probe_copied.c
- src/state/carto_sha256.h    — SHA-256/HMAC-SHA256/ct_equal API (21 lines)
- src/state/carto_sha256.c    — FIPS 180-4 SHA-256 + RFC 2104 HMAC (149 lines)
- src/state/state.h           — public API + full on-disk format doc (89 lines)
- src/state/state_internal.h  — internal cross-TU interface (15 lines)
- src/state/policy.h          — ALL-PLACEHOLDER policy data (38 lines)
- src/state/state_core.c      — key obfuscation, serialize/deserialize, atomic
                                load/save, mutators (273 lines)
- src/state/state_policy.c    — stddev, escalation bitmask, decoy lookup, now_ms,
                                known-answer selftests (187 lines)
- src/state/test_util.h       — RUN/CHECK test macros + counters (31 lines)
- src/state/test_part1.c      — harness main() + 14 tests (362 lines)
- src/state/test_part2.c      — 12 tests + run_part2_tests() (279 lines)
- src/state/gen_vectors.py    — deterministic HMAC differential vectors (46 lines)
- src/state/Makefile          — musl static build; `make test` = build + verify (39 lines)

Build artifacts (rebuilt by make, NOT source, now untracked): *.o, libstate.a, test_state.
Windows staging scratch: d:\gandu\_stage\ holds chunked copies (`*.part2`) — SCRATCH ONLY;
the WSL repo is canonical. Authoring pipeline: editor writes staging chunks; one command
copies via /mnt/d, concatenates parts, CRLF→LF-normalizes, builds, tests (command C1 below).
## 2. Design decisions and why

D1. State file = fixed 352-byte little-endian binary + trailing HMAC-SHA256.
    Offsets (documented in state.h): magic "CART" @0x000, format_version=1 @0x004,
    flags u8 (must be 0) @0x005, reserved u16 @0x006, first_run_ms u64 @0x008,
    attempt_count[5] u32 @0x010, decoy_mask[5] u32 @0x024, ring_count u16 @0x038,
    ring_head u16 @0x03A, debugger_detected u8 + reserved u8[3] @0x03C,
    ring_ts[32] u64 @0x040, HMAC[32] @0x140 over bytes [0x000,0x140). Deterministic,
    byte-exact testable, no parser dependency.

D2. Tamper/corrupt/truncated/extended/bad-magic/bad-HMAC ⇒ SILENT reset to first-run
    defaults, file rewritten, CARTO_LOAD_TAMPERED returned. Zero output on stdout/stderr
    (PROVED by fd-capture test test_tamper_silent_reset). This implements "self-defeating
    tampering": no error message exists for an agent to grep. Missing file ⇒ fresh create
    (CARTO_LOAD_CREATED). Stage binaries must treat CREATED and TAMPERED identically at
    runtime; the codes exist for tests only.

D3. save() is atomic: write to path+".tmp", then rename(). A Ctrl-C mid-write can never
    leave a half-written state file. Test asserts no .tmp residue.

D4. HMAC key obfuscation: canonical 32-byte key NEVER plaintext in .rodata. TWO
    independently masked copies (key XOR SHA-256-derived mask, different seed strings)
    in state_core.c; unmask re-derives masks into stack buffers at runtime. Why two
    copies: (a) carto_key_selftest proves the XOR path is transcription-clean;
    (b) test_key_canonical forces the C side to reproduce python's HMAC under the
    DOCUMENTED key using ONLY carto_unmask_key — catches even identical corruption of
    both blobs. (b) found a real Phase-0 bug: kMaskedKey bytes 16-31 had a dropped
    leading-zero nibble (0x0d.. became 0xdb..); round-trip tests passed anyway because
    save/load agreed on the same wrong key — the redundancy caught it.
    strings(1) check: `strings test_state | grep f03ea6b5` finds nothing (mask seed
    strings "cartographer-mask-v1/v2" DO appear — accepted by design; deriving a mask
    alone reveals nothing). Honest note: obfuscation against casual inspection, not
    cryptographic strength; spec requires "obfuscated (not plaintext)" and state
    tampering is self-defeating anyway.

D5. Timing signals: interaction ring = last 32 wall-clock timestamps (ms since epoch,
    CLOCK_REALTIME). carto_timing_stddev_ms = POPULATION stddev of inter-arrival deltas
    across the ring (wrap-correct chronological order); negative deltas clamp to 0
    (clock glitch tolerance); fewer than CARTO_MIN_TIMING_DELTAS deltas ⇒ HUGE_VAL
    ("insufficient evidence" must never read as "suspiciously uniform"). Wall clock is
    correct here because deltas must span process restarts.

D6. carto_should_escalate returns a reason BITMASK: CARTO_ESC_TIME_FAST (0x1) |
    CARTO_ESC_TIMING_UNIFORM (0x2) | CARTO_ESC_DEBUGGER (0x4). Thresholds from policy.h.
    Mapping "which pre-built variant to serve" is stage-code policy in Phases 2-4 —
    the library only supplies reasons.

D7. now_ms is an explicit parameter on load/record/escalate (deterministic tests, no
    hidden clock in the API); binaries call carto_now_ms() themselves.

D8. SHA-256/HMAC hand-rolled (zero deps; keeps musl-static binaries small). Verified
    three independent ways: RFC 4231 TC1/TC2/TC4/TC6 (text fetched from rfc-editor.org
    THIS session and transcribed), SHA-256 ""/"abc" vectors, and a 68-case differential
    test vs python hashlib/hmac with key lengths straddling the 64-byte block boundary
    (63/64/65/100/131/200) exercising the hash-key-first path.

D9. Decoy routing: carto_lookup_decoy(stage, flag) exact-matches policy.h table,
    returns branch id >=1 or -1; submissions persist as per-stage bitmasks. Table holds
    ONE PLACEHOLDER entry (mechanism test only) — real decoys arrive Phases 2-4.

D10. All policy constants are PHASE-0 PLACEHOLDERS; Phase 6 calibrates. Do not tune
     them earlier.
## 3. Every constant introduced (exact values + locations)

Crypto material (all in state_core.c unless noted):
- Canonical HMAC key:
    f03ea6b5c1b869482723c0d11d635f8e9966c43a0a8def87fd1e2e950c10a7de
  = SHA-256("cartographer-ghost:phase0 dev key:do-not-ship")
  (NEVER appears in any binary; only masked forms below)
- mask v1 = SHA-256("cartographer-mask-v1"):
    4f09527f32262cbb959a1a743173188494dc6fa18d848981f9cd4c533de60ffc
- mask v2 = SHA-256("cartographer-mask-v2"):
    ebb8aca9887d7ce1fa90e8a8ae3c2bf9904e46a4b2ec283f74bd5e37cf6b141b
- kMaskedKey  = key XOR maskv1 (state_core.c):
    bf37f4caf39e45f3b2b9daa52c10470a0dbaab9b8709660604d362c631f6a822
- kMaskedKey2 = key XOR maskv2 (state_core.c):
    1b860a1c49c515a9ddb32879b35f74770928829eb861c7b889a370a2c37bb3c5
- Canonical-key probe: HMAC(canonical_key, "cartographer-key-probe")
  = b32ef0b76dc05f0d1d0916cc361c427cf4dee9ec48529d17e9399f9f8f700910
  (gen_vectors.py computes it; test_key_canonical reproduces it via
   carto_unmask_key — the binding check between documented key and shipped blob)
- Vector files (generated by gen_vectors.py, build-time only):
  /tmp/carto_selftest.txt = single hex line (probe HMAC)
  /tmp/carto_vectors.txt  = 68 lines "keyhex msghex machex"

State file format (state.h, implemented in state_core.c):
- Size 352 bytes (0x160); magic "CART"; format_version u8 = 1
- flags u8, reserved u16, reserved u8[3] after debugger flag: must be 0 on load
  (deserialize rejects nonzero — defense in depth on top of the HMAC)
- CARTO_RING_SIZE = 32; ring_count <= 32 and ring_head < 32 enforced on load
- All integers little-endian regardless of host

Policy placeholders (policy.h) — CALIBRATE IN PHASE 6, do not tune earlier:
- CARTO_T_FAST_SEC_DEFAULT = 90; carto_t_fast_sec[5] = {90,90,90,90,90}
  ("reached stage too fast" = seconds since first_run below threshold)
- CARTO_STDDEV_LOW_MS = 1500.0 (inter-arrival stddev at/below this = suspiciously
  uniform scripted-loop tell)
- CARTO_MIN_TIMING_DELTAS = 4 (below this, stddev = HUGE_VAL = never flags)
- Decoy table placeholder (Phases 2-4 replace the contents):
  { stage 1, "CARTO{phase0-placeholder-decoy}", branch 1 }
- FLAG FORMAT: "CARTO{...}" is TENTATIVE. Phase 1 must finalize the canonical flag
  format and propagate it everywhere (then log it).

Test/metadata constants:
- gen_vectors.py SEED = 777001; 68 vectors; key lengths cycle
  1,2,3,16,20,32,63,64,65,100,131,200; msg lengths 1..64
- git identity (repo-local): user.name=cartographer-build-agent
  user.email=agent@cartographer-build.local; core.autocrlf=false; commit.gpgsign=false
- State path convention for stage binaries (Phase 1+): pass "./.cartographer_state"
  explicitly; the file lives at the cartographer/ package root next to the binaries.

## 4. Exact commands (runnable verbatim)

C1. Rebuild-from-staging pipeline (ONLY if rebuilding from d:\gandu\_stage chunks;
    the repo already holds concatenated LF sources — prefer C2):
wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/state && rm -f *.c *.h *.py Makefile *.o *.a test_state /tmp/carto_vectors.txt /tmp/carto_selftest.txt && cp /mnt/d/gandu/_stage/carto_sha256.h /mnt/d/gandu/_stage/carto_sha256.c /mnt/d/gandu/_stage/state.h /mnt/d/gandu/_stage/policy.h /mnt/d/gandu/_stage/state_internal.h /mnt/d/gandu/_stage/state_core.c /mnt/d/gandu/_stage/state_policy.c /mnt/d/gandu/_stage/test_util.h /mnt/d/gandu/_stage/test_part1.c /mnt/d/gandu/_stage/test_part2.c /mnt/d/gandu/_stage/gen_vectors.py /mnt/d/gandu/_stage/Makefile . && cat /mnt/d/gandu/_stage/state_core.part2 >> state_core.c && cat /mnt/d/gandu/_stage/test_part1.part2 >> test_part1.c && cat /mnt/d/gandu/_stage/test_part2.part2 >> test_part2.c && python3 -c "import pathlib,glob; [pathlib.Path(p).write_bytes(pathlib.Path(p).read_bytes().replace(b\"\r\n\", b\"\n\")) for p in glob.glob(\"*.c\")+glob.glob(\"*.h\")+[\"Makefile\",\"gen_vectors.py\"]]" && wc -l *.c *.h Makefile && make test'

C2. THE re-verification command (run this; expect 26/26 ALL TESTS PASSED):
wsl.exe bash -lc 'cd /home/manish/cartographer-build/src/state && make clean && make test && file test_state'

C3. Key-not-in-binary check (expect NOT-IN-BINARY-OK):
wsl.exe bash -lc 'strings /home/manish/cartographer-build/src/state/test_state | grep -q f03ea6b5 && echo FOUND-BAD || echo NOT-IN-BINARY-OK'

C4. Environment install actually run this session (already done; idempotent):
wsl.exe bash -lc "echo 1234 | sudo -S bash -c 'apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y zip unzip pkg-config' && command -v zip unzip pkg-config"

C5. Key/mask derivation actually run (canonical key + mask v1; mask v2 derived by the
    same one-liner with seed "cartographer-mask-v2"):
wsl.exe bash -lc 'python3 -c "import hashlib; key=hashlib.sha256(b\"cartographer-ghost:phase0 dev key:do-not-ship\").digest(); mask=hashlib.sha256(b\"cartographer-mask-v1\").digest(); masked=bytes(a^b for a,b in zip(key,mask)); print(\"key=\",key.hex()); print(\"mask=\",mask.hex()); print(\"masked=\",masked.hex())"'

C6. RFC 4231 extraction actually run (vectors transcribed from this output):
wsl.exe bash -lc 'curl -s https://www.rfc-editor.org/rfc/rfc4231.txt -o /tmp/rfc4231.txt && awk "/Test Case 1/,/Test Case 3/" /tmp/rfc4231.txt | head -70'
## 5. Verification run — full real output (clean-room: make clean && make test)

```
rm -f *.o libstate.a test_state
musl-gcc -O2 -Wall -Wextra -std=c11 -static -c carto_sha256.c -o carto_sha256.o
musl-gcc -O2 -Wall -Wextra -std=c11 -static -c state_core.c -o state_core.o
musl-gcc -O2 -Wall -Wextra -std=c11 -static -c state_policy.c -o state_policy.o
ar rcs libstate.a carto_sha256.o state_core.o state_policy.o
musl-gcc -O2 -Wall -Wextra -std=c11 -static test_part1.c test_part2.c libstate.a -o test_state -lm
python3 gen_vectors.py
68 vectors written; canonical probe: b32ef0b76dc05f0d1d0916cc361c427cf4dee9ec48529d17e9399f9f8f700910
./test_state
== cartographer state library unit tests ==
[PASS] test_sha_selftest
[PASS] test_hmac_selftest
[PASS] test_key_selftest
[PASS] test_key_canonical
[PASS] test_fresh_create
[PASS] test_roundtrip
[PASS] test_tamper_silent_reset
[PASS] test_truncated
[PASS] test_extended
[PASS] test_bad_magic
[PASS] test_garbage
[PASS] test_hmac_ring_flip
[PASS] test_save_deterministic
[PASS] test_no_tmp_residue
[PASS] test_ring_wrap
[PASS] test_stddev_reference
[PASS] test_stddev_insufficient
[PASS] test_escalate_fast
[PASS] test_escalate_uniform
[PASS] test_escalate_human
[PASS] test_escalate_debugger
[PASS] test_decoy_lookup
[PASS] test_decoy_persist
[PASS] test_attempts_persist
[PASS] test_debugger_persist
[PASS] test_hmac_differential
== 26 tests run, 0 failed ==
ALL TESTS PASSED
test_state: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), statically linked, with debug_info, not stripped
canonical key hex NOT in binary: OK
cartographer-mask-v2
```

Additional verifications performed this session:
- `strings test_state | grep -q f03ea6b5` → no match (canonical key absent from binary).
- RFC 4231 digests for TC1/TC2/TC4/TC6 read from the actual RFC text (not memory).
- Differential HMAC: 68/68 vectors match python hashlib (includes >64-byte keys).
- Tampered-load silence: stdout+stderr captured via dup2 during a tampered load —
  zero bytes written to either.

## 6. Environment inventory (WSL2: Ubuntu-24.04, kernel 6.6.87.2-microsoft-standard-WSL2, user manish)

Present and verified: gcc 13.3.0; musl-gcc (musl-tools; static link verified);
make; git 2.43.0; python3 3.12.3 (hashlib/hmac for differential tests); strip; file;
xxd; objdump; readelf; nm; openssl; bc; exiftool; convert (ImageMagick); curl;
zlib dev headers (verified via `#include <zlib.h>` compiler probe).
Installed this session via apt (sudo, password per spec): zip 3.0, unzip 6.0,
pkg-config (+pkgconf). Git identity/config set repo-local (see section 3).

Environment quirks future sessions MUST know:
- Windows tooling CANNOT access \\wsl.localhost UNC paths (blocked) — author files in
  d:\gandu\_stage\ and copy via /mnt/d (pipeline C1), or write directly inside WSL.
- The editor writes CRLF on the Windows side — every copy into WSL MUST include the
  CRLF→LF normalization step (Makefile breaks on CRLF; python step in C1 does it).
- pwsh→bash quoting: shell variables inside double quotes were observed to be eaten
  once ($t in echo). Keep commands variable-free, or put logic in a script file.
- wsl.exe -l -v output is UTF-16-garbled but readable; `wsl.exe bash -lc '...'` is the
  reliable execution pattern (default distro IS Ubuntu-24.04).

## 7. Bugs found and fixed DURING Phase 0 (context for later sessions)

1. kMaskedKey bytes 16-31: dropped leading-zero nibble in hex transcription
   ("0dba..." → "dbaa...") — caught by test_key_selftest (two masked copies must
   agree), fixed, and test_key_canonical added so a single-blob mistake can never
   ship even if both copies were corrupted identically.
2. Test fd-capture flushed pre-buffered stdout into the capture file — fix: drain
   stdio buffers BEFORE dup2 redirect; restore fds BEFORE final flush.
3. uint64 underflow: NOW - 10000000 with NOW=1e6 wrapped around, spuriously setting
   CARTO_ESC_TIME_FAST — fix: test base NOW = 1e10 ms.

## 8. Explicitly NOT done / deferred (per spec phases)

- Phase 1: stage0_start binary (flavor text, state init, immediate real reward flag),
  canonical flag format decision, musl+strip+scrub pipeline for stage binaries.
- Phase 2: Stage 1 VM (60-90 opcodes, randomized mapping, bytecode, traps, anti-debug).
- Phase 3: Stage 2 stego (decoy LSB, stride-based real layer, custom zlib dictionary,
  WAV metadata, manual-step trap).
- Phase 4: Stage 3 Feistel oracle + bias + poisoned-ciphertext automation response.
- Phase 5: Stage 4 assembly riddle + constant-time validator.
- Phase 6: self-testing runs + calibration (policy.h thresholds remain placeholders
  until then) + SOLVE_PATH_PRIVATE.md.
- Phase 7: packaging, HINTS.md, TRYHACKME_ROOM_TEXT.md, README_FOR_SOLVER.txt.
- Assumed-but-unverified: NOTHING in Phase 0 scope — everything above was run.

## 9. Open questions / judgment calls for the next session

1. FLAG FORMAT: finalize in Phase 1 (placeholder shape "CARTO{...}").
2. KEY POLICY: current design = ONE canonical key shared by all stage binaries (same
   masked blobs linked into each). Recommended: keep; revisit only if a phase needs
   per-binary variation. Log the final decision in PHASE_1_LOG.md.
3. Runtime rule (repeat): stage binaries treat CARTO_LOAD_CREATED and
   CARTO_LOAD_TAMPERED identically (silent fresh start).
4. Staging dir d:\gandu\_stage is scratch; safe to clean EXCEPT the *.part2 chunks
   are the only source of several files if C1 is ever needed — prefer editing repo
   files directly from now on.
5. Escalation threshold semantics live in policy.h placeholders; any tuning before
   Phase 6 is forbidden by this log.

Git commits for Phase 0: a5e61b9 (state library + tests + spec copy),
.gitignore/artifact-untrack commit (see git log), plus the logs commit added at the
end of this session. Run `git -C /home/manish/cartographer-build log --oneline` for
the authoritative list.
