/*
 * state_core.c -- the cartographer v2 state record.
 *
 * One 1168-byte record holds every tool's interaction history: per-stage
 * attempt counters, per-branch decoy bits, gate evidence, a 64-entry rolling
 * interaction ring, a chain digest over the record and an HMAC over
 * everything but the chain and the tag itself.
 *
 * Any load failure of any kind is a SILENT fresh-state reset.  A tool never
 * reports that a state was unreadable, never exits non-zero, and never
 * writes a diagnostic: a damaged record simply starts over.
 */
#define _POSIX_C_SOURCE 200809L

#include "state.h"
#include "policy.h"
#include "carto_sha256.h"
#include "keys_blob.h"

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

static const uint8_t MAGIC[4] = { 'C', 'G', 'V', '2' };

#define OFF_MAGIC     0
#define OFF_VERSION   4
#define OFF_FLAGS     6
#define OFF_FIRSTRUN  8
#define OFF_ATTEMPTS  0x010
#define OFF_WRONGS    0x028
#define OFF_GATES     0x040
#define OFF_RINGCOUNT 0x058
#define OFF_RINGHEAD  0x05A
#define OFF_DEBUG     0x05C
#define OFF_DISTINCT  0x05D
#define OFF_RING      0x060
#define OFF_CHAIN     0x460
#define OFF_HMAC      0x470
#define MAC_LEN       32
#define CHAIN_LEN     16

/* ---- little-endian codec ------------------------------------------------- */
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

/* The layout leaves three of the four "reserved" bytes before the ring:
 * 0x05D + 4 would already be the ring's first entry.  Those three bytes
 * carry the distinct-figure counter (24-bit, saturating). */
static void put24(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16);
}

static uint32_t get24(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16);
}

/* ---- key material ------------------------------------------------------- */

void carto_unmask_blob(const uint8_t masked[32], const char *mask_seed,
                       uint8_t out[32])
{
    uint8_t mask[32];
    int i;
    carto_sha256((const uint8_t *)mask_seed, strlen(mask_seed), mask);
    for (i = 0; i < 32; i++)
        out[i] = (uint8_t)(masked[i] ^ mask[i]);
    memset(mask, 0, sizeof mask);
}

void carto_unmask_master(uint8_t out[32])
{
    carto_unmask_blob(kMaskedMaster, CARTO_MASTER_MASK_SEED, out);
}

void carto_state_key(uint8_t out[32])
{
    uint8_t master[32];
    uint8_t buf[64];
    static const char TAG[] = "ghost2:state";

    carto_unmask_master(master);
    memcpy(buf, master, 32);
    memcpy(buf + 32, TAG, sizeof TAG - 1);
    carto_sha256(buf, 32 + sizeof TAG - 1, out);
    memset(master, 0, sizeof master);
    memset(buf, 0, sizeof buf);
}

void carto_derive_stage_key(int stage, uint8_t out[32])
{
    uint8_t master[32];
    uint8_t buf[64];
    char tag[32];
    int n;

    if (stage < 0 || stage >= CARTO_NUM_STAGES) {
        memset(out, 0, 32);
        return;
    }
    carto_unmask_master(master);
    memcpy(tag, "ghost2:stage:", 13);
    n = 13;
    tag[n++] = (char)('0' + stage);
    memcpy(buf, master, 32);
    memcpy(buf + 32, tag, (size_t)n);
    carto_sha256(buf, 32 + (size_t)n, out);
    memset(master, 0, sizeof master);
    memset(buf, 0, sizeof buf);
}

/* ---- chain --------------------------------------------------------------
 * The chain is a digest over the canonical serialisation of everything that
 * precedes it.  It is recomputed at load: a record whose fields were edited
 * without re-deriving the chain is rejected exactly like a bad HMAC.
 */
static void chain_of(const uint8_t *body, uint8_t out[CHAIN_LEN])
{
    uint8_t d[32];
    carto_sha256(body, OFF_CHAIN, d);
    memcpy(out, d, CHAIN_LEN);
}

/* The per-stage tags are derived FROM the chain, so they must not feed it:
 * the chain is taken over a view of the record with the tag halves zeroed. */
static void zero_tags(uint8_t *buf)
{
    int i;
    for (i = 0; i < CARTO_NUM_STAGES; i++)
        put16(buf + OFF_GATES + 4 * i + 2, 0);
}

uint32_t carto_state_chain_digest32(const carto_state_t *st)
{
    return (uint32_t)st->chain[0] | ((uint32_t)st->chain[1] << 8) |
           ((uint32_t)st->chain[2] << 16) | ((uint32_t)st->chain[3] << 24);
}

uint32_t carto_gate_tag(const carto_state_t *st, int stage)
{
    uint8_t d[32];
    char seed[32];
    uint32_t salt;
    int n;

    if (stage < 0 || stage >= CARTO_NUM_STAGES)
        return 0;
    memcpy(seed, "ghost2:gtag:", 12);
    n = 12;
    seed[n++] = (char)('0' + stage);
    carto_sha256((const uint8_t *)seed, (size_t)n, d);
    salt = (uint32_t)d[0] | ((uint32_t)d[1] << 8) |
           ((uint32_t)d[2] << 16) | ((uint32_t)d[3] << 24);
    return (carto_state_chain_digest32(st) ^ salt) & 0xFFFFu;
}

/* ---- serialise / deserialise -------------------------------------------- */

/* Returns 0 on success, non-zero when the buffer is not a valid record. */
static int parse(const uint8_t *buf, carto_state_t *st)
{
    int i;

    if (memcmp(buf + OFF_MAGIC, MAGIC, 4) != 0)
        return -1;
    if (get16(buf + OFF_VERSION) != 2u)
        return -1;
    if (get16(buf + OFF_FLAGS) != 0u)
        return -1;

    st->first_run_ms = get64(buf + OFF_FIRSTRUN);
    for (i = 0; i < CARTO_NUM_STAGES; i++) {
        st->attempt_count[i] = get32(buf + OFF_ATTEMPTS + 4 * i);
        st->wrong_flag_mask[i] = get32(buf + OFF_WRONGS + 4 * i);
        st->gate_state[i] = get32(buf + OFF_GATES + 4 * i);
        if (st->gate_state[i] & ~(CARTO_GB_MASK | CARTO_GTAG_MASK))
            return -1;
    }
    st->ring_count = get16(buf + OFF_RINGCOUNT);
    st->ring_head = get16(buf + OFF_RINGHEAD);
    st->debugger_flag = buf[OFF_DEBUG];
    st->distinct_figures = get24(buf + OFF_DISTINCT);

    if (st->ring_head >= CARTO_RING_SIZE)
        return -1;
    if (st->debugger_flag > 1u)
        return -1;
    memcpy(st->ring, buf + OFF_RING,
           (size_t)CARTO_RING_SIZE * CARTO_RING_ENTRY_SIZE);
    memcpy(st->chain, buf + OFF_CHAIN, CHAIN_LEN);
    return 0;
}

static void build(const carto_state_t *st, uint8_t *buf)
{
    int i;

    memset(buf, 0, CARTO_STATE_FILE_SIZE);
    memcpy(buf + OFF_MAGIC, MAGIC, 4);
    put16(buf + OFF_VERSION, 2u);
    put16(buf + OFF_FLAGS, 0u);
    put64(buf + OFF_FIRSTRUN, st->first_run_ms);
    for (i = 0; i < CARTO_NUM_STAGES; i++) {
        put32(buf + OFF_ATTEMPTS + 4 * i, st->attempt_count[i]);
        put32(buf + OFF_WRONGS + 4 * i, st->wrong_flag_mask[i]);
        put32(buf + OFF_GATES + 4 * i, st->gate_state[i]);
    }
    put16(buf + OFF_RINGCOUNT, st->ring_count);
    put16(buf + OFF_RINGHEAD, st->ring_head);
    buf[OFF_DEBUG] = st->debugger_flag;
    put24(buf + OFF_DISTINCT, st->distinct_figures);
    memcpy(buf + OFF_RING, st->ring,
           (size_t)CARTO_RING_SIZE * CARTO_RING_ENTRY_SIZE);
    memcpy(buf + OFF_CHAIN, st->chain, CHAIN_LEN);
}

static void state_path(char *out, size_t cap, const char *root,
                       const char *suffix)
{
    size_t n;

    if (!root || !*root)
        root = ".";
    n = strlen(root);
    if (n >= cap)
        n = cap - 1;
    memcpy(out, root, n);
    out[n] = '\0';
    if (n > 0 && out[n - 1] == '/')
        n--;
    snprintf(out + n, cap - n, "/%s%s", CARTO_STATE_NAME, suffix);
}

static void fresh(carto_state_t *st, uint64_t now_ms)
{
    memset(st, 0, sizeof *st);
    st->first_run_ms = now_ms;
}

/* ---- load / save -------------------------------------------------------- */

int carto_state_load(const char *root, carto_state_t *st, uint64_t now_ms)
{
    char path[4096];
    uint8_t buf[CARTO_STATE_FILE_SIZE];
    uint8_t key[32], mac[MAC_LEN], chain[CHAIN_LEN];
    FILE *fh;
    size_t got;
    int result = CARTO_LOAD_OK;

    state_path(path, sizeof path, root, "");
    /* If path is a symlink, do not follow it (containment & anti-tamper rule) */
    {
        struct stat st_l;
        if (lstat(path, &st_l) == 0 && S_ISLNK(st_l.st_mode)) {
            unlink(path);
            fresh(st, now_ms);
            result = CARTO_LOAD_TAMPERED;
            goto finish;
        }
    }
    fh = fopen(path, "rb");
    if (!fh) {
        fresh(st, now_ms);
        result = CARTO_LOAD_CREATED;
        goto finish;
    }
    got = fread(buf, 1, CARTO_STATE_FILE_SIZE, fh);
    if (got != CARTO_STATE_FILE_SIZE || fgetc(fh) != EOF) {
        fclose(fh);
        fresh(st, now_ms);
        result = CARTO_LOAD_TAMPERED;
        goto finish;
    }
    fclose(fh);

    carto_state_key(key);
    carto_hmac_sha256(key, 32, buf, OFF_HMAC, mac);
    if (!carto_ct_equal(mac, buf + OFF_HMAC, MAC_LEN)) {
        fresh(st, now_ms);
        result = CARTO_LOAD_TAMPERED;
        goto finish;
    }
    /* The chain is a digest over the record with the derived tags absent. */
    {
        uint8_t view[CARTO_STATE_FILE_SIZE];
        memcpy(view, buf, CARTO_STATE_FILE_SIZE);
        zero_tags(view);
        chain_of(view, chain);
    }
    if (!carto_ct_equal(chain, buf + OFF_CHAIN, CHAIN_LEN)) {
        fresh(st, now_ms);
        result = CARTO_LOAD_TAMPERED;
        goto finish;
    }
    if (parse(buf, st) != 0) {
        fresh(st, now_ms);
        result = CARTO_LOAD_TAMPERED;
        goto finish;
    }
    /* A record stamped in the future is nonsense: a clock that was moved
     * backwards must not be able to fake a long history. */
    if (st->first_run_ms > now_ms + 60000ull) {
        fresh(st, now_ms);
        result = CARTO_LOAD_TAMPERED;
        goto finish;
    }

finish:
    memset(key, 0, sizeof key);
    memset(mac, 0, sizeof mac);
    /* Evidence the record cannot justify is dropped, silently. */
    carto_recompute_gates(st, now_ms);
    if (result == CARTO_LOAD_CREATED || result == CARTO_LOAD_TAMPERED)
        carto_ring_append(st, now_ms, CARTO_STAGE_LEDGER, CARTO_OP_CREATE, 0);
    carto_state_save(root, st);
    return result;
}

int carto_state_save(const char *root, const carto_state_t *st)
{
    char path[4096], tmp[4096];
    uint8_t buf[CARTO_STATE_FILE_SIZE];
    uint8_t key[32], mac[MAC_LEN], chain[CHAIN_LEN], view[CARTO_STATE_FILE_SIZE];
    carto_state_t tmpst;
    int fd, i;

    state_path(path, sizeof path, root, "");
    state_path(tmp, sizeof tmp, root, ".tmp");

    /* If target path is a symlink, remove it so we never overwrite through a symlink */
    {
        struct stat st_l;
        if (lstat(path, &st_l) == 0 && S_ISLNK(st_l.st_mode))
            unlink(path);
    }

    /* 1. chain over the record with the tags absent */
    build(st, buf);
    memcpy(view, buf, CARTO_STATE_FILE_SIZE);
    zero_tags(view);
    chain_of(view, chain);
    memcpy(buf + OFF_CHAIN, chain, CHAIN_LEN);

    /* 2. tags derived from that chain */
    tmpst = *st;
    memcpy(tmpst.chain, chain, CHAIN_LEN);
    for (i = 0; i < CARTO_NUM_STAGES; i++) {
        uint32_t tags = (carto_gate_tag(&tmpst, i) << CARTO_GTAG_SHIFT);
        put32(buf + OFF_GATES + 4 * i,
              (st->gate_state[i] & 0xFFFFu) | tags);
    }

    /* 3. one tag over everything */
    carto_state_key(key);
    carto_hmac_sha256(key, 32, buf, OFF_HMAC, mac);
    memcpy(buf + OFF_HMAC, mac, MAC_LEN);
    memset(key, 0, sizeof key);
    memset(mac, 0, sizeof mac);

    unlink(tmp);
    fd = open(tmp, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd < 0)
        return -1;
    if (write(fd, buf, CARTO_STATE_FILE_SIZE) != CARTO_STATE_FILE_SIZE) {
        close(fd);
        unlink(tmp);
        return -1;
    }
    fsync(fd);
    close(fd);
    if (rename(tmp, path) != 0) {
        unlink(tmp);
        return -1;
    }
    return 0;
}

/* ---- mutators ----------------------------------------------------------- */

void carto_bump_attempt(carto_state_t *st, int stage)
{
    if (stage < 0 || stage >= CARTO_NUM_STAGES)
        return;
    if (st->attempt_count[stage] != 0xFFFFFFFFu)
        st->attempt_count[stage]++;
}

void carto_mark_wrong_flag(carto_state_t *st, int stage, uint32_t branch_bit)
{
    if (stage < 0 || stage >= CARTO_NUM_STAGES)
        return;
    st->wrong_flag_mask[stage] |= branch_bit;
}

int carto_wrong_flag_seen(const carto_state_t *st, int stage, uint32_t bit)
{
    if (stage < 0 || stage >= CARTO_NUM_STAGES)
        return 0;
    return (st->wrong_flag_mask[stage] & bit) ? 1 : 0;
}

void carto_set_debugger_flag(carto_state_t *st, int v)
{
    st->debugger_flag = v ? 1u : 0u;
}

// cppcheck-suppress unusedFunction
int carto_get_debugger_flag(const carto_state_t *st)
{
    return st->debugger_flag ? 1 : 0;
}

void carto_note_figure(carto_state_t *st, uint16_t fingerprint)
{
    uint32_t occupied = (st->ring_count < CARTO_RING_SIZE)
                      ? (uint32_t)st->ring_count : (uint32_t)CARTO_RING_SIZE;
    int latest_idx = ((int)st->ring_head - 1 + CARTO_RING_SIZE) % CARTO_RING_SIZE;
    uint32_t i;

    for (i = 0; i < occupied; i++) {
        int idx = (int)i;
        const uint8_t *e;
        uint32_t aux;
        uint16_t fig;

        if (st->ring_count > 0 && idx == latest_idx)
            continue;

        e = st->ring[idx];
        if (e[CARTO_RING_OFF_STAGE] != CARTO_STAGE_ORACLE)
            continue;
        if (e[CARTO_RING_OFF_OP] != CARTO_OP_QUERY &&
            e[CARTO_RING_OFF_OP] != CARTO_OP_TALLY)
            continue;

        aux = (uint32_t)e[CARTO_RING_OFF_AUX] |
              ((uint32_t)e[CARTO_RING_OFF_AUX + 1] << 8) |
              ((uint32_t)e[CARTO_RING_OFF_AUX + 2] << 16) |
              ((uint32_t)e[CARTO_RING_OFF_AUX + 3] << 24);
        fig = (uint16_t)((aux & 0xFFFF0000u) >> 16);
        if (fig == fingerprint)
            return;
    }

    if (st->distinct_figures < 0xFFFFFFu)
        st->distinct_figures++;
}

/* ---- ring --------------------------------------------------------------- */

void carto_ring_append(carto_state_t *st, uint64_t ts_ms, int stage, int op,
                       uint32_t aux)
{
    uint8_t *e;
    uint16_t dt = 0;

    if (stage < 0 || stage >= CARTO_NUM_STAGES)
        stage = 0;
    if (op < 0 || op > 255)
        op = 0;

    if (st->ring_count > 0) {
        int prev_idx = (int)st->ring_head - 1;
        if (prev_idx < 0)
            prev_idx = CARTO_RING_SIZE - 1;
        {
            uint64_t prev = get64(st->ring[prev_idx] + CARTO_RING_OFF_TS);
            if (ts_ms > prev) {
                uint64_t d = ts_ms - prev;
                dt = (d > 0xFFFFull) ? 0xFFFFu : (uint16_t)d;
            }
        }
    }

    e = st->ring[st->ring_head];
    put64(e + CARTO_RING_OFF_TS, ts_ms);
    e[CARTO_RING_OFF_STAGE] = (uint8_t)stage;
    e[CARTO_RING_OFF_OP] = (uint8_t)op;
    put16(e + CARTO_RING_OFF_DT, dt);
    put32(e + CARTO_RING_OFF_AUX, aux);

    st->ring_head = (uint16_t)((st->ring_head + 1) % CARTO_RING_SIZE);
    if (st->ring_count < 0xFFFFu)
        st->ring_count++;
}

const uint8_t *carto_ring_entry(const carto_state_t *st, int i)
{
    if (i < 0 || i >= CARTO_RING_SIZE)
        return NULL;
    return st->ring[i];
}

uint64_t carto_time_since_first_run_ms(const carto_state_t *st, uint64_t now_ms)
{
    if (now_ms <= st->first_run_ms)
        return 0;
    return now_ms - st->first_run_ms;
}

uint64_t carto_now_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return (uint64_t)ts.tv_sec * 1000ull + (uint64_t)(ts.tv_nsec / 1000000);
}

/* ---- known-answer self-tests -------------------------------------------- */

static int hex2bin32(const char *hex, uint8_t out[32])
{
    int i, hi, lo;

    if (strlen(hex) != 64)
        return -1;
    for (i = 0; i < 32; i++) {
        char c1 = hex[2 * i], c2 = hex[2 * i + 1];
        if (c1 >= '0' && c1 <= '9')      hi = c1 - '0';
        else if (c1 >= 'a' && c1 <= 'f') hi = c1 - 'a' + 10;
        else return -1;
        if (c2 >= '0' && c2 <= '9')      lo = c2 - '0';
        else if (c2 >= 'a' && c2 <= 'f') lo = c2 - 'a' + 10;
        else return -1;
        out[i] = (uint8_t)((hi << 4) | lo);
    }
    return 0;
}

static int check32(const uint8_t got[32], const char *hex)
{
    uint8_t want[32];
    if (hex2bin32(hex, want) != 0)
        return -1;
    return carto_ct_equal(got, want, 32) ? 0 : -1;
}

int carto_sha_selftest(void)
{
    uint8_t d[32];

    carto_sha256((const uint8_t *)"", 0, d);
    if (check32(d, "e3b0c44298fc1c149afbf4c8996fb924"
                  "27ae41e4649b934ca495991b7852b855"))
        return -1;
    carto_sha256((const uint8_t *)"abc", 3, d);
    if (check32(d, "ba7816bf8f01cfea414140de5dae2223"
                  "b00361a396177a9cb410ff61f20015ad"))
        return -1;
    return 0;
}

/* Vectors from RFC 4231 section 4. */
int carto_hmac_selftest(void)
{
    uint8_t mac[32], k4[25], d4[50], k6[131];
    int i;
    static const uint8_t K1[20] = {
        0x0b, 0x0b, 0x0b, 0x0b, 0x0b, 0x0b, 0x0b, 0x0b,
        0x0b, 0x0b, 0x0b, 0x0b, 0x0b, 0x0b, 0x0b, 0x0b,
        0x0b, 0x0b, 0x0b, 0x0b
    };

    carto_hmac_sha256(K1, sizeof K1, (const uint8_t *)"Hi There", 8, mac);
    if (check32(mac, "b0344c61d8db38535ca8afceaf0bf12b"
                     "881dc200c9833da726e9376c2e32cff7"))
        return -1;
    carto_hmac_sha256((const uint8_t *)"Jefe", 4,
                      (const uint8_t *)"what do ya want for nothing?", 28, mac);
    if (check32(mac, "5bdcc146bf60754e6a042426089575c7"
                     "5a003f089d2739839dec58b964ec3843"))
        return -1;
    for (i = 0; i < 25; i++)
        k4[i] = (uint8_t)(i + 1);
    memset(d4, 0xcd, sizeof d4);
    carto_hmac_sha256(k4, sizeof k4, d4, sizeof d4, mac);
    if (check32(mac, "82558a389a443c0ea4cc819899f2083a"
                     "85f0faa3e578f8077a2e3ff46729665b"))
        return -1;
    memset(k6, 0xaa, sizeof k6);
    carto_hmac_sha256(k6, sizeof k6,
                      (const uint8_t *)"Test Using Larger Than Block-Size Key"
                                       " - Hash Key First", 54, mac);
    if (check32(mac, "60e431591ee0b67f0d8a26aacbf5b77f"
                     "8e0bc6213728c5140546040f0ee37f54"))
        return -1;
    return 0;
}

int carto_key_selftest(void)
{
    uint8_t ks[32], k0[32], k0b[32], k1[32];

    /* the handshake key and every stage key must be distinct, and the
     * derivation must be stable across calls */
    carto_state_key(ks);
    carto_derive_stage_key(0, k0);
    carto_derive_stage_key(0, k0b);
    carto_derive_stage_key(1, k1);
    if (!carto_ct_equal(k0, k0b, 32))
        return -1;
    if (carto_ct_equal(k0, k1, 32) || carto_ct_equal(k0, ks, 32) ||
        carto_ct_equal(k1, ks, 32))
        return -1;
    return 0;
}
