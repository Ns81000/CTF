/* test-only helper: lay the record shape a sitting would have left behind,
 * so the plate can be exercised without a person at the keyboard.  It fills a
 * full 64-entry window with real, terminal-shaped interactions, so the
 * behaviour gates see exactly what they would see from a person.  Never
 * shipped. */
#define _POSIX_C_SOURCE 200809L

#include "state.h"
#include "policy.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MINUTE_MS (60ull * 1000ull)
#define WINDOW_FILL 80

int main(int argc, char **argv)
{
    static const uint64_t human[16] = {
        1800, 2400, 1500, 3000, 2100, 1200, 2700, 1900,
        1600, 3300, 2200, 1400, 2600, 1700, 2900, 2000
    };
    static const uint64_t bursty[16] = {
        80, 3000, 90, 3100, 70, 2900, 95, 3200,
        85, 2800, 75, 3300, 60, 3000, 70, 60
    };
    static const uint64_t uniform[16] = {
        2000, 2000, 2000, 2000, 2000, 2000, 2000, 2000,
        2000, 2000, 2000, 2000, 2000, 2000, 2000, 2000
    };
    const uint64_t *gaps = human;
    const char *mode = (argc > 2) ? argv[2] : "human";
    carto_state_t st;
    const char *root = (argc > 1) ? argv[1] : ".";
    uint64_t now = carto_now_ms();
    uint64_t sum = 0, t;
    uint32_t aux = CARTO_AUX_TTY_IN | CARTO_AUX_TTY_OUT;
    int i, k;

    if (!strcmp(mode, "bursty"))
        gaps = bursty;
    else if (!strcmp(mode, "uniform"))
        gaps = uniform;

    for (i = 0; i < 16; i++)
        sum += gaps[i];
    t = (now > sum * (WINDOW_FILL / 16)) ? now - sum * (WINDOW_FILL / 16) : 0;

    memset(&st, 0, sizeof st);
    if (carto_state_load(root, &st, t) == CARTO_LOAD_TAMPERED) {
        /* starts over */
    }
    st.first_run_ms = (now > 46 * MINUTE_MS) ? now - 46 * MINUTE_MS : 0;
    if (!strcmp(mode, "young"))
        st.first_run_ms = (now > 5000ull) ? now - 5000ull : 0;

    carto_ring_append(&st, t, CARTO_STAGE_LEDGER, CARTO_OP_NOARG, aux);
    for (k = 0; k < WINDOW_FILL; k++) {
        int stage = (k < 6) ? 0 : (k < 12) ? 1 : (k < 18) ? 2 : 3;
        t += gaps[k % 16];
        carto_ring_append(&st, t, stage, CARTO_OP_INVOKE, aux);
        carto_bump_attempt(&st, stage);
    }
    if (!strcmp(mode, "replay")) {
        for (k = 0; k < 40; k++)
            carto_ring_append(&st, t + (uint64_t)k * 1800ull,
                              CARTO_STAGE_ORACLE, CARTO_OP_QUERY,
                              aux | (0x4242u << CARTO_AUX_FIG_SHIFT));
    }
    st.debugger_flag = 0;
    if (strcmp(mode, "thin"))            /* a thin record never gets there */
        st.ring_count = 7000;
    st.distinct_figures = strcmp(mode, "thin") ? 3200 : 12;
    carto_recompute_gates(&st, now);
    if (carto_state_save(root, &st) != 0)
        return 1;
    return 0;
}
