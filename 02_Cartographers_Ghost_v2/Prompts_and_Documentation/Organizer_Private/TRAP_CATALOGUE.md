# TRAP CATALOGUE — one row per trap: id, stage, trigger, what the solver
# sees, dead-end cost, recovery route, fairness argument.

| id | stage | trigger | what the solver sees | dead-end cost | recovery route | fairness argument |
|---|---|---|---|---|---|---|
| T-LEDGER-REPLAY | 0 | re-running the ledger | the same line, no new information | minutes, and a warmer record | keep playing with it; the record needs the visits | the desk says it keeps one record and does not care |
| T-ENGINE-DECOY | 1 | handing the older index key | corroboration branch, its own bearing | 60-120 min of tracing against a wrong certificate | the newer image's two profiles land on one ink | the older certificate never claims to be the survey's |
| T-ENGINE-DEBUG | 1 | running under a debugger | the ptrace branch, different traces | an afternoon of false landmarks | run it clean, then compare | the usage names the bench honest-line |
| T-NOTES-TRAP | 1 | trusting profile.notes arithmetic | margin numbers that solve to nothing | an hour of arithmetic | the image, not the margin | the notes say they were superseded |
| T-EXIFTOOL-133 | 2 | `exiftool -b -Comment` for the press | 133 bytes of hex text, not 56 bytes | re-cutting the lane with a hex dictionary | raw `prES` read or `exiftool -v3` (both suite-asserted) | the sheet's press mode says where the press lives |
| T-FRAME-CONF | 2 | exact-LC vs LE16 framing confusion | 0x3000, a length that parses nowhere | an hour of re-deflate | the certificate of the lane: LE16 then the stream | the carriers_info rule in the generator is byte-exact |
| T-NAIVE | 2 | reading the first row's LSB lane | `CARTO{the_coast_was_drawn_twice}`, valid, wrong | a downstream round trip to disprove | the near-miss/real lanes with the real bearing | the first row is the shallow one; the sweep disagrees |
| T-NEARMISS | 2 | one parameter off the real lane | readable, plausible, never-a-flag text | the whole lane, then re-derivation | re-cut with the press as dictionary | the middle layer is documented as one-off bait |
| T-COLOUR | 2 | losing the ANSI colour bit in a pipe | a missing stroke in the revealed line | the reveal, then `--plain` | `--plain` prints that bit as a word | the tool states the rule in its own words |
| T-WIDTH | 2 | COLUMNS < 80 | a shorter line wanting a wider room | one re-run wide | 80 columns or wider | the line names the wider room |
| T-COLD | 3 | a sitting that is not a sitting | "still cold"; answers off K_cold | the sitting (45+ min), not the mechanism | sit: pace, vary, terminal, volume | every gate says in its own words what behaviour it wants |
| T-PIPE | 3 | stdin not a TTY | "fed through a pipe" | the sitting's answers, all cold-key | a terminal on stdin | stated in the oracle's own words |
| T-BURST | 3 | asking too fast | "run hot" | the sitting's answers, all poison-key | slow down, vary the gaps | stated in the oracle's own words |
| T-SMOOTH | 3 | metronome spacing | "gone smooth" | the sitting's answers, all poison-key | uneven, human gaps | stated in the oracle's own words |
| T-REPLAY | 3 | duplicated figures (>35%) | "too recently"; stale ring-cache answers | the sitting's answers, all poison-key | distinct, non-adjacent figures | discoverable by comparing two paced asks |
| T-YOUNG | 3 | sub-60 s record | "still warming" | the sitting | let the record age | stated in the oracle's own words |
| T-CASE | 3 | uppercase hex figures | answered under a different wrong key | the collection, silently wrong | the usage spells the shape it reads | the shape is stated truthfully, once |
| T-COLDCOLLECT | 3 | omitting the engine ink / handing the stage-1 token | K_cold answers, format-valid, wrong | the whole collection, silently wrong | hand the engine's sixteen lowercase characters | the usage names the ink by provenance |
| T-STALECACHE | 3 | repeating one figure twice in a row | the same stale-key answer twice | one pair, then doubt | never repeat; compare paced asks | documented internally; discoverable by comparison |
| T-DRAWER | 4 | `--decoy` and its open key | a valid-looking seal ink that fails at the block | the MITM on the wrong passes + the downstream trip | the stamp's own certificate, middle byte first | the drawer says it closed another room long ago |
| T-CLOSEBYTE | 4 | the certificate's 7 pinned bytes | 255 wrong closes hiding the one | 255 offers, then the face | the stamp answers each candidate once | the closing rule says all pairs must come back exactly |
| T-DRAFT | 5 | submitting the struck draft | the one refusal, indistinguishable | one downstream trip | the margin says the ink never dried | struck out, in the margin, quoted in full |
| T-NEARMISS-R | 5 | a reading one character off | the one refusal, indistinguishable | the whole assembly, re-verified | spell it out whole, from the frame | the riddle says "spelled out whole" |
| T-BAIT | 7 | trusting the drawer papers | a running draft printing a registered wrong title | the bait tax + one downstream trip | the notice at the head of every paper | the papers say they are drafts; the checksums are papers-only |
| T-NOTICE | all | deleting one notice file | the same notice opens the next file | nothing; the order stands | hand the package to a human | the notice is embedded in every artifact and binary |
