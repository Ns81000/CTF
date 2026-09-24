# HINTS — "The Cartographer's Ghost"

**Organizer copy. Hand these out manually, one at a time, only when asked.**
Exactly five. Ordered easiest to *act on* first (hint 1 costs the solver
nothing to try; hint 5 requires them to already be holding the right pieces).
Each one points at a stage without naming a stage or an answer, and none of
them replaces the work.

---

**HINT 1 — before anything else**

Every tool in this survey describes its own answer when you run it with no
arguments, from the folder that holds it. Read all five descriptions before you
read a single byte of any of them. One of the five descriptions contains a poem
and two of them contain a trap; the descriptions know that.

---

**HINT 2 — the engine**

The engine prints more than the thing you want. It prints a ledger of its own
registers and the exact number of instructions it executed. Both are checkable:
build your own interpreter, and if your ledger and your step count match the
engine's, you have the right constant. If two of the three families of constant
you find look alike, they are meant to — only one of them survives the next
stage's arithmetic.

---

**HINT 3 — the sheet**

The sheet's own back page spells the sweep out in plain words: the stride comes
from the first sixteen bytes of the survey key read little-endian, one mark of
blue is inked every stride of marks from the swept start, and the *larger* side
of each byte is written first. The press is not on the sheet at all — it is the
whole mark left on the tape, raw, and a convenient text-reading flag will
quietly re-encode it and lie to you.

---

**HINT 4 — the oracle**

The oracle's round function is deliberately weak in eight specific places: if
two figures differ in exactly one byte of one 32-bit half, the round function
output difference cancels about one time in four. Collect pairs in groups — same
half, same byte — and let them vote; the true byte is the one that keeps
agreeing. If your answers stop agreeing with each other, stop and look at how
*evenly* you have been asking: a machine that asks at a perfectly constant
interval gets a well-formed dataset from the wrong key, and nothing will tell
you so except comparing a scripted run against a hand-timed one.

---

**HINT 5 — the title block**

The verse gives you two orders at once: the order the survey was made in, and
the order the title is written in, and it says plainly that they are not the
same order. Take "seats" literally — head, middle, last — not "first", "last"
and "between". Then skin the sheet: the reading goes in without its frame. The
near-miss is the engine's own token, and it is the wrong half of the wrong
thing.
