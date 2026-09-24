#include "sha256ctr.h"
#include "carto_sha256.h"
#include <string.h>

void prambh_put_le64(uint8_t out[8], uint64_t v)
{
    int i;
    for (i = 0; i < 8; i++)
        out[i] = (uint8_t)(v >> (8 * i));
}

uint64_t prambh_get_le64(const uint8_t in[8])
{
    uint64_t v = 0;
    int i;
    for (i = 7; i >= 0; i--)
        v = (v << 8) | in[i];
    return v;
}

void prambh_sha256ctr_xor(const uint8_t key[32], uint8_t *buf, size_t len)
{
    uint8_t in[40], block[32];
    uint64_t ctr = 0;
    size_t off = 0;

    memcpy(in, key, 32);
    while (off < len) {
        size_t n = len - off < 32 ? len - off : 32;
        size_t i;
        prambh_put_le64(in + 32, ctr++);
        carto_sha256(in, 40, block);
        for (i = 0; i < n; i++)
            buf[off + i] ^= block[i];
        off += n;
    }
    memset(in, 0, sizeof in);
    memset(block, 0, sizeof block);
}
