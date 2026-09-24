#include "carto_sha256.h"
#include <stdlib.h>
#include <string.h>

#define ROTR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))

static const uint32_t K[64] = {
    0x428a2f98u, 0x71374491u, 0xb5c0fbcfu, 0xe9b5dba5u,
    0x3956c25bu, 0x59f111f1u, 0x923f82a4u, 0xab1c5ed5u,
    0xd807aa98u, 0x12835b01u, 0x243185beu, 0x550c7dc3u,
    0x72be5d74u, 0x80deb1feu, 0x9bdc06a7u, 0xc19bf174u,
    0xe49b69c1u, 0xefbe4786u, 0x0fc19dc6u, 0x240ca1ccu,
    0x2de92c6fu, 0x4a7484aau, 0x5cb0a9dcu, 0x76f988dau,
    0x983e5152u, 0xa831c66du, 0xb00327c8u, 0xbf597fc7u,
    0xc6e00bf3u, 0xd5a79147u, 0x06ca6351u, 0x14292967u,
    0x27b70a85u, 0x2e1b2138u, 0x4d2c6dfcu, 0x53380d13u,
    0x650a7354u, 0x766a0abbu, 0x81c2c92eu, 0x92722c85u,
    0xa2bfe8a1u, 0xa81a664bu, 0xc24b8b70u, 0xc76c51a3u,
    0xd192e819u, 0xd6990624u, 0xf40e3585u, 0x106aa070u,
    0x19a4c116u, 0x1e376c08u, 0x2748774cu, 0x34b0bcb5u,
    0x391c0cb3u, 0x4ed8aa4au, 0x5b9cca4fu, 0x682e6ff3u,
    0x748f82eeu, 0x78a5636fu, 0x84c87814u, 0x8cc70208u,
    0x90befffau, 0xa4506cebu, 0xbef9a3f7u, 0xc67178f2u
};

static uint32_t be32get(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8)  |  (uint32_t)p[3];
}

static void be32put(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)(v >> 24);
    p[1] = (uint8_t)(v >> 16);
    p[2] = (uint8_t)(v >> 8);
    p[3] = (uint8_t)(v);
}

static void sha256_compress(uint32_t h[8], const uint8_t block[64])
{
    uint32_t w[64];
    int i;

    for (i = 0; i < 16; i++)
        w[i] = be32get(block + 4 * i);
    for (i = 16; i < 64; i++) {
        uint32_t s0 = ROTR(w[i - 15], 7) ^ ROTR(w[i - 15], 18) ^ (w[i - 15] >> 3);
        uint32_t s1 = ROTR(w[i - 2], 17) ^ ROTR(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }

    uint32_t a = h[0], b = h[1], c = h[2], d = h[3];
    uint32_t e = h[4], f = h[5], g = h[6], hh = h[7];

    for (i = 0; i < 64; i++) {
        uint32_t S1  = ROTR(e, 6) ^ ROTR(e, 11) ^ ROTR(e, 25);
        uint32_t ch  = (e & f) ^ (~e & g);
        uint32_t t1  = hh + S1 + ch + K[i] + w[i];
        uint32_t S0  = ROTR(a, 2) ^ ROTR(a, 13) ^ ROTR(a, 22);
        uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
        uint32_t t2  = S0 + maj;
        hh = g; g = f; f = e; e = d + t1;
        d = c; c = b; b = a; a = t1 + t2;
    }

    h[0] += a; h[1] += b; h[2] += c; h[3] += d;
    h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
}

void carto_sha256(const uint8_t *data, size_t len, uint8_t out[32])
{
    uint32_t h[8] = {
        0x6a09e667u, 0xbb67ae85u, 0x3c6ef372u, 0xa54ff53au,
        0x510e527fu, 0x9b05688cu, 0x1f83d9abu, 0x5be0cd19u
    };
    uint8_t block[64];
    size_t i = 0, rem;
    uint64_t bits;
    int k;

    while (len - i >= 64) {
        sha256_compress(h, data + i);
        i += 64;
    }
    rem = len - i;
    memcpy(block, data + i, rem);
    block[rem] = 0x80;
    if (rem + 1 < 64)
        memset(block + rem + 1, 0, 64 - rem - 1);
    if (rem >= 56) {
        sha256_compress(h, block);
        memset(block, 0, 56);
    }
    bits = (uint64_t)len * 8u;
    for (k = 0; k < 8; k++)
        block[56 + k] = (uint8_t)(bits >> (56 - 8 * k));
    sha256_compress(h, block);
    for (k = 0; k < 8; k++)
        be32put(out + 4 * k, h[k]);
}

void carto_hmac_sha256(const uint8_t *key, size_t key_len,
                       const uint8_t *msg, size_t msg_len, uint8_t out[32])
{
    uint8_t k[64], pad[64], inner[32], outer[96];
    uint8_t *buf;
    int i;

    memset(k, 0, sizeof k);
    if (key_len > 64)
        carto_sha256(key, key_len, k);   /* 32 bytes written, rest stays zero */
    else
        memcpy(k, key, key_len);

    buf = (uint8_t *)malloc(64 + msg_len);
    if (!buf) {
        memset(out, 0, 32);
        return;
    }
    for (i = 0; i < 64; i++)
        pad[i] = (uint8_t)(k[i] ^ 0x36);
    memcpy(buf, pad, 64);
    if (msg_len)
        memcpy(buf + 64, msg, msg_len);
    carto_sha256(buf, 64 + msg_len, inner);
    free(buf);

    for (i = 0; i < 64; i++)
        pad[i] = (uint8_t)(k[i] ^ 0x5c);
    memcpy(outer, pad, 64);
    memcpy(outer + 64, inner, 32);
    carto_sha256(outer, 96, out);

    memset(k, 0, sizeof k);
    memset(pad, 0, sizeof pad);
    memset(inner, 0, sizeof inner);
    memset(outer, 0, sizeof outer);
}

int carto_ct_equal(const uint8_t *a, const uint8_t *b, size_t n)
{
    uint8_t d = 0;
    size_t i;

    for (i = 0; i < n; i++)
        d |= (uint8_t)(a[i] ^ b[i]);
    return d == 0;
}
