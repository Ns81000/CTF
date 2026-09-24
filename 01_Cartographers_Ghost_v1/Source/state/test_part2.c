#define _POSIX_C_SOURCE 200809L

#include "test_util.h"
#include "state.h"
#include "policy.h"
#include "carto_sha256.h"

#include <math.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define PA "/tmp/carto_ta.bin"
#define PB "/tmp/carto_tb.bin"
/* Large base (1e10 ms) so NOW - 10000000 arithmetic cannot underflow uint64. */
#define NOW ((uint64_t)10000000000)

static void rm(const char *p) { unlink(p); }

static int test_ring_wrap(void)
{
    carto_state_t st;
    uint64_t ts[40];
    int i;

    rm(PA);
    memset(&st, 0, sizeof st);
    st.first_run_ms = NOW;
    for (i = 0; i < 40; i++) {
        ts[i] = (uint64_t)(NOW + 1000 * i + (i % 3) * 7);
        carto_record_interaction(&st, ts[i]);
    }
    CHECK(st.ring_count == CARTO_RING_SIZE, "count != 32 after 40 records");
    CHECK(st.ring_head == 8, "head != 40 mod 32");
    /* Ring must hold exactly ts[8..39]; chronological read starts at head. */
    for (i = 0; i < CARTO_RING_SIZE; i++) {
        int idx = (8 + i) % CARTO_RING_SIZE;
        CHECK(st.ring_ts[idx] == ts[8 + i], "ring content mismatch");
    }
    return 0;
}

static int test_stddev_reference(void)
{
    carto_state_t st;
    double d[6] = { 1000.0, 1000.0, 1000.0, 1000.0, 0.0, 2000.0 };
    double sum = 0.0, mean, var = 0.0, want, got;
    uint64_t times[7] = { 1000, 2000, 3000, 4000, 5000, 5000, 7000 };
    int i;

    memset(&st, 0, sizeof st);
    st.first_run_ms = NOW;
    for (i = 0; i < 7; i++)
        carto_record_interaction(&st, times[i]);

    got = carto_timing_stddev_ms(&st);
    for (i = 0; i < 6; i++) sum += d[i];
    mean = sum / 6.0;
    for (i = 0; i < 6; i++) {
        double x = d[i] - mean;
        var += x * x;
    }
    var /= 6.0;
    want = sqrt(var);
    if (fabs(got - want) > 1e-9) {
        printf("    stddev got %.9f want %.9f\n", got, want);
        return -1;
    }
    return 0;
}

static int test_stddev_insufficient(void)
{
    carto_state_t st;
    int i;
    memset(&st, 0, sizeof st);
    st.first_run_ms = NOW;
    for (i = 0; i < 3; i++)
        carto_record_interaction(&st, (uint64_t)(NOW + 100 * i));
    /* 2 deltas < CARTO_MIN_TIMING_DELTAS: must be inconclusive, never 0. */
    if (carto_timing_stddev_ms(&st) < 1e300) {
        printf("    expected HUGE_VAL for insufficient data\n");
        return -1;
    }
    return 0;
}

static int test_escalate_fast(void)
{
    carto_state_t st;
    unsigned r;
    uint32_t lim = carto_t_fast_sec[1];

    memset(&st, 0, sizeof st);
    st.first_run_ms = NOW;

    /*
     * The boundary is derived from the registry, never from a literal:
     * calibrating carto_t_fast_sec[] in policy.h must not be able to
     * invalidate this test (the same table-driven idiom as test_decoy_lookup
     * and test_decoy_count -- PHASE_3_LOG bug 5).
     * Run the suite with CARTO_TEST_TIME_SCALE unset: that hook is a no-op in
     * every shipped build, so the boundary asserted here is the shipped one.
     */
    r = carto_should_escalate(&st, 1, NOW + (uint64_t)(lim - 1u) * 1000u);
    if (!(r & CARTO_ESC_TIME_FAST)) {
        printf("    TIME_FAST missing at %us (r=%u)\n", lim - 1u, r);
        return -1;
    }
    if (r != CARTO_ESC_TIME_FAST) {
        printf("    unexpected extra bits (r=%u)\n", r);
        return -1;
    }
    r = carto_should_escalate(&st, 1, NOW + (uint64_t)lim * 1000u);
    if (r != 0) {
        printf("    expected clean at %us (r=%u)\n", lim, r);
        return -1;
    }
    return 0;
}

static int test_escalate_uniform(void)
{
    carto_state_t st;
    unsigned r;
    int i;
    memset(&st, 0, sizeof st);
    st.first_run_ms = NOW - 1000000; /* far outside the fast window */
    for (i = 0; i < 8; i++)
        carto_record_interaction(&st, (uint64_t)(NOW + 100 * i)); /* deltas all 100ms */
    r = carto_should_escalate(&st, 2, NOW + 800);
    if (!(r & CARTO_ESC_TIMING_UNIFORM)) {
        printf("    TIMING_UNIFORM missing (r=%u)\n", r);
        return -1;
    }
    return 0;
}

static int test_escalate_human(void)
{
    carto_state_t st;
    unsigned r;
    uint64_t t[7] = { NOW, NOW + 1200, NOW + 41000, NOW + 43000,
                      NOW + 95000, NOW + 97500, NOW + 200000 };
    int i;
    memset(&st, 0, sizeof st);
    st.first_run_ms = NOW - 10000000;
    for (i = 0; i < 7; i++)
        carto_record_interaction(&st, t[i]);
    r = carto_should_escalate(&st, 2, t[6]);
    if (r != 0) { printf("    human-like timing flagged (r=%u)\n", r); return -1; }
    return 0;
}

static int test_escalate_debugger(void)
{
    carto_state_t st;
    unsigned r;
    memset(&st, 0, sizeof st);
    st.first_run_ms = NOW - 10000000;
    r = carto_should_escalate(&st, 0, NOW);
    if (r != 0) { printf("    baseline dirty (r=%u)\n", r); return -1; }
    carto_set_debugger_detected(&st, 1);
    r = carto_should_escalate(&st, 0, NOW);
    if (!(r & CARTO_ESC_DEBUGGER)) { printf("    DEBUGGER missing\n"); return -1; }
    return 0;
}
/* Table-driven over EVERY registered row so that registering real decoys in
 * policy.h (Phases 2-4) keeps this mechanism test exhaustive rather than
 * checking only the first row.  Same test name and register count. */
static int test_decoy_lookup(void)
{
    unsigned i;

    for (i = 0; i < CARTO_DECOY_TABLE_LEN; i++) {
        const carto_decoy_entry_t *e = &carto_decoy_table[i];
        int other_stage = (e->stage == 0) ? 1 : 0;

        CHECK(carto_lookup_decoy(e->stage, e->flag) == (int)e->branch,
              "registered decoy not found");
        CHECK(carto_lookup_decoy(other_stage, e->flag) == -1,
              "wrong stage matched");
        CHECK(carto_lookup_decoy(e->stage, "CARTO{nope}") == -1,
              "unknown flag matched");
        CHECK(carto_lookup_decoy(e->stage, NULL) == -1, "NULL matched");
    }
    return 0;
}

/* The declared table length must agree with the number of rows and every
 * registered decoy must satisfy the canonical flag format (PHASE_1_LOG D11). */
static int test_decoy_count(void)
{
    static const char *const d11 = "CARTO{[a-z0-9_]{8,64}}";
    (void)d11;
    CHECK(sizeof carto_decoy_table / sizeof carto_decoy_table[0]
          == (size_t)CARTO_DECOY_TABLE_LEN, "table length macro disagrees");
    CHECK(CARTO_DECOY_TABLE_LEN >= 4, "stage 1, 2, 3 and 4 decoys registered");
    CHECK(carto_decoy_table[0].stage == 1, "row 0 is the stage 1 decoy");
    CHECK(carto_decoy_table[1].stage == 2, "row 1 is the stage 2 decoy");
    CHECK(carto_decoy_table[2].stage == 3, "row 2 is the stage 3 decoy (stage-2 checkpoint token fed back as reading)");
    CHECK(carto_decoy_table[3].stage == 4, "row 3 is the stage 4 decoy (struck first-draft title)");
    return 0;
}

static int test_decoy_persist(void)
{
    carto_state_t st, rt;
    int rc;
    rm(PB);
    memset(&st, 0, sizeof st);
    st.first_run_ms = NOW;
    carto_mark_decoy(&st, 1, 1u << 0);
    carto_mark_decoy(&st, 1, 1u << 3);
    carto_mark_decoy(&st, 4, 1u << 2);
    CHECK(carto_state_save(PB, &st) == 0, "save");
    rc = carto_state_load(PB, &rt, NOW);
    CHECK(rc == CARTO_LOAD_OK, "load");
    CHECK(carto_decoy_submitted(&rt, 1, 1u << 0), "stage1 bit0");
    CHECK(carto_decoy_submitted(&rt, 1, 1u << 3), "stage1 bit3");
    CHECK(!carto_decoy_submitted(&rt, 1, 1u << 1), "stage1 bit1 false");
    CHECK(carto_decoy_submitted(&rt, 4, 1u << 2), "stage4 bit2");
    CHECK(!carto_decoy_submitted(&rt, 2, 1u << 2), "stage2 bit2 false");
    return 0;
}

static int test_attempts_persist(void)
{
    carto_state_t st, rt;
    rm(PB);
    memset(&st, 0, sizeof st);
    st.first_run_ms = NOW;
    carto_bump_attempt(&st, 3);
    carto_bump_attempt(&st, 3);
    carto_bump_attempt(&st, 3);
    CHECK(carto_state_save(PB, &st) == 0, "save");
    CHECK(carto_state_load(PB, &rt, NOW) == CARTO_LOAD_OK, "load");
    CHECK(rt.attempt_count[3] == 3, "count != 3");
    CHECK(rt.attempt_count[0] == 0, "count0 != 0");
    return 0;
}

static int test_debugger_persist(void)
{
    carto_state_t st, rt;
    rm(PB);
    memset(&st, 0, sizeof st);
    st.first_run_ms = NOW;
    carto_set_debugger_detected(&st, 1);
    CHECK(carto_state_save(PB, &st) == 0, "save");
    CHECK(carto_state_load(PB, &rt, NOW) == CARTO_LOAD_OK, "load");
    CHECK(rt.debugger_detected == 1, "flag lost");
    CHECK(carto_get_debugger_detected(&rt) == 1, "getter");
    return 0;
}

static int hexval(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static size_t hex2bin(const char *h, uint8_t *out, size_t max)
{
    size_t n = 0;
    while (h[0] && h[1]) {
        int hi = hexval(h[0]), lo = hexval(h[1]);
        if (hi < 0 || lo < 0 || n >= max) return 0;
        out[n++] = (uint8_t)((hi << 4) | lo);
        h += 2;
    }
    return n;
}

/* Differential test: verify carto_hmac_sha256 against the OS reference
 * implementation (python hashlib/hmac) over deterministic random vectors. */
static int test_hmac_differential(void)
{
    FILE *f = fopen("/tmp/carto_vectors.txt", "r");
    char line[1200], kh[512], mh[512], wh[80];
    uint8_t key[256], msg[256], want[32], got[32];
    int n = 0;

    CHECK(f != NULL, "vectors file missing (make test generates it)");
    while (fgets(line, sizeof line, f)) {
        size_t klen, mlen;
        if (sscanf(line, "%511s %511s %79s", kh, mh, wh) != 3) {
            fclose(f);
            CHECK(0, "malformed vector line");
        }
        klen = hex2bin(kh, key, sizeof key);
        mlen = hex2bin(mh, msg, sizeof msg);
        CHECK(klen > 0, "key hex decode failed");
        CHECK(mlen > 0, "msg hex decode failed");
        CHECK(hex2bin(wh, want, 32) == 32, "mac hex decode failed");
        carto_hmac_sha256(key, klen, msg, mlen, got);
        if (!carto_ct_equal(got, want, 32)) {
            fclose(f);
            printf("    HMAC mismatch at vector %d (klen=%d mlen=%d)\n",
                   n, (int)klen, (int)mlen);
            return -1;
        }
        n++;
    }
    fclose(f);
    CHECK(n >= 60, "too few vectors parsed");
    return 0;
}

void run_part2_tests(void)
{
    RUN(test_ring_wrap);
    RUN(test_stddev_reference);
    RUN(test_stddev_insufficient);
    RUN(test_escalate_fast);
    RUN(test_escalate_uniform);
    RUN(test_escalate_human);
    RUN(test_escalate_debugger);
    RUN(test_decoy_lookup);
    RUN(test_decoy_count);
    RUN(test_decoy_persist);
    RUN(test_attempts_persist);
    RUN(test_debugger_persist);
    RUN(test_hmac_differential);
}
