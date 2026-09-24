#ifndef CARTO_SHA256_H
#define CARTO_SHA256_H

#include <stddef.h>
#include <stdint.h>

/*
 * Minimal self-contained SHA-256 (FIPS 180-4) + HMAC-SHA256 (RFC 2104).
 * Purpose: HMAC-signing the cartographer state file. No external deps so
 * stage binaries stay small and fully static under musl.
 */

void carto_sha256(const uint8_t *data, size_t len, uint8_t out[32]);

void carto_hmac_sha256(const uint8_t *key, size_t key_len,
                       const uint8_t *msg, size_t msg_len, uint8_t out[32]);

/* Constant-time byte comparison; returns 1 if equal, 0 otherwise. */
int carto_ct_equal(const uint8_t *a, const uint8_t *b, size_t n);

#endif /* CARTO_SHA256_H */
