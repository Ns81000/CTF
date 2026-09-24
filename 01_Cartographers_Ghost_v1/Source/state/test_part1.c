#define _POSIX_C_SOURCE 200809L

#include "test_util.h"
#include "state.h"
#include "state_internal.h"
#include "policy.h"
#include "carto_sha256.h"

#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define P1 "/tmp/carto_t1.bin"
#define P2 "/tmp/carto_t2.bin"
#define P3 "/tmp/carto_t3.bin"
#define PCAP_OUT "/tmp/carto_cap_out"
#define PCAP_ERR "/tmp/carto_cap_err"
#define NOW ((uint64_t)1000000)

int g_run = 0;
int g_fail = 0;

static void rm(const char *p) { unlink(p); }

static void rm_all(void)
{
    rm(P1); rm(P2); rm(P3);
    rm(P1 ".tmp"); rm(P2 ".tmp"); rm(P3 ".tmp");
    rm(PCAP_OUT); rm(PCAP_ERR);
}

/* Capture fd 1 and fd 2 to files so we can PROVE a tampered load is silent. */
static int capture_begin(int *so, int *se)
{
    int fo = open(PCAP_OUT, O_RDWR | O_CREAT | O_TRUNC, 0600);
    int fe = open(PCAP_ERR, O_RDWR | O_CREAT | O_TRUNC, 0600);
    if (fo < 0 || fe < 0)
        return -1;
    /* Drain stdio buffers FIRST: anything buffered from earlier test output
     * must land on the real stdout, not inside the capture files. */
    fflush(stdout);
    fflush(stderr);
    *so = dup(1);
    *se = dup(2);
    dup2(fo, 1);
    dup2(fe, 2);
    close(fo);
    close(fe);
    return 0;
}

static long capture_end(int so, int se)
{
    long bad = 0;
    struct stat sb;
    dup2(so, 1);
    dup2(se, 2);
    close(so);
    close(se);
    fflush(stdout);
    fflush(stderr);
    if (stat(PCAP_OUT, &sb) == 0 && sb.st_size != 0) bad |= 1;
    if (stat(PCAP_ERR, &sb) == 0 && sb.st_size != 0) bad |= 2;
    return bad; /* 0 = perfectly silent */
}

static int test_sha_selftest(void)
{
    CHECK(carto_sha_selftest() == 0, "SHA-256 known-answer vectors failed");
    return 0;
}

static int test_hmac_selftest(void)
{
    CHECK(carto_hmac_selftest() == 0, "HMAC RFC 4231 vectors failed");
    return 0;
}

static int test_key_selftest(void)
{
    CHECK(carto_key_selftest() == 0, "two masked key copies disagree");
    return 0;
}

static int hexval4(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

/*
 * Strongest key check: python computes HMAC(canonical_key, "cartographer-key-probe")
 * with the DOCUMENTED canonical key; the C side must reproduce it purely via
 * carto_unmask_key(). Catches any transcription error in the masked key blob,
 * even if both masked copies were corrupted identically.
 */
static int test_key_canonical(void)
{
    uint8_t k[32], want[32], got[32];
    const char *probe = "cartographer-key-probe";
    char hex[80];
    FILE *f = fopen("/tmp/carto_selftest.txt", "r");
    int i;

    CHECK(f != NULL, "selftest file missing (make test generates it)");
    CHECK(fgets(hex, sizeof hex, f) != NULL, "no line in selftest file");
    fclose(f);
    for (i = 0; i < 32; i++) {
        int hi = hexval4(hex[2 * i]), lo = hexval4(hex[2 * i + 1]);
        if (hi < 0 || lo < 0) { printf("    bad hex in selftest file\n"); return -1; }
        want[i] = (uint8_t)((hi << 4) | lo);
    }
    carto_unmask_key(k);
    carto_hmac_sha256(k, 32, (const uint8_t *)probe, 22, got);
    if (!carto_ct_equal(got, want, 32)) {
        printf("    canonical key mismatch (masked key blob wrong)\n");
        return -1;
    }
    return 0;
}

static int test_fresh_create(void)
{
    carto_state_t st, st2;
    struct stat sb;
    int rc, i;

    rc = carto_state_load(P1, &st, NOW);
    CHECK(rc == CARTO_LOAD_CREATED, "expected CREATED");
    CHECK(stat(P1, &sb) == 0, "state file not created");
    CHECK(sb.st_size == CARTO_STATE_FILE_SIZE, "wrong file size");
    CHECK(st.first_run_ms == NOW, "first_run not set from now_ms");
    for (i = 0; i < CARTO_NUM_STAGES; i++) {
        CHECK(st.attempt_count[i] == 0, "attempt not zeroed");
        CHECK(st.decoy_mask[i] == 0, "decoy not zeroed");
    }
    CHECK(st.ring_count == 0, "ring not zeroed");
    CHECK(st.debugger_detected == 0, "debug flag not zeroed");

    rc = carto_state_load(P1, &st2, NOW + 5000);
    CHECK(rc == CARTO_LOAD_OK, "second load not OK");
    CHECK(st2.first_run_ms == NOW, "first_run changed on reload");
    return 0;
}

static int test_roundtrip(void)
{
    carto_state_t st, rt;
    int rc, i;

    memset(&st, 0, sizeof st);
    st.first_run_ms = 1234567;
    for (i = 0; i < CARTO_NUM_STAGES; i++) {
        st.attempt_count[i] = (uint32_t)(i + 1);
        st.decoy_mask[i]    = (uint32_t)(0xF0F0u << i);
    }
    for (i = 0; i < 7; i++)
        carto_record_interaction(&st, (uint64_t)(2000000 + 137 * i));
    st.debugger_detected = 1;

    CHECK(carto_state_save(P2, &st) == 0, "save failed");
    rc = carto_state_load(P2, &rt, 999);
    CHECK(rc == CARTO_LOAD_OK, "load failed");
    CHECK(rt.first_run_ms == st.first_run_ms, "first_run");
    for (i = 0; i < CARTO_NUM_STAGES; i++) {
        CHECK(rt.attempt_count[i] == st.attempt_count[i], "attempts");
        CHECK(rt.decoy_mask[i] == st.decoy_mask[i], "decoys");
    }
    CHECK(rt.ring_count == st.ring_count, "ring_count");
    CHECK(rt.ring_head == st.ring_head, "ring_head");
    for (i = 0; i < CARTO_RING_SIZE; i++)
        CHECK(rt.ring_ts[i] == st.ring_ts[i], "ring ts");
    CHECK(rt.debugger_detected == 1, "debugger flag");
    return 0;
}
static int test_tamper_silent_reset(void)
{
    carto_state_t st, st2, st3;
    FILE *f;
    int so, se, rc;
    long noisy;

    CHECK(carto_state_load(P3, &st, NOW) == CARTO_LOAD_CREATED, "setup create");
    carto_bump_attempt(&st, 2);
    carto_bump_attempt(&st, 2);
    carto_bump_attempt(&st, 2);
    carto_record_interaction(&st, NOW + 100);
    carto_set_debugger_detected(&st, 1);
    CHECK(carto_state_save(P3, &st) == 0, "setup save");

    f = fopen(P3, "r+b");
    CHECK(f != NULL, "open for tamper");
    fseek(f, 40, SEEK_SET); /* inside attempt_count region */
    fputc(0x5A, f);
    fclose(f);

    if (capture_begin(&so, &se) != 0)
        return -1;
    rc = carto_state_load(P3, &st2, NOW);
    noisy = capture_end(so, se);

    if (rc != CARTO_LOAD_TAMPERED) {
        printf("    rc=%d expected CARTO_LOAD_TAMPERED\n", rc);
        return -1;
    }
    if (noisy != 0) {
        printf("    load printed to stdout/stderr (mask %ld)\n", noisy);
        return -1;
    }
    if (st2.first_run_ms != NOW) { printf("    not reset to fresh\n"); return -1; }
    if (st2.attempt_count[2] != 0) { printf("    attempts not zeroed\n"); return -1; }
    if (st2.ring_count != 0) { printf("    ring not zeroed\n"); return -1; }
    if (st2.debugger_detected != 0) { printf("    debug flag not zeroed\n"); return -1; }

    /* File must have been rewritten to fresh defaults. */
    rc = carto_state_load(P3, &st3, NOW);
    if (rc != CARTO_LOAD_OK) { printf("    reload rc=%d\n", rc); return -1; }
    if (st3.attempt_count[2] != 0) { printf("    file not reset\n"); return -1; }
    return 0;
}

static int test_truncated(void)
{
    carto_state_t st;
    CHECK(carto_state_load(P1, &st, NOW) >= 0, "setup");
    CHECK(carto_state_save(P1, &st) == 0, "setup save");
    CHECK(truncate(P1, 100) == 0, "truncate failed");
    CHECK(carto_state_load(P1, &st, NOW) == CARTO_LOAD_TAMPERED,
          "truncated file not TAMPERED");
    return 0;
}

static int test_extended(void)
{
    carto_state_t st;
    FILE *f;
    CHECK(carto_state_load(P1, &st, NOW) >= 0, "setup");
    CHECK(carto_state_save(P1, &st) == 0, "setup save");
    f = fopen(P1, "ab");
    CHECK(f != NULL, "append open");
    fputc(0xFF, f);
    fclose(f);
    CHECK(carto_state_load(P1, &st, NOW) == CARTO_LOAD_TAMPERED,
          "overlong file not TAMPERED");
    return 0;
}

static int test_bad_magic(void)
{
    carto_state_t st;
    FILE *f;
    CHECK(carto_state_load(P1, &st, NOW) >= 0, "setup");
    CHECK(carto_state_save(P1, &st) == 0, "setup save");
    f = fopen(P1, "r+b");
    CHECK(f != NULL, "open");
    fseek(f, 0, SEEK_SET);
    fputc('X', f);
    fclose(f);
    CHECK(carto_state_load(P1, &st, NOW) == CARTO_LOAD_TAMPERED,
          "bad magic not TAMPERED");
    return 0;
}

static int test_garbage(void)
{
    carto_state_t st;
    uint8_t buf[CARTO_STATE_FILE_SIZE];
    FILE *f;
    int i;
    for (i = 0; i < (int)sizeof buf; i++)
        buf[i] = (uint8_t)(i * 7 + 3);
    f = fopen(P1, "wb");
    CHECK(f != NULL, "open");
    fwrite(buf, 1, sizeof buf, f);
    fclose(f);
    CHECK(carto_state_load(P1, &st, NOW) == CARTO_LOAD_TAMPERED,
          "garbage not TAMPERED");
    return 0;
}

static int test_hmac_ring_flip(void)
{
    carto_state_t st;
    FILE *f;
    CHECK(carto_state_load(P1, &st, NOW) >= 0, "setup");
    CHECK(carto_state_save(P1, &st) == 0, "setup save");
    f = fopen(P1, "r+b");
    CHECK(f != NULL, "open");
    fseek(f, 300, SEEK_SET); /* inside HMAC-covered ring region */
    fputc(0xFF, f);
    fclose(f);
    CHECK(carto_state_load(P1, &st, NOW) == CARTO_LOAD_TAMPERED,
          "hmac did not catch flipped byte");
    return 0;
}

static int test_save_deterministic(void)
{
    carto_state_t st;
    uint8_t a[CARTO_STATE_FILE_SIZE], b[CARTO_STATE_FILE_SIZE];
    FILE *f;

    memset(&st, 0, sizeof st);
    st.first_run_ms = 4242;
    carto_bump_attempt(&st, 0);
    carto_record_interaction(&st, 9999);
    CHECK(carto_state_save(P2, &st) == 0, "save1");
    f = fopen(P2, "rb");
    CHECK(f != NULL, "read1");
    CHECK(fread(a, 1, sizeof a, f) == sizeof a, "read1 short");
    fclose(f);
    CHECK(carto_state_save(P2, &st) == 0, "save2");
    f = fopen(P2, "rb");
    CHECK(f != NULL, "read2");
    CHECK(fread(b, 1, sizeof b, f) == sizeof b, "read2 short");
    fclose(f);
    CHECK(memcmp(a, b, sizeof a) == 0, "two saves differ");
    return 0;
}

static int test_no_tmp_residue(void)
{
    carto_state_t st;
    struct stat sb;
    memset(&st, 0, sizeof st);
    st.first_run_ms = NOW;
    CHECK(carto_state_save(P2, &st) == 0, "save");
    CHECK(stat(P2 ".tmp", &sb) != 0, ".tmp residue left behind");
    return 0;
}

int main(void)
{
    rm_all();
    printf("== cartographer state library unit tests ==\n");
    RUN(test_sha_selftest);
    RUN(test_hmac_selftest);
    RUN(test_key_selftest);
    RUN(test_key_canonical);
    RUN(test_fresh_create);
    RUN(test_roundtrip);
    RUN(test_tamper_silent_reset);
    RUN(test_truncated);
    RUN(test_extended);
    RUN(test_bad_magic);
    RUN(test_garbage);
    RUN(test_hmac_ring_flip);
    RUN(test_save_deterministic);
    RUN(test_no_tmp_residue);
    run_part2_tests();
    printf("== %d tests run, %d failed ==\n", g_run, g_fail);
    if (g_fail == 0) {
        printf("ALL TESTS PASSED\n");
        return 0;
    }
    printf("TESTS FAILED\n");
    return 1;
}
