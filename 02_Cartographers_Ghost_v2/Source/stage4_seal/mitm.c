/*
 * mitm -- test-only tool: the intended attack on the seal, written out the
 * way a solver would write it.
 *
 * The middle pass is the only one keyed by a single byte, so the search
 * meets there: enumerate the two outer keys (2^24 each) and hold the two
 * outer results up to the certificate, then read the middle byte off the
 * certificate's own middle state.  Nothing about the key ships anywhere;
 * this tool starts from the certificate alone and lands on the key.
 */
#define _POSIX_C_SOURCE 200809L

#include "seal_tables.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static uint32_t rotl32(uint32_t x, int n)
{
    return (x << n) | (x >> (32 - n));
}

static uint32_t spread(uint32_t a)
{
    return (uint32_t)kT[0][a & 0xFF] ^ (uint32_t)kT[1][(a >> 8) & 0xFF] ^
           ((uint32_t)kT[2][(a >> 16) & 0xFF] << 16) ^
           ((uint32_t)kT[3][(a >> 24) & 0xFF] << 24);
}

static uint32_t f_round(int z, uint32_t y, uint32_t k)
{
    return rotl32(spread(y ^ k), 8 * z) ^ k ^ kSalt[z];
}

static void block_of(const uint8_t in[8], uint32_t *l, uint32_t *r)
{
    *l = in[0] | ((uint32_t)in[1] << 8) | ((uint32_t)in[2] << 16) |
         ((uint32_t)in[3] << 24);
    *r = in[4] | ((uint32_t)in[5] << 8) | ((uint32_t)in[6] << 16) |
         ((uint32_t)in[7] << 24);
}

/* chained multi-map: delta -> every a that produced it */
#define BBITS 22
#define BSIZE (1u << BBITS)
#define NNODES (1u << 24)

static uint32_t *h_head;
static uint32_t *h_next;
static uint32_t *h_nkey;
static uint32_t *h_nval;
static uint32_t ncount;

static void h_reset(void)
{
    memset(h_head, 0xFF, sizeof(uint32_t) * BSIZE);
    ncount = 0;
}

static void h_put(uint32_t k, uint32_t v)
{
    uint32_t bkt = (k * 2654435761u) >> (32 - BBITS);
    h_nkey[ncount] = k;
    h_nval[ncount] = v;
    h_next[ncount] = h_head[bkt];
    h_head[bkt] = ncount;
    ncount++;
}

static uint32_t h_first(uint32_t k, uint32_t *v_out)
{
    uint32_t bkt = (k * 2654435761u) >> (32 - BBITS);
    uint32_t n = h_head[bkt];
    while (n != 0xFFFFFFFFu) {
        if (h_nkey[n] == k) {
            *v_out = h_nval[n];
            return n;       /* node index; continue with h_next_from */
        }
        n = h_next[n];
    }
    return 0xFFFFFFFFu;
}

static uint32_t h_next_from(uint32_t n, uint32_t k, uint32_t *v_out)
{
    n = h_next[n];
    while (n != 0xFFFFFFFFu) {
        if (h_nkey[n] == k) {
            *v_out = h_nval[n];
            return n;
        }
        n = h_next[n];
    }
    return 0xFFFFFFFFu;
}

static void le24_put(uint8_t *p, uint32_t v)
{
    p[0] = v & 0xFF;
    p[1] = (v >> 8) & 0xFF;
    p[2] = (v >> 16) & 0xFF;
}

int main(void)
{
    uint32_t l0[4], r0[4], l3[4], r3[4];
    uint8_t key[8];
    struct timespec ts0, ts1;
    double secs;
    uint32_t a, b;
    unsigned long long work = 0;
    int found = 0;
    clock_t c0, c1;

    {
        int i;
        for (i = 0; i < 4; i++) {
            block_of(kCertP[i], &l0[i], &r0[i]);
            block_of(kCertC[i], &l3[i], &r3[i]);
        }
    }
    memset(key, 0, sizeof key);

    h_head = malloc(sizeof(uint32_t) * BSIZE);
    h_next = malloc(sizeof(uint32_t) * NNODES);
    h_nkey = malloc(sizeof(uint32_t) * NNODES);
    h_nval = malloc(sizeof(uint32_t) * NNODES);
    if (!h_head || !h_next || !h_nkey || !h_nval)
        return 1;

    clock_gettime(CLOCK_MONOTONIC, &ts0);
    c0 = clock();

    /* forward over a = k0, pairs 1 and 2 */
    h_reset();
    for (a = 0; a < (1u << 24); a++) {
        uint32_t la0 = l0[0] ^ f_round(0, r0[0], a);
        uint32_t la1 = l0[1] ^ f_round(0, r0[1], a);
        uint32_t delta = la0 ^ la1;
        h_put(delta, a);
        work++;
    }

    /* backward over b = k2, pairs 1 and 2 */
    for (b = 0; b < (1u << 24) && !found; b++) {
        uint32_t r3p0 = r3[0] ^ f_round(2, l3[0], b);
        uint32_t r3p1 = r3[1] ^ f_round(2, l3[1], b);
        uint32_t delta = r3p0 ^ r3p1;
        uint32_t n, av;
        work++;
        n = h_first(delta, &av);
        while (n != 0xFFFFFFFFu && !found) {
            /* candidate outer keys: a = av, b = b.  the middle pass must
             * satisfy, on pair 1:  R2 = L1 ^ F(1, R1, k1),
             * i.e. F(1, R1, k1) = R0 ^ L3 with R1 = la; that target needs
             * no b at all.  walk the byte and let the four pairs decide. */
            uint32_t la = l0[0] ^ f_round(0, r0[0], av);
            uint32_t target = r0[0] ^ l3[0];
            int t;
            work += 256;
            for (t = 0; t < 256 && !found; t++) {
                uint32_t k1 = (uint32_t)t;
                uint32_t f = rotl32(spread(la ^ k1), 8) ^ k1 ^ kSalt[1];
                int i, good;
                if (f != target)
                    continue;
                le24_put(key, av);
                key[3] = (uint8_t)t;
                le24_put(key + 4, b);
                key[7] = 0;
                good = 1;
                for (i = 0; i < 4 && good; i++) {
                    uint32_t l, r;
                    uint32_t ks[3];
                    int step;
                    ks[0] = key[0] | ((uint32_t)key[1] << 8) |
                            ((uint32_t)key[2] << 16);
                    ks[1] = key[3];
                    ks[2] = key[4] | ((uint32_t)key[5] << 8) |
                            ((uint32_t)key[6] << 16);
                    block_of(kCertP[i], &l, &r);
                    for (step = 0; step < 3; step++) {
                        uint32_t nr = l ^ f_round(step, r, ks[step]);
                        l = r;
                        r = nr;
                    }
                    good = (l == l3[i]) && (r == r3[i]);
                }
                if (good)
                    found = 1;
            }
            n = h_next_from(n, delta, &av);
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &ts1);
    c1 = clock();
    secs = (double)(ts1.tv_sec - ts0.tv_sec) +
           (double)(ts1.tv_nsec - ts0.tv_nsec) / 1e9;

    if (found) {
        printf("KEY %02x%02x%02x%02x%02x%02x%02x%02x\n",
               key[0], key[1], key[2], key[3],
               key[4], key[5], key[6], key[7]);
        printf("WORK %llu\n", work);
        printf("WALL %.1f\n", secs);
        printf("CPU %.1f\n", (double)(c1 - c0) / CLOCKS_PER_SEC);
        return 0;
    }
    printf("MISS\n");
    return 2;
}
