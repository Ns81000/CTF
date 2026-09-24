/*
 * state_policy.c -- the cartographer v2 behaviour engine.
 *
 * Everything a tool knows about how it is being driven comes from here: the
 * shape of the interaction ring (spacing, spread, rate, terminal presence),
 * the cumulative counters, and the chain.  Gate bits are never trusted from
 * the record: they are recomputed from the evidence, and evidence the record
 * cannot justify is dropped without a word.
 */
#define _POSIX_C_SOURCE 200809L

#include "state.h"
#include "policy.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

/* ---- ring window -------------------------------------------------------- */

int carto_ring_window(const carto_state_t *st, uint64_t ts[CARTO_RING_SIZE],
                      uint8_t stage[CARTO_RING_SIZE],
                      uint8_t op[CARTO_RING_SIZE],
                      uint32_t aux[CARTO_RING_SIZE])
{
    uint32_t occupied = (st->ring_count < CARTO_RING_SIZE)
                      ? st->ring_count : CARTO_RING_SIZE;
    int start;
    uint32_t i;

    start = ((int)st->ring_head - (int)occupied + CARTO_RING_SIZE)
            % CARTO_RING_SIZE;
    for (i = 0; i < occupied; i++) {
        int idx = (start + (int)i) % CARTO_RING_SIZE;
        const uint8_t *e = st->ring[idx];
        uint64_t t = 0;
        int b;
        for (b = 7; b >= 0; b--)
            t = (t << 8) | (uint64_t)e[b];
        ts[i] = t;
        stage[i] = e[CARTO_RING_OFF_STAGE];
        op[i] = e[CARTO_RING_OFF_OP];
        aux[i] = (uint32_t)e[CARTO_RING_OFF_AUX] |
                 ((uint32_t)e[CARTO_RING_OFF_AUX + 1] << 8) |
                 ((uint32_t)e[CARTO_RING_OFF_AUX + 2] << 16) |
                 ((uint32_t)e[CARTO_RING_OFF_AUX + 3] << 24);
    }
    return (int)occupied;
}

/* ---- statistics --------------------------------------------------------- */

static int cmp_u64(const void *a, const void *b)
{
    uint64_t x = *(const uint64_t *)a, y = *(const uint64_t *)b;
    if (x < y) return -1;
    if (x > y) return 1;
    return 0;
}

static uint16_t aux_fig(uint32_t aux)
{
    return (uint16_t)((aux & CARTO_AUX_FIG_MASK) >> CARTO_AUX_FIG_SHIFT);
}

void carto_stats_compute(const carto_state_t *st, uint64_t now_ms,
                         carto_stats_t *out)
{
    uint64_t ts[CARTO_RING_SIZE];
    uint8_t stage[CARTO_RING_SIZE], op[CARTO_RING_SIZE];
    uint32_t aux[CARTO_RING_SIZE];
    uint64_t gaps[CARTO_RING_SIZE];
    int n, i, ng = 0;
    uint32_t tty = 0;

    memset(out, 0, sizeof *out);
    n = carto_ring_window(st, ts, stage, op, aux);
    out->entries = (uint32_t)n;
    out->cumulative_entries = st->ring_count;
    out->distinct_figures = st->distinct_figures;
    out->span_ms = carto_time_since_first_run_ms(st, now_ms);
    out->first_contact_ms = (n > 0) ? ts[0] : st->first_run_ms;
    if (n <= 0)
        return;

    for (i = 1; i < n; i++)
        gaps[ng++] = (ts[i] > ts[i - 1]) ? (ts[i] - ts[i - 1]) : 0;

    for (i = 0; i < n; i++) {
        if ((aux[i] & (CARTO_AUX_TTY_IN | CARTO_AUX_TTY_OUT)) ==
            (CARTO_AUX_TTY_IN | CARTO_AUX_TTY_OUT))
            tty++;
    }
    out->tty_fraction = (double)tty / (double)n;
    out->pipe_fraction = 1.0 - out->tty_fraction;

    if (ng > 0) {
        uint64_t sorted[CARTO_RING_SIZE];
        double sum = 0.0, var = 0.0;
        uint64_t burst = carto_burst_gap_ms();
        for (i = 0; i < ng; i++) {
            sum += (double)gaps[i];
            sorted[i] = gaps[i];
            if (gaps[i] < burst)
                out->burst_ratio += 1.0;
        }
        out->burst_ratio /= (double)ng;
        out->mean_ms = sum / (double)ng;
        for (i = 0; i < ng; i++) {
            double d = (double)gaps[i] - out->mean_ms;
            var += d * d;
        }
        var /= (double)ng;
        out->stddev_ms = (var > 0.0) ? sqrt(var) : 0.0;
        qsort(sorted, (size_t)ng, sizeof(uint64_t), cmp_u64);
        out->median_ms = (ng % 2) ? (double)sorted[ng / 2]
            : ((double)sorted[ng / 2 - 1] + (double)sorted[ng / 2]) / 2.0;
        out->iqr_ms = (double)sorted[(ng - 1) * 3 / 4]
                    - (double)sorted[(ng - 1) / 4];
        for (i = 1; i < ng; i++) {
            uint64_t a = gaps[i - 1], b = gaps[i];
            uint64_t d = (a > b) ? (a - b) : (b - a);
            if (d > 100ull)
                out->nonuniform_pairs++;
        }
    }

    /* peak rate: the most interactions landing inside one rate window */
    {
        uint64_t win = carto_rate_window_ms();
        for (i = 0; i < n; i++) {
            uint32_t c = 0;
            int j;
            for (j = i; j < n; j++) {
                if (ts[j] - ts[i] <= win)
                    c++;
                else
                    break;
            }
            if (c > out->max_rate_per_min)
                out->max_rate_per_min = c;
        }
    }

    /* how often a figure repeats the one before it */
    {
        uint16_t prev = 0;
        int have_prev = 0;
        int nq = 0;
        for (i = 0; i < n; i++) {
            if (op[i] != CARTO_OP_QUERY)
                continue;
            nq++;
            if (have_prev && aux_fig(aux[i]) == prev)
                out->duplicate_query_ratio += 1.0;
            prev = aux_fig(aux[i]);
            have_prev = 1;
        }
        out->queries = (uint32_t)nq;
        if (nq > 1)
            out->duplicate_query_ratio /= (double)(nq - 1);
    }

    /* stage-visit order: entropy of the transition alphabet, plus how often
     * consecutive interactions move between stages */
    {
        uint32_t counts[256];
        int ntrans = 0;
        memset(counts, 0, sizeof counts);
        for (i = 1; i < n; i++) {
            counts[((size_t)stage[i - 1] * 7u + (size_t)stage[i]) & 0xFFu]++;
            ntrans++;
            if (stage[i] != stage[i - 1])
                out->interleaved_stage_ratio += 1.0;
        }
        if (ntrans > 0) {
            double entropy = 0.0;
            out->interleaved_stage_ratio /= (double)ntrans;
            for (i = 0; i < 256; i++) {
                if (counts[i]) {
                    double p = (double)counts[i] / (double)ntrans;
                    entropy -= p * (log(p) / log(2.0));
                }
            }
            out->stage_order_entropy = entropy;
        }
    }
}

/* ---- gates -------------------------------------------------------------- */

int carto_gate_human(const carto_state_t *st, const carto_stats_t *s)
{
    (void)st;
    if (s->entries < 4)
        return 0;
    if (s->tty_fraction * 100.0 < (double)CARTO_HUMAN_TTY_NUM)
        return 0;
    if (s->stddev_ms < carto_spread_need_ms())
        return 0;
    if (s->max_rate_per_min > CARTO_HUMAN_RATE_MAX)
        return 0;
    if (s->duplicate_query_ratio * 100.0 > (double)CARTO_HUMAN_DUP_NUM)
        return 0;
    return 1;
}

int carto_gate_volume(const carto_state_t *st, const carto_stats_t *s)
{
    uint64_t need;

    (void)st; /* the span already lives in the statistics */
    if (s->cumulative_entries < CARTO_VOL_MIN_ENTRIES)
        return 0;
    if (s->distinct_figures < CARTO_VOL_MIN_FIGURES)
        return 0;
    need = carto_span_need_ms();
    if (s->span_ms < need)
        return 0;
    return 1;
}

/* The interactions must move forward through the tower: a record in
 * which the work jumps back to an earlier stage, or skips required stages,
 * is not a record of the tower being climbed. */
int carto_gate_chain(const carto_state_t *st)
{
    uint64_t ts[CARTO_RING_SIZE];
    uint8_t stage[CARTO_RING_SIZE], op[CARTO_RING_SIZE];
    uint32_t aux[CARTO_RING_SIZE];
    int i, n, s;
    int max_stage = 0;
    int seen_stage[CARTO_NUM_STAGES] = {0};

    n = carto_ring_window(st, ts, stage, op, aux);
    if (n <= 0)
        return 0;

    for (i = 0; i < n; i++) {
        if (i > 0 && stage[i] < stage[i - 1])
            return 0;
        if (stage[i] < CARTO_NUM_STAGES)
            seen_stage[stage[i]] = 1;
        if (stage[i] > max_stage)
            max_stage = stage[i];
    }

    if (st->ring_count <= CARTO_RING_SIZE) {
        /* When the full history fits in the ring, stage 0 must lead and
         * each required stage up to max_stage must have occurred. */
        if (stage[0] != 0)
            return 0;
        for (s = 0; s <= max_stage; s++) {
            if (!seen_stage[s])
                return 0;
        }
    } else {
        /* When ring has wrapped, cumulative attempt counts or the ring
         * must show that each required stage up to max_stage occurred. */
        for (s = 0; s <= max_stage; s++) {
            if (!seen_stage[s] && st->attempt_count[s] == 0)
                return 0;
        }
    }
    return 1;
}

/* ---- evidence reconciliation ------------------------------------------- */

/* Every evidence bit has to be justified by something the record actually
 * contains; anything else is cleared.  The flag bits that a tool earns by
 * doing work are derived from the ring too, so writing them into the file by
 * hand does not keep them. */
void carto_recompute_gates(carto_state_t *st, uint64_t now_ms)
{
    carto_stats_t s;
    uint64_t ts[CARTO_RING_SIZE];
    uint8_t stage[CARTO_RING_SIZE], op[CARTO_RING_SIZE];
    uint32_t aux[CARTO_RING_SIZE];
    uint32_t derived = 0;
    int n, i, s_i;
    int tty_seen = 0, press_seen = 0, decoy_seen = 0, noarg_seen = 0;
    int reveal_seen = 0, query_seen = 0, verify_seen = 0, tally_seen = 0;

    carto_stats_compute(st, now_ms, &s);
    n = carto_ring_window(st, ts, stage, op, aux);
    for (i = 0; i < n; i++) {
        if ((aux[i] & (CARTO_AUX_TTY_IN | CARTO_AUX_TTY_OUT)) ==
            (CARTO_AUX_TTY_IN | CARTO_AUX_TTY_OUT))
            tty_seen = 1;
        if (op[i] == CARTO_OP_PRESS)
            press_seen = 1;
        if (op[i] == CARTO_OP_QUERY)
            query_seen = 1;
        if (op[i] == CARTO_OP_NOARG)
            noarg_seen = 1;
        if (op[i] == CARTO_OP_REVEAL)
            reveal_seen = 1;
        if (op[i] == CARTO_OP_VERIFY)
            verify_seen = 1;
        if (op[i] == CARTO_OP_TALLY)
            tally_seen = 1;
        if (((aux[i] & CARTO_AUX_LANE_MASK) >> CARTO_AUX_LANE_SHIFT) == 1u)
            decoy_seen = 1;
    }
    if (tty_seen)
        derived |= CARTO_GB_TTY;
    if (press_seen)
        derived |= CARTO_GB_PRESS;
    if (decoy_seen)
        derived |= CARTO_GB_DECOY;
    if (query_seen)
        derived |= CARTO_GB_TTY; /* a query is only meaningful from a hand */
    (void)noarg_seen; (void)reveal_seen; (void)verify_seen; (void)tally_seen;
    if (carto_gate_human(st, &s))
        derived |= CARTO_GB_HUMAN;
    if (carto_gate_volume(st, &s))
        derived |= CARTO_GB_VOLUME;
    if (carto_gate_chain(st))
        derived |= CARTO_GB_CHAIN;
    if (st->debugger_flag)
        derived |= CARTO_GB_DEBUG;

    for (s_i = 0; s_i < CARTO_NUM_STAGES; s_i++) {
        uint32_t want = derived;
        /* Bits that are evidence of a *later* stage's work still live in the
         * stage slot that earned them, so the reconciliation is shared: a
         * slot keeps only what the record can justify, whatever earned it. */
        st->gate_state[s_i] = want;
    }
    for (s_i = 0; s_i < CARTO_NUM_STAGES; s_i++)
        st->gate_state[s_i] |= (carto_gate_tag(st, s_i) << CARTO_GTAG_SHIFT);
}

uint32_t carto_gate_witness(const carto_state_t *st, int stage)
{
    uint32_t tag = carto_gate_tag(st, stage);
    /* a stable challenge/response: the low half of the tag mixed with the
     * stage slot and the cumulative interaction count */
    uint32_t v = (tag ^ (uint32_t)(stage * 0x9E3779B1u)
                  ^ (uint32_t)st->ring_count);
    if (v == 0)
        v = 1;
    return v;
}

/* ---- test-build time hook ---------------------------------------------- */

#ifdef CARTO_TEST_TIME_SCALE_ENABLE
uint64_t carto_time_scale(void)
{
    const char *e = getenv("CARTO_TEST_TIME_SCALE");
    long v;
    if (!e || !*e)
        return 1;
    v = strtol(e, NULL, 10);
    if (v < 1 || v > 1000000)
        return 1;
    return (uint64_t)v;
}
#endif

uint64_t carto_span_need_ms(void)
{
    uint64_t d = CARTO_VOL_MIN_SPAN_MS / carto_time_scale();
    // cppcheck-suppress knownConditionTrueFalse
    return d ? d : 1;
}

uint64_t carto_rate_window_ms(void)
{
    uint64_t d = 60000ull / carto_time_scale();
    // cppcheck-suppress knownConditionTrueFalse
    return d ? d : 1;
}

uint64_t carto_burst_gap_ms(void)
{
    uint64_t d = (uint64_t)CARTO_BURST_GAP_MS / carto_time_scale();
    // cppcheck-suppress knownConditionTrueFalse
    return d ? d : 1;
}

double carto_spread_need_ms(void)
{
    double d = CARTO_HUMAN_STDDEV_MIN_MS / (double)carto_time_scale();
    return d > 1e-6 ? d : 1e-6;
}
