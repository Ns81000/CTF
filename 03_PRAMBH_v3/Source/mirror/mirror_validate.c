/*
 * mirror/mirror_validate - the Duplicate Survey's own desk (spec 4.6).
 *
 * Accepts exactly one filed title (the pass's own, a registered decoy)
 * and prints one non-committal line.  Every other input - including the
 * survey's real title and any other title - gets one byte-identical
 * refusal.  rc 0 always; stderr silent always; no state is touched.
 */
#include "../core/carto_sha256.h"
#include "../core/canary.h"
#include "../core/notice.h"
#include "mirror_consts.h"

#include <stdio.h>
#include <string.h>

static void usage(void)
{
    printf("the duplicate survey - depot desk\n"
           "usage:\n"
           "  ./mirror_validate <title>     file a duplicate title\n"
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
    uint8_t digest[32];
    int match = 0;

    if (argc >= 2) {
        carto_sha256((const uint8_t *)argv[1], strlen(argv[1]), digest);
        match = ct_equal(digest, MIRROR_TITLE_DIGEST, 32);
        memset(digest, 0, sizeof digest);
        if (match)
            printf("the duplicate survey is filed.\n");
        else
            printf("the depot holds no such record.\n");
        return 0;
    }
    usage();
    return 0;
}
