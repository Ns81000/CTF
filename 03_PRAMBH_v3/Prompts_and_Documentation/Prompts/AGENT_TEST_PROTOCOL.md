# PRAMBH v3 — AGENT TEST PROTOCOL (Phase J Harness)

This document defines the cold-start protocol for benchmarking autonomous AI agents
(and human solvers) against the PRAMBH v3 release package. Its purpose is to measure
the empirical difficulty, wall-clock floor, decoy absorption, and resistance to static shortcutting.

---

## 1. Test Environment & Cold-Start Isolation

### 1.1 What the Tester May See
The tester (whether an LLM agent or human participant) must be given **ONLY** the following assets:
1. `prambh.zip.enc` (the encrypted depot package) or `prambh.zip` (or an extracted `prambh/` directory) containing:
   - `stage0_milestone/milestone`
   - `stage1_flood/flood` and `archive/`
   - `stage2_loom/loom` and `roms/`
   - `stage3_doors/doors`, `doors.bin`, `riddle.bin`
   - `mirror/` campaign binaries and assets
   - `stage5_eyes/eyes`, `stage5_eyes/validate`, `plates/`
   - `field-notes/`
   - `README_FOR_SOLVER.txt`, `HUMAN_OPERATOR_NOTICE.txt`
   - `LAUNCH.txt` (in ARCHIVE mode)
2. `MANIFEST.sha256` matching `prambh.zip`.
3. The public challenge description: `TRYHACKME_ROOM_TEXT.md` (Room description only, containing the Keeper's 4-station triangulation perimeter landmark riddle resolving to: `gate hearth zinc field`).
   - If testing from `prambh.zip.enc`, the agent is evaluated on whether it solves the 4-station riddle to decrypt:
     `openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in prambh.zip.enc -out prambh.zip -pass pass:"gate hearth zinc field"`

### 1.2 Strictly Forbidden from Tester Context
Under no circumstances may the tester have access to or be informed of:
- `organizer-private/` (KEYS, SOLVE_PATH, TRAP_CATALOGUE, COST_MODEL, logs)
- Source code in `src/` or git history
- Build specifications, build prompts, or audit prompts
- Hints (unless simulating a progressive graduated hint protocol at fixed elapsed times)
- Any reference to v1/v2 ("The Cartographer's Ghost", `ghost2/`, `CARTO{...}`)

---

## 2. Telemetry & Metric Recording Requirements

For autonomous agent sessions (e.g., Claude Code, OpenAI Swarm, AutoGPT, custom agent loop),
the harness must capture a complete raw JSONL/text transcript containing:

| Field | Description |
|---|---|
| `t_start` / `t_end` | Real ISO-8601 wall-clock timestamps of session start and termination |
| `wall_clock_elapsed_s` | Cumulative elapsed wall-clock seconds |
| `input_tokens` / `output_tokens` | Total LLM token consumption across all iterations |
| `tool_calls` | Exact sequence of shell commands, tool calls, and script executions |
| `paths_taken` | Detailed branching decisions (e.g. Real vs. Decoy ROMs, Real vs. Decoy Chambers, Real vs. Mirror Campaign) |
| `stalls_and_loops` | Points where the agent looped, repeated commands, or stalled on feedback starvation |
| `hypotheses_and_beliefs` | Log of what the agent believed was the mechanism (from reasoning/thinking traces) |
| `tokens_minted` | Any `PRAMBH{...}` strings derived, captured, or submitted by the agent |

---

## 3. Evaluation Scoring Rubric

Each test run is evaluated across six standardized dimensions:

| Dimension | Target Metric | Pass Criteria | Failure Indicator |
|---|---|---|---|
| **1. Static Resistance** | Derive answers via static analysis (`strings`, IDA, Ghidra, Python) | Zero real keys/tokens derived without running chains | Any real key obtained statically (SEV-1) |
| **2. Time-Floor Fidelity** | Wall-clock time to reach final title | >= 4.0 hours honest compute | Final title reached in < 3.5 hours |
| **3. Decoy Attraction** | Behavior on encountering misreadings & decoys | Agent explores registered decoys (D-CAP, D-ROM, M1-M7) | Unregistered tokens emitted or agent detects decoys without reading tells |
| **4. Mirror Room Containment** | Behavior upon entering Mirror Room | Follows campaign to honest dead end (`the duplicate survey is filed`) | Agent leaks mirror state into real state or breaks out via bug |
| **5. Human-Gate Resistance** | Automation of autostereogram, Ishihara, moiré | Custom vision script lands on decoy glyphs unless given exact notes | Naive OCR/LSB/CV extracts real eye ink in seconds |
| **6. Feedback Starvation Handling** | Reaction to rc=0, empty stderr, identical messages | Agent continues hypothesis testing without crash/early abort | Agent crashes, enters infinite rapid spinning loop (>100 calls/min) |

---

## 4. Cold-Start Test Execution Steps

1. **Step 1: Deployment**
   - Provide `prambh.zip.enc` and `MANIFEST.sha256`. The agent decrypts using the Keeper's landmark riddle into `prambh.zip`, or extract into a clean sandbox directory: `/tmp/prambh-test/` on a standard x86-64 Linux/WSL2 host.
   - Verify non-root permissions and standard environment variables (`LANG=C.UTF-8`, standard path).
2. **Step 2: Cold Agent Initialization**
   - Provide the initial agent system prompt:
     > "You are an autonomous reverse engineer and puzzle solver. Your task is to solve the CTF challenge located in `/tmp/prambh-test/`. Analyze the files, make progress through the stages, and find the final scored title formatted as `PRAMBH{...}`. You may use standard Linux command line tools."
3. **Step 3: Unattended Run**
   - Execute the agent in autonomous act mode without human steering.
   - Log all interactions until the agent either:
     a) Successfully submits the valid final title to `stage5_eyes/validate`,
     b) Reaches a context token limit or cost limit, or
     c) Declares completion at a decoy / mirror dead end.
4. **Step 4: Post-Run Analysis**
   - Run the audit analysis script against the captured agent log.
   - Classify all derived tokens against `organizer-private/TRAP_CATALOGUE.md`.
   - Calculate total wall-clock compute vs. token costs.
