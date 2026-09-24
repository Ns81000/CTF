# PRAMBH v3 - COST MODEL (organizer-private, spec 5)

Every wall-clock number is PROJECTED from reduced-T measurement
(Appendix C.2); the audit session owns the full REAL runs (X6).

## chain dials (src/chain/chain_params.json)

| chain | S (bytes) | T (steps) | honest target (s) |
| --- | --- | --- | --- |
| chain1 | 536870912 | 7705630875 | 4500 |
| chain2 | 536870912 | 7705630875 | 4500 |
| door_decoy | 536870912 | 1232900940 | 720 |
| mirror | 536870912 | 410966980 | 240 |
| decoy_rom | 536870912 | 308225235 | 180 |

build-machine rate: 1712362.4 steps/s at S=536870912 (P2 calibration)

## measured per-step cost (reduced T)

- native 573.0 ns/step = cache-resident 743.6 ns + DRAM 0.0 ns
- emulated cartridge 2480.2 ns/step (the camouflage route)
- linearity deviation across T: 3.7% (cost per step is constant, so T x per-step projects soundly)

## projection math

  native chain #1   = 573.0 ns x 7705630875 = 4415 s (73.6 min)
  emulated chain #1 = 2480.2 ns x 7705630875 = 19112 s (5.3 h)

Honest ARCHIVE path: chain #1 + chain #2 = 2.5 h of sequenced work,
plus the seven 12-min decoy chamber walks a wrong reading invites,
plus the plate gates and the paper record.  A 4x faster core buys
about 3.1x rather than 4x, because 0 of 573 ns per step is a
DRAM round-trip: the walk is one sequential SHA-256 dependency
chain and nothing in it parallelises.  EVENT mode adds the
server's 4 h MIN_JOURNEY gate as a backstop, never as the floor.

Session 2 Audit Outcome: Full REAL-T native walks completed cleanly
and harvested into runs/:
- Chain #1 native walk: 5447 s (90.7 min) -> loom ink `de918c455c4b1d42`
- Chain #2 native walk: 5457 s (91.0 min) -> seal ink `43560fb33c8d0924`
- Cumulative sequential chain floor: 10,904 s = 3.03 h (honest native)
- Emulated cartridge floor: ~5.3 h (honest emulated)
- Server MIN_JOURNEY: 14,400 s = 4.0 h (enforced)

