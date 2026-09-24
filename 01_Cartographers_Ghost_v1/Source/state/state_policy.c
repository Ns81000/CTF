#define _POSIX_C_SOURCE 200809L

#include "state.h"
#include "state_internal.h"
#include "policy.h"
#include "carto_sha256.h"

#include <float.h>
#include <math.h>
#include <string.h>
#include <time.h>

/*
 * ---- TEST-ONLY TIME SCALE (Phase FINAL, kickoff section 2) --------------
 * Compiled in ONLY when the build defines CARTO_TEST_TIME_SCALE_ENABLE
 * (src/state/Makefile: `make CARTO_TEST_BUILD=1`).  Every shipped binary is
 * built without that define, so neither this helper nor the literal
 * environment-variable name reaches their .rodata -- asserted by
 * src/final/verify_adversarial.sh against the packaged copies.
 *
 * When compiled in, CARTO_TEST_TIME_SCALE=<n> divides every elapsed-time
 * threshold in this library AND the inter-arrival uniformity threshold, so
 * the calibrated pacing budget can be exercised in seconds instead of tens
 * of minutes while keeping the decision semantics identical:
 *     CARTO_TEST_TIME_SCALE=60  ->  a 5100 s threshold fires at 85 s
 *                                   a 150 ms stddev floor behaves like 2.5 ms
 * (Scaling BOTH is required: a time-compressed paced query loop shrinks its
 * inter-arrival deltas by the same factor, so scaling only one side would
 * make the compressed run look scripted-uniform and get poisoned.)
 */
#ifdef CARTO_TEST_TIME_SCALE_ENABLE
#include <stdlib.h>
static uint32_t carto_test_time_scale(void)
{
    static long cached = -1;
    if (cached < 0) {
        const char *s = getenv("CARTO_TEST_TIME_SCALE");
        char       *end = NULL;
        long        v = 1;
        if (s != NULL && *s != '\0') {
            long t = strtol(s, &end, 10);
            if (end != NULL && *end == '\0' && t >= 1L && t <= 1000000L)
                v = t;
        }
        cached = v;
    }
    return (uint32_t)cached;
}
#define CARTO_STDDEV_LOW_MS_EFF \
    (CARTO_STDDEV_LOW_MS / (double)carto_test_time_scale())
#else
#define carto_test_time_scale() 1u
#define CARTO_STDDEV_LOW_MS_EFF CARTO_STDDEV_LOW_MS
#endif

uint64_t carto_time_since_first_run_ms(const carto_state_t *st, uint64_t now_ms)
{
    return (now_ms > st->first_run_ms) ? (now_ms - st->first_run_ms) : 0u;
}

/*
 * Population stddev (ms) of inter-arrival deltas of the last N recorded
 * interactions. Returns HUGE_VAL when there is not enough data to judge
 * (fewer than CARTO_MIN_TIMING_DELTAS deltas) -- "insufficient evidence"
 * must never read as "suspiciously uniform".
 */
double carto_timing_stddev_ms(const carto_state_t *st)
{
    uint64_t ordered[CARTO_RING_SIZE];
    double   deltas[CARTO_RING_SIZE];
    double   sum = 0.0, mean, var = 0.0;
    int n, nd, i, start;

    n = (int)st->ring_count;
    if (n < 2)
        return HUGE_VAL;
    nd = n - 1;
    if (nd < CARTO_MIN_TIMING_DELTAS)
        return HUGE_VAL;

    start = (int)st->ring_head - n;
    if (start < 0)
        start += CARTO_RING_SIZE;
    for (i = 0; i < n; i++)
        ordered[i] = st->ring_ts[(start + i) % CARTO_RING_SIZE];

    for (i = 0; i < nd; i++) {
        uint64_t a = ordered[i], b = ordered[i + 1];
        deltas[i] = (b > a) ? (double)(b - a) : 0.0; /* clamp clock glitches */
    }
    for (i = 0; i < nd; i++)
        sum += deltas[i];
    mean = sum / (double)nd;
    for (i = 0; i < nd; i++) {
        double d = deltas[i] - mean;
        var += d * d;
    }
    var /= (double)nd;
    return sqrt(var);
}

unsigned carto_should_escalate(const carto_state_t *st, int stage, uint64_t now_ms)
{
    unsigned reasons = 0u;
    uint32_t limit = CARTO_T_FAST_SEC_DEFAULT;

    if (stage >= 0 && stage < CARTO_NUM_STAGES)
        limit = carto_t_fast_sec[stage];

    /* Test-only scaling (no-op in shipped builds; see the block above). */
    limit /= carto_test_time_scale();
    if (limit == 0u)
        limit = 1u;

    if (carto_time_since_first_run_ms(st, now_ms) < (uint64_t)limit * 1000u)
        reasons |= CARTO_ESC_TIME_FAST;
    if (carto_timing_stddev_ms(st) <= CARTO_STDDEV_LOW_MS_EFF)
        reasons |= CARTO_ESC_TIMING_UNIFORM;
    if (st->debugger_detected)
        reasons |= CARTO_ESC_DEBUGGER;
    return reasons;
}

int carto_decoy_submitted(const carto_state_t *st, int stage, uint32_t decoy_bit)
{
    if (stage < 0 || stage >= CARTO_NUM_STAGES)
        return 0;
    return (st->decoy_mask[stage] & decoy_bit) ? 1 : 0;
}

int carto_get_debugger_detected(const carto_state_t *st)
{
    return st->debugger_detected ? 1 : 0;
}

int carto_lookup_decoy(int stage, const char *submitted_flag)
{
    int i;
    if (!submitted_flag)
        return -1;
    for (i = 0; i < CARTO_DECOY_TABLE_LEN; i++) {
        const carto_decoy_entry_t *e = &carto_decoy_table[i];
        if (e->stage == stage && strcmp(e->flag, submitted_flag) == 0)
            return (int)e->branch;
    }
    return -1;
}

uint64_t carto_now_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return (uint64_t)ts.tv_sec * 1000u + (uint64_t)(ts.tv_nsec / 1000000u);
}

/* ---- known-answer self-tests --------------------------------------------- */
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
    if (check32(d, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"))
        return -1;
    carto_sha256((const uint8_t *)"abc", 3, d);
    if (check32(d, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"))
        return -1;
    return 0;
}

/* Vectors transcribed from RFC 4231 section 4 (verified against the RFC text
 * fetched during Phase 0) and cross-checked against python hashlib via the
 * differential vector file in the test harness. */
int carto_hmac_selftest(void)
{
    uint8_t mac[32], k4[25], d4[50], k6[131];
    int i;
    static const uint8_t K1[20] = {
        0x0b, 0x0b, 0x0b, 0x0b, 0x0b, 0x0b, 0x0b, 0x0b,
        0x0b, 0x0b, 0x0b, 0x0b, 0x0b, 0x0b, 0x0b, 0x0b,
        0x0b, 0x0b, 0x0b, 0x0b
    };

    /* TC1 */ carto_hmac_sha256(K1, sizeof K1, (const uint8_t *)"Hi There", 8, mac);
    if (check32(mac, "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"))
        return -1;
    /* TC2 */ carto_hmac_sha256((const uint8_t *)"Jefe", 4,
                               (const uint8_t *)"what do ya want for nothing?", 28, mac);
    if (check32(mac, "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"))
        return -1;
    /* TC4 */ for (i = 0; i < 25; i++) k4[i] = (uint8_t)(i + 1);
    memset(d4, 0xcd, sizeof d4);
    carto_hmac_sha256(k4, sizeof k4, d4, sizeof d4, mac);
    if (check32(mac, "82558a389a443c0ea4cc819899f2083a85f0faa3e578f8077a2e3ff46729665b"))
        return -1;
    /* TC6 */ memset(k6, 0xaa, sizeof k6);
    carto_hmac_sha256(k6, sizeof k6,
                      (const uint8_t *)"Test Using Larger Than Block-Size Key - Hash Key First",
                      54, mac);
    if (check32(mac, "60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54"))
        return -1;
    return 0;
}

int carto_key_selftest(void)
{
    uint8_t a[32], b[32];
    carto_unmask_key(a);
    carto_unmask_key2(b);
    return carto_ct_equal(a, b, 32) ? 0 : -1;
}
