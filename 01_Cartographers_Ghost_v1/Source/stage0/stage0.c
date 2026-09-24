/*
 * stage0_start -- "The Cartographer's Ghost", Stage 0: Orientation.
 * Phase 1 deliverable. Full design record: logs/PHASE_1_LOG.md.
 *
 * Behavior (per build spec, Phase 1):
 *   - loads or creates ./.cartographer_state via the shared state library
 *     (src/state); the library itself records first_run_ms on fresh create
 *   - bumps the Stage-0 attempt counter and records an interaction timestamp
 *   - prints the Stage-0 flag: a real, bankable partial flag -- an ungated
 *     win by design, handed over on every correct run
 *   - treats CARTO_LOAD_CREATED and CARTO_LOAD_TAMPERED identically (silent
 *     fresh start, no diagnostics) per the Phase-0 runtime rule
 *   - escalation/decoy mechanics are deliberately NOT used here: Stage 0 is
 *     the orientation stage and stays fair and ungated
 *
 * Run from the cartographer/ package root:  ./stage0_start/stage0_start
 */
#define _POSIX_C_SOURCE 200809L

#include "flag_blob.h"
#include "state.h"

#include <stdio.h>
#include <string.h>
#include <time.h>

#define STATE_PATH "./.cartographer_state"

_Static_assert(CARTO_S0_FLAG_LEN == sizeof kCartoS0MaskedFlag,
               "masked flag blob length mismatch");

static void print_flag(void)
{
    unsigned char flag[CARTO_S0_FLAG_LEN + 1];
    unsigned i;

    for (i = 0; i < CARTO_S0_FLAG_LEN; i++)
        flag[i] = (unsigned char)(kCartoS0MaskedFlag[i] ^ kCartoS0FlagMask[i]);
    flag[CARTO_S0_FLAG_LEN] = 0u;
    printf("    %s\n", (const char *)flag);
    memset(flag, 0, sizeof flag);
}

static void print_first_entry(uint64_t first_run_ms)
{
    char buf[64];
    time_t t = (time_t)(first_run_ms / 1000u);
    struct tm tmv;

    if (gmtime_r(&t, &tmv) != NULL &&
        strftime(buf, sizeof buf, "%Y-%m-%d %H:%M:%S UTC", &tmv) > 0)
        printf("  First entry inked: %s\n", buf);
    else
        printf("  First entry inked: (an unreadable hour)\n");
}

int main(void)
{
    carto_state_t st;
    uint64_t now;
    int fresh;

    now   = carto_now_ms();
    fresh = (carto_state_load(STATE_PATH, &st, now) != CARTO_LOAD_OK);

    carto_bump_attempt(&st, CARTO_STAGE0);
    carto_record_interaction(&st, now);
    (void)carto_state_save(STATE_PATH, &st);

    printf("======================================================================\n");
    printf("  THE CARTOGRAPHER'S GHOST\n");
    printf("  Stage 0 -- Orientation: The Surveyor's Ledger\n");
    printf("======================================================================\n");
    printf("\n");
    if (fresh) {
        printf("They say the old surveyor drew his final map the night the fog\n");
        printf("took him: no body, no farewell. Only his study, still warm, and a\n");
        printf("ledger lying open on the desk, a page waiting for a hand.\n");
        printf("\n");
        printf("You take up the pen. The ledger accepts yours as the keeper's\n");
        printf("hand and yields the first token of his survey:\n");
    } else {
        printf("The ledger already knows your hand. The first token stands:\n");
    }
    printf("\n");
    print_flag();
    printf("\n");
    printf("Bank it -- it is yours, and it is real. He drew in order, coast\n");
    printf("first, interior last. So, it appears, shall you.\n");
    printf("\n");
    print_first_entry(st.first_run_ms);
    printf("======================================================================\n");
    return 0;
}
