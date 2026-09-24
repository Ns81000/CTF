/* test-only helper: lay a paced, terminal-shaped session into the record so
 * the sheet's reveal can be exercised without a person at the keyboard.
 * Never shipped. */
#define _POSIX_C_SOURCE 200809L

#include "state.h"
#include "policy.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
    static const uint32_t gaps[16] = {
        430, 700, 260, 900, 330, 1200, 470, 760,
        250, 1500, 520, 880, 610, 410, 690, 300
    };
    carto_state_t st;
    const char *root = (argc > 1) ? argv[1] : ".";
    uint64_t now = carto_now_ms();
    uint64_t t;
    uint32_t aux = CARTO_AUX_TTY_IN | CARTO_AUX_TTY_OUT;
    uint64_t sum = 0;
    int i;

    for (i = 0; i < 16; i++)
        sum += gaps[i];
    t = (now > sum) ? now - sum : 0;

    if (carto_state_load(root, &st, t) == CARTO_LOAD_TAMPERED) {
        /* starts over */
    }
    carto_ring_append(&st, t, CARTO_STAGE_LEDGER, CARTO_OP_NOARG, aux);
    for (i = 0; i < 16; i++) {
        t += gaps[i];
        carto_ring_append(&st, t, i % 4, CARTO_OP_INVOKE, aux);
        carto_bump_attempt(&st, i % 4);
    }
    st.debugger_flag = 0;
    carto_recompute_gates(&st, now);
    if (carto_state_save(root, &st) != 0)
        return 1;
    return 0;
}
