#ifndef PRAMBH_SHA256CTR_H
#define PRAMBH_SHA256CTR_H

#include <stddef.h>
#include <stdint.h>

/*
 * SHA256ctr key stream: block i = SHA-256(key || LE64(i)), i = 0,1,2,...
 * XORs the stream into buf in place.  Used for every raw-XOR sealed blob
 * in the package (riddle, chambers, notes).  No format markers by design.
 */
void prambh_sha256ctr_xor(const uint8_t key[32], uint8_t *buf, size_t len);

/* LE64 encode/decode helpers shared across tools. */
void prambh_put_le64(uint8_t out[8], uint64_t v);
uint64_t prambh_get_le64(const uint8_t in[8]);

#endif
