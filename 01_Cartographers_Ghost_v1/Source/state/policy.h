#ifndef CARTO_POLICY_H
#define CARTO_POLICY_H

/*
 * Policy data consumed by the state library.
 * The threshold values below were CALIBRATED in Phase FINAL; they stood as
 * Phase-0 placeholders until then.  Rationale, the cadence table and both
 * measured runs: SOLVE_PATH_PRIVATE.md section 5.  The decoy table contents
 * were registered by Phases 2-4 as each stage's decoy appeared.
 */

#include "state.h"

/* CALIBRATED (was a Phase-0 placeholder): time-from-first-run below this
 * (per stage), in seconds, counts as "reached the stage too fast".  These
 * thresholds only select a presentation variant -- every stage suite proves
 * the key/verdict is bit-identical across escalated and plain states. */
#define CARTO_T_FAST_SEC_DEFAULT 3u
static const uint32_t carto_t_fast_sec[CARTO_NUM_STAGES] = { 3u, 3u, 20u, 60u, 300u };

/* CALIBRATED (was a Phase-0 placeholder): inter-arrival stddev (ms) at or
 * below this counts as "suspiciously uniform timing" (the scripted-loop
 * tell).  1500.0 -> 150.0: the old floor forced a ~1.5 s average Stage-3
 * query spacing and cost ~128 min on that stage alone.  150.0 still fires on
 * a fixed sleep(0.05) loop (stddev ~4 ms) and on a fixed sleep(1) loop
 * (stddev ~10 ms), while a genuinely-varying solver cadence sits far above it
 * (the calibrated run's pacing measured ~400 ms).  This constant also gates
 * the Stage-3 poison, so it is a real calibration lever, not presentation. */
#define CARTO_STDDEV_LOW_MS 150.0

/* The timing check needs at least this many inter-arrival deltas to be
 * meaningful; below this it is inconclusive and never flags. */
#define CARTO_MIN_TIMING_DELTAS 4

typedef struct {
    int         stage;
    const char *flag;
    uint32_t    branch;
} carto_decoy_entry_t;

/* Real decoy registry.  The lookup/storage mechanism is untouched Phase-0
 * code; only the contents change as stages register their discoverable
 * decoys (Phase 2+).  Branch ids are 1-based and callers map branch B to the
 * per-stage state bit (1u << (B - 1)).
 *
 * Stage 1 (Phase 2): minted from the ".rodata forgotten debug checkpoint"
 * constant inside stage1_vm -- see logs/PHASE_2_LOG.md (internal).
 * Stage 2 (Phase 3): minted from the naive whole-image LSB layer at the head
 * of survey_frame.png -- see logs/PHASE_3_LOG.md (internal).
 */
static const carto_decoy_entry_t carto_decoy_table[] = {
    { 1, "CARTO{12f8a367b772817e805725e7292acfb6}", 1u },
    { 2, "CARTO{twice_over_the_coast_before_the_interior}", 1u },
    { 3, "CARTO{b27692a0d5f63d4f1a0c3fb79afbf81b}", 1u },
    { 4, "CARTO{dba9e10a73bc8633ccc1875207c075e1}", 1u },
};
#define CARTO_DECOY_TABLE_LEN 4

#endif /* CARTO_POLICY_H */
