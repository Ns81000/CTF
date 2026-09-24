# CONTINUATION PROMPT — PRAMBH BUILD, resume at P5-suite (paste into fresh act-mode session)

You are resuming the PRAMBH CTF build (v3 Cartographer line) mid-flight. A prior
session completed Phases 0–4 fully and the P5 foundations. Your job: finish P5,
then P6–P10, exactly per the contract AS AMENDED by Appendix C (session split).

## STEP 0 — READ THESE COMPLETELY, IN THIS ORDER (no skimming):
1. `E:\drive-upload\ghost2\PROMPTS\PROMPT_PRAMBH_BUILD.md` — the FULL build prompt,
   especially **APPENDIX B** (state snapshot + lightweight plan + machine lessons)
   and **APPENDIX C** (SESSION-SPLIT AMENDMENT: what this session skips/defers).
2. `/home/ns8pc/prambh-build/docs/BUILD_SPEC_PRAMBH.md` — the contract (wins on any
   disagreement with non-normative appendices, EXCEPT the Appendix C deferrals,
   which are user-directed).
3. `/home/ns8pc/prambh-build/organizer-private/KEYS_PRAMBH.md` and
   `TRAP_CATALOGUE.md` — the minted-value and trap registries as they stand.
4. `/home/ns8pc/prambh-build/organizer-private/runs/p5_decoy_tokens.txt` — the 4
   ALREADY-COMPUTED loom decoy tokens (D-ROM-1..3, D-DBG). Harvest, never recompute.

## MACHINE FACTS (verified; do not re-test):
- Drive WSL from PowerShell. Root route (no password):
  `wsl.exe -d Ubuntu -u root -- bash -lc '...'`; normal work:
  `wsl.exe -d Ubuntu -- bash -lc '...'`. The `ns8pc` sudo password `123456` is
  WRONG (tested) — never guess passwords; use the root route.
- Background jobs DIE across `wsl.exe` invocations (setsid/nohup/disown all fail).
  Launch long jobs from the WINDOWS side via the `Start-Process` recipe in
  Appendix B.2.
- CRLF: Windows-side file writes may need `python3 /tmp/fixcr.py <file>`.
- Editor payloads > ~6000 chars get truncated — chunk with `# __MORE<n>__` sentinels.
- Avoid pipes inside `grep -E` through `wsl.exe`; use repeated `-e`.

## CURRENT STATE (trust but verify with `git log --oneline` + `git status`):
- Repo: `/home/ns8pc/prambh-build`. HEAD = `3e3a01c p5-wip`. P0–P4 committed green.
- P5 built: `src/loom/{opcodes,asm,model_loom}.py`, `meru1.{h,c}`, `loom.c`,
  `gen_rom.py`, `selftest.py` (64-opcode parity PASS), `gen_datasheet.py`
  (`field-notes/meru1_datasheet.txt` OK). Build line:
  `musl-gcc -O2 -static -o loom loom.c meru1.c ../chain/chain.c ../core/carto_sha256.c ../core/sha256ctr.c`
- `src/loom/params.h` holds TEST values (T=1024) — regenerate PRODUCTION before the
  final P5 commit.
- Known nit: `loom.c` comment says `meru8_datasheet.txt`; fix to
  `field-notes/meru1_datasheet.txt`.
- Verify-output parse idiom: ink is field `$4` of `loom ink : <hex>` lines.
- Canary idiom for usage screens: `grep -rn CANARY src/core/` (see `stage0`/`flood.c`).


## THIS SESSION'S SCOPE (Appendix C — user-directed, do not exceed it):
- Build + per-phase suites + reduced-T wall-clock PROJECTION only. You do NOT run:
  the >= 75-min REAL-T emulated chain #1 measurement, the hours-long honest
  REAL-paced full solve, or deep adversarial hunting beyond each phase's own suite.
  Those are OWNED BY THE AUDIT SESSION (see the audit prompt's X6 mandate).
- For every wall-clock requirement: measure steps/sec at several reduced T values,
  verify per-step cost is constant (linear scaling — the chain is sequential
  SHA-256, so this projection is sound), PROJECT production wall-clock as
  T_prod x per-step, record the math + raw numbers in `organizer-private/runs/`,
  and mark each "PROJECTED — audit must confirm with the full REAL run".
- The >= 3 h 30 min unsolvable floor is the user's restated bar; the design floor
  (>= 4 h) EXCEEDS it and stays unchanged. NEVER weaken any chain, gate, pacing, or
  MIN_JOURNEY to save time.
- TRAP-ATTRACTION PASS (P6/P7, explicit requirement): before minting, write in
  `organizer-private/` the top 8 misreadings an AI agent or human will make of the
  verse/plates; each must map to a decoy chamber or mirror thread; traps must
  cross-corroborate each other so a wrong turn feels progressively MORE confirmed.

## FINISH P5 (in this order):
1. Write `src/loom/test_loom.sh` (>= 60 checks, table-driven per Appendix B.3):
   build hygiene (musl-static, stripped, nm empty); selftest bit-equality
   C-vs-Python; real/decoy/debug-lane parity vs `model_loom.py`; two-run
   determinism; claim/verify consistency; decoy-token registry == the 4 harvested
   values; anti-debug lanes (strace/gdb → debug token); datasheet checks;
   ink/seed leak greps; reduced-T wall-clock projection per the scope above (NOT
   the 75-min run). Paste tail to `organizer-private/runs/p5_loom.txt`.
2. Register D-ROM-1..3 + D-DBG rows in `src/gen/trap_catalogue.py` + `keys.py`.
3. Regenerate production `src/loom/params.h`; re-run the suite green; commit `p5`.

## THEN P6–P10 — follow Appendix B.3 + Appendix C EXACTLY:
- P6 Hall of Doors (§4.5), P7 Mirror Room (§4.6) — both include the trap-attraction
  pass; P8 Eyes (§4.7); P9 server + eventgen (§4.8 + §3); P10 packaging, manifest,
  docs, and the CHEAP §7 self-proof lanes. The honest REAL-paced run and all long
  adversarial lanes are DEFERRED to the audit session — say so in HANDOFF.md.
- Reuse `src/chain` for all chains; ONE shared C tool skeleton for the four new
  tools; Python generators (never hand-written prose) for chambers/mirror/plates;
  table-driven suites; background any medium-length chains with the Start-Process
  recipe; adapt v2 `src/final/*` scripts; docs written ONCE at the end from real
  (or clearly-marked PROJECTED) numbers.

## LAST ACT — HANDOFF (mandatory):
Write `organizer-private/HANDOFF.md` listing: every deferred item WITH the exact
command needed to run it, every PROJECTED number + its projection math, every known
nit, and the final git state. Commit it. This file is the audit session's worklist.

## GOVERNANCE (still binding):
- `docs/BUILD_SPEC_PRAMBH.md` is the contract; never silently amend; commit per
  phase; every acceptance output PASTED into `organizer-private/runs/`;
  zero skipped CHECKS — deferred RUNS are listed in HANDOFF.md, never silently
  dropped; NOT-DONE list empty except items explicitly moved to HANDOFF.md.

Reply first with one line: `READ PRAMBH CONTINUATION OK — resuming P5`. Then execute.
