#ifndef CARTO_POLICY_H
#define CARTO_POLICY_H

#include <stdint.h>

#include "state.h"

/* ---- interaction ring: op codes ---------------------------------------- */
#define CARTO_OP_NONE    0u
#define CARTO_OP_CREATE  1u   /* first state creation                          */
#define CARTO_OP_NOARG   2u   /* tool invoked with no arguments                */
#define CARTO_OP_INVOKE  3u   /* tool invoked to do work                       */
#define CARTO_OP_REVEAL  4u   /* a reveal/peek request                         */
#define CARTO_OP_QUERY   5u   /* oracle figure submitted                       */
#define CARTO_OP_VERIFY  6u   /* a candidate string handed to a checker        */
#define CARTO_OP_PRESS   7u   /* press-mode self-consistency check             */
#define CARTO_OP_TALLY   8u   /* tally witness requested                       */
#define CARTO_OP_RESET   9u   /* a silent state reset happened                 */

/* ---- ring aux bit assignment ------------------------------------------- */
/*  bit 0        stdin was a terminal
 *  bit 1        stdout was a terminal
 *  bits 2..7    variant/profile id (0 = none)
 *  bits 8..15   side channel byte (lane id / witness byte)
 *  bits 16..31  figure fingerprint (oracle) / candidate fingerprint
 */
#define CARTO_AUX_TTY_IN   0x00000001u
#define CARTO_AUX_TTY_OUT  0x00000002u
#define CARTO_AUX_VARIANT_SHIFT 2
#define CARTO_AUX_VARIANT_MASK  0x000000FCu
#define CARTO_AUX_LANE_SHIFT    8
#define CARTO_AUX_LANE_MASK     0x0000FF00u
#define CARTO_AUX_FIG_SHIFT     16
#define CARTO_AUX_FIG_MASK      0xFFFF0000u

/* Interaction ops that a tool records for the next tool to read. */
#define CARTO_OP_BEARING_LO 10u  /* aux = low 32 bits of the bearing      */
#define CARTO_OP_BEARING_HI 11u  /* aux = high 32 bits of the bearing     */

/* ---- gate evidence bits stored in gate_state[stage] -------------------- */
#define CARTO_GB_HUMAN   0x00000001u
#define CARTO_GB_VOLUME  0x00000002u
#define CARTO_GB_CHAIN   0x00000004u
#define CARTO_GB_TTY     0x00000008u
#define CARTO_GB_PRESS   0x00000010u
#define CARTO_GB_DECOY   0x00000020u
#define CARTO_GB_DEBUG   0x00000040u
#define CARTO_GB_MASK    0x0000007Fu
/* bits 16..31 of gate_state[i] carry this stage's chain tag. */
#define CARTO_GTAG_SHIFT 16
#define CARTO_GTAG_MASK  0xFFFF0000u

/* ---- the behaviour dials (durations in ms unless noted) ---------------- */
#define CARTO_HUMAN_TTY_NUM        60u   /* tty_fraction >= 60/100            */
#define CARTO_HUMAN_STDDEV_MIN_MS  150.0 /* spread of inter-entry gaps        */
#define CARTO_HUMAN_RATE_MAX       40u   /* entries in any 60 s window        */
#define CARTO_HUMAN_DUP_NUM        35u   /* duplicate_query_ratio <= 35/100   */
#define CARTO_VOL_MIN_ENTRIES      6000u /* ring appends, cumulative          */
#define CARTO_VOL_MIN_FIGURES      3000u /* distinct figures answered         */
#define CARTO_VOL_MIN_SPAN_MS      (45ull * 60ull * 1000ull)
#define CARTO_BURST_GAP_MS         200u  /* a gap under this counts as a burst */

/* The test-build time hook.  Compiled in ONLY when the build passes
 * -DCARTO_TEST_TIME_SCALE_ENABLE (see Makefile); shipped artefacts never
 * contain the variable name.  It divides every *duration* dial -- the sitting
 * that the volume gate asks for, the window the rate is measured over, and
 * the spread the behaviour gate asks for -- so a calibrated budget can be
 * exercised in seconds.  Counts are never scaled. */
#ifdef CARTO_TEST_TIME_SCALE_ENABLE
uint64_t carto_time_scale(void);
#else
#define carto_time_scale() 1ull
#endif

uint64_t carto_span_need_ms(void);
uint64_t carto_rate_window_ms(void);
uint64_t carto_burst_gap_ms(void);
double   carto_spread_need_ms(void);

/* ---- behaviour statistics ---------------------------------------------- */
typedef struct {
    uint32_t entries;              /* entries in the ring window             */
    uint32_t cumulative_entries;   /* appends since the record was created   */
    uint64_t span_ms;              /* now - first_run_ms                     */
    uint32_t distinct_figures;     /* saturating distinct-figure counter     */
    double   mean_ms;
    double   median_ms;
    double   stddev_ms;
    double   iqr_ms;
    double   burst_ratio;
    uint32_t max_rate_per_min;
    double   tty_fraction;
    double   pipe_fraction;
    uint64_t first_contact_ms;
    double   stage_order_entropy;
    double   duplicate_query_ratio;
    double   interleaved_stage_ratio;
    uint32_t queries;              /* query-op entries in the window         */
    uint32_t nonuniform_pairs;     /* gaps that differ from their neighbour   */
} carto_stats_t;

void carto_stats_compute(const carto_state_t *st, uint64_t now_ms,
                         carto_stats_t *out);

/* Gate evaluation: 1 = satisfied, 0 = not.  Recomputed, never trusted. */
int carto_gate_human(const carto_state_t *st, const carto_stats_t *s);
int carto_gate_volume(const carto_state_t *st, const carto_stats_t *s);
int carto_gate_chain(const carto_state_t *st);

/* Drops every evidence bit that recomputation cannot justify. */
void carto_recompute_gates(carto_state_t *st, uint64_t now_ms);

/* Gate witness: a 32-bit challenge/response derived from the stage chain
 * tag.  Tools print it when their stage gate holds.  Never an ink. */
uint32_t carto_gate_witness(const carto_state_t *st, int stage);

/* The ring window, ordered oldest first. */
int carto_ring_window(const carto_state_t *st, uint64_t ts[CARTO_RING_SIZE],
                      uint8_t stage[CARTO_RING_SIZE],
                      uint8_t op[CARTO_RING_SIZE],
                      uint32_t aux[CARTO_RING_SIZE]);

#endif /* CARTO_POLICY_H */
