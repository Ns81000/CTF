THE CARTOGRAPHER'S GHOST
=======================

A five-stage offline reversing / crypto challenge.


WHAT THIS IS
------------
A folder of five small programs and two data files. One folder of the survey
is already open; the rest of it has to be read out of them. Everything runs on
your own machine. There is no server, no network access, and no root needed.


REQUIREMENTS
------------
Linux, or Windows with WSL2. 64-bit x86-64.

The programs are statically linked, so nothing needs to be installed for them
to run. You will probably want the ordinary reversing/parsing tools of your
choice (file, strings, xxd, nm, objdump, readelf, a hex editor, gdb, python3,
exiftool, ImageMagick). Nothing is required: the survey can be read with less.

Some steps are slow on purpose. Nothing is timed out and nothing expires.

One more thing about pace: the programs in this folder were written for a
person at a keyboard, not for a loop. If you script a stage, let the gaps
between your requests vary the way a person's do -- a run that asks its
questions at a perfectly even interval is not the same thing as a careful
reader, and the survey knows the difference even though it will never say so.


HOW TO START
------------
Unpack this folder somewhere you can write to, then open a terminal IN the
folder you unpacked (the one that contains this file and the five subfolders)
and run:

    ./stage0_start/stage0_start

Read what it prints. It hands you the first token outright.

Run every later program from THAT SAME FOLDER, the same way -- the path in
front of each program is part of how it is meant to be called:

    ./stage1_vm/stage1_vm
    ./stage2_stego/stage2_stego
    ./stage3_oracle/oracle
    ./stage4_assembly/validate

The programs with no arguments explain themselves. Run each one with no
arguments first before you try anything clever.

If a program is not executable after unpacking, run:  chmod +x */[a-z]*


WHAT YOU ARE LOOKING FOR
------------------------
Short strings shaped like this:

    CARTO{lowercase_letters_digits_and_underscores}

Uppercase, braces, no spaces, no other punctuation. Tokens that look like that
but are not the real ones exist in this survey; the survey will tell you what
it thinks of each one you hand it, so hand them over and watch what it says.


SUBMITTING ANSWERS (TryHackMe)
------------------------------
Two of the strings you find are scored answers. Submit each exactly as printed,
including the CARTO{ } wrapper, with no quotes and no trailing spaces:

    Stage 0 token   -> the first answer field
    Final title     -> the final answer field

Everything else you find along the way is a checkpoint, not an answer: keep it,
because later stages are built out of earlier ones, but do not expect a
checkpoint to be accepted as a final answer.

TryHackMe answer fields are literal string comparisons. If an answer is
rejected, check for a trailing space or a missing brace before anything else.


IF YOU GET STUCK
----------------
The folder you are reading was written in order, and it says so. Every stage
tells you what the next one is going to want, in the words it uses. Two
sentences in this survey are worth more than any tool: the note on the back of
the sheet, and the verse in the last program.

Nothing here is a guessing game. Every obstacle has a definite answer that a
careful reader can reach without luck.