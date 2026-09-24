/* Part 2: the behaviour engine -- statistics, gates and the rule that gate
 * evidence cannot outlive the record that justified it. */
#define _POSIX_C_SOURCE 200809L

#include "test_util.h"
#include "state.h"
#include "policy.h"

#include <fcntl.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define ROOT "/tmp/carto_p1"
#define SPATH ROOT "/" CARTO_STATE_NAME

extern int g_run;
extern int g_fail;

static int near(double a, double b, double tol)
{
    double d = a - b;
    if (d < 0)
        d = -d;
    return d <= tol;
}

static void ring_reset(carto_state_t *st, uint64_t base)
{
    memset(st, 0, sizeof *st);
    st->first_run_ms = base;
}

/* six interactions 100/200/300/400/500 ms apart */
static int test_stats_known_gaps(void)
{
    carto_state_t st;
    carto_stats_t s;
    uint64_t t = 1700000000000ull;

    ring_reset(&st, t);
    carto_ring_append(&st, t, 0, CARTO_OP_INVOKE, CARTO_AUX_TTY_IN | CARTO_AUX_TTY_OUT);
    carto_ring_append(&st, t + 200, 0, CARTO_OP_INVOKE, 0);
    carto_ring_append(&st, t + 500, 0, CARTO_OP_INVOKE, 0);
    carto_ring_append(&st, t + 900, 0, CARTO_OP_INVOKE, 0);
    carto_ring_append(&st, t + 1400, 0, CARTO_OP_INVOKE, 0);
    carto_ring_append(&st, t + 2000, 0, CARTO_OP_INVOKE, 0);
    carto_stats_compute(&st, t + 2000, &s);
    CHECK(near(s.mean_ms, 400.0, 0.001), "mean of 200..600");
    CHECK(near(s.median_ms, 400.0, 0.001), "median of 200..600");
    CHECK(near(s.stddev_ms, sqrt(20000.0), 0.01), "stddev of 200..600");
    CHECK(near(s.iqr_ms, 200.0, 0.001), "iqr of 200..600");
    CHECK(near(s.burst_ratio, 0.0, 0.001), "no gaps under the burst line");
    CHECK(s.max_rate_per_min == 6, "all six inside one minute");
    CHECK(s.entries == 6, "window size");
    return 0;
}

static int test_stats_burst_and_even_median(void)
{
    carto_state_t st;
    carto_stats_t s;
    uint64_t t = 1700000000000ull;
    int i;

    ring_reset(&st, t);
    for (i = 0; i < 11; i++)
        carto_ring_append(&st, t + (uint64_t)i * 50ull, 0, CARTO_OP_INVOKE, 0);
    carto_stats_compute(&st, t + 500, &s);
    CHECK(near(s.burst_ratio, 1.0, 0.001), "every gap is a burst gap");
    CHECK(near(s.median_ms, 50.0, 0.001), "median with an odd count");
    CHECK(s.max_rate_per_min == 11, "peak rate counts the window");
    return 0;
}

static int test_stats_duplicates_and_entropy(void)
{
    carto_state_t st;
    carto_stats_t s;
    uint64_t t = 1700000000000ull;
    int i;

    ring_reset(&st, t);
    for (i = 0; i < 6; i++) {
        static const uint32_t figs[6] = { 0x11u, 0x11u, 0x22u, 0x33u, 0x33u,
                                          0x44u };
        carto_ring_append(&st, t + (uint64_t)i * 700ull, 3, CARTO_OP_QUERY,
                          (figs[i] << CARTO_AUX_FIG_SHIFT) |
                          CARTO_AUX_TTY_IN | CARTO_AUX_TTY_OUT);
    }
    carto_stats_compute(&st, t + 4200, &s);
    CHECK(s.queries == 6, "query count");
    CHECK(near(s.duplicate_query_ratio, 2.0 / 5.0, 0.001),
          "two of five transitions repeat the previous figure");
    CHECK(near(s.stage_order_entropy, 0.0, 0.001),
          "one stage only: no order entropy");
    CHECK(near(s.tty_fraction, 1.0, 0.001), "all from a terminal");
    return 0;
}

static int test_gate_human_accepts_a_paced_hand(void)
{
    carto_state_t st;
    carto_stats_t s;
    uint64_t t = 1700000000000ull;
    int i;
    static const uint64_t gaps[12] = {
        420, 660, 250, 900, 310, 1200, 480, 730, 260, 1500, 540, 880
    };
    uint64_t cur = t;

    ring_reset(&st, t);
    carto_ring_append(&st, cur, 0, CARTO_OP_INVOKE,
                      CARTO_AUX_TTY_IN | CARTO_AUX_TTY_OUT);
    for (i = 0; i < 12; i++) {
        cur += gaps[i];
        carto_ring_append(&st, cur, i % 3, CARTO_OP_INVOKE,
                          CARTO_AUX_TTY_IN | CARTO_AUX_TTY_OUT);
    }
    carto_stats_compute(&st, cur, &s);
    CHECK(s.stddev_ms > 150.0, "spread is wide enough");
    CHECK(s.max_rate_per_min <= CARTO_HUMAN_RATE_MAX, "not a flood");
    CHECK(carto_gate_human(&st, &s) == 1, "a paced hand passes");
    return 0;
}

static int test_gate_human_rejects_robots(void)
{
    carto_state_t st;
    carto_stats_t s;
    uint64_t t = 1700000000000ull;
    int i;

    /* (a) uniform spacing */
    ring_reset(&st, t);
    for (i = 0; i < 12; i++)
        carto_ring_append(&st, t + (uint64_t)i * 500ull, 0, CARTO_OP_INVOKE,
                          CARTO_AUX_TTY_IN | CARTO_AUX_TTY_OUT);
    carto_stats_compute(&st, t + 6000, &s);
    CHECK(carto_gate_human(&st, &s) == 0, "metronome rejected");

    /* (b) no terminal */
    ring_reset(&st, t);
    for (i = 0; i < 12; i++)
        carto_ring_append(&st, t + (uint64_t)i * (uint64_t)(100 + 37 * i), 0,
                          CARTO_OP_INVOKE, 0);
    carto_stats_compute(&st, t + 9000, &s);
    CHECK(carto_gate_human(&st, &s) == 0, "pipes rejected");

    /* (c) flood */
    ring_reset(&st, t);
    for (i = 0; i < 64; i++)
        carto_ring_append(&st, t + (uint64_t)i * 900ull, 0, CARTO_OP_INVOKE,
                          CARTO_AUX_TTY_IN | CARTO_AUX_TTY_OUT);
    carto_stats_compute(&st, t + 60000, &s);
    CHECK(carto_gate_human(&st, &s) == 0, "60+ calls a minute rejected");

    /* (d) replaying one figure */
    ring_reset(&st, t);
    for (i = 0; i < 20; i++)
        carto_ring_append(&st, t + (uint64_t)i * (uint64_t)(300 + 61 * i), 3,
                          CARTO_OP_QUERY,
                          (0x1234u << CARTO_AUX_FIG_SHIFT) |
                          CARTO_AUX_TTY_IN | CARTO_AUX_TTY_OUT);
    carto_stats_compute(&st, t + 20000, &s);
    CHECK(carto_gate_human(&st, &s) == 0, "a replayed figure is a machine tell");
    return 0;
}

/* ---- volume and chain --------------------------------------------------- */

#define MINUTE (60ull * 1000ull)

static int test_gate_volume(void)
{
    carto_state_t st;
    carto_stats_t s;
    uint64_t now = 1700000000000ull;

    /* plenty of span, nowhere near enough work */
    ring_reset(&st, now - 46 * MINUTE);
    st.ring_count = 100;
    st.distinct_figures = 20;
    carto_stats_compute(&st, now, &s);
    CHECK(carto_gate_volume(&st, &s) == 0, "span alone is not work");

    /* plenty of work, nowhere near enough span */
    ring_reset(&st, now - 10 * MINUTE);
    st.ring_count = CARTO_VOL_MIN_ENTRIES + 1;
    st.distinct_figures = CARTO_VOL_MIN_FIGURES + 1;
    carto_stats_compute(&st, now, &s);
    CHECK(carto_gate_volume(&st, &s) == 0, "a burst is not a sitting");

    /* enough figures but not enough entries */
    ring_reset(&st, now - 46 * MINUTE);
    st.ring_count = CARTO_VOL_MIN_ENTRIES - 1;
    st.distinct_figures = CARTO_VOL_MIN_FIGURES + 1;
    carto_stats_compute(&st, now, &s);
    CHECK(carto_gate_volume(&st, &s) == 0, "entry count is checked");

    /* both counters and the span */
    ring_reset(&st, now - 46 * MINUTE);
    st.ring_count = CARTO_VOL_MIN_ENTRIES + 1;
    st.distinct_figures = CARTO_VOL_MIN_FIGURES + 1;
    carto_stats_compute(&st, now, &s);
    CHECK(carto_gate_volume(&st, &s) == 1, "a long sitting passes");

    /* distinct figure deduplication */
    {
        uint32_t init_dist;
        ring_reset(&st, now);
        st.distinct_figures = 10;
        carto_ring_append(&st, now, CARTO_STAGE_ORACLE, CARTO_OP_QUERY,
                          (0x1234u << CARTO_AUX_FIG_SHIFT));
        carto_note_figure(&st, 0x1234u);
        CHECK(st.distinct_figures == 11, "new figure increments distinct_figures");
        init_dist = st.distinct_figures;
        /* duplicate query with same figure in ring */
        carto_ring_append(&st, now + 1000, CARTO_STAGE_ORACLE, CARTO_OP_QUERY,
                          (0x1234u << CARTO_AUX_FIG_SHIFT));
        carto_note_figure(&st, 0x1234u);
        CHECK(st.distinct_figures == init_dist, "duplicate figure in ring does not increment");
        /* query with different figure */
        carto_ring_append(&st, now + 2000, CARTO_STAGE_ORACLE, CARTO_OP_QUERY,
                          (0x5678u << CARTO_AUX_FIG_SHIFT));
        carto_note_figure(&st, 0x5678u);
        CHECK(st.distinct_figures == init_dist + 1, "different figure increments");
    }
    return 0;
}

static int test_gate_chain_order(void)
{
    carto_state_t st;
    uint64_t t = 1700000000000ull;

    ring_reset(&st, t);
    carto_ring_append(&st, t, 0, CARTO_OP_INVOKE, 0);
    carto_ring_append(&st, t + 1000, 1, CARTO_OP_INVOKE, 0);
    carto_ring_append(&st, t + 2000, 2, CARTO_OP_INVOKE, 0);
    carto_ring_append(&st, t + 3000, 3, CARTO_OP_QUERY, 0);
    CHECK(carto_gate_chain(&st) == 1, "stages reached in order");

    ring_reset(&st, t);
    carto_ring_append(&st, t, 2, CARTO_OP_INVOKE, 0);
    carto_ring_append(&st, t + 1000, 1, CARTO_OP_INVOKE, 0);
    CHECK(carto_gate_chain(&st) == 0, "out of order is rejected");

    /* skipped stage must be rejected */
    ring_reset(&st, t);
    carto_ring_append(&st, t, 0, CARTO_OP_INVOKE, 0);
    carto_ring_append(&st, t + 1000, 2, CARTO_OP_INVOKE, 0);
    CHECK(carto_gate_chain(&st) == 0, "skipped stage is rejected");

    /* starting at non-zero stage must be rejected */
    ring_reset(&st, t);
    carto_ring_append(&st, t, 1, CARTO_OP_INVOKE, 0);
    carto_ring_append(&st, t + 1000, 2, CARTO_OP_INVOKE, 0);
    CHECK(carto_gate_chain(&st) == 0, "starting without ledger is rejected");
    return 0;
}

/* ---- evidence cannot outlive its record --------------------------------- */

static int test_forged_gate_bits_are_dropped(void)
{
    carto_state_t st, back;
    int i;

    unlink(SPATH);
    memset(&st, 0, sizeof st);
    st.first_run_ms = 1700000000000ull;
    for (i = 0; i < CARTO_NUM_STAGES; i++)
        st.gate_state[i] = CARTO_GB_MASK;   /* every bit claimed, no evidence */
    st.ring_count = CARTO_VOL_MIN_ENTRIES + 10;
    st.distinct_figures = CARTO_VOL_MIN_FIGURES + 10;
    CHECK(carto_state_save(ROOT, &st) == 0, "save a record with claimed bits");
    CHECK(carto_state_load(ROOT, &back, 1700000060000ull) == CARTO_LOAD_OK,
          "reload");
    for (i = 0; i < CARTO_NUM_STAGES; i++) {
        CHECK((back.gate_state[i] & CARTO_GB_HUMAN) == 0,
              "human bit dropped without evidence");
        CHECK((back.gate_state[i] & CARTO_GB_VOLUME) == 0,
              "volume bit dropped without evidence");
        CHECK((back.gate_state[i] & CARTO_GB_TTY) == 0,
              "terminal bit dropped without evidence");
        CHECK((back.gate_state[i] & CARTO_GB_PRESS) == 0,
              "press bit dropped without evidence");
    }
    return 0;
}

static int test_earned_bits_survive(void)
{
    static const uint64_t gaps[10] = { 420, 660, 250, 900, 310, 1200,
                                       480, 730, 260, 1500 };
    carto_state_t st, back;
    uint64_t t = 1700000000000ull;
    uint64_t cur = t;
    int i;

    unlink(SPATH);
    memset(&st, 0, sizeof st);
    st.first_run_ms = t;
    carto_ring_append(&st, t, 0, CARTO_OP_INVOKE,
                      CARTO_AUX_TTY_IN | CARTO_AUX_TTY_OUT);
    for (i = 0; i < 10; i++) {
        cur += gaps[i];
        carto_ring_append(&st, cur, 2, CARTO_OP_REVEAL,
                          CARTO_AUX_TTY_IN | CARTO_AUX_TTY_OUT);
    }
    carto_ring_append(&st, cur + 900, 2, CARTO_OP_PRESS,
                      CARTO_AUX_TTY_IN | CARTO_AUX_TTY_OUT);
    CHECK(carto_state_save(ROOT, &st) == 0, "save an earned record");
    CHECK(carto_state_load(ROOT, &back, cur + 1000) == CARTO_LOAD_OK, "reload");
    CHECK((back.gate_state[2] & CARTO_GB_HUMAN) != 0,
          "the human bit survives with evidence");
    CHECK((back.gate_state[2] & CARTO_GB_TTY) != 0,
          "the terminal bit survives with evidence");
    CHECK((back.gate_state[2] & CARTO_GB_PRESS) != 0,
          "the press bit survives with evidence");
    CHECK((back.gate_state[2] & CARTO_GB_VOLUME) == 0,
          "the volume bit still needs the whole sitting");
    return 0;
}

static int test_witness_is_stable_and_distinct(void)
{
    carto_state_t a, b;
    uint32_t w0, w0b, w1;

    memset(&a, 0, sizeof a);
    memset(&b, 0, sizeof b);
    a.first_run_ms = 1700000000000ull;
    b.first_run_ms = 1700000000000ull;
    carto_ring_append(&a, 1700000000001ull, 0, CARTO_OP_INVOKE, 0);
    w0 = carto_gate_witness(&a, 0);
    w0b = carto_gate_witness(&a, 0);
    w1 = carto_gate_witness(&a, 1);
    CHECK(w0 != 0, "witness is non-zero");
    CHECK(w0 == w0b, "witness is stable for a record");
    CHECK(w0 != w1, "witness differs per stage");
    carto_ring_append(&b, 1700000000002ull, 0, CARTO_OP_INVOKE, 0);
    carto_ring_append(&b, 1700000000003ull, 0, CARTO_OP_INVOKE, 0);
    CHECK(carto_gate_witness(&a, 0) != carto_gate_witness(&b, 0),
          "witness follows the record");
    return 0;
}

void run_part2_tests(void)
{
    RUN(test_stats_known_gaps);
    RUN(test_stats_burst_and_even_median);
    RUN(test_stats_duplicates_and_entropy);
    RUN(test_gate_human_accepts_a_paced_hand);
    RUN(test_gate_human_rejects_robots);
    RUN(test_gate_volume);
    RUN(test_gate_chain_order);
    RUN(test_forged_gate_bits_are_dropped);
    RUN(test_earned_bits_survive);
    RUN(test_witness_is_stable_and_distinct);
}
