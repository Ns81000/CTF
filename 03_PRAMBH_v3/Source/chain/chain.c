#include "chain.h"
#include "../core/carto_sha256.h"
#include "../core/sha256ctr.h"

#include <stdlib.h>
#include <string.h>

#define FILL_LABEL "prambh:chain:fill:v1"   /* 20 bytes */
#define RUN_LABEL  "prambh:chain:run:v1"    /* 19 bytes */

void prambh_chain_fill(const uint8_t seed[32], uint8_t *table,
                       uint64_t nblocks, uint64_t table_bytes,
                       uint64_t steps)
{
    uint8_t in[68];
    uint64_t i;

    /* table[0] = SHA-256(label || seed || LE64(S) || LE64(T)) */
    memcpy(in, FILL_LABEL, 20);
    memcpy(in + 20, seed, 32);
    prambh_put_le64(in + 52, table_bytes);
    prambh_put_le64(in + 60, steps);
    carto_sha256(in, 68, table);

    /* table[i] = SHA-256(table[i-1] || LE64(i)) */
    for (i = 1; i < nblocks; i++) {
        memcpy(in, table + (i - 1) * 32, 32);
        prambh_put_le64(in + 32, i);
        carto_sha256(in, 40, table + i * 32);
    }
    memset(in, 0, sizeof in);
}

void prambh_chain_walk(const uint8_t seed[32], const uint8_t *table,
                       uint64_t nblocks, uint64_t steps, uint8_t out[32])
{
    uint8_t in[83], s[32];
    uint64_t t, idx;

    /* s = SHA-256(run label || seed || table[n-1]) */
    memcpy(in, RUN_LABEL, 19);
    memcpy(in + 19, seed, 32);
    memcpy(in + 51, table + (nblocks - 1) * 32, 32);
    carto_sha256(in, 83, s);

    for (t = 1; t <= steps; t++) {
        idx = prambh_get_le64(s) % nblocks;
        memcpy(in, s, 32);
        memcpy(in + 32, table + idx * 32, 32);
        prambh_put_le64(in + 64, t);
        carto_sha256(in, 72, s);
    }
    memcpy(out, s, 32);
    memset(in, 0, sizeof in);
    memset(s, 0, sizeof s);
}

int prambh_chain_run(const uint8_t seed[32], uint64_t table_bytes,
                     uint64_t steps, uint8_t out[32])
{
    uint64_t nblocks = table_bytes / 32;
    uint8_t *table;

    if (nblocks == 0)
        return -1;
    table = malloc((size_t)table_bytes);
    if (!table)
        return -1;
    prambh_chain_fill(seed, table, nblocks, table_bytes, steps);
    prambh_chain_walk(seed, table, nblocks, steps, out);
    memset(table, 0, (size_t)table_bytes);
    free(table);
    return 0;
}
