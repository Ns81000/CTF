#define _POSIX_C_SOURCE 200809L

#include "state.h"
#include "state_internal.h"
#include "carto_sha256.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const uint8_t MAGIC[4] = { 'C', 'A', 'R', 'T' };

#define OFF_VERSION   4
#define OFF_FLAGS     5
#define OFF_RESERVED1 6
#define OFF_FIRSTRUN  8
#define OFF_ATTEMPTS  16
#define OFF_DECOYS    36
#define OFF_RINGCNT   56
#define OFF_RINGHEAD  58
#define OFF_DEBUG     60
#define OFF_RING      64
#define OFF_HMAC      320

/* ---- HMAC key (obfuscated; NEVER stored plaintext) ----------------------
 * canonical key = SHA-256("cartographer-ghost:phase0 dev key:do-not-ship")
 *             = f03ea6b5c1b869482723c0d11d635f8e9966c43a0a8def87fd1e2e950c10a7de
 * mask v1      = SHA-256("cartographer-mask-v1")
 *             = 4f09527f32262cbb959a1a743173188494dc6fa18d848981f9cd4c533de60ffc
 * mask v2      = SHA-256("cartographer-mask-v2")
 *             = ebb8aca9887d7ce1fa90e8a8ae3c2bf9904e46a4b2ec283f74bd5e37cf6b141b
 * kMaskedKey  = key XOR maskv1  = bf37f4caf39e45f3b2b9daa52c10470a
 *                                  0dbaab9b8709660604d362c631f6a822
 * kMaskedKey2 = key XOR maskv2  = 1b860a1c49c515a9ddb32879b35f7477
 *                                  0928829eb861c7b889a370a2c37bb3c5
 * The plaintext key exists only in stack buffers at runtime. Two independent
 * masked copies let carto_key_selftest() prove the unmask path is clean.
 */
static const uint8_t kMaskedKey[32] = {
    0xbf, 0x37, 0xf4, 0xca, 0xf3, 0x9e, 0x45, 0xf3,
    0xb2, 0xb9, 0xda, 0xa5, 0x2c, 0x10, 0x47, 0x0a,
    0x0d, 0xba, 0xab, 0x9b, 0x87, 0x09, 0x66, 0x06,
    0x04, 0xd3, 0x62, 0xc6, 0x31, 0xf6, 0xa8, 0x22
};

static const uint8_t kMaskedKey2[32] = {
    0x1b, 0x86, 0x0a, 0x1c, 0x49, 0xc5, 0x15, 0xa9,
    0xdd, 0xb3, 0x28, 0x79, 0xb3, 0x5f, 0x74, 0x77,
    0x09, 0x28, 0x82, 0x9e, 0xb8, 0x61, 0xc7, 0xb8,
    0x89, 0xa3, 0x70, 0xa2, 0xc3, 0x7b, 0xb3, 0xc5
};

static void unmask_with(const uint8_t masked[32], const char *seed,
                        uint8_t out[32])
{
    uint8_t mask[32];
    int i;
    carto_sha256((const uint8_t *)seed, strlen(seed), mask);
    for (i = 0; i < 32; i++)
        out[i] = (uint8_t)(masked[i] ^ mask[i]);
    memset(mask, 0, sizeof mask);
}

void carto_unmask_key(uint8_t out[32])
{
    static const char SEED[] = "cartographer-mask-v1";
    unmask_with(kMaskedKey, SEED, out);
}

void carto_unmask_key2(uint8_t out[32])
{
    static const char SEED[] = "cartographer-mask-v2";
    unmask_with(kMaskedKey2, SEED, out);
}

/* ---- little-endian codec ------------------------------------------------ */
static void put16(uint8_t *p, uint16_t v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
}

static void put32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16);
    p[3] = (uint8_t)(v >> 24);
}

static void put64(uint8_t *p, uint64_t v)
{
    int i;
    for (i = 0; i < 8; i++)
        p[i] = (uint8_t)(v >> (8 * i));
}

static uint16_t get16(const uint8_t *p)
{
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t get32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint64_t get64(const uint8_t *p)
{
    uint64_t v = 0;
    int i;
    for (i = 7; i >= 0; i--)
        v = (v << 8) | (uint64_t)p[i];
    return v;
}
/* ---- serialize / deserialize -------------------------------------------- */
static void serialize(const carto_state_t *st, uint8_t buf[CARTO_STATE_FILE_SIZE])
{
    int i;
    memset(buf, 0, CARTO_STATE_FILE_SIZE);
    memcpy(buf, MAGIC, 4);
    buf[OFF_VERSION] = 1u;
    buf[OFF_FLAGS]   = 0u;
    put64(buf + OFF_FIRSTRUN, st->first_run_ms);
    for (i = 0; i < CARTO_NUM_STAGES; i++) {
        put32(buf + OFF_ATTEMPTS + 4 * i, st->attempt_count[i]);
        put32(buf + OFF_DECOYS   + 4 * i, st->decoy_mask[i]);
    }
    put16(buf + OFF_RINGCNT,  st->ring_count);
    put16(buf + OFF_RINGHEAD, st->ring_head);
    buf[OFF_DEBUG] = st->debugger_detected;
    for (i = 0; i < CARTO_RING_SIZE; i++)
        put64(buf + OFF_RING + 8 * i, st->ring_ts[i]);
}

/* Structural sanity beyond the HMAC (defense in depth). 0 = ok, -1 = bad. */
static int deserialize(const uint8_t buf[CARTO_STATE_FILE_SIZE], carto_state_t *st)
{
    int i;
    memset(st, 0, sizeof *st);
    if (buf[OFF_FLAGS] != 0u)                                   return -1;
    if (get16(buf + OFF_RESERVED1) != 0u)                       return -1;
    if (buf[OFF_DEBUG + 1] || buf[OFF_DEBUG + 2] || buf[OFF_DEBUG + 3]) return -1;
    if (get16(buf + OFF_RINGCNT) > CARTO_RING_SIZE)             return -1;
    if (get16(buf + OFF_RINGHEAD) >= CARTO_RING_SIZE)           return -1;

    st->first_run_ms = get64(buf + OFF_FIRSTRUN);
    for (i = 0; i < CARTO_NUM_STAGES; i++) {
        st->attempt_count[i] = get32(buf + OFF_ATTEMPTS + 4 * i);
        st->decoy_mask[i]    = get32(buf + OFF_DECOYS   + 4 * i);
    }
    st->ring_count        = get16(buf + OFF_RINGCNT);
    st->ring_head         = get16(buf + OFF_RINGHEAD);
    st->debugger_detected = buf[OFF_DEBUG];
    for (i = 0; i < CARTO_RING_SIZE; i++)
        st->ring_ts[i] = get64(buf + OFF_RING + 8 * i);
    return 0;
}

/* ---- lifecycle ----------------------------------------------------------- */
int carto_state_load(const char *path, carto_state_t *st, uint64_t now_ms)
{
    uint8_t buf[CARTO_STATE_FILE_SIZE];
    uint8_t key[32], mac[32];
    FILE *f;
    size_t got;
    int bad = 0, extra;

    memset(st, 0, sizeof *st);

    f = fopen(path, "rb");
    if (!f) {
        /* First run: create fresh defaults and persist them. */
        st->first_run_ms = now_ms;
        if (carto_state_save(path, st) != 0)
            return CARTO_LOAD_TAMPERED; /* save failed; treat as unusable */
        return CARTO_LOAD_CREATED;
    }

    got   = fread(buf, 1, sizeof buf, f);
    extra = fgetc(f);
    fclose(f);
    if (got != sizeof buf || extra != EOF)
        bad = 1;

    carto_unmask_key(key);
    if (!bad) {
        if (memcmp(buf, MAGIC, 4) != 0) bad = 1;
        if (buf[OFF_VERSION] != 1u)     bad = 1;
        if (!bad) {
            carto_hmac_sha256(key, 32, buf, OFF_HMAC, mac);
            if (!carto_ct_equal(mac, buf + OFF_HMAC, 32))
                bad = 1;
        }
    }
    memset(key, 0, sizeof key);
    memset(mac, 0, sizeof mac);

    if (bad || deserialize(buf, st) != 0) {
        /* Tampered/corrupt: silently reset to first-run defaults (no output),
         * overwrite the file, and carry on. Self-defeating tampering. */
        memset(st, 0, sizeof *st);
        st->first_run_ms = now_ms;
        carto_state_save(path, st);
        return CARTO_LOAD_TAMPERED;
    }
    return CARTO_LOAD_OK;
}

int carto_state_save(const char *path, const carto_state_t *st)
{
    uint8_t buf[CARTO_STATE_FILE_SIZE];
    uint8_t key[32];
    size_t plen, w;
    char *tmp;
    FILE *f;
    int ok;

    serialize(st, buf);
    carto_unmask_key(key);
    carto_hmac_sha256(key, 32, buf, OFF_HMAC, buf + OFF_HMAC);
    memset(key, 0, sizeof key);

    plen = strlen(path);
    tmp  = (char *)malloc(plen + 5);
    if (!tmp)
        return -1;
    memcpy(tmp, path, plen);
    memcpy(tmp + plen, ".tmp", 4);
    tmp[plen + 4] = '\0';

    f = fopen(tmp, "wb");
    if (!f) {
        free(tmp);
        return -1;
    }
    w = fwrite(buf, 1, sizeof buf, f);
    fclose(f);

    /* Atomic swap so a Ctrl-C mid-write can never leave a half state file. */
    ok = (w == sizeof buf) && (rename(tmp, path) == 0);
    if (!ok)
        remove(tmp);
    free(tmp);
    return ok ? 0 : -1;
}

/* ---- mutators ------------------------------------------------------------ */
void carto_bump_attempt(carto_state_t *st, int stage)
{
    if (stage >= 0 && stage < CARTO_NUM_STAGES)
        st->attempt_count[stage] += 1u;
}

void carto_mark_decoy(carto_state_t *st, int stage, uint32_t decoy_bit)
{
    if (stage >= 0 && stage < CARTO_NUM_STAGES)
        st->decoy_mask[stage] |= decoy_bit;
}

void carto_record_interaction(carto_state_t *st, uint64_t now_ms)
{
    st->ring_ts[st->ring_head] = now_ms;
    st->ring_head = (uint16_t)((st->ring_head + 1u) % CARTO_RING_SIZE);
    if (st->ring_count < CARTO_RING_SIZE)
        st->ring_count++;
}

void carto_set_debugger_detected(carto_state_t *st, int v)
{
    st->debugger_detected = v ? 1u : 0u;
}
