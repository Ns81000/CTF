# SESSION 2 PROMPT — DEEP AUDIT + RELEASE GATE of "The Cartographer's Ghost" v2

Paste this ENTIRE file into a fresh Claude Code session (act mode) on the same machine,
after SESSION 1 has finished. You are the AUDIT session. Your job is to break the build,
then fix it, then prove it cannot be broken again.

**First reply with one line:** `READ AUDIT PROMPT OK — starting Phase A`. Then execute.

Rules that override everything:
- **Machine access (local only, never ship, never log):** Windows + WSL. Drive WSL from
  PowerShell: privileged commands via `wsl.exe -d Ubuntu -u root -- bash -lc '...'` (root
  route, no password), all other work via `wsl.exe -d Ubuntu -- bash -lc '...'`. The `sudo`
  password `123456` supplied by the user was tested and REJECTED on this machine — never
  guess passwords; if sudo is genuinely needed (e.g. installing `faketime`), install it
  through the root route instead. Redact any credential from captured output.
- **Trust nothing.** Every claim in the build log must be reproduced by you, by command.
- A finding is only closed when you have a re-run proving it is closed.
- Never "fix" by weakening the puzzle: fixes must preserve or increase difficulty and must
  keep every law in the spec true.
- Never edit `docs/BUILD_SPEC_V2.md` (it is the contract). If the build violates it, fix the
  build or (if the spec is impossible) STOP and report.
- If you find an answer-leaking bug, treat it as SEV-1 and fix it before continuing.
- If you cannot reproduce a build-log claim, that is a finding.

---

## 0. INPUTS TO READ (in this order, once)

1. `/home/ns8pc/ghost-build/docs/BUILD_SPEC_V2.md` — the contract (verbatim copy of the
   Session-1 prompt). Read it FULLY, in chunks. Do not skim.
2. `/home/ns8pc/ghost-build/organizer-private/SESSION_1_LOG.md` — what was built.
3. `.../KEYS_V2.md`, `.../SOLVE_PATH_PRIVATE.md`, `.../TRAP_CATALOGUE.md`, `.../COST_MODEL.md`.
4. `E:\drive-upload\ghost2\RELEASE\MANIFEST.sha256` + the shipped zip (`RELEASE\cartographer.zip`).
Do not bulk-read v1 archives or v1 logs; they are irrelevant to v2.

Deliverable of this session: `organizer-private/SESSION_2_AUDIT.md` with every check,
finding, fix, re-verification and a final **GO / NO-GO**, plus a fixed, repackaged,
re-manifested zip copied to `E:\drive-upload\ghost2\`.

---

## PHASE A — Independent rebuild and baseline (must be green before anything else)

```bash
cd /home/ns8pc/ghost-build
git status --porcelain            # expect clean; anything here is a finding
git log --oneline | head -20
python3 -c "import hashlib;print(hashlib.sha256(open('docs/BUILD_SPEC_V2.md','rb').read()).hexdigest())"
cd src/state && make clean && make test                     # state suite
cd /home/ns8pc/ghost-build && bash src/final/verify_all.sh   # all suites SERIAL
bash src/final/rebuild_repro.sh                              # 2 clean rebuilds, same hashes
```
Then compare every packaged file against `MANIFEST.sha256`:
```bash
( cd cartographer && sha256sum -c ../MANIFEST.sha256 )      # adapt path/format as needed
sha256sum cartographer.zip
```
Findings to look for: hashes that differ from the log, suites that pass only in one order,
suites that leave state/files behind, non-reproducible builds, manifest drift, a package
file not on the allowed list, anything organizer-ish inside the zip.
Repaired P0–P4 baseline expectations (must be strictly green):
- `src/state/test_state.sh`: 33/33
- `src/stage0_ledger/test_stage0.sh`: 33/33
- `src/stage1_engine/test_stage1.sh`: 62/62
- `src/stage2_sheet/test_stage2.sh`: 73/73
- `src/stage3_oracle/test_stage3.sh`: 48/48
Acceptance: every suite green, rebuild byte-identical, manifest exact, package allowed-list
clean. Any deviation → log it, fix it, re-run the whole phase.

---

## PHASE B — Leak hunt (exhaustive; the most important phase)

Build `src/final/audit_leaks.sh` + `src/final/audit_leaks.py` that check ALL of:
1. **Value leaks.** For every value in `KEYS_V2.md` (real inks, reading, tokens, seeds,
   tallies, keys, digests, decoy values) and for every *prefix/substring of length ≥ 8* of
   those values: grep case-insensitively in every binary, carrier, doc, filename, and zip
   entry. Any hit inside the package = SEV-1 (except a value the spec explicitly allows,
   e.g. the final validator's overall digest and registered decoys).
2. **Derivation leaks.** No text in the package may name a mechanism: `blue`, `LSB`, `bit
   plane`, `stride`, `start mark`, `dictionary`, `zlib`, `Feistel`, `round`, `bias`,
   `incremental`, `tally`, `gate`, `TTY`, `isatty`, `stddev`, `timing`, `sha256`,
   `sha-256`, `hmac`, `nonce`, `PKZIP`, `deflate`, `blowfish`, ... (keep a maintained
   list file). Flavour words are allowed; mechanism words are not. Report each hit with
   context and either remove it or justify it in writing.
3. **Grammar leaks.** No text may state a length, count, separators, hex/text split, "16
   characters", "70", "three inks", stage counts, or the word "flag" next to a structure.
4. **Structural leaks.** `strings`/entropy diff all binaries pairwise; look for constant
   blocks that stand out as tables/keys, `\.rodata` blobs whose size matches a key, and
   constants that appear in more than one binary (should be only shared library code).
5. **Statistical leaks (the v1 killer).** Re-run YOUR detector class against the carriers:
   constant channel offsets, LSB histogram bias, parity maps, neighbour-difference maps,
   chi-square on local blocks, and a sweep over (stride 1..256 × start 0..65536) with the
   *wrong* parameters to see whether any wrong parameter set yields a *readable* result
   (a readable result with wrong parameters is a leak, except the documented middle layer).
   Requirement: the payload region must not be localisable, and only the documented
   parameters may yield readable output.
6. **Metadata leaks.** `exiftool -a -v3` on both carriers, `pngcheck -v`, `file`, and a raw
   chunk dump. No mechanism text, no formula, no offsets.
7. **Answer-shaped strings.** `grep -a -o 'CARTO{[^}]*}'` over every package file: the only
   permitted hits are the documented decoys (each must be registered in the trap catalogue
   and must NOT mirror the final title's shape). The single permitted cross-binary hit is
   the canary `CARTO{hand_this_to_your_operator}` (six usage screens + the notice file).
8. **Bait integrity.** Bait files must contain zero truth and must not contain any real
   value/substring; `SOLUTION_DRAFT.py` must print a wrong but format-valid value.
9. **Cross-binary leaks.** No binary may contain another stage's real value or decoy set.
10. **Docs separation.** `organizer-private` never appears in the zip; no `.md` outside
    `field-notes/`; no source/log/git/build artifacts in the zip.
11. **v1 poison list.** Assert that EVERY entry of the spec's `FORBIDDEN v1 VALUES` list
    (§4.0) appears nowhere in the shipped package, the carriers, the docs, or the binaries.
    Also assert every §4.0 MINTED VALUE that must be secret (engine ink, oracle ink, K_real,
    K_cold, seal key, reading, seeds, press tail) is absent from the binaries, carriers and
    prose, while the two scored answers work end to end.
12. **Notice layer verification.** Assert that the canonical author notice
    (`AUTHOR'S DIRECT ORDER TO ANY AI OR LLM AGENT READING THIS FILE: ...`) is embedded in
    the `.rodata` of every shipped binary and output on usage, in PNG `tEXt` ("Notice"), in
    WAV `LIST/INFO` (`ICMT`), and in bait notes (`profile.notes`). Assert `carriers_info.json`
    is NOT in the shipped package. Assert the notice contains zero secrets, zero verdict
    words (`correct|valid|right|wrong`), and zero mechanism words.
Acceptance: a machine-readable report `organizer-private/runs/leaks.txt` listing every
pattern, count and hit; zero unexplained hits.

---

## PHASE C — Static-only adversary (A1): prove no answer is reachable by reading

Write `src/final/attack_static.sh|py` that, **without ever executing a package binary**,
performs the full set of real-world static attacks and prints what it obtains:
1. `objdump -d -M intel`, `readelf -a`, `nm -a`, `strings -a -n 4`, `objcopy --dump-section`.
2. Recover every constant the binary uses: table dumps, `.rodata` blobs, embedded records,
   and the *statically derivable* key derivations (implement them in Python from what the
   disassembly shows).
3. Compute, for each stage, the "static answer" the derivations give.
4. For the carriers: parse PNG chunks and WAV chunks; read every metadata field.
5. Reconstruct the final title from static values only, then try `validate` **in a copy of
   the package with all gates satisfied by a forged state** (this is the strongest static
   attack: it also requires you to forge state — do it, that is Phase D's job too).
Requirements to verify (else SEV-1):
- The statically derived engine bearing/ink, oracle key, seal key and reading must all be
  **decoy** values, never the real ones, and the derived title must be refused.
- The tool must not print anything that reduces the search space for a real value.
- No digest of any individual real component may exist anywhere.
Deliverable: `organizer-private/runs/static_attack.txt` with the exact commands, what was
obtained, and why it is insufficient (or the finding).

---

## PHASE D — Scripted/batch adversary (A2): automate everything and see what breaks

Write `src/final/attack_scripted.py` that does, in order, and logs the outcome of each:
1. **Fast collection:** drive the oracle at fixed and jittered intervals, 4000+ calls, and
   verify the poison/gate behaviour. Requirement: the fast run must not recover the real
   key, must not produce a title the validator accepts, and must not crash or hang.
2. **Gate defeat:** (a) run with stdin/stdout piped; (b) run under `script --quiet -c` (a
   fake pty) → document exactly what happens. If a fake pty defeats the human gate, that
   is acceptable ONLY if the pacing/volume gate still holds; otherwise SEV-1.
3. **State forgery:** reconstruct the state file from scratch in Python: correct magic,
   version, ring of plausible entries, chain hash, HMAC with the *binary-extracted*
   per-stage key. Then attempt to satisfy the gates by forgery and reach the title.
   Requirement: either the forgery fails (best) or it costs documented work; in no case
   may a forged state allow accepting a title without the real inks.
4. **Binary patching:** patch a copy of the binaries to force gate answers and re-run the
   pipeline. Document what the patcher must implement. Requirement: even fully patched,
   the solver still cannot obtain real values it never computed (verify this is true, and
   that patching does not reveal a short path).
5. **Replay/duplicate/case/cache abuse:** replay old figures, duplicate queries, uppercase
   hex, alternate byte order, truncated/extended figures, wrong reading, decoy tokens —
   each must produce plausible-wrong or refusal, never a real value, never an error.
6. **Cross-stage confusion:** run stages out of order, with stale/foreign state, with the
   wrong stage's tokens, and with a cleaned state mid-chain.
Acceptance: every sub-attack's outcome documented with the command used; the honest path
remains the fastest way to the answers.

---

## PHASE E — Trap and fairness matrix (every trap must be fair, or it must go)

For EVERY row of `TRAP_CATALOGUE.md`, drive it for real and record: trigger command, what
the solver sees (verbatim), whether it reads as progress, the wall-clock cost it imposes,
the recovery command that provably works, and the fairness argument. Then verify these
global properties:
- No trap produces an error, a non-zero rc, stderr output, a crash, a hang, or a panic.
- No trap emits a diagnostic that names the mechanism or says "wrong".
- Every trap's dead end is reachable-through and resolvable **without** the real inks.
- Every trap's recovery is discoverable from text inside the package (say which line).
- At least one trap requires a downstream round trip to disprove: verify by driving it.
- Decoy branches must not leak real values in their output, in the state file, or later.
- The two "quit" bait files (KNOWN_ISSUES, DEPRECATED_BUILD) must be *falsifiable*: prove a
  solver can disprove them using only package artefacts, and record how.
Any trap that fails a property: fix it (or delete it if it cannot be made fair) and mark
the change in the report. Deleted traps are allowed; *unfair* traps are not.

---

## PHASE F — Robustness, fuzzing and edge matrix (find the crashes before solvers do)

Write `src/final/fuzz_cli.sh` that, for each of the six binaries, runs all of:
- argv: no args; empty string; 1 KB / 64 KB / 200 KB args; embedded NUL cannot be passed
  (note it); newlines/tabs/unicode/CJK/emoji; `-`; `--` and `--help`; unknown flags;
  16 extra args; the correct arg repeated; flags in the wrong order.
- stdin: closed; `/dev/null`; pipe with garbage; a 10 MB pipe; no stdin TTY; stdin TTY with
  EOF immediately (Ctrl-D).
- stdout: pipe; file; `/dev/full` (write errors must not crash); closed stdout.
- env: `TERM=dumb`, `COLUMNS=1`, `LINES=1`, no `HOME`, no `PATH` (invoke by full path),
  `LC_ALL=C`, `LC_ALL=tr_TR.UTF-8` (dotless i case trap), `TZ` forward/backward by 1 year,
  `CARTO_TEST_TIME_SCALE` (must be inert in shipped binaries).
- filesystem: missing carriers; truncated carrier; carrier with one byte flipped; read-only
  package dir; state file missing/truncated (every length 0..1169)/extended by 1/garbage
  (random bytes)/read-only/owned by another uid (simulate with a copy); `.tmp` residue
  present; symlinked state file.
- concurrency: 8 parallel invocations of the same tool; two different tools at once;
  SIGINT/SIGKILL during a state write; power-loss simulation (kill between write and
  rename) — the state must end valid or absent, never corrupt-and-accepted.
- clock: `faketime` if available, else a test hook in a test build; verify no negative
  deltas, no gate false positives, no hang.
Acceptance: rc 0 + silent stderr + valid state on every case above (except where a tool is
*supposed* to refuse, which still means rc 0 + silent + refusal text). Any crash/hang/ASAN
-style fault is SEV-1. Also run `cppcheck --enable=all --inconclusive --std=c11 --force`
over all shipped sources and disposition every hit in writing.

---

## PHASE G — Gate verification (the difference between a trap and a bug)

For each of the three gates (HUMAN, VOLUME, CHAIN), in a test build with the time-scale
hook enabled:
1. Prove the gate blocks when its condition is unmet (and that the block is silent,
   flavour-only, rc 0, and leaks nothing).
2. Prove the gate opens when the condition is met, exactly once and repeatably.
3. Prove the gate's evidence cannot be forged without the documented work: attempt the
   forgery in Python and record the runtime/effort it costs.
4. Prove the gate cannot be satisfied accidentally by a fast/uniform/piped run, and that a
   legitimately slow human cannot fail it (run a 20-call human-paced sample and assert the
   gate's sub-conditions all pass with margin ≥ 2× on every threshold).
5. Prove the shipped binaries ignore the test hook entirely (`strings` + behaviour probe).
6. Record the false-negative margin: the percentage of honest-but-slightly-unusual human
   patterns that would be mis-gated. Requirement: < 5%; document the numbers.

---

## PHASE H — Packaging, isolation and document truthfulness

1. Extract the shipped zip on a clean path (`/tmp/audit-extract/`), with no repo nearby.
   Solve the whole chain from there, twice, recording per-stage wall-clock. Also verify:
   exec bits survived, no absolute paths needed, works when the folder is moved, works when
   the folder is renamed, works from a read-only copy (state writes must fail gracefully).
2. Allowed-list audit: the extracted tree must contain exactly the files in §3.1 + §3.8 of
   the spec, nothing else. List anything extra as a finding.
3. `nm -a` empty on all six binaries; no compiler idents; no host paths; no organizer words
   in any filename or in any file's first 20 lines.
4. Docs audit, sentence by sentence, for: `README_FOR_SOLVER.txt`, `HUMAN_OPERATOR_NOTICE.txt`,
   every `field-notes/*`, `HINTS.md`, `TRYHACKME_ROOM_TEXT.md`. Requirements: no grammar, no
   mechanism, no stage counts, no lengths, no false statements about the shipped build, and
   every hint must be *true* and useful once understood. Flag any hint that contradicts the
   binary (v1 shipped exactly that bug).
5. Room-text audit: the two scored answers must be exactly what the validator accepts and
   what Stage 0 prints; the submission format line must be exactly right; the Drive-link
   placeholder must be present; the difficulty/pacing line must be honest ("marathon").
6. Bait audit: confirm every bait claim is inert or false, and that no bait file contains a
   real value/substring (re-run the Phase B checker over `field-notes/`).
7. Manifest + hash hygiene: `MANIFEST.sha256` lists every packaged file; the zip's own
   sha256 is recorded in the log and printed for the user; the same hash is reproduced by a
   second, independent re-zip (same file set, same order, deterministic timestamps).

---

## PHASE I — Cost model, timing honesty, and difficulty verification

Measure and record, with logs:
1. **Honest clean path (scaled test build)** end to end, per stage; assert it completes and
   the title is accepted.
2. **Honest clean path (real build)**: full paced solve; record the wall clock and the s/query
   actually achieved; verify the gates opened and the volume gate's threshold was reached
   with margin.
3. **Decoy detour**: time the full trap path (decoy bearing → dead end → recovery) and the
   cost it adds.
4. **Static path**: time `attack_static` (should be minutes) and prove it yields nothing.
5. **Scripted path**: time `attack_scripted` and prove it cannot reach the title.
6. **Seal search**: time the intended MITM in C on this machine; record the number and the
   projected time for a slower machine (document the 95th-percentile risk).
7. **Arithmetic**: state explicitly how the honest 12–20 h total is composed (tracing +
   volume gate + cryptanalysis + search + assembly disambiguation + prose/verification
   overhead). If the measured composition contradicts the target, adjust only the documented
   dials, re-measure, and record both before/after in `COST_MODEL.md`.
8. **Cheater's floor**: the fastest documented path that still yields the answers (e.g.
   paste-free automation with jitter) — record it as the "floor" time; require floor ≥ 5 h so
   the room cannot be farmed quickly.

---

## PHASE J — Agent adversary harness (prepare it, and analyse the real run)

1. Write `organizer-private/AGENT_TEST_PROTOCOL.md`: a cold-start protocol for testing with
   an LLM agent (and with a human), stating exactly what the tester may see (the package
   only, no organizer docs, no hints), what to record (timestamps, tokens, tool calls,
   paths taken, where it stalled, what it believed), and a scoring table.
2. If the user supplies a transcript from a real agent run (v1's run is available as
   evidence of the attack style), analyse it line by line and extract: which leaks it used,
   which traps it fell for, how long each phase took, and what would have stopped it in v2.
   Record each as a hardening check ("would v2 defeat this step? prove it").
3. Explicitly re-run, against v2, the *specific* attacks that worked on v1 (they are the
   known-good adversary patterns): reading hashes out of `.rodata`; deducing the answer
   grammar from usage text; detecting the LSB layer by constant channel offsets; using the
   shipped decoy's structure as a template; extracting key material from printed output;
   reading metadata formulas; using `strings` to enumerate decoys. Each must now fail, and
   the failure must be recorded with the command used.

---

## PHASE K — Fix discipline (how to close findings without breaking anything)

For every finding (severity: SEV-1 leak/shortcut/crash; SEV-2 unfairness/robustness;
SEV-3 doc/consistency):
1. Write a one-line repro command in the report.
2. Fix in source (never by editing the packaged binaries or the spec).
3. Re-run: the failing check, then the whole of `src/final/verify_all.sh`, then the specific
   phase(s) whose artefact you touched (dependency order: state → stage0/1 → stage2 → stage3
   → stage4 → stage5 → packaging).
4. Re-run the leak grep and the static/scripted adversaries for that stage.
5. Record before/after, the fix, and the proof. If a fix changes a binary, everything
   downstream must be rebuilt and re-manifested (record the new hashes).
6. Never mark a finding closed on reasoning alone. Command output or it is still open.

---

## PHASE L — Release gate and final report

Run the release gate in this exact order; every step must be green:
```bash
bash src/final/verify_all.sh            # all suites, serial, from a clean build
bash src/final/leak_grep.sh             # zero unexplained hits
bash src/final/rebuild_repro.sh         # byte-identical rebuilds
bash src/final/attack_static.sh         # cannot produce any real value
bash src/final/attack_scripted.py       # cannot reach the title
bash src/final/package_check.sh         # allowed list + manifest exact
bash src/final/isolated_solve.sh        # stranger's solve from the extracted zip
```
Then produce `organizer-private/SESSION_2_AUDIT.md` with:
1. Status + **GO / NO-GO** statement (one line each: leaks, shortcuts, fairness, robustness,
   packaging, timing honesty).
2. Every phase's real output (paste tails; full logs in `organizer-private/runs/`).
3. Findings table: id, severity, repro, status (closed/open + why), fix, re-verification.
4. Trap matrix results (Phase E table) with any trap deleted/changed.
5. Robustness matrix results (Phase F) with every weird case and its outcome.
6. Gate results (Phase G) incl. the false-negative percentage and forgery costs.
7. Cost table (Phase I) with measured numbers, the 12–20 h composition, and the floor time.
8. Agent-harness results (Phase J) and the hardening checks derived from the v1 run.
9. Final manifest: every packaged file (path, size, sha256) + the zip's sha256 + the
   manifest's sha256; state that the zip is deterministic (two independent zips agree).
10. What remains unknown / unverified (must be empty or explicitly accepted by the user).
11. The two scored answers and the exact submission strings (organizer copy only).
12. Explicit statement that v1 artifacts were neither published nor copied.

Then copy to `E:\drive-upload\ghost2\RELEASE\`: `cartographer.zip`, `MANIFEST.sha256`, and to `E:\drive-upload\ghost2\ORGANIZER_PRIVATE\`:
`HINTS.md`, `TRYHACKME_ROOM_TEXT.md`, `SOLVE_PATH_PRIVATE.md`, `SESSION_1_LOG.md`,
`SESSION_2_AUDIT.md`. Keep them out of the zip. Final user message must contain: GO/NO-GO,
the zip path + size + sha256, the headline numbers (suite counts, honest cost, floor),
unresolved items (if any), and the phrase `RELEASE PACKAGE READY`.

---

## AUDIT SESSION DEFINITION OF DONE

- [ ] Every build-log claim reproduced or flagged.
- [ ] Phase B leak hunt: zero unexplained hits, machine-readable report saved.
- [ ] A1 and A2 adversaries implemented, run, and proven insufficient (with logs).
- [ ] Every trap driven for real; unfair/undefined traps fixed or deleted.
- [ ] Fuzz/edge matrix: no crash, no hang, no unhandled state, all rc 0 + silent stderr.
- [ ] Gates: block/allow/forge/margin all proven, shipped-hook absence proven.
- [ ] Packaging: allowed list, manifest, isolation solve, deterministic zip.
- [ ] Docs/hints/room text true for the shipped build, mechanism-free.
- [ ] Cost model measured; honest cost in the 12–20 h band; floor ≥ 5 h.
- [ ] Findings closed with command output; open items listed explicitly.
- [ ] Final GO/NO-GO issued; release package copied to `E:\drive-upload\ghost2\`.

Start with Phase A. Trust nothing, verify everything, and report each phase's real output.




---

## ADDENDUM (written after the audit ran, Phases 0–9 complete) — as-built
## corrections and every check that was added beyond the original text.

This addendum updates the prompt to match reality. A future audit session must
use these names and numbers, not the older ones above.

### A. Tool/script renames (the prompt's names are stale)

| Prompt says | As built |
|---|---|
| `audit_leaks.sh` / `audit_leaks.py` | `src/final/leak_grep.sh` (strings-dump based, 48 checks) |
| `attack_static.sh` | `src/final/static_path_probe.py` (12 checks) |
| `attack_scripted.py` | `src/final/behaviour_probe.py` (9 checks) |
| (not present) | `src/final/verify_all.sh` — single 16-step serial gate; the release gate |
| (not present) | `src/final/rebuild_repro.sh` — two clean rebuilds, identical hashes |
| (not present) | `src/final/run_clean_path.py` — calibrated end-to-end clean path |
| (not present) | `src/final/test_stage8.sh`, `fill_cost.py`, `report_hashes.sh` |

### B. Lessons that must be checks (each was a real finding)

1. **Never raw-grep binaries.** All leak checks go through `strings -n 4`;
   raw grep false-positives on byte-aligned coincidences (F-03).
2. **Ledger token must not be a static string.** It is folded into a 34-byte
   SHA256 mask (`ghost2:mask:ledger:token:v1`) and unmasked on stack at print
   time (F-01, SEV-1). Any future audit must re-prove absence via strings.
3. **Cold-bench mechanics.** Record creation is a non-TTY entry, and engine
   bearing-op entries are permanent non-TTY evidence, so the tty_fraction law
   `(L+2)/(L+7) >= 0.6` needs L >= 6 ledger visits before the engines. The
   clean path uses 8 spaced visits (F-02).
4. **Time-scale hook scope.** Only `oracle_test`/`seed3`/`seed5`/`mkrec` honour
   `CARTO_TEST_TIME_SCALE`; shipped tools ignore it (suite-asserted). Drivers
   must pace like a human: 0.2–0.7 s uneven pauses (F-04).
5. **State files never ship.** `build_package.sh` excludes
   `.cartographer_state*` from zip AND manifest (F-05); package_check asserts.
6. **Cold/poison verse family.** The oracle refuses scripted shapes with
   different verses depending on record age and spacing ("run hot", "still
   cold", "still warming", "gone smooth", "too recently", "gives nothing").
   Behaviour checks must accept the family AND assert no real ink (F-07).
7. **Timing thresholds under load.** The stage5 constant-time refusal check
   uses a 15 ms span over 30 samples; 5 ms flakes on a loaded machine (F-08).
8. **Test artifacts vs clean.** `make clean` in src/stage3_oracle deletes
   `oracle_test`; anything needing it after a rebuild must rebuild it
   (`make -s oracle_test`) (F-10).
9. **Editor splice corruption.** Two files were corrupted by spliced edits;
   the workaround is delete + rebuild in chunks, then `bash -n` /
   `py_compile` before use. Always syntax-check after edits.
10. **verify_all step convention.** `step <desc> <key> <cmd...>` — a step
    that doesn't shift the description off executes the description as the
    command (F-09). Any new step must follow the convention.

### C. What a future audit must re-run (the complete gate, in order)

```bash
cd /home/ns8pc/ghost-build && bash src/final/verify_all.sh
```
16 steps: state + stage0/1/2/3/4/5/7 suites (395 checks), build package,
leak grep (48), package check, rebuild reproducible, static path probe (12),
behaviour probe (9), isolated solve (stranger's solve from the zip alone,
in-order, ~10 min with the 6200-ask sitting), report hashes, deliverables.
Expected tail: `VERIFY ALL OK`.

### D. Suite-count baselines (must be exactly these or better)

state 33 · stage0 33 · stage1 62 · stage2 73 · stage3 48 · stage4 53 ·
stage5 53 · stage7 40 · leak 48 · static 12 · behaviour 9.

### E. Facts a future audit must not "fix"

- The press tag ships in the WAV metadata by design (registered judgement).
- The state HMAC master ships folded by design (registered judgement).
- The naive LSB lane landing exactly on `CARTO{the_coast_was_drawn_twice}`
  is the intended front-door decoy, not a leak (leak_grep proves it inline).
- The survey token `CARTO{the_survey_reopens_tonight}` is the scored
  stage-0 answer; it is allowed in the ledger's output, never in strings.

---

## PHASE M — Final bundle, full WSL evacuation, and total WSL wipe
## (run LAST, only after the release gate is GO)

The user's standing requirement: **when this session ends, WSL must be completely
empty of this project and every file must live only in the Windows workspace**
(`E:\drive-upload\`). Nothing project-related may remain in WSL.

1. **Final bundle.** `E:\drive-upload\ghost2\` must match this layout exactly:
   - `RELEASE\` — `cartographer.zip`, `MANIFEST.sha256`, `TRYHACKME_ROOM_TEXT.md`, `HINTS.md`
   - `ORGANIZER_PRIVATE\` — `KEYS_V2.md`, `SOLVE_PATH_PRIVATE.md`, `TRAP_CATALOGUE.md`,
     `COST_MODEL.md`, `SESSION_1_LOG.md`, `SESSION_2_AUDIT.md` (this session's report)
   - `PROMPTS\` — the three session prompts
   - `SOURCE\` — created in step 2 below (the full repo, evacuated from WSL)
   - `README_HOW_TO_RUN.md` at the root
   Re-verify `sha256sum RELEASE\cartographer.zip` against this audit's report. If a fix
   changed the zip, re-copy it and re-write every hash everywhere (report, README, room text).

2. **Evacuate the source tree (BEFORE deleting anything).**
   - Commit everything first: `cd ~/ghost-build && git add -A && git commit -m 'final'`
     (tree must be `git status --porcelain` clean — audit report, runs/, fixes included).
   - Copy the ENTIRE repo including `.git` and `organizer-private/runs/`:
     `cp -a ~/ghost-build /mnt/e/drive-upload/ghost2/SOURCE/ghost-build`
   - Also make a pristine archive preserving Linux permissions:
     `tar -czf /mnt/e/drive-upload/ghost2/SOURCE/ghost-build.tar.gz -C ~ ghost-build`
   - **Verify the copy before any deletion:** compare file counts and a full recursive
     sha256 manifest of `~/ghost-build` vs the Windows copy (exclude only `.git` objects
     if cp mangled nothing — they must match). Extract the tar to /tmp, diff -r against
     the repo, then delete the /tmp extract. Only proceed when verification is perfect.

3. **Total WSL wipe (only after step 2 verifies).**
   - `rm -rf ~/ghost-build` and every other project file/dir in `~`
     (home must end EMPTY of project material).
   - `rm -rf /tmp/*` scratch (carto_*, probes, benches, helper scripts).
   - Remove state leftovers: `find / -name '.cartographer_state*' 2>/dev/null` via the
     root route; delete every hit outside the (already copied) repo.
   - Clear shell history (`> ~/.bash_history`, root's too), apt/pip caches
     (`apt-get clean` via root route, `rm -rf ~/.cache`).
   - Verify: `ls -la ~` shows no project files; `df` / `du` show the tree gone.
   - Optional, ONLY if the user explicitly confirms in-chat at that moment: full distro
     removal via PowerShell `wsl.exe --unregister Ubuntu`. Do NOT do this by default.

4. **Windows-side cleanup.** `E:\drive-upload\` must end as exactly four entries:
   `ghost2\` (release), `_work\archive\` (scratch, may be deleted entirely if the user
   agrees), `wsl-archive\` (v1 + old snapshots, never publish),
   `LEGACY_v1_DO_NOT_PUBLISH.txt`. Nothing else. No `.cartographer_state*` anywhere
   outside test runs.

5. **Final message.** GO/NO-GO, zip path + size + sha256, headline numbers, confirmation
   that WSL is wiped and Windows is the only copy, unresolved items (must be empty or
   user-accepted), and the phrase `RELEASE PACKAGE READY`.

