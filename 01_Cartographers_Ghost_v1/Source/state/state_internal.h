#ifndef CARTO_STATE_INTERNAL_H
#define CARTO_STATE_INTERNAL_H

/* Internal cross-TU interface for the state library (not shipped to solvers). */

#include <stdint.h>

/* Unmask the canonical HMAC key into a 32-byte stack buffer (mask v1 path). */
void carto_unmask_key(uint8_t out[32]);

/* Independent redundant copy of the same key (mask v2 path), used only by
 * carto_key_selftest() to prove the XOR/unmask path is transcription-clean. */
void carto_unmask_key2(uint8_t out[32]);

#endif /* CARTO_STATE_INTERNAL_H */
