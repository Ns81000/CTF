# "The Cartographer's Ghost" — TryHackMe room text

**Organizer copy.** Drop the pieces below straight into the room editor. The
answer values are the two scored flags; everything else in the survey is an
in-challenge checkpoint and is deliberately *not* a TryHackMe answer field.

---

## Room title

**The Cartographer's Ghost**

## Room description (flavor text)

> They say the old surveyor drew his final map the night the fog took him: no
> body, no farewell. Only his study, still warm, and a ledger lying open on the
> desk, a page waiting for a hand.
>
> The survey is still in the drawer. Five pieces of it, and none of them a map
> with the figure drawn on it plainly. He drew in order — coast first, interior
> last — and he kept drawing after his hand stopped.
>
> Finish the survey.

## Difficulty / tags

Medium. `reversing`, `crypto`, `steganography`, `forensics`.

## Hosting note

This is a **download-and-run** room. No target machine, no network, no boot-2-
root. Publish the Google Drive link below and let solvers work entirely on their
own machine (Linux or WSL2, x86-64).

**Google Drive link (fill in before publishing):**

    <<< GOOGLE DRIVE LINK HERE >>>

## Task 1 — Orientation

> Download the survey from the link above. Read `README_FOR_SOLVER.txt` first.
> Run `./stage0_start/stage0_start` from the folder that holds it.
>
> **Q1. What token does the ledger inked on your first entry?**
>
> **Answer:** `CARTO{first_ink_in_the_ledger}`

## Task 2 — The title block

> The survey ends in a title block. Assemble the three inks it names, in the
> order the verse gives them, and lay the finished title in the block.
>
> **Q2. What is the assembled title?**
>
> **Answer:** `CARTO{73070925a159f9e2_a5d66f1b2b5f596e_no_figure_sits_in_every_pixel}`

Only these two fields are scored. The Stage-1 token, the Stage-2 checkpoint
token and the Stage-2 reading are checkpoints the survey itself validates; do
not accept them as final answers.

## Native TryHackMe hint (separate from the organizer HINTS.md)

> The survey tells you its own answers if you let it talk. Every tool here
> describes its input format when you run it with no arguments — including the
> one at the end, whose description is a verse. Two of those descriptions are
> traps aimed at people who skim. Read all five before you read any bytes.

## Flag submission format

Exactly as printed, braces included, no quotes, no trailing whitespace:
`CARTO{[a-z0-9_]+}`. Both answers are lowercase, underscore-separated and
case-sensitive.

---

## Organizer notes (do not publish)

- Scored answers: the Stage-0 token and the assembled Stage-4 title. Rationale
  in `SOLVE_PATH_PRIVATE.md` section 6: the intermediate tokens are
  format-valid even on the decoy and debugger paths, so scoring them would
  reject a decoy instantly and collapse the 1–1.5 h trap.
- The challenge is fully offline; the only file it ever writes is
  `.cartographer_state` in its own folder.
- Expected pacing and both measured calibration runs: `SOLVE_PATH_PRIVATE.md`
  section 5.
