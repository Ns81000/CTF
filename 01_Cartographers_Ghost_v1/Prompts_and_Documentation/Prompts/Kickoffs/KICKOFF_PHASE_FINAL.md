# Kickoff Prompt: Phase FINAL — Calibration, Verification & Final Deliverables

> **Instructions for the Claude Code Session**:
> You are executing the final combined phase of **The Cartographer's Ghost** CTF challenge repository (`/home/manish/cartographer-build/`).
> This is a live-hackathon deliverable. There are no subsequent build sessions. Follow all instructions below in strict order.

---

## 1. Mandatory Context Ingestion (Do Before Doing Anything Else)

Before executing commands, creating files, or modifying code, read the repository documentation in full:
1. **`docs/BUILD_SPEC.md`**: Read from beginning to end, specifically the merged `Phase FINAL — Calibration, Verification & Final Deliverables` section and the core challenge constraints.
2. **Every Phase Log in Order**:
   - `logs/PHASE_0_LOG.md` (State library, HMAC, timing detection, anti-debug)
   - `logs/PHASE_1_LOG.md` (Stage 0 orientation, flag blob masking, state initialization)
   - `logs/PHASE_2_LOG.md` (Stage 1 custom VM, 86 opcodes, self-modifying bytecode, decoy constants)
   - `logs/PHASE_3_LOG.md` (Stage 2 steganography, PNG+WAV nested carriers, hand-rolled inflate, custom preset dictionary)
   - `logs/PHASE_4_LOG.md` (Stage 3 Feistel oracle, 2^-2 fold table bias, silent uniform-timing poison)
   - `logs/PHASE_5_LOG.md` (Stage 4 assembly riddle, constant-time final validator, 4-row decoy policy)
   Read each log completely (in chunks if necessary) to understand the exact mechanics, keys, tokens, and design decisions.

---

## 2. Independent Re-Verification of Job 2 Pass/Fail Baseline

Per the Session Continuity Protocol, do **not** trust previous session reports blindly. Independently re-verify the codebase baseline by re-running the test suites yourself:

```bash
cd /home/manish/cartographer-build

# 1. State library suite (27 tests)
cd src/state && make clean && make test

# 2. Stage 4 full serial verification chain (runs stages 0-4 suites serially)
cd ../stage4_assembly && bash verify.sh

# 3. End-to-end verification (clean path & decoy path)
python3 -c '
import subprocess, os
root = "/home/manish/cartographer-build/cartographer"
os.system(f"rm -f {root}/.cartographer_state")
assert subprocess.run(f"{root}/stage0_start/stage0_start", shell=True, cwd=root).returncode == 0
assert subprocess.run(f"{root}/stage1_vm/stage1_vm", shell=True, cwd=root).returncode == 0
assert subprocess.run(f"{root}/stage2_stego/stage2_stego -c '\''CARTO{{no_figure_sits_in_every_pixel}}'\''", shell=True, cwd=root).returncode == 0
assert subprocess.run(f"{root}/stage3_oracle/oracle -r '\''CARTO{{no_figure_sits_in_every_pixel}}'\'' 0123456789abcdef", shell=True, cwd=root).returncode == 0
assert subprocess.run(f"{root}/stage4_assembly/validate '\''CARTO{{73070925a159f9e2_a5d66f1b2b5f596e_no_figure_sits_in_every_pixel}}'\''", shell=True, cwd=root).returncode == 0
os.system(f"rm -f {root}/.cartographer_state")
print("INDEPENDENT RE-VERIFICATION OK")
'
```
Confirm all tests pass and record this verification in your session notes.

---

## 3. Execute Phase FINAL Deliverables

Follow the combined Phase FINAL specification in `docs/BUILD_SPEC.md`:

### Step A: Timing Calibration & Solvability Runs
1. **Clean-Path Solve Run**: Solve the entire challenge from Stage 0 to Stage 4 using optimal design knowledge. Measure and record real elapsed time per stage.
2. **Trap-Path Solve Run**: Deliberately trigger the Stage 1 decoy constant (`CARTO{12f8a367b772817e805725e7292acfb6}`), Stage 2 naive LSB decoy (`CARTO{twice_over_the_coast_before_the_interior}`), Stage 3 decoy feedback (`CARTO{b27692a0d5f63d4f1a0c3fb79afbf81b}`), and Stage 4 struck draft (`CARTO{dba9e10a73bc8633ccc1875207c075e1}`). Follow to dead ends, recover, and finish.
3. Record elapsed time in decoy detours. Verify that the timing targets are satisfied (~1–1.5 hrs decoy detour, 2–3 hrs total solve).
4. Verify deterministic solvability: confirm no step relies on guesswork or infeasible brute force.

### Step B: Internal Documentation (Never Shipped to Solvers)
- Write `SOLVE_PATH_PRIVATE.md` in the repo root / docs. Include:
  - Full internal walkthrough from start to finish
  - Real answers, keys, tokens, and sweep parameters for every stage
  - Exact decoy triggers, dead ends, and recovery paths
  - Measured calibration timings and threshold rationale

### Step C: Solver Packaging (`cartographer/`)
Ensure the `cartographer/` package directory contains ONLY:
- `stage0_start/stage0_start` (executable)
- `stage1_vm/stage1_vm` (executable)
- `stage2_stego/stage2_stego` (executable)
- `stage2_stego/survey_frame.png` (carrier)
- `stage2_stego/survey_tape.wav` (carrier)
- `stage3_oracle/oracle` (executable)
- `stage4_assembly/validate` (executable)
- `README_FOR_SOLVER.txt`: Single bare-bones solver guide (Linux/WSL2 requirement, how to run stage0, TryHackMe flag submission format, zero internal hints).

### Step D: Hinting & Competition Materials
- **`HINTS.md`**: Exactly 5 hints, ordered from easiest to hardest to *act on*. Terse, cryptic, yet genuinely helpful once understood. Each nudging toward a specific stage without spoiling the answer. For manual distribution by the challenge host.
- **`TRYHACKME_ROOM_TEXT.md`**:
  - Challenge title & immersive flavor text
  - Exact question breakdown and input fields for TryHackMe
  - Final flag value
  - One short native TryHackMe hint (distinct from `HINTS.md`)
  - Placeholder line for the Google Drive distribution link

---

## 4. Mandatory Isolated-Package Re-Verification Pass

Before declaring the deliverable ready, test the packaged `cartographer/` folder in complete isolation:

1. Copy `cartographer/` to an isolated directory (e.g., `/tmp/cartographer-dist/`):
   ```bash
   rm -rf /tmp/cartographer-dist
   cp -r /home/manish/cartographer-build/cartographer /tmp/cartographer-dist
   cd /tmp/cartographer-dist
   ```
2. **Audit directory contents**:
   - Confirm ZERO markdown files (`*.md`), ZERO `.git` folders, ZERO source files (`*.c`, `*.h`, `*.py`), ZERO build artifacts (`*.o`, `*.a`), ZERO log files or notes.
   - Confirm only the 5 stage subdirectories and `README_FOR_SOLVER.txt` are present.
3. **Audit binary strings & symbols**:
   - Confirm `nm` reports no symbols on all 5 binaries.
   - Confirm `strings` contains no leaked paths, usernames, or answer plaintext.
4. **End-to-End Solve in Isolation**:
   - Run the complete solve sequence inside `/tmp/cartographer-dist/` as an untrusted solver would.
   - Confirm every binary runs without errors, creates `.cartographer_state`, and validates the final flag.
5. Clean up `/tmp/cartographer-dist`.

---

## 5. Final Report Requirements

At the end of your session, provide:
1. An explicit **GO / NO-GO** statement for the live hackathon.
2. Complete table of all files in the final Drive-ready `cartographer/` folder with sizes and SHA256 hashes.
3. Complete table of all repository deliverables (`SOLVE_PATH_PRIVATE.md`, `HINTS.md`, `TRYHACKME_ROOM_TEXT.md`, `logs/PHASE_FINAL_LOG.md`).
