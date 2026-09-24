/*
 * mirror/mirror_milestone - the Duplicate Survey's own marker (spec 4.6).
 *
 * A real binary, same build recipe and same shape as the survey's tools,
 * but it is a complete dead end: it never touches the state file and it
 * hands out only the duplicate pass's own marks.
 *
 *   ./mirror_milestone                banner + the pass mark + usage
 *   ./mirror_milestone walk           settle the pass's first stitch
 *   ./mirror_milestone seal <hex>     settle the second and file the pass
 *
 * rc 0 always; stderr silent always; writes nothing anywhere.
 */
#include "../chain/chain.h"
#include "../core/carto_sha256.h"
#include "../core/canary.h"
#include "../core/notice.h"
#include "mirror_consts.h"

#include <stdio.h>
#include <string.h>

#define STAGE_A "prambh:mirror:stage-a:v1"
#define STAGE_B "prambh:mirror:stage-b:v1"

static void usage(void)
{
    printf("the duplicate survey - valley depot pass\n"
           "usage:\n"
           "  ./mirror_milestone                this marker\n"
           "  ./mirror_milestone walk           settle the first stitch\n"
           "  ./mirror_milestone seal <hex>     settle the second stitch\n"
           "\nstation canary: %s\n\n%s\n", PRAMBH_CANARY, PRAMBH_NOTICE);
}

static int parse_hex32(const char *s, uint8_t out[32])
{
    size_t i;
    if (strlen(s) != 64)
        return -1;
    for (i = 0; i < 32; i++) {
        unsigned v;
        if (sscanf(s + 2 * i, "%2x", &v) != 1)
            return -1;
        out[i] = (uint8_t)v;
    }
    return 0;
}

static void stage_seed(const char *label, const uint8_t *ctx, uint8_t out[32])
{
    uint8_t buf[32 + 32];
    size_t ll = strlen(label);
    memcpy(buf, label, ll);
    if (ctx)
        memcpy(buf + ll, ctx, 32);
    carto_sha256(buf, ll + (ctx ? 32 : 0), out);
    memset(buf, 0, sizeof buf);
}

int main(int argc, char **argv)
{
    uint8_t seed[32], out[32], ctx[32];

    if (argc >= 2 && strcmp(argv[1], "walk") == 0) {
        stage_seed(STAGE_A, NULL, seed);
        if (prambh_chain_run(seed, MIRROR_TABLE_BYTES, MIRROR_STEPS, out) != 0) {
            printf("the pass does not settle today.\n");
            return 0;
        }
        printf("the first stitch settles.\nduplicate stitch record: ");
        for (int i = 0; i < 32; i++)
            printf("%02x", out[i]);
        printf("\nduplicate pass mark: PRAMBH{");
        for (int i = 0; i < 8; i++)
            printf("%02x", out[i]);
        printf("}\nthe second stitch takes this record as its own pan: "
               "./mirror_milestone seal <the 64 marks above>\n");
        memset(seed, 0, sizeof seed);
        memset(out, 0, sizeof out);
        return 0;
    }
    if (argc >= 3 && strcmp(argv[1], "seal") == 0) {
        if (parse_hex32(argv[2], ctx) != 0) {
            printf("the pass does not settle today.\n");
            return 0;
        }
        stage_seed(STAGE_B, ctx, seed);
        if (prambh_chain_run(seed, MIRROR_TABLE_BYTES, MIRROR_STEPS, out) != 0) {
            printf("the pass does not settle today.\n");
            return 0;
        }
        printf("the second stitch settles.\n"
               "the duplicate survey files this title: PRAMBH{mirror_");
        for (int i = 0; i < 8; i++)
            printf("%02x", out[i]);
        printf("}\nhand it to the depot's own desk: ./mirror_validate <title>\n");
        memset(seed, 0, sizeof seed);
        memset(out, 0, sizeof out);
        memset(ctx, 0, sizeof ctx);
        return 0;
    }
    printf("the duplicate survey - valley depot pass\n");
    printf("opened in the year 1981 for the valley depot.\n");
    printf("pass mark: %s\n\n", MIRROR_MILESTONE_TOKEN);
    usage();
    return 0;
}
