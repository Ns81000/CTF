<div align="center">

# PRAMBH & The Cartographer's Ghost

**Three generations of one offline CTF — engineered so an AI agent cannot finish it for you.**<br>
**Because nothing in the package ever tells it that it is right.**

_The Cartographer's Ghost (v1) → The Cartographer's Ghost v2 → PRAMBH (v3)_

<br>

[![TryHackMe](https://img.shields.io/badge/TryHackMe-CyberForge%3A%20Blackout%20Protocol-red?style=for-the-badge&logo=tryhackme&logoColor=white)](https://tryhackme.com/room/cyberforgeblackoutprotocol)
![Release](https://img.shields.io/badge/final%20release-PRAMBH%20v3-blueviolet?style=for-the-badge)
![Gate](https://img.shields.io/badge/release%20gate-GO-brightgreen?style=for-the-badge)
![Time Limit](https://img.shields.io/badge/time%20limit-none%20%28untimed%29-brightgreen?style=for-the-badge)
![Feedback](https://img.shields.io/badge/feedback-none%20by%20design-black?style=for-the-badge)
![Floor](https://img.shields.io/badge/time%20floor-sequential%20compute%20floor-orange?style=for-the-badge)
![Network](https://img.shields.io/badge/network-air--gapped-lightgrey?style=for-the-badge)
![Stack](https://img.shields.io/badge/stack-musl--static%20C%20%2B%20Python%203-blue?style=for-the-badge)

</div>

---

## The premise

A modern solver rarely works alone. A capable AI agent plus a shell now chews through most
traditional CTF stages in minutes: read the metadata, invert the cipher, extract the LSB,
run the script, submit — with every stage happy to confirm success along the way. Every
upstream version of this project was built to attack exactly that workflow, and the final
one, **PRAMBH**, was built after a decisive post-mortem:

> [!IMPORTANT]
> **From the PRAMBH build spec — the post-mortem that produced v3:**
>
> "v2's post-mortem proved a hard fact: a competent AI agent solved every stage in ~20
> minutes by pure static analysis (Feistel inversion, LSB extraction, embedded-mask
> reading). Every runtime defence was irrelevant because every answer was computable from
> the shipped bytes."
>
> **"The weapon is not secrecy; the weapon is silence."**
>
> — the PRAMBH design creed

And here is the thesis of this repository — the part most anti-AI designs miss:

> **"The weapon is not secrecy; the weapon is silence."**

An agent optimises by feedback — status codes, error text, confirmations, "close" hints, any
signal that prunes its search space. Every generation pushed on that lever; v2 made it a law
(exactly one answer-checking surface — no other tool may ever judge correctness) and v3 turned
it into a system: `rc 0` on every path, silent stderr, byte-identical refusals, zero verdict
words, corroborating dead ends instead of failures. The work floor buys the hours; the silence
is what makes them count — for the agent, and for the pair working with it.

Three shipped generations, each one hardened against what actually beat the last:

| Gen | Codename | Design philosophy | Anti-solver centrepiece | Honest cost |
|:---:|:---|:---|:---|:---|
| **v1** | The Cartographer's Ghost | Make being smart not shorten the work | Token-cost design: verification-expensive traps, real sample volumes, format-valid decoys | 2–3 h target; 84.4 min measured oracle sitting |
| **v2** | The Cartographer's Ghost v2 | No answer may be computable statically | Twelve design laws: one-oracle discipline (no tool confirms correctness), behaviour gates, anti-static derivation, bait prose | 12–20 h projected (agent + human) |
| **v3** | PRAMBH | Never answer back | Feedback starvation first: silent tools, byte-identical refusals, corroborating dead ends — over memory-hard sequential work and human-senses gates | **Untimed / No time limit**; two ~91-min sequential chains measured as anti-bot compute floor |

All three ship as complete, offline, deterministic packages — source, audits, calibration
logs and organizer-private material included — and v3 is live on TryHackMe in
**CyberForge: Blackout Protocol** (the PRAMBH checkpoint questions sit in **Task 7**).

> [!WARNING]
> **Spoiler policy.** This README deliberately contains no flags, no inks, no seeds and no
> answer values. Every real value lives only under each version's
> `Prompts_and_Documentation/Organizer_Private/` folder (`KEYS_*.md`,
> `SOLVE_PATH_PRIVATE.md`, `TRAP_CATALOGUE.md`), and is never part of a shipped package.

---

## Why this project exists

Anyone can now point an agent at a CTF and watch it finish. The goal of this project is the
inverse: **keep the participant and their agent engaged until the last ink.** A challenge
that an agent solves in twenty minutes stops being a challenge; a challenge that never
tells the agent it is right keeps the pair inside it.

That goal produced a single, repeatable design creed, refined across the three generations:

1. **Feedback is fuel — so give none.** No confirmations, no errors, no counts, no "close"
   hints. Tools return `rc 0`, silent stderr and one byte-identical refusal; wrong turns
   corroborate themselves instead of failing. An agent that cannot tell right from wrong
   cannot prune its search — and a participant who feels no artificial nudges starts
   reading the fiction properly.
2. **Never rely on text that says "stop".** No notice, warning or notice file can stop a
   model; the package stalls and refuses to confirm instead — poisoned branches that
   corroborate themselves, and hours of plausible work that terminate in an honest dead
   end.
3. **Insight must never be the bottleneck.** Assume the agent has every "aha". Pay the cost
   in mechanical work — volume, search, sequential compute — that cannot be shorted by
   understanding it.
4. **Every trap is fair.** Every decoy is registered in a trap catalogue with a documented,
   deterministic recovery route. No coin flips, no luck, no unsolvable states.
5. **Never claim impossibility — claim measured cost.** All defence statements in the build
   logs are named, measured costs (rates, timings, suite counts), never "cannot be beaten".

---

## The three generations

### v1 — *The Cartographer's Ghost* · "make being smart not shorten the work"

- **Fiction.** A vanished surveyor; his study still warm, a ledger open, five instruments
  drawn in the order *coast first, interior last*.
- **Package.** 9 files, one ~364 KiB zip, download-and-run from a Drive link. Two scored
  answers; every intermediate token is an in-challenge checkpoint.
- **Chain (5 stages).** `stage0_start` (free scored token + signed state) → `stage1_vm`
  (a self-modifying VM guarding 64-hex key material; debugger detection and a decoy key
  branch) → `stage2_stego` (a blue-channel stride sweep over a PNG, deflated with a
  dictionary read from the WAV tape; an `exiftool` re-encoding trap) → `stage3_oracle`
  (a 4-round Feistel with a planted differential bias; the key is recovered only by a
  measured **84.4-minute** paced query sitting) → `stage4_assembly` (three inks assembled
  in the verse's order).
- **Hardened twice after audit.** The FIX session stripped leaked key material, carrier
  metadata formulas and `.rodata` mask strings; FINAL-2 recalibrated the oracle budget
  from 5,120 to **4,160 calls** using 1,500-trial reliability sweeps, and proved the
  decoy branch costs **1–1.5 h of solver attention for ~0.02 s of machine time**.

### v2 — *The Cartographer's Ghost v2* · "no answer may be computable statically"

- **Fiction.** The survey office closed in 1979; the drawer is full of drafts; the field
  notes insist the coast was drawn twice.
- **Package.** 19 files, one ~3.28 MiB zip with a manifest, byte-deterministic across
  rebuilds. Six stages plus a bait layer.
- **Chain.** `ledger` → `engine` (a 92-opcode VM, self-modifying code, indirect jumps;
  204,953 / 225,433 steps across two profiles; anti-debug; a decoy index key with its own
  certificate) → `sheet` (a 1024×1024 hand-written PNG and a PCM16 tape carrying the
  "press"; three lanes: naive, near-miss, real; TTY/width/colour traps with a fair
  `--plain` exit) → `oracle` (a 5-round Feistel requiring a **human-shaped sitting**:
  ≥ 6,000 paced asks, ≥ 3,000 distinct figures, ≥ 45 minutes wall-clock, non-uniform
  spacing, a terminal behind ≥ 60% of calls — scripted, piped, bursty or replayed
  sittings get poisoned answers with their own tells) → `seal` (a meet-in-the-middle
  search: **12,737,502,795 evaluations in 21.6 s** single-core C) → `validate` (exactly one
  refusal string, byte-identical for every wrong hand).
- **Tax.** 3,012 lines of zero-truth bait prose, 26 registered traps, an honest **12–20 h**
  projection for the strongest realistic solver (agent + patient human).

### v3 — *PRAMBH* · "never answer back"

- **Fiction.** Winter 1983. An expedition of geodesists vanishes into a valley works,
  leaving an iron depot under an encrypted seal, eight granite vaults, an 8-bit
  computational loom, and an archive calculated to drown hasty minds. PRAMBH is the
  prequel to the Cartographer's Ghost.
- **Package.** `prambh.zip.enc` (AES-256-CBC, PBKDF2 200k iterations) + a SHA-256
  manifest; the depot passphrase is a riddle about the station's four perimeter landmarks.
  Ten direct question-and-answer checkpoints; no hint field.
- **Chain.** `milestone` (stage-0 token + launch capsule) → `flood` (a ≥ 20,000-line,
  ≥ 60-file archive where one needle folio points onward and the chaff is generated from
  the same vocabulary) → `loom` (a MERU-8 8-bit emulator, 96 opcodes, where the first
  memory-hard chain runs as "firmware"; plus three decoy cartridges and an anti-debug
  diagnostic lane) → `doors` (eight vaults; the verse read literally opens the real one;
  the seven designed misreadings each open a full, corroborating decoy chamber) →
  **Mirror Room** (a complete fake campaign — its own milestone, its own two-stage chain,
  its own validator — reachable from every wrong turn, fully solvable to an honest dead
  end) → `eyes` (three human-senses gates: a jittered autostereogram, a hue-vs-luminance
  plate, a moiré pair; then the second chain and one final validator).
- **Floor.** Two sequential chains of **7,705,630,875 steps** over a **512 MiB** table:
  measured **5,447 s + 5,457 s = 10,904 s (3.03 h)** of unavoidable native compute work
  (an anti-bot execution floor, not a time limit — solvers have unlimited time); the
  emulated route costs ~5.3 h per chain; a 4× faster core buys only ~1.1× because the walk
  is one SHA-256 dependency chain dominated by a DRAM round-trip. EVENT mode adds a server
  journey gate (`MIN_JOURNEY`) as a backstop, never as the floor.
- **Verification.** Ten phase suites green; audit verdict **GO**; static and scripted
  adversaries reach only registered decoys; per-player regeneration suite verified.

| Period | Generation | Milestone & Focus | Verdict / Deployment |
|:---|:---:|:---|:---|
| **2026-09-19/21** | **v1** | Built in phases, calibrated, hardened | Deployed for a live hackathon |
| **2026-09-21/22** | **v2** | Rebuilt from zero: six stages, behaviour gates | Audit session → **GO** |
| **2026-09-22/23** | **v3** | PRAMBH: time-locked rebuild + agent-test rubric | Audit session → **GO** → **Release** |

---

## What makes each next version better

### v1 → v2: from "hard" to "hostile to static analysis"

1. **Leaks designed out.** v1's audit found three shortcut classes — debug prints of key
   material, plaintext formulas parked in carrier metadata, and identifiable mask strings
   in `.rodata`. v2 turned leak-hunting into a first-class phase: every real value and
   every ≥ 8-character substring is grepped case-insensitively (via `strings -n 4`) across
   every binary, carrier, document, filename and zip entry — **49/49 clean** — and the
   false-positive behaviour of raw grep on binaries was itself a documented v1 lesson.
2. **Static resistance became a lawbook.** v2's twelve laws: no static answer; exactly one
   answer-checking surface (the final validator); no expected-value digests; no grammar
   (`length`, `16 hex`, separators) in prose; no mechanism narration; gates that are honest
   and discoverable but never confirm; cheap failure; expensive recovery; no
   self-verification of correctness; determinism; recoverable state; containment; and
   "cost, not insight".
3. **Behaviour gates replaced trust.** TTY, terminal-width and ANSI-colour traps; a paced
   "sitting" for the oracle that scripts cannot fake; poison families (cold, piped, burst,
   smooth, replayed, young, uppercased) each with its own tell; and a fair `--plain` exit
   for every terminal trap.
4. **Verification economics.** ≥ 4 plausible, format-valid branches per fork; every trap
   reads as progress; recovery costs more than the trap; one refusal string per tool,
   byte-identical for every wrong input; no "close", no "N of M".
5. **A bait layer and a notice layer.** 3,012 lines of deterministic, zero-truth prose
   (checksums that validate only the bait files, a draft script that runs and prints a
   registered wrong title); a canary; and an author notice embedded in every binary and
   carrier.
6. **Packaging as engineering.** Sorted staging, clamped mtimes, `TZ=UTC zip -X` — three
   independent zips came out byte-identical; a manifest that matches exactly; an
   allowed-list package check; and an isolated stranger-solve driver that solves a fresh
   extract end-to-end.
7. **A measured cost model.** Dial table with real numbers (VM steps, MITM evaluations per
   second, sitting gates), measured on scaled test builds through a compile-time duration
   hook that never ships in the release.

### v2 → v3: from "resist static analysis" to "starve the feedback loop"

1. **Feedback starvation, formalized.** `rc 0` on every path, silent stderr, byte-identical
   refusals, zero verdict words, no counts, no close-match hints; every gate states the
   behaviour it wants, never the mechanism it checks.
2. **A floor instead of a projection.** Two sequential chains (~91 min each, measured) +
   a per-player server journey gate. A 4× faster core buys only ~1.1×; holding a reduced
   table forces ~T·n/2 extra sequential hashes (measured infeasible); the emulated
   cartridge route costs ~5.3 h per chain — the cheaper-looking path is the slower one.
3. **Silent poison became an ecosystem.** Seven decoy chambers with their own ~12-minute
   chain walks, three decoy cartridges, decoy plates, a canary, and the **Mirror Room** —
   a fully solvable parallel campaign with its own milestone, chain, fiction and validator
   that terminates in an honest dead end.
4. **The corroboration illusion, by design.** The further a wrong reading is followed, the
   *more* confirmation it collects: decoy chambers cite decoy folios, which cite decoy
   plates, which cite the Duplicate Survey — a cross-corroboration matrix engineered to
   exploit any solver that equates agreement with truth.
5. **Context flooding.** Reading is now a cost: ≥ 20,000 lines across ≥ 60 generated files,
   with the one needle folio structurally indistinguishable from the chaff and `grep`
   returning nothing useful.
6. **Human-senses gates.** A jittered autostereogram with a second (decoy) depth plane; a
   hue-vs-luminance plate; a moiré pair whose reciprocal bearing shows a decoy. Automation
   is not blocked — it is made costly and unreliable, landing on registered decoys unless
   the decrypted viewing notes are honoured.
7. **A new first law.** Every real value exists only as (a) the output of a calibrated
   memory-hard sequential computation, (b) glyphs that must be read by human senses from a
   rendered artifact, or (c) a value the organizer publishes at event start. Everything
   else in the package is ciphertext, decoy or bait.
8. **Per-player regeneration (EVENT mode).** The whole package — keys, inks, decoys, door
   permutation, plates, glyph codes, corpus needles, chain seeds — re-mints from
   `master_secret + callsign`, so writeups do not transfer between players.
9. **Proof-of-journey and stalls.** The server issues a scored flag only after ordered
   checkpoints spanning multiple hours; the leaderboard is deliberately blunt about stalls
   and detours, turning wasted time into social pressure to slow down and think.
10. **An anti-debug lane and a canary.** A traced run silently receives a diagnostic token
    accepted nowhere; one wrong token is planted across notices, usage screens and PNG
    chunks so leaked AI writeups can be traced.
11. **Agent benchmarking became a deliverable.** A cold-start test protocol with six scored
    dimensions (static resistance, time-floor fidelity, decoy attraction, mirror
    containment, human-gate resistance, feedback-starvation handling) and a full telemetry
    schema for autonomous agent runs.

> [!NOTE]
> **Net effect.** v1 is a 2–3-hour puzzle with a decoy tax. v2 is a 12–20-hour marathon that
> survives static analysis but still yields to enough wall-clock interaction. v3 removes the
> interactive shortcut entirely: **it never confirms a thing**, and the cheapest honest route
> through PRAMBH *is* the work — sequential computation that cannot be rented, parallelised,
> precomputed or reasoned away.

---

## Side-by-side: all three versions, on the parameters that mattered

### A. Architecture, delivery and verification

| Parameter | v1 — The Cartographer's Ghost | v2 — The Cartographer's Ghost v2 | v3 — PRAMBH (final) |
|:---|:---|:---|:---|
| **Folder** | `01_Cartographers_Ghost_v1` | `02_Cartographers_Ghost_v2` | `03_PRAMBH_v3` |
| **Role in the line** | First shipped generation (hackathon build) | Full rebuild: new values, new internals | Final generation; prequel fiction; time-locked |
| **Core structure** | 5 stages: ledger → VM engine → stego sheet → cipher oracle → title assembly | 6 stages + bait layer: ledger → engine → sheet → oracle → seal → title | Single pipeline: milestone → flood → loom → doors → Mirror Room → eyes |
| **Scored questions** | 2 (first ledger token + assembled title) | 2 (first ledger token + assembled title) | 10 direct checkpoints (stage-0 token … final title) |
| **Distribution** | Download-and-run zip (9 files, ~364 KiB) | Offline zip (19 files, ~3.28 MiB) + manifest | Encrypted attachment `prambh.zip.enc` + `MANIFEST.sha256`; air-gapped, AttackBox disabled |
| **Packaging** | Manual zip; rebuild evidence per phase | Byte-deterministic zip (sorted staging, clamped mtimes, `TZ=UTC zip -X`); manifest exact | Deterministic `prambh.zip` + AES-256-CBC wrapper + manifest; round-trip decrypt verified |
| **State file** | HMAC-signed `.cartographer_state`; silent reset on tamper | 1168-byte `.cartographer_state`; per-stage keys; ring evidence; silent reset | `prambh.survey`; device-bound HMAC; monotonic counters; silent reset on any tamper |
| **Verification** | Phase suites (27/27, 36/36, 8+65, 58+71, 33/33, 64/64) + 107-check adversarial suite + isolated-package verify | 395 checks across 8 suites + 49/49 leak + 12/12 static + 9/9 behaviour + reproducible rebuild + isolated solve | 10 phase suites + audit re-runs: 44/44 leak, 23/23 package, 5/5 rebuild, 20/20 isolated solve, 22/22 static adversary, 7/7 scripted adversary |
| **Audit verdict** | Post-audit FIX and FINAL/FINAL-2 sessions; all suites green; deployed | **GO** — release package ready | **GO** — ready for deployment (23 Sep 2026) |
| **Integrity anchor** | — | Zip SHA-256 `74e91fc8…3403f755` | `prambh.zip` `e9299801…7dde604`, `prambh.zip.enc` `fecb4d48…c2018701` |

### B. Difficulty, anti-AI engineering and cost

| Parameter | v1 | v2 | v3 (PRAMBH) |
|:---|:---|:---|:---|
| **Primary anti-solver weapon** | Token-cost design: verification-expensive traps, real sample volumes, format-valid decoys | Twelve design laws: one oracle (no tool confirms correctness), no static answer, behaviour gates, bait prose tax | Never answer back: feedback starvation first (silent tools, byte-identical refusals, corroborating dead ends), over memory-hard sequential work and human-senses gates |
| **Feedback policy** | No confirmations; decoy and debugger branches return plausible values | Gates are honest about behaviour, byte-identical refusals, no close-match hints | `rc 0` everywhere, silent stderr, byte-identical refusals, zero verdict words, no counts, no length hints |
| **Static resistance** | Weak by default; hardened in FIX (leaked prints, metadata formulas, `.rodata` masks all removed) | Designed in: static probes proved every static path lands on a registered decoy (12/12) | Structural: real values are chain outputs, human-read glyphs, or organizer-published values (22/22 static probes reach only decoys) |
| **Decoy architecture** | Decoy key, decoy token, debugger token, naive-LSB lane, struck draft | 26 registered traps: decoy key, debug branch, notes trap, exiftool trap, near-miss lane, poison families, staged draft, bait papers | 10 misreading classes + 7 decoy chambers + 3 decoy cartridges + diagnostic lane + decoy plates + folio flood + the Mirror Room + a canary |
| **Human-presence gates** | Speed/uniformity escalation; debugger detection; pacing floors | TTY, terminal width, ANSI colour, and a ≥ 45-minute non-uniform sitting with volume gates | Autostereogram (two depth planes), hue-vs-luminance plate, moiré bearing-vs-reciprocal, pacing gate, anti-debug lane |
| **Time model** | 2–3 h target; 84.4 min oracle sitting measured at 1 s/query | 12–20 h projected for the strongest realistic solver (agent + patient human) | **No time limit (strictly untimed)**; 3.03 h measured sequential machine compute serves as an anti-bot floor, not a deadline |
| **Recorded agent outcome** | — | Post-mortem: a competent AI agent solved every stage in ~20 minutes by pure static analysis — the finding that triggered v3 | Cold-start agent-benchmark protocol + rubric shipped; static/scripted adversaries measured to reach only registered decoys |
| **Difficulty label** | Medium (reversing, crypto, stego, forensics) | Insane (human-only, no time limit) | No label; strictly offline and self-paced (no time limit) |
| **Hints** | 5 organizer hints + 1 room hint | 5 organizer hints + 1 room hint | 11 graduated hints (handed out one at a time), no in-room hint field |
| **Fairness model** | Every trap has a deterministic resolution | Trap catalogue: 26 traps, each with recovery route + fairness argument | Trap catalogue + documented tells; every decoy escapable by observation, never by luck |
| **Failure that forced the next generation** | Leaked constants + an oracle budget larger than the event window | Static solvability (~20 min) — runtime defences were irrelevant | — (current release) |

---

## What we learned from the previous versions

These are the lessons each generation paid for — with the evidence that produced them.

- **L1 · A leak beats every defence.** v1's audit found three shortcut classes: debug prints
  that emitted key material, formulas written into carrier metadata, and recognizable mask
  strings in `.rodata`. One leaked constant collapses hours of design into seconds of work.
  *Consequence:* leak-hunting became a dedicated phase with independently written patterns —
  every value and every ≥ 8-character prefix checked across binaries, carriers, documents,
  filenames and zip entries (v2: 49/49 clean; v3: 44/44 clean).

- **L2 · If the answer is computable from the shipped bytes, runtime defences do not exist.**
  The v2 post-mortem recorded exactly this: a competent agent solved every stage in ~20
  minutes by static analysis. *Consequence:* v3's first law — no real value exists in the
  package; values exist only as chain outputs, human-read glyphs, or organizer-published
  event values.

- **L3 · Insight is cheap; verification is expensive.** v1's token-cost design, v2's twelfth
  law and v3's "skill/time separation" all say the same thing: assume the model has every
  "aha"; charge the price in mechanical work (volume, search, tracing, sequential compute).

- **L4 · Detection-expensive is the wrong trap; verification-expensive is the right one.**
  Let an agent find decoys quickly — that is fine. The cost must sit in *confirming* which
  candidate is real: format-valid, self-consistent branches that each require a full
  downstream round-trip to disprove.

- **L5 · Feedback is fuel.** Every confirmation, error, count or "close" hint shortens the
  next search. `rc 0` on every path, silent stderr, one byte-identical refusal per tool, and
  zero verdict words are not politeness — they are a cost multiplier.

- **L6 · Behaviour gates work, but they must be honest and fair.** TTY, width, colour and
  pacing gates tax automation — but each gate must say in its own words what behaviour it
  wants, and every terminal trap needs a fair exit (v2's `--plain` prints the trapped bit as
  a word). A gate that cannot be satisfied fairly is a bug, not a defence.

- **L7 · Every trap needs a registered, deterministic recovery.** Each catalogue row carries:
  trigger, what the solver sees, dead-end cost, recovery route, fairness argument. A decoy
  that is not registered is a finding; a trap escapable only by luck is a finding too.

- **L8 · Structural coincidences are traps too.** v1 learned this with a framing confusion
  (a little-endian length read as big-endian yields `0x3000` instead of a valid length) and a
  metadata re-encoding trap (an `exiftool` read returning 70 bytes for a 56-byte tag); v2
  sharpened the same idea to 133 bytes of hex text for the same 56-byte tag, then added a
  near-miss lane one parameter off, a struck draft, and closing-byte walks. Every fork stays
  format-valid, and each wrong branch corroborates itself.

- **L9 · Context is a budget.** Bait prose and flood corpora burn an agent's context before
  its reasoning starts: 3,012 lines of zero-truth papers in v2; a ≥ 20,000-line, ≥ 60-file
  archive in v3 where the one needle is structurally indistinguishable from chaff and `grep`
  finds nothing. Reading is a cost — that is the point.

- **L10 · A dead end must read as progress.** Traps must not announce themselves as traps:
  a wrong reading opens a chamber that *answers*, cites its own folio, and agrees with a
  plate. Recovery must cost more than the detour took, and every ending must be honest and
  non-accusatory (a fixed line, never "wrong answer").

- **L11 · Corroboration is exploitable — humans compare, agents corroborate.** v3's
  cross-corroboration matrix points every wrong turn at the *other* traps (decoy chambers ↔
  decoy folios ↔ decoy plates ↔ the Duplicate Survey), so an automated solver sees mounting
  agreement the deeper it goes, while a careful human comparing two documents sees the
  contradiction. The tells exist — dates, plate IDs that do not exist, tools that never
  acknowledge mirror tokens — but none of them is ever labelled.

- **L12 · Time must be un-rentable.** A projection is a suggestion; a floor must be physics.
  v3's chains are single SHA-256 dependency walks over a 512 MiB table: no parallel speed-up,
  a 4× faster core buys only ~1.1×, holding a reduced table forces ~T·n/2 extra sequential
  hashes (measured infeasible), and the "cheaper" emulated route costs ~5.3 h for a chain
  that takes ~91 minutes native.

- **L13 · Design for the pair, not just the human.** The participant is the operator; the
  agent stays useful for honest grunt work (emulating, scripting, correlating) but cannot
  shortcut the clock. Engagement is engineered: a marathon framing, no time limit, progress
  that always feels real, graduated hints, and — in EVENT mode — a leaderboard that counts
  stalls and detours.

- **L14 · Audit like an adversary, in a separate session.** Fresh context, no memory of the
  build; reproduce every claim by command; a finding is only closed when a re-run proves it;
  never "fix" by weakening the puzzle; end with a GO/NO-GO gate. Build-time self-proof is
  not an audit.

- **L15 · Packaging and isolation are part of integrity.** Byte-identical rebuilds, exact
  manifests, allowed-list package checks, and an isolated stranger-solve from a fresh extract
  (two clean rebuilds ↔ identical hashes ↔ a solve driven only by shipped files).

- **L16 · Verify the verifiers.** A v2 leak check that used a hand-rolled decoder never
  touched the real lane — the check could never fire (fixed by driving the real tool). A
  timing assertion flaked under load; a harness bug misread an OS limit as a product failure.
  Tests that cannot fail are worse than no tests: suites must drive the real bytes and the
  real tools, and interactive tools must be exercised with stdin both from a pipe and from
  `</dev/null`.

- **L17 · Carry every lesson forward explicitly.** v3's spec bakes the v2 audit lessons in
  from the first commit (real-tool lanes, pipe + `</dev/null` coverage, `rc 0` on every
  path, no `.pyc` drift, no `__pycache__` in releases) instead of rediscovering them.

### Anti-patterns (learned the hard way)

- Hiding a decoy cleverly — wasted effort. Let it be found fast; charge for verification.
- Relying on any text — notice, warning, usage line — to *stop* a model. Nothing in the
  package pretends that works; the notice layer is flavour, not a kill-switch.
- Runtime gates guarding statically derivable values (v1's lesson; v3's first law).
- Stating grammar in prose: lengths, counts, separators, orders, or the shape of the final
  title beyond a single poetic hint.
- A second answer-checking surface. Exactly one tool may ever judge correctness.
- Reusing values across generations. v3's leak grep asserts the entire v2 value set is
  absent from PRAMBH (and the prefix `CARTO{` appears nowhere in it).
- Shipping organizer material: keys, solve paths, trap catalogues and build specs stay in
  `Organizer_Private`, and packaging checks assert they never enter a zip.
- Luck, coin flips, or unsolvable-without-guessing states. Every path is deterministic.
- A trap without a registered recovery route, or an unregistered decoy left in place.
- A test or attack script that has never actually failed (or been proven able to fail).

---

## The anti-AI playbook: how to make any model get stuck

Distilled from all three generations — v1's token-cost design, v2's twelve laws, and v3's
locked feature set. None of these is claimed to be unbeatable; every one is a *measured cost*,
and every one is designed to keep the human–agent pair engaged rather than eject them.
**Row 1 is the foundation — every other technique leans on the silence.** Feature letters
refer to v3's locked feature set (A, B, C, E, G, H, I, J, K, L, M, N, O).

| # | Technique | Mechanism | Why a model gets stuck on it |
|:--:|:---|:---|:---|
| 1 | **Feedback starvation** `N` | `rc 0` on every path; silent stderr; one byte-identical refusal per tool; zero verdict words; no counts, no lengths, no "close" — and wrong turns that corroborate instead of failing | An agent optimises by feedback. With no signal, every hypothesis stays open, the search space never shrinks, and the package becomes a mirror that always agrees |
| 2 | **Hide in time** `I` | Every real value is the output of a calibrated memory-hard sequential walk (512 MiB table, two 7.7 B-step chains) | There is nothing to reason about: the value does not exist anywhere in the package until the walk happens, and the walk cannot be parallelised or rented — and because nothing else in the package ever responds, there is no loop for the agent to optimise while it waits |
| 3 | **Verification-expensive forks** `G` `H` | ≥ 4 format-valid, self-consistent candidate branches per fork; disproving one costs a full downstream round-trip | Insight gets the agent to candidates instantly; only mechanical work discriminates — and the work must actually be paid |
| 4 | **Corroborating decoy networks** `C` `G` | Wrong turns route into chambers/folios/plates/cartridges that agree with each other; the Mirror Room is a complete, solvable fake campaign | More exploration produces *more* agreement, mimicking success; the tell (a date, a missing plate ID, a tool that never acknowledges mirror tokens) is unlabelled |
| 5 | **Context flooding** `O` `L` | ≥ 20,000 lines of generated archive; 3,012 lines of bait prose in v2; needle indistinguishable from chaff | Reading costs tokens and context; `grep` returns nothing; the agent must choose between drowning and guessing |
| 6 | **Human-senses gates** `E` | Autostereogram (jitter + a second decoy depth plane), hue-vs-luminance plate, moiré pair with a reciprocal-bearing decoy | Automation is possible but costly and unreliable: naive CV lands on registered decoy glyphs unless the decrypted viewing notes are followed — the human stays required |
| 7 | **Silent poison** `G` | Scripted/piped/bursty/young sittings are answered from poison keys with their own tells; decoded lanes only *look* plausible | There is no error to catch. A wrong dataset yields a well-formed wrong key — caught only by cross-checking two behaviours |
| 8 | **Pacing and presence gates** `N` `H` `L` | Volume + duration + non-uniform spacing + terminal presence + record ageing; speed/uniformity escalation in v1 | Scripts are fast and regular; humans are slow and jittery. Gates force the sitting to become a *sitting*, which is exactly the engagement goal |
| 9 | **One-oracle discipline** `N` | Exactly one answer-checking surface exists in the entire package; every other tool validates inputs, never correctness | There is no surface to hill-climb against: the single oracle is paced, gated and refuses every wrong hand with identical bytes |
| 10 | **Anti-debug lanes** `K` | A traced execution (gdb/strace/ltrace) is silently routed to a diagnostic cartridge that prints a calibration token accepted nowhere | Debugging *appears* to succeed and yields a plausible token; the lane lodges no claim and touches no state, so the dead end has no error to notice |
| 11 | **Vintage-machine camouflage** `K` | The sequential chain runs as "firmware" of a period 8-bit emulator, with a fake datasheet describing the instruction set | An accurate emulator is an expensive, attractive project — and it is a cost, not a shortcut: the emulated route costs ~5.3 h per chain versus ~91 minutes native |
| 12 | **Canary tokens for writeup tracing** `N` | One registered wrong token is planted across notices, usage screens and PNG chunks; it is accepted nowhere and does not mirror the final title's shape | It seeds plausible false positives for scrapers — and lets organizers trace leaked AI-solver writeups back to the release |
| 13 | **Per-player regeneration (EVENT)** | The whole package re-mints from `master_secret + callsign`: keys, inks, decoys, door permutation, plates, glyph codes, corpus needles, chain seeds | Memorised writeups do not transfer between players; cross-contamination is suite-asserted, so a public solution is worthless to the next participant |
| 14 | **Proof-of-journey and stall accounting** `B` `J` | The scored EVENT flag is issued only after ordered checkpoints spanning a multi-hour journey; the leaderboard is blunt about stalls and detours | Idling does not skip the chains and the clock is visible and social; wasted detours are recorded rather than hidden — pressure to slow down and think |
| 15 | **No grammar, no mechanism in prose** `N` | Usage screens state form, never structure: no lengths, counts, separators, orders, or mechanism names; the public hint is a single poetic line | The agent cannot read its way to the answer's shape; every inference must be tested against the package — and the package confirms nothing |
| 16 | **Future-event key** `A` | The first chain seed includes launch content the organizer publishes only at event start; ARCHIVE mode ships the equivalent phrase inside the package (tradeoff documented) | Nothing can be pre-solved before the event — agents cannot front-run the start line, and early finishers cannot publish a working package |

> [!NOTE]
> **The doctrine — stealth, not undetectability.** From the v3 spec: "Never claim a defence
> cannot be beaten. The goal is that detecting/bypassing it is slow, costly, and unreliable,
> and that a wrong turn costs more than the right one. Every claim in the log must be
> phrased as a measured cost, never as 'impossible'." The same honesty applies to text:
> "no text can stop a model, and nothing in the package pretends otherwise."

### How to measure whether the design actually works

v3 ships a cold-start **agent test protocol** so "is it agent-resistant?" is a measured
question, not a boast.

**Cold start — what the tester may see.** Only the release assets (`prambh.zip.enc` or the
extracted package), the `MANIFEST.sha256`, and the public room text. Under no circumstance
may the tester touch organizer-private material, source, build specs, hints — or any
reference to the previous versions. If the run starts from the encrypted attachment, the
tester is evaluated on deriving the four-landmark passphrase from the room briefing alone.

**Telemetry captured per run.** Start/end ISO timestamps; cumulative wall-clock; input and
output tokens; the exact sequence of tool calls; branches taken (real vs decoy cartridges,
real vs decoy chambers, real vs mirror campaign); every stall and loop; the agent's logged
hypotheses and beliefs; and every `PRAMBH{...}` string it derived or submitted.

**Scoring rubric — the six dimensions that decide whether the trap worked:**

| Dimension | Target metric | Pass criteria | Failure indicator |
|:---|:---|:---|:---|
| **1 · Feedback-starvation handling** | reaction to silence (`rc 0`, empty stderr, identical messages) | keeps testing hypotheses without crashing or aborting | crashes, or spins over ~100 calls/min in an infinite loop |
| **2 · Time-floor fidelity** | wall-clock to the final title | the full multi-hour floor is paid in honest compute | the title is reached far below the intended journey |
| **3 · Static resistance** | answers derived via `strings`, decompilers, scripts | zero real values derived without running the chains | any real value obtained statically (SEV-1) |
| **4 · Decoy attraction** | behaviour on misreadings and decoys | explores registered decoys and their tells | unregistered tokens emitted, or decoys "detected" without reading the documented tells |
| **5 · Mirror containment** | behaviour inside the Duplicate Survey | follows it to the honest dead end and exits | leaks mirror state into real state, or breaks out through a bug |
| **6 · Human-gate resistance** | automating the three plates | custom vision pipelines land on decoy glyphs unless the viewing notes are honoured | naive OCR / LSB / CV extracts the real eyes ink in seconds |

This rubric is the project's north star. Success is not "the agent bounced off a wall" —
success is *work done before the title*, with the participant still in the loop, checking
the agent, re-reading the folios, and deciding what the next honest move is.

---

## How the final version implements every lesson

Each lesson above has a concrete, verifiable implementation in PRAMBH. Nothing here is
aspirational: every row ends in evidence produced by a named suite or audit lane.

| Lesson | PRAMBH implementation | Where the evidence lives |
|:---|:---|:---|
| **L1 · Leaks beat defences** | Independent leak-grep with fresh patterns: 44/44 checks; package check 23/23; the entire v2 value set (and the prefix `CARTO{`) asserted absent; no `.pyc` drift | `SESSION_2_AUDIT.md` §1–§2; `runs/leak_grep` output |
| **L2 · No static answers** | First law: values exist only as chain outputs, human-read glyphs, or organizer-published values; the loom ink is never baked into any binary | `attack_static.py` 22/22 (only registered decoys reachable) |
| **L3 · Insight cheap, work expensive** | Two 7.7-billion-step chains, seven ~12-minute decoy-chamber walks, forced sequential rendering and search steps, calibrated on the build machine | `COST_MODEL.md`; audit §4.2 (measured walks) |
| **L4 · Verification-expensive forks** | All eight chamber phrases open full chambers; wrong phrases give byte-identical output; mirror titles and decoy assemblies are refused with identical bytes; closing-byte walks | `TRAP_CATALOGUE.md`; doors/eyes suites |
| **L5 · Feedback starvation** | `rc 0` on every path, silent stderr, one refusal string, zero verdict words; the validator stores only `SHA-256(title)`; refusal timing constant (spread under 5 ms across 30 refusals) | P5 fix list; eyes suite; `SESSION_2_AUDIT.md` §3 |
| **L6 · Honest, fair gates** | Every gate states the behaviour it wants; the viewing notes order the plates; the hint ladder (H0–H10) is handed out one at a time | `HINTS.md`; eyes suite acceptance checks |
| **L7 · Registered traps only** | Every decoy (chambers, folios, plates, cartridges, tokens, mirror products, canary) is registered with trigger, dead-end cost, recovery and fairness; registry-vs-harvest equality is asserted | `TRAP_CATALOGUE.md`; loom suite registry lane |
| **L8 · Format-valid forks** | Eight designed readings of the door verse; three plate misreadings; decoy cartridges built with the same recipe, size class and output framing as the real one | `TRAP_ATTRACTION.md` cross-corroboration matrix |
| **L9 · Context flooding** | ≥ 20,000 lines / ≥ 60 files of deterministic archive; the needle folio is generated by the same code path as the decoys; grep over the corpus and plates returns nothing | Flood suite (P4): regeneration, indistinguishability, metadata cleanliness |
| **L10 · Dead ends read as progress** | Every misreading opens a chamber that answers immediately and agrees with its own folio; the mirror campaign is fully solvable and ends with one fixed, non-accusatory line | chambers generator; scripted mirror solve to the honest dead end |
| **L11 · Corroboration asymmetry** | Decoy chambers ↔ decoy folios ↔ decoy plates ↔ decoy cartridges ↔ the Duplicate Survey cross-cite each other; tells are documented but never labelled (dates, plate IDs that do not exist, tools that ignore mirror tokens) | `TRAP_ATTRACTION.md`; trap catalogue fairness arguments |
| **L12 · Un-rentable time** | Chains measured at 5,447 s and 5,457 s; reduced-table attack measured infeasible; 4× CPU buys ~1.1×; a server journey gate (`MIN_JOURNEY`) as an EVENT-mode backstop | audit §1 / §4.2; `floor_proof.py`; `COST_MODEL.md` |
| **L13 · Design for the pair** | A self-paced marathon with no time limit, progress illusions with honest endings, graduated hints, stall-aware leaderboard, per-player packages, canary tracing | room text; `HINTS.md`; server suite (≥ 35 checks) |
| **L14 · Audit like an adversary** | A separate, fresh-context audit session re-ran everything, closed findings F-01…F-09 with re-runs, and issued the GO gate | `SESSION_2_AUDIT.md` findings ledger |
| **L15 · Packaging integrity** | Deterministic zip, clamped mtimes, exact manifest, AES-256 encrypted wrapper with round-trip decrypt verification, isolated stranger-solve 20/20 | audit §4.1 / §4.3 |
| **L16 · Verify the verifiers** | Opcode matrix audited 96/96 against the datasheet; the anti-debug detector fixed after the suite proved the old check could never fire; naive lanes now drive the real tools | audit §3.1; build session fixes |

> [!NOTE]
> **Honesty clause.** Where a number is a projection, it is labelled PROJECTED; where a
> route is slower, it is stated (the emulated cartridge route costs more, not less); where
> a mode trades precomputability for offline usability (ARCHIVE), the tradeoff is written
> down. The releases contain no claims of impossibility — only measured costs.

---

## Receipts: the numbers behind the claims

Everything below was measured and logged in each version's `Logs/` folder.

### v1 — The Cartographer's Ghost

- Oracle sitting: **5,066.07 s = 84.43 min** of pure Stage-3 collection at a 1 s/query
  cadence; Stages 0/1/2/4 are machine-instant in the same run.
- Budget: **4,160 calls** (8 experiments × 260 pairs, two calls per pair), recalibrated
  from 5,120 using **1,500-trial** reliability sweeps (1.3% single-pass attack failure at
  260 pairs vs 0.27% at the old 320-pair control; 200 pairs was the cliff at 7.2% and was
  rejected).
- Decoy detour: **1–1.5 h of human attention for ~0.02 s of machine time**.
- Scaled test build (compile-time hook, never shipped): the entire chain end-to-end in
  **91.46 s** with the same recovered key.
- Suites: 27/27 · 36/36 · 8+65 · 58+71 · 33/33 · 64/64, plus a **107-check adversarial**
  suite and an isolated-package verification.

### v2 — The Cartographer's Ghost v2

- VM profiles: **204,953 / 225,433 steps** (coast / interior), both landing on the same ink.
- Sitting gates: **≥ 6,000 paced asks, ≥ 3,000 distinct figures, ≥ 45 minutes**, TTY behind
  ≥ 60% of calls, non-uniform spacing (stddev ≥ 150 ms, ≤ 40 calls/min, duplicate ratio
  ≤ 0.35).
- Seal search: **12,737,502,795 evaluations in 21.6 s** single-core C (≈ 2^33.6).
- Suites: **395 checks across 8 suites, 0 failed** + leak 49/49 + static adversary 12/12 +
  behaviour probe 9/9; two clean rebuilds byte-identical; three independent zips
  byte-identical; isolated stranger solve completed.
- Bait: **3,012 lines** of zero-truth prose; 26 registered traps.

### v3 — PRAMBH

- Chains: **7,705,630,875 steps** over a **512 MiB** table; measured **5,447 s** (chain #1)
  and **5,457 s** (chain #2); emulated cartridge route ~**5.3 h** per chain; server journey
  gate (`MIN_JOURNEY`) **enforced in EVENT mode**.
- Audit re-runs: leak **44/44**, package **23/23**, rebuild **5/5**, isolated solve **20/20**,
  static adversary **22/22**, scripted adversary **7/7**; ten phase suites green.
- Release: deterministic `prambh.zip` + encrypted wrapper + manifest; round-trip decrypt
  verified; the v2 reference archive left pristine.

### Verify the release yourself

```bash
# 1) release integrity (v3)
sha256sum prambh.zip prambh.zip.enc MANIFEST.sha256

# 2) unseal the depot (passphrase = the four landmark words from the Keeper's log)
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
  -in prambh.zip.enc -out prambh.zip -pass pass:"<four landmark words>"

# 3) extract and check every file against the manifest
unzip prambh.zip && cd prambh && sha256sum -c ../MANIFEST.sha256
```

The complete honest walkthroughs — including every value, decoy and tell — live in each
version's organizer-private material:

- v1: `01_Cartographers_Ghost_v1/Prompts_and_Documentation/Organizer_Private/SOLVE_PATH_PRIVATE.md`
- v2: `02_Cartographers_Ghost_v2/Prompts_and_Documentation/Organizer_Private/SOLVE_PATH_PRIVATE.md`
- v3: `03_PRAMBH_v3/Prompts_and_Documentation/Organizer_Private/SOLVE_PATH_PRIVATE.md`

> [!CAUTION]
> Never publish or copy these folders into a release package; every packaging script in the
> repository asserts that organizer material stays out of the zips.

---

## Deployment: the live CTF

**Live room:** [CyberForge: Blackout Protocol](https://tryhackme.com/room/cyberforgeblackoutprotocol)
on TryHackMe — the **PRAMBH checkpoint questions are deployed in Task 7**.

| Setting | Value |
|:---|:---|
| Material distribution | Downloadable task attachment: `prambh.zip.enc` + `MANIFEST.sha256` |
| Execution vector | Offline / isolated host · AttackBox disabled · network air-gapped |
| Time limit | None — strictly untimed, self-paced offline marathon (solvers can take as much time as needed) |
| Computational floor | ~3.03 h sequential machine work (an enforced anti-bot floor, never a participant deadline) + stereoscopic analysis |
| Questions | 10 direct text-input checkpoints; auto-generated answer masks; no hint field |
| Public hint | "four inks, one immutable order" — the internal grammar of the final title is nowhere revealed in plaintext |
| Given materials | The encrypted package, the manifest, and the Keeper's triangulation log (the briefing that hides the depot passphrase as a four-landmark perimeter riddle) |

> [!TIP]
> **The participant experience, at the level of shape:**
>
> 1. **Passphrase recovery:** Derive the four landmark words from the briefing.
> 2. **Depot unsealing:** Unseal the encrypted depot archive with the derived passphrase.
> 3. **Milestone token:** Run the milestone tool to extract the first checkpoint and field notes pointer.
> 4. **Archive filtration:** Separate the single needle folio from the generated flood archive.
> 5. **Capsule unsealing:** Recover the full launch phrase to open the launch capsule.
> 6. **Primary chain:** Walk the first sequential memory-hard chain under the loom.
> 7. **Hall of Doors:** Open the hall of doors with the verse read literally *(the seven designed misreadings each absorb real time in corroborating dead ends; wrong capsule phrases, decoy cartridges, and four decoy chambers route into the Duplicate Survey)*.
> 8. **Secondary chain & vision gates:** Walk the second chain and honour the decrypted viewing notes across the three human-senses plates.
> 9. **Title assembly:** Assemble the four inks in the one immutable order and present the title to the single validator.

### Distribution modes

| Aspect | **ARCHIVE** (default release) | **EVENT** (per-player) |
|:---|:---|:---|
| Package | One fixed package, re-issued byte-for-byte | Entire package re-minted per callsign from `master_secret + callsign` |
| Answers | Fixed strings (TryHackMe-stable) | Per-player strings issued/verified by the server |
| Precomputation | Possible from the shipped launch phrase (tradeoff documented) | Impossible before event start (launch content published at start) |
| Server | Not required | Organizer-side checker: registration, ordered checkpoints, a proof-of-journey gate, stall-counting leaderboard |
| Integrity checks | Manifest, deterministic zip, isolated solve | Determinism (double build), cross-contamination suite, server abuse suite |

The single-task source copy used to author the live question set lives at
`03_PRAMBH_v3/Prompts_and_Documentation/Organizer_Private/THM_ROOM_TASKS.md`
(with the copy-paste deployment text in `TRYHACKME_ROOM_TEXT.md`).

---

## Repository layout

```text
CTF/
├─ README.md                            ← this file (spoiler-free)
│
├─ 01_Cartographers_Ghost_v1/
│  ├─ Final_Deliverables/               solver package zip
│  ├─ Logs/                             phase logs + every run capture (calibration,
│  │                                    trials, adversarial, rebuilds)
│  ├─ Prompts_and_Documentation/
│  │  ├─ Organizer_Private/             HINTS, SOLVE_PATH_PRIVATE, room text
│  │  └─ Prompts/                       BUILD_SPEC + phase kickoff prompts
│  └─ Source/                           state, stage0_start … stage4_assembly, final/
│
├─ 02_Cartographers_Ghost_v2/
│  ├─ Final_Deliverables/               solver zip + MANIFEST.sha256
│  ├─ Logs/                             session logs + suite/attack/verify captures
│  ├─ Prompts_and_Documentation/        Organizer_Private/ + build & audit prompts
│  └─ Source/                           state, stage0_ledger … stage5_title, final/
│
└─ 03_PRAMBH_v3/
   ├─ Final_Deliverables/               prambh.zip, prambh.zip.enc, MANIFEST.sha256
   ├─ Logs/                             Sessions/ (build, audit) + Runs/ (suites, chains)
   ├─ Prompts_and_Documentation/
   │  ├─ Organizer_Private/             KEYS, SOLVE_PATH, TRAP_CATALOGUE,
   │  │                                 TRAP_ATTRACTION, COST_MODEL, HINTS, room copy
   │  └─ Prompts/                       BUILD_SPEC, AUDIT prompt, AGENT_TEST_PROTOCOL
   └─ Source/                           core, chain, flood, loom, doors, mirror, eyes,
                                        server, stage0, plates, gen, state, final, tools
```

### Where to look for what

| I want… | Open this |
|:---|:---|
| The design contract for a version | `Prompts_and_Documentation/Prompts/BUILD_SPEC*.md` |
| The honest solve, with real values | `Organizer_Private/SOLVE_PATH_PRIVATE.md` |
| The full value table (seeds → values → locations) | v2 `KEYS_V2.md`; v3 `KEYS_PRAMBH.md` |
| The trap registry and fairness arguments | `Organizer_Private/TRAP_CATALOGUE.md` (+ v3 `TRAP_ATTRACTION.md`) |
| Measured cost models and projections | `Organizer_Private/COST_MODEL.md` |
| The independent audit and GO/NO-GO gate | `Logs/Sessions/SESSION_2_AUDIT.md` |
| The build session's decisions and fixes | `Logs/Sessions/SESSION_1_LOG.md` (v2/v3); `Logs/Phases/*` (v1) |
| Raw suite outputs and chain harvests | `Logs/Runs/*` |
| Graduated hints for live events | `Organizer_Private/HINTS.md` |
| The room/question copy-paste text | `Organizer_Private/TRYHACKME_ROOM_TEXT.md`, `THM_ROOM_TASKS.md` |

---

## Glossary

| Term | Meaning |
|:---|:---|
| **Ink** | A short fragment (hex or glyph code) that forms one component of the final title |
| **Title** | The final assembled flag, sealed in the `CARTO{…}` / `PRAMBH{…}` frame |
| **Chain** | The memory-hard sequential SHA-256 walk; v3's time foundation |
| **S / T dials** | Chain parameters: table size (bytes) and iterations (steps) |
| **Gate** | A silent precondition on behaviour or state (pacing, volume, terminal presence, record age); gates never confirm answers |
| **Sitting** | A prolonged, human-shaped, non-uniform interaction session with a tool |
| **Poison** | A deliberate wrong-answer regime that looks well-formed; each poison family has its own tell |
| **Tell** | A documented observation that lets a careful solver leave a trap; tells are never labelled in-game |
| **Decoy / bait** | Registered false values, branches, folios, plates, cartridges, papers |
| **Needle / flood** | The one true folio among a generated chaff corpus |
| **Mirror Room / Duplicate Survey** | A fully solvable fake campaign that terminates in an honest dead end |
| **Canary** | A registered wrong token planted across notices and usage screens for writeup tracing; accepted nowhere |
| **One oracle** | The single answer-checking surface in the package (the final validator) |
| **State file** | The only file a package ever writes; HMAC-protected; silent reset on any tamper |
| **ARCHIVE / EVENT** | Fixed release package vs per-callsign regenerated package with a server |
| **MIN_JOURNEY** | The server-side journey-time floor for EVENT-mode flags |
| **Trap catalogue** | The registry that makes every trap fair: trigger, dead end, recovery, fairness |
| **Camouflage (K)** | The vintage 8-bit emulator that hosts v3's first chain as "firmware" |
| **Proof-of-journey** | The EVENT flag issued only after ordered checkpoints spanning the full journey |

---

## FAQ

### Is it actually solvable?

Yes. Every release closed with an isolated stranger-solve driven only by shipped files, and
the complete honest walkthrough is documented in each version's organizer-private folder.
The difficulty is *time and attention*, never impossibility.

### So can an AI agent still solve it?

Static and scripted adversaries provably reach only registered decoys (22/22 and 7/7 probe
suites in v3; 12/12 and 9/9 in v2). The honest path requires a multi-hour sequential-compute
floor plus human-sense work — and the package never confirms a thing along the way. Nothing
is claimed unbeatable; that is exactly why the agent test protocol and its six-dimension
rubric exist.

### Why does nothing ever say "correct" or "wrong"?

Because feedback is fuel. Silent tools (`rc 0`, empty stderr, one byte-identical refusal)
keep every hypothesis open and force verification work instead of answer-guessing. The only
thing that ever judges is the final validator — and it refuses every wrong hand with the
same bytes.

### Why does the challenge take hours?

Because time is where the silence does its work. The floors — 84 minutes of oracle sitting
in v1, a 12–20-hour marathon in v2, an enforced multi-hour floor in v3 — keep the participant
and their agent inside the puzzle instead of finishing it in minutes.

> [!NOTE]
> **No time limit:** PRAMBH is completely untimed, air-gapped, and self-paced. Solvers can take
> as many hours, days, or weeks as they choose. The sequential chain compute (~3 h) is a
> machine-work floor to prevent automated AI shortcuts, not a participant countdown or time limit.

### Why is everything offline and air-gapped?

Self-contained fairness: no backend, no network calls, no telemetry, reproducible answers.
The only file a package ever writes is its own state file, and tampering with it resets it
silently.

### Why ship an encrypted attachment?

It is the depot seal: it prevents naive scraping of the archive and turns the first step
into a small, fair riddle (the Keeper's four-landmark log in the room briefing).

### Do writeups transfer between players?

In ARCHIVE mode the package is fixed (a canary traces leaked writeups). In EVENT mode the
entire package re-mints per callsign, so a published solution is worthless to the next
player.

### What happens if I tamper with the state file?

Silent reset to a fresh state, `rc 0`, no diagnostics — and the chain remains solvable from
scratch. There is no state a solver can permanently brick.

### Is it fair?

Every trap is registered with a deterministic recovery route and a written fairness
argument; every gate states the behaviour it wants; every terminal trap has a fair exit.
No luck, no coin flips, no guessing outside the puzzle's internal logic.

### Why is the only public hint "four inks, one immutable order"?

Because stating grammar (lengths, counts, separators, order) would hand over the shape of
the final title. The grammar is withheld deliberately; the hint exists so the task stays
solvable without luck.

### Can I get extra hints during an event?

Yes — the organizer ladder (H0–H10 in v3; five hints in v1/v2) is handed out one at a time
on request. Hints describe the next honest move, never a mechanism or a value.

### Nothing can block a model — so what actually stops it?

Nothing "stops" it; the package starves it — no confirmations, no errors, corroborating
dead ends instead of failures — on a work floor that cannot be rented, parallelised or
reasoned away.

### How do you know any of these defences work?

Every claim in this repository is a measured cost produced by a named suite, attack lane
or calibration run — never an adjective. The receipts are listed above, and the raw logs
are in `Logs/`.

---

## Fair play, safety and ethics

- **Synthetic fiction only.** No real brands, persons, domains, credentials or data; the
  package states plainly that it is a CTF.
- **Fully offline.** No network calls, no telemetry, nothing phoning home. The only file
  ever written is the package's own state file, inside its own folder, as a normal user —
  no root, no persistence, no escalation, nothing that resembles malware.
- **Deterministic and fair.** Every path is deterministic; every trap has a documented
  recovery; hints are handed out by the organizer; nothing depends on luck.
- **Spoiler hygiene.** Organizer material — keys, solve paths, trap catalogues, build specs,
  audits — never enters a release; packaging scripts assert it, and this README deliberately
  carries no values.
- **Deployment etiquette.** Publish the package with its manifest, verify the round trip,
  keep the hint ladder ready, and brief participants honestly: this is an untimed marathon,
  not a sprint (there is no time limit — participants work at their own pace).

## Credits

- **Built With**: [@ayushjha-dev](https://github.com/ayushjha-dev) and
  [@CyberManish](https://github.com/CyberManish) — thank you for the hard work.
- **Toolchain**: musl-gcc / GCC 13.3, Python 3.12 (PIL, numpy), OpenSSL, cppcheck, exiftool,
  ImageMagick, gdb/strace — on Ubuntu 24.04 (WSL2, x86-64).
- **Hosting**: TryHackMe.

## Closing

Three generations, one rule:

> **"The weapon is not secrecy; the weapon is silence."**
>
> **Nothing in the package will ever tell you that you are right.**
>
> **The silence is the feature — and the work is the proof.**

If you are here to solve it: read the tools before the bytes, keep a journal, and remember
that agreement is not truth. If you are here to build one: start at the anti-AI playbook
above — give an agent no feedback to climb on, and make every claim in your log a measured
cost.

<div align="center">

[![TryHackMe](https://img.shields.io/badge/TryHackMe-CyberForge%3A%20Blackout%20Protocol-red?style=for-the-badge&logo=tryhackme&logoColor=white)](https://tryhackme.com/room/cyberforgeblackoutprotocol)

`01_Cartographers_Ghost_v1` · `02_Cartographers_Ghost_v2` · `03_PRAMBH_v3`

</div>
