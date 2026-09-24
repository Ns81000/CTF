# TRYHACKME ROOM TEXT

## Room title

The Cartographer's Ghost

## Flavour

The survey office closed in 1979 and the map was never finished.  The
surveyor's instruments are still on the desk, the drawer is full of
drafts, and the field notes insist the coast was drawn twice.  Finish
the survey.

This is an offline, human-only challenge: download the package, run it
on Linux or WSL2, sit at a terminal, and work through six instruments
in order.  There is no time limit.  The tools were written for a person
at a keyboard, and they notice when they are driven.

## The two scored questions

1. **The surveyor's first entry.**  The ledger opens with a line it
   reads back every time.  Submit it exactly.

   Answer: `CARTO{the_survey_reopens_tonight}`

2. **The finished title.**  The title block takes exactly one assembled
   title.  Submit it exactly.

   Answer: `CARTO{3821ad004ab30263_e509312ae8a2e0ad_145e1d23feac3932_rust_blooms_under_tin_roofs}`

## One native hint

The plate reads the room, not a pipe.

## Difficulty and tags

Difficulty: Insane.  Tags: ctf, reverse-engineering, forensics,
cryptanalysis, behaviour-gates, marathon.

## Download and run

[DRIVE LINK PLACEHOLDER -- attach cartographer.zip from the organiser
package]

SHA-256 of the published zip: see MANIFEST.sha256 in the organiser
package.

Unzip anywhere, open a terminal in the package folder, and begin with
`./stage0_ledger/ledger`.  Run every tool from the package root.
A marathon; no time limit.
