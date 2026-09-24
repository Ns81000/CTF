/* test-only helper: lay the record shape a sitting would have left behind,
 * so the title block can be exercised without a person at the keyboard.
 * The window walks the ground in order -- ledger, engine, sheet, oracle,
 * seal -- with human spacing, so the chain gate sees what it would see.
 * Never shipped. */
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
    const uint64_t *gaps = human;
    const char *mode = (argc > 2) ? argv[2] : "human";
    carto_state_t st;
    const char *root = (argc > 1) ? argv[1] : ".";
    uint64_t now = carto_now_ms();
    uint64_t sum = 0, t;
    uint32_t aux = CARTO_AUX_TTY_IN | CARTO_AUX_TTY_OUT;
    int i, k;

    for (i = 0; i < 16; i++)
        sum += gaps[i];
    t = (now > sum * (WINDOW_FILL / 16)) ? now - sum * (WINDOW_FILL / 16) : 0;

    memset(&st, 0, sizeof st);
    if (carto_state_load(root, &st, t) == CARTO_LOAD_TAMPERED) {
        /* starts over */
    }
    st.first_run_ms = (now > 46 * MINUTE_MS) ? now - 46 * MINUTE_MS : 0;
    if (!strcmp(mode, "thin"))
        st.first_run_ms = (now > 5000ull) ? now - 5000ull : 0;

    carto_ring_append(&st, t, CARTO_STAGE_LEDGER, CARTO_OP_NOARG, aux);
    carto_bump_attempt(&st, CARTO_STAGE_LEDGER);
    if (!strcmp(mode, "thin")) {
        /* a record that never left the first room: the chain cannot hold */
        for (k = 0; k < 3; k++) {
            t += gaps[k % 16];
            carto_ring_append(&st, t, CARTO_STAGE_LEDGER, CARTO_OP_INVOKE, aux);
            carto_bump_attempt(&st, CARTO_STAGE_LEDGER);
        }
    } else {
        for (k = 0; k < WINDOW_FILL; k++) {
            int stage;
            t += gaps[k % 16];
            if (k < 6)
                stage = CARTO_STAGE_LEDGER;
            else if (k < 12)
                stage = CARTO_STAGE_ENGINE;
            else if (k < 18)
                stage = CARTO_STAGE_SHEET;
            else if (k < 24)
                stage = CARTO_STAGE_ORACLE;
            else
                stage = CARTO_STAGE_SEAL;
            carto_ring_append(&st, t, stage, CARTO_OP_INVOKE, aux);
            carto_bump_attempt(&st, stage);
        }
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
