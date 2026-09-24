#ifndef PRAMBH_CHAIN_H
#define PRAMBH_CHAIN_H

#include <stdint.h>

/*
 * PRAMBH-CHAIN (spec 4.1) - EXACT construction:
 *
 *   n = S / 32
 *   table[0] = SHA-256("prambh:chain:fill:v1" || seed || LE64(S) || LE64(T))
 *   table[i] = SHA-256(table[i-1] || LE64(i))                    i in [1, n)
 *   s        = SHA-256("prambh:chain:run:v1" || seed || table[n-1])
 *   for t in 1 .. T:
 *       idx = LE64(s[0:8]) mod n
 *       s   = SHA-256(s || table[idx] || LE64(t))
 *   return s
 *
 * The walk's next index depends on the current 32-byte state, so the
 * walk is inherently sequential; skipping or corrupting a table block
 * changes the result.
 */

void prambh_chain_fill(const uint8_t seed[32], uint8_t *table,
                       uint64_t nblocks, uint64_t table_bytes,
                       uint64_t steps);

void prambh_chain_walk(const uint8_t seed[32], const uint8_t *table,
                       uint64_t nblocks, uint64_t steps, uint8_t out[32]);

/* fill + walk, allocating the table internally; 0 on success. */
int prambh_chain_run(const uint8_t seed[32], uint64_t table_bytes,
                     uint64_t steps, uint8_t out[32]);

#endif
