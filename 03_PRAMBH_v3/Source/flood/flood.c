/*
 * PRAMBH flood tool (spec 4.3): ./flood <token> - <index>
 *   token: up to 8 chars, from a folio stitch header
 *   prints one generated page of the token's lane; lanes are 8 pages.
 * Every token yields a plausible page. No lane contains anything real.
 * rc is always 0; stderr stays silent.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/carto_sha256.h"
#include "../core/sha256ctr.h"
#include "../core/notice.h"
#include "flood_words.h"

#define LANE_LABEL "prambh:flood:lane:v1"
#define BODY_LINES 45
#define LANE_PAGES 8

static void page_key(const char *tok, uint32_t index, uint8_t key[32])
{
    uint8_t buf[64];
    size_t n = 0;
    size_t tl = strlen(tok);
    memcpy(buf + n, LANE_LABEL, strlen(LANE_LABEL));
    n += strlen(LANE_LABEL);
    memcpy(buf + n, tok, tl);
    n += tl;
    buf[n++] = index & 0xff;
    buf[n++] = (index >> 8) & 0xff;
    buf[n++] = (index >> 16) & 0xff;
    buf[n++] = (index >> 24) & 0xff;
    carto_sha256(buf, n, key);
}

static void print_page(const char *tok, uint32_t index)
{
    uint8_t key[32], stream[4096];
    int li;

    page_key(tok, index, key);
    memset(stream, 0, sizeof(stream));
    prambh_sha256ctr_xor(key, stream, sizeof(stream));

    printf("MERU FIELD SURVEY - folio %03d-%02d / stitch %s\n",
           100 + stream[0] % 900, stream[1] % 64, tok);
    for (li = 0; li < BODY_LINES; li++) {
        size_t base = 2 + (size_t)li * 16;
        int nw = 5 + stream[base] % 6;
        int j;
        for (j = 0; j < nw; j++)
            printf("%s%s", j ? " " : "",
                   PRAMBH_WORDS[stream[base + 1 + (size_t)j] % PRAMBH_N_WORDS]);
        if (stream[base + 11] & 1)
            printf(" = %d.%02d m", stream[base + 12] % 40, stream[base + 13] % 100);
        printf("\n");
    }
}

static int valid_index(const char *s, uint32_t *out)
{
    unsigned long v = 0;
    size_t n = strlen(s);
    size_t k;
    if (n == 0 || n > 2)
        return 0;
    for (k = 0; k < n; k++) {
        if (s[k] < '0' || s[k] > '9')
            return 0;
        v = v * 10 + (unsigned long)(s[k] - '0');
    }
    if (v >= LANE_PAGES)
        return 0;
    *out = (uint32_t)v;
    return 1;
}

int main(int argc, char **argv)
{
    uint32_t index;

    if (argc != 4 || strcmp(argv[2], "-") != 0 ||
        strlen(argv[1]) == 0 || strlen(argv[1]) > 8 ||
        !valid_index(argv[3], &index)) {
        printf("PRAMBH flood reader\n"
               "usage: ./flood <token> - <index>\n"
               "  token: up to 8 chars, from a folio stitch header\n"
               "  index: page number 0..%d; every lane has %d pages\n\n"
               "%s\n", LANE_PAGES - 1, LANE_PAGES, PRAMBH_NOTICE);
        return 0;
    }
    print_page(argv[1], index);
    return 0;
}
