/* test-only helper: write a record and LEAVE IT BEHIND so an independent
 * Python implementation can check the bytes.  Never shipped. */
#define _POSIX_C_SOURCE 200809L

#include "state.h"
#include "policy.h"

#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    carto_state_t st;
    uint64_t now = 1700000000000ull;
    const char *root = (argc > 1) ? argv[1] : ".";

    if (argc > 2)
        now = strtoull(argv[2], NULL, 10);
    carto_state_load(root, &st, now);
    st.distinct_figures = 7;
    carto_ring_append(&st, now + 1000ull, CARTO_STAGE_ORACLE, CARTO_OP_QUERY,
                      (0x1234u << CARTO_AUX_FIG_SHIFT) |
                      CARTO_AUX_TTY_IN | CARTO_AUX_TTY_OUT);
    if (carto_state_save(root, &st) != 0)
        return 1;
    return 0;
}
