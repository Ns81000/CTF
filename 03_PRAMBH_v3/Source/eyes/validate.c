/*
 * stage5_eyes/validate - the final record (spec 4.7).
 *
 * Takes the assembled title.  On the exact byte string, with the state
 * gates held and the pacing gate open, it prints ONE acceptance line;
 * on ANYTHING else - wrong titles, registered decoy titles, mirror
 * products, missing gates - it prints ONE refusal line, the same bytes
 * for every failure class.  rc 0 always; stderr silent always; the only
 * thing it stores is SHA-256(title).
 */
#include "../core/carto_sha256.h"
#include "../core/canary.h"
#include "../core/notice.h"
#include "../state/state.h"
#include "eyes_consts.h"

#include <stdio.h>
#include <string.h>

#define GATES (PRAMBH_BIT_LOOM_DONE | PRAMBH_BIT_DOORS_REAL | \
               PRAMBH_BIT_CHAIN2_DONE)

static void usage(void)
{
    printf("the survey record desk - first survey field station\n"
           "usage:\n"
           "  ./validate <title>            file the survey title\n"
           "\nstation canary: %s\n\n%s\n", PRAMBH_CANARY, PRAMBH_NOTICE);
}

static int ct_equal(const uint8_t *a, const uint8_t *b, size_t n)
{
    uint8_t d = 0;
    size_t i;
    for (i = 0; i < n; i++)
        d |= (uint8_t)(a[i] ^ b[i]);
    return d == 0;
}

int main(int argc, char **argv)
{
    char root[4096];
    prambh_state st;
    uint8_t digest[32];
    uint64_t wall, mono, last_wall, last_mono;
    int gated, paced, match = 0;

    if (prambh_package_root(root, sizeof root) != 0)
        strcpy(root, ".");
    prambh_state_load(root, &st);

    if (argc < 2) {
        usage();
        return 0;
    }
    prambh_now_ms(&wall, &mono);
    last_wall = prambh_state_get64(&st, ST_OFF_VAL_WALL);
    last_mono = prambh_state_get64(&st, ST_OFF_VAL_MONO);
    paced = prambh_pacing_allow(wall, mono, last_wall, last_mono,
                                EYES_PACING_MS);
    prambh_state_set64(&st, ST_OFF_VAL_WALL, wall);
    prambh_state_set64(&st, ST_OFF_VAL_MONO, mono);
    gated = (prambh_state_get64(&st, ST_OFF_STAGE) & GATES) == GATES;

    carto_sha256((const uint8_t *)argv[1], strlen(argv[1]), digest);
    match = ct_equal(digest, EYES_TITLE_DIGEST, 32);
    /* the record keeps only the digest of what was offered */
    memcpy(st.bytes + ST_OFF_RESERVED, digest, 32);
    memset(digest, 0, sizeof digest);
    if (gated && paced && match)
        prambh_state_set64(&st, ST_OFF_STAGE,
                           prambh_state_get64(&st, ST_OFF_STAGE)
                           | PRAMBH_BIT_TITLE_ASSEMBLED);
    prambh_state_save(root, &st);

    if (gated && paced && match)
        printf("the survey record is complete.\n");
    else
        printf("the survey holds no such record.\n");
    return 0;
}
