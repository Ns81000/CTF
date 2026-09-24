/* Suite header: these tests share /tmp/carto_p1 as the package root and a
 * single state record, so they must run SERIALLY.  Never parallelise. */
#define _POSIX_C_SOURCE 200809L

#include "test_util.h"
#include "state.h"
#include "policy.h"
#include "carto_sha256.h"

#include <dirent.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define ROOT "/tmp/carto_p1"
#define SPATH ROOT "/" CARTO_STATE_NAME
#define TMPATH ROOT "/" CARTO_STATE_NAME ".tmp"
#define VFILE "/tmp/carto_v2_vectors.txt"

#define OFF_GATES  0x040
#define OFF_RING   0x060
#define OFF_CHAIN  0x460
#define OFF_HMAC   0x470

int g_run = 0;
int g_fail = 0;

static char v_Kstate[65], v_Kstage[6][65], v_sha100[65];
static char v_hmac_state[65], v_hmac_stage[6][65], v_chain_zero[33];

static void wipe(void)
{
    unlink(SPATH);
    unlink(TMPATH);
}

static int read_file(const char *p, unsigned char *buf, size_t cap)
{
    FILE *fh = fopen(p, "rb");
    size_t n;
    if (!fh)
        return -1;
    n = fread(buf, 1, cap, fh);
    fclose(fh);
    return (int)n;
}

static int write_file(const char *p, const unsigned char *buf, size_t n)
{
    FILE *fh = fopen(p, "wb");
    if (!fh)
        return -1;
    if (fwrite(buf, 1, n, fh) != n) {
        fclose(fh);
        return -1;
    }
    fclose(fh);
    return 0;
}

static int load_vectors(void)
{
    FILE *fh = fopen(VFILE, "r");
    char line[160], key[64], val[96];
    int stage;

    if (!fh)
        return -1;
    while (fgets(line, sizeof line, fh)) {
        if (sscanf(line, "%63s %95s", key, val) != 2)
            continue;
        if (!strcmp(key, "K_state"))
            strcpy(v_Kstate, val);
        else if (!strcmp(key, "SHA_100"))
            strcpy(v_sha100, val);
        else if (!strcmp(key, "HMAC_state_100"))
            strcpy(v_hmac_state, val);
        else if (!strcmp(key, "CHAIN_zero_body"))
            strcpy(v_chain_zero, val);
        else if (sscanf(key, "K_stage_%d", &stage) == 1 && stage >= 0 &&
                 stage < CARTO_NUM_STAGES)
            strcpy(v_Kstage[stage], val);
        else if (sscanf(key, "HMAC_stage_%d_100", &stage) == 1 &&
                 stage >= 0 && stage < CARTO_NUM_STAGES)
            strcpy(v_hmac_stage[stage], val);
    }
    fclose(fh);
    return 0;
}

static void to_hex(const unsigned char *b, size_t n, char *out)
{
    static const char *H = "0123456789abcdef";
    size_t i;
    for (i = 0; i < n; i++) {
        out[2 * i] = H[b[i] >> 4];
        out[2 * i + 1] = H[b[i] & 15];
    }
    out[2 * n] = '\0';
}

/* capture stdout/stderr to prove a code path says nothing at all */
static int capture_begin(int *so, int *se)
{
    int fo = open("/tmp/carto_p1.out", O_RDWR | O_CREAT | O_TRUNC, 0600);
    int fe = open("/tmp/carto_p1.err", O_RDWR | O_CREAT | O_TRUNC, 0600);
    if (fo < 0 || fe < 0)
        return -1;
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
    if (stat("/tmp/carto_p1.out", &sb) == 0 && sb.st_size != 0) bad |= 1;
    if (stat("/tmp/carto_p1.err", &sb) == 0 && sb.st_size != 0) bad |= 2;
    return bad;
}

/* ---- vectors ------------------------------------------------------------ */

static int test_sha_selftest(void)
{
    CHECK(carto_sha_selftest() == 0, "SHA-256 known-answer vectors");
    return 0;
}

static int test_hmac_selftest(void)
{
    CHECK(carto_hmac_selftest() == 0, "HMAC RFC 4231 vectors");
    return 0;
}

static int test_key_selftest(void)
{
    CHECK(carto_key_selftest() == 0, "key derivation sanity");
    return 0;
}

static int test_vectors_sha(void)
{
    unsigned char msg[100], d[32];
    char hex[65];
    int i;
    for (i = 0; i < 100; i++)
        msg[i] = (unsigned char)i;
    carto_sha256(msg, sizeof msg, d);
    to_hex(d, 32, hex);
    CHECK(strcmp(hex, v_sha100) == 0, "SHA-256(0..99) vs python");
    return 0;
}

static int test_vectors_keys(void)
{
    unsigned char k[32];
    char hex[65];
    int i;

    carto_state_key(k);
    to_hex(k, 32, hex);
    CHECK(strcmp(hex, v_Kstate) == 0, "K_state vs python");
    for (i = 0; i < CARTO_NUM_STAGES; i++) {
        carto_derive_stage_key(i, k);
        to_hex(k, 32, hex);
        CHECK(strcmp(hex, v_Kstage[i]) == 0, "K_stage_i vs python");
    }
    return 0;
}

static int test_vectors_hmac(void)
{
    unsigned char msg[100], k[32], mac[32];
    char hex[65];
    int i;

    for (i = 0; i < 100; i++)
        msg[i] = (unsigned char)i;
    carto_state_key(k);
    carto_hmac_sha256(k, 32, msg, sizeof msg, mac);
    to_hex(mac, 32, hex);
    CHECK(strcmp(hex, v_hmac_state) == 0, "HMAC(K_state) vs python");
    for (i = 0; i < CARTO_NUM_STAGES; i++) {
        carto_derive_stage_key(i, k);
        carto_hmac_sha256(k, 32, msg, sizeof msg, mac);
        to_hex(mac, 32, hex);
        CHECK(strcmp(hex, v_hmac_stage[i]) == 0, "HMAC(K_stage_i) vs python");
    }
    return 0;
}

static int test_vectors_chain_zero(void)
{
    carto_state_t st;
    unsigned char buf[CARTO_STATE_FILE_SIZE];
    char hex[33];
    int n;

    wipe();
    memset(&st, 0, sizeof st);
    st.first_run_ms = 1700000000000ull;
    CHECK(carto_state_save(ROOT, &st) == 0, "save");
    n = read_file(SPATH, buf, sizeof buf);
    CHECK(n == CARTO_STATE_FILE_SIZE, "size on disk");
    to_hex(buf + OFF_CHAIN, 16, hex);
    CHECK(strcmp(hex, v_chain_zero) == 0, "chain over a zero body vs python");
    return 0;
}

/* ---- lifecycle ---------------------------------------------------------- */

static int test_create_and_layout(void)
{
    carto_state_t st;
    unsigned char buf[CARTO_STATE_FILE_SIZE];
    int rc, n;

    wipe();
    rc = carto_state_load(ROOT, &st, 1000000ull);
    CHECK(rc == CARTO_LOAD_CREATED, "fresh record reported as created");
    CHECK(st.first_run_ms == 1000000ull, "first_run stamped");
    CHECK(st.ring_count == 1, "creation appended a ring entry");
    CHECK(st.ring_head == 1, "ring head advanced");
    n = read_file(SPATH, buf, sizeof buf);
    CHECK(n == CARTO_STATE_FILE_SIZE, "file is exactly 1168 bytes");
    CHECK(memcmp(buf, "CGV2", 4) == 0, "magic");
    CHECK(buf[4] == 2 && buf[5] == 0, "version 2");
    CHECK(buf[6] == 0 && buf[7] == 0, "flags zero");
    CHECK(access(TMPATH, F_OK) != 0, "no temp file left behind");
    return 0;
}

static int test_first_run_stable(void)
{
    carto_state_t a, b;

    wipe();
    carto_state_load(ROOT, &a, 1000000ull);
    carto_state_load(ROOT, &b, 9000000ull);
    CHECK(b.first_run_ms == a.first_run_ms, "first_run_ms is stable");
    CHECK(b.ring_count == a.ring_count, "a plain load records no interaction");
    return 0;
}

static int test_roundtrip(void)
{
    carto_state_t a, b;
    int i;

    wipe();
    carto_state_load(ROOT, &a, 2000000ull);
    for (i = 0; i < CARTO_NUM_STAGES; i++) {
        a.attempt_count[i] = (uint32_t)(100 + i);
        carto_mark_wrong_flag(&a, i, 1u << (i % 8));
    }
    a.debugger_flag = 1;
    a.distinct_figures = 4242;
    carto_ring_append(&a, 2500000ull, 3, CARTO_OP_QUERY, 0x00010007u);
    CHECK(carto_state_save(ROOT, &a) == 0, "save");
    CHECK(carto_state_load(ROOT, &b, 3000000ull) == CARTO_LOAD_OK, "reload");
    for (i = 0; i < CARTO_NUM_STAGES; i++) {
        CHECK(b.attempt_count[i] == (uint32_t)(100 + i), "attempt roundtrip");
        CHECK(b.wrong_flag_mask[i] == a.wrong_flag_mask[i], "wrong roundtrip");
    }
    CHECK(b.debugger_flag == 1, "debugger flag roundtrip");
    CHECK(b.distinct_figures == 4242, "counter roundtrip");
    return 0;
}

/* every byte of the record is covered: a single flipped bit anywhere in the
 * file must read back as a tampered (silently reset) record */
static int test_tamper_every_byte(void)
{
    unsigned char buf[CARTO_STATE_FILE_SIZE];
    carto_state_t st;
    int off, n;

    wipe();
    memset(&st, 0, sizeof st);
    st.first_run_ms = 1700000000000ull;
    carto_state_save(ROOT, &st);
    n = read_file(SPATH, buf, sizeof buf);
    CHECK(n == CARTO_STATE_FILE_SIZE, "baseline size");
    for (off = 0; off < CARTO_STATE_FILE_SIZE; off++) {
        unsigned char save = buf[off];
        int rc;
        buf[off] = (unsigned char)(save ^ 0x01u);
        CHECK(write_file(SPATH, buf, sizeof buf) == 0, "rewrite");
        rc = carto_state_load(ROOT, &st, 4000000ull);
        CHECK(rc == CARTO_LOAD_TAMPERED, "flipped bit must be tampered");
        buf[off] = save;
        CHECK(write_file(SPATH, buf, sizeof buf) == 0, "restore");
    }
    return 0;
}

static int test_tamper_structural(void)
{
    static const int offsets[] = {
        0x000, 0x004, 0x006, 0x008, 0x010, 0x028, 0x040,
        0x058, 0x05A, 0x05C, 0x05D, 0x060, 0x460, 0x470, 0x48F
    };
    unsigned char buf[CARTO_STATE_FILE_SIZE];
    carto_state_t st;
    size_t i;
    int n;

    wipe();
    memset(&st, 0, sizeof st);
    st.first_run_ms = 1700000000000ull;
    carto_state_save(ROOT, &st);
    n = read_file(SPATH, buf, sizeof buf);
    CHECK(n == CARTO_STATE_FILE_SIZE, "baseline size");
    for (i = 0; i < sizeof offsets / sizeof offsets[0]; i++) {
        int off = offsets[i];
        buf[off] = (unsigned char)(buf[off] ^ 0x80u);
        CHECK(write_file(SPATH, buf, sizeof buf) == 0, "rewrite");
        CHECK(carto_state_load(ROOT, &st, 4200000ull) == CARTO_LOAD_TAMPERED,
              "structural field tamper detected");
        buf[off] = (unsigned char)(buf[off] ^ 0x80u);
        CHECK(write_file(SPATH, buf, sizeof buf) == 0, "restore");
    }
    return 0;
}

static int test_truncate_and_extend(void)
{
    static const size_t sizes[] = { 0, 1, 100, 1151, 1167 };
    unsigned char buf[CARTO_STATE_FILE_SIZE + 1];
    carto_state_t st;
    size_t i;
    int n;

    wipe();
    memset(&st, 0, sizeof st);
    st.first_run_ms = 1700000000000ull;
    carto_state_save(ROOT, &st);
    n = read_file(SPATH, buf, sizeof buf);
    CHECK(n == CARTO_STATE_FILE_SIZE, "baseline size");
    for (i = 0; i < sizeof sizes / sizeof sizes[0]; i++) {
        CHECK(write_file(SPATH, buf, sizes[i]) == 0, "truncate");
        CHECK(carto_state_load(ROOT, &st, 4300000ull) == CARTO_LOAD_TAMPERED,
              "truncated record detected");
    }
    buf[CARTO_STATE_FILE_SIZE] = 0x41;
    CHECK(write_file(SPATH, buf, CARTO_STATE_FILE_SIZE + 1) == 0, "extend");
    CHECK(carto_state_load(ROOT, &st, 4400000ull) == CARTO_LOAD_TAMPERED,
          "oversized record detected");
    return 0;
}

static int test_silence_on_tamper(void)
{
    unsigned char buf[CARTO_STATE_FILE_SIZE];
    carto_state_t st;
    int so = 0, se = 0;
    long bad;
    int n;

    wipe();
    memset(&st, 0, sizeof st);
    st.first_run_ms = 1700000000000ull;
    carto_state_save(ROOT, &st);
    n = read_file(SPATH, buf, sizeof buf);
    CHECK(n == CARTO_STATE_FILE_SIZE, "baseline size");
    buf[OFF_HMAC] ^= 0xFF;
    CHECK(write_file(SPATH, buf, sizeof buf) == 0, "corrupt the tag");
    CHECK(capture_begin(&so, &se) == 0, "capture");
    CHECK(carto_state_load(ROOT, &st, 4500000ull) == CARTO_LOAD_TAMPERED,
          "tampered");
    bad = capture_end(so, se);
    CHECK(bad == 0, "a silent reset prints nothing on either stream");
    return 0;
}

/* ---- ring --------------------------------------------------------------- */

static int test_ring_wrap(void)
{
    carto_state_t st;
    int i;

    memset(&st, 0, sizeof st);
    st.first_run_ms = 1700000000000ull;
    for (i = 0; i < 200; i++)
        carto_ring_append(&st, 1700000000000ull + (uint64_t)i * 1000ull,
                          i % CARTO_NUM_STAGES, CARTO_OP_INVOKE, 0);
    CHECK(st.ring_count == 200, "cumulative count");
    CHECK(st.ring_head == 200 % CARTO_RING_SIZE, "head wrapped");
    {
        uint64_t wts[CARTO_RING_SIZE];
        uint8_t wstage[CARTO_RING_SIZE], wop[CARTO_RING_SIZE];
        uint32_t wax[CARTO_RING_SIZE];
        int n = carto_ring_window(&st, wts, wstage, wop, wax);
        CHECK(n == CARTO_RING_SIZE, "a full window after wrapping");
        CHECK(wts[0] == 1700000000000ull + 136ull * 1000ull,
              "oldest surviving entry is #136");
        CHECK(wts[n - 1] == 1700000000000ull + 199ull * 1000ull,
              "newest entry is #199");
        for (i = 1; i < n; i++)
            CHECK(wts[i] > wts[i - 1], "window stays chronological");
    }
    return 0;
}

static int test_ring_dt_saturate(void)
{
    carto_state_t st;
    const uint8_t *e0, *e1;
    unsigned dt;

    memset(&st, 0, sizeof st);
    carto_ring_append(&st, 1000ull, 0, CARTO_OP_INVOKE, 0);
    carto_ring_append(&st, 1000000ull, 0, CARTO_OP_INVOKE, 0);
    e0 = carto_ring_entry(&st, 0);
    e1 = carto_ring_entry(&st, 1);
    CHECK(e0 != NULL && e1 != NULL, "ring entries");
    dt = (unsigned)e1[CARTO_RING_OFF_DT] | ((unsigned)e1[CARTO_RING_OFF_DT + 1] << 8);
    CHECK(dt == 0xFFFFu, "a long gap saturates rather than wrapping");
    CHECK(e0[CARTO_RING_OFF_STAGE] == 0, "stage byte");
    CHECK(e0[CARTO_RING_OFF_OP] == CARTO_OP_INVOKE, "op byte");
    return 0;
}

static int test_ring_window_order(void)
{
    carto_state_t st;
    uint64_t ts[CARTO_RING_SIZE];
    uint8_t stage[CARTO_RING_SIZE], op[CARTO_RING_SIZE];
    uint32_t aux[CARTO_RING_SIZE];
    int i, n;

    memset(&st, 0, sizeof st);
    for (i = 0; i < 5; i++)
        carto_ring_append(&st, 5000ull + (uint64_t)i * 250ull, i,
                          CARTO_OP_INVOKE, (uint32_t)i);
    n = carto_ring_window(&st, ts, stage, op, aux);
    CHECK(n == 5, "window size before wrap");
    for (i = 1; i < n; i++)
        CHECK(ts[i] > ts[i - 1], "window is chronological");
    CHECK(stage[0] == 0 && aux[4] == 4u, "oldest first, newest last");

    for (i = 0; i < 100; i++)
        carto_ring_append(&st, 9000ull + (uint64_t)i * 100ull, 3,
                          CARTO_OP_QUERY, (uint32_t)i);
    n = carto_ring_window(&st, ts, stage, op, aux);
    CHECK(n == CARTO_RING_SIZE, "window is capped at 64 entries");
    for (i = 1; i < n; i++)
        CHECK(ts[i] > ts[i - 1], "window stays chronological after wrap");
    CHECK(aux[n - 1] == 99u, "newest entry is last");
    return 0;
}

static int test_chain_changes(void)
{
    carto_state_t a, b;

    memset(&a, 0, sizeof a);
    memset(&b, 0, sizeof b);
    a.first_run_ms = 1700000000000ull;
    b.first_run_ms = 1700000000000ull;
    carto_ring_append(&a, 1700000000001ull, 0, CARTO_OP_INVOKE, 0);
    carto_ring_append(&b, 1700000000001ull, 0, CARTO_OP_INVOKE, 0);
    wipe();
    CHECK(carto_state_save(ROOT, &a) == 0, "save a");
    carto_ring_append(&b, 1700000000002ull, 0, CARTO_OP_INVOKE, 0);
    CHECK(carto_state_save(ROOT, &b) == 0, "save b");
    {
        carto_state_t c;
        CHECK(carto_state_load(ROOT, &c, 1800000000000ull) == CARTO_LOAD_OK,
              "reload");
        CHECK(c.chain[0] != 0 || c.chain[1] != 0, "chain is populated");
        CHECK(memcmp(c.chain, a.chain, 16) != 0,
              "a changed record has a different chain");
    }
    return 0;
}

static int test_only_state_file_written(void)
{
    DIR *d;
    const struct dirent *ent;
    int others = 0;

    wipe();
    {
        carto_state_t st;
        carto_state_load(ROOT, &st, 5000000ull);
        carto_ring_append(&st, 5001000ull, 1, CARTO_OP_INVOKE, 0);
        carto_state_save(ROOT, &st);
    }
    d = opendir(ROOT);
    CHECK(d != NULL, "opendir");
    while ((ent = readdir(d)) != NULL) {
        if (!strcmp(ent->d_name, ".") || !strcmp(ent->d_name, ".."))
            continue;
        if (strcmp(ent->d_name, CARTO_STATE_NAME) != 0)
            others++;
    }
    closedir(d);
    CHECK(others == 0, "the record is the only thing written");

    /* symlink defense: neither load nor save may follow a symlink out of root */
    {
        carto_state_t st;
        char symtarget[256];
        snprintf(symtarget, sizeof symtarget, "%s/target_symlink_file", ROOT);
        write_file(symtarget, (const unsigned char *)"escape", 6);
        unlink(SPATH);
        symlink(symtarget, SPATH);
        CHECK(carto_state_load(ROOT, &st, 6000000ull) == CARTO_LOAD_TAMPERED,
              "symlink state must reset");
        {
            unsigned char checkbuf[16] = {0};
            read_file(symtarget, checkbuf, 6);
            CHECK(memcmp(checkbuf, "escape", 6) == 0,
                  "symlink target was not overwritten");
            unlink(symtarget);
        }
    }
    return 0;
}

static int test_layout_constants(void)
{
    CHECK(CARTO_STATE_FILE_SIZE == 1168, "record size is normative");
    CHECK(CARTO_RING_SIZE == 64, "ring holds 64 entries");
    CHECK(CARTO_RING_ENTRY_SIZE == 16, "ring entry is 16 bytes");
    CHECK(CARTO_NUM_STAGES == 6, "six stage slots");
    CHECK(0x060 + CARTO_RING_SIZE * CARTO_RING_ENTRY_SIZE == 0x460,
          "ring ends where the chain begins");
    CHECK(0x460 + 16 == 0x470, "chain ends where the tag begins");
    CHECK(0x470 + 32 == CARTO_STATE_FILE_SIZE, "the tag ends the record");
    return 0;
}

static int test_future_stamp_resets(void)
{
    unsigned char buf[CARTO_STATE_FILE_SIZE];
    carto_state_t st;
    int n;

    wipe();
    memset(&st, 0, sizeof st);
    st.first_run_ms = 1900000000000ull;      /* far in the future */
    CHECK(carto_state_save(ROOT, &st) == 0, "save");
    n = read_file(SPATH, buf, sizeof buf);
    CHECK(n == CARTO_STATE_FILE_SIZE, "size");
    CHECK(carto_state_load(ROOT, &st, 1700000000000ull) == CARTO_LOAD_TAMPERED,
          "a record stamped in the future is refused");
    CHECK(st.first_run_ms == 1700000000000ull, "and reset to the clock");
    return 0;
}

static int test_wrong_flag_bits_are_per_stage(void)
{
    carto_state_t st;

    memset(&st, 0, sizeof st);
    carto_mark_wrong_flag(&st, 1, 1u << 3);
    carto_mark_wrong_flag(&st, 4, 1u << 5);
    CHECK(carto_wrong_flag_seen(&st, 1, 1u << 3) == 1, "stage 1 branch marked");
    CHECK(carto_wrong_flag_seen(&st, 1, 1u << 5) == 0, "other branch untouched");
    CHECK(carto_wrong_flag_seen(&st, 4, 1u << 5) == 1, "stage 4 branch marked");
    CHECK(carto_wrong_flag_seen(&st, 4, 1u << 3) == 0, "stage 4 isolated");
    CHECK(carto_wrong_flag_seen(&st, 9, 1u) == 0, "out of range is safe");
    return 0;
}

static int test_clock_moving_backwards(void)
{
    carto_state_t st;
    uint64_t t = 1700000000000ull;

    wipe();
    carto_state_load(ROOT, &st, t);
    carto_ring_append(&st, t + 5000ull, 1, CARTO_OP_INVOKE, 0);
    carto_state_save(ROOT, &st);
    /* the wall clock now reads slightly before the recorded first run: the
     * record is kept and elapsed time never goes negative */
    CHECK(carto_state_load(ROOT, &st, t - 30000ull) == CARTO_LOAD_OK,
          "a small backwards step keeps the record");
    CHECK(carto_time_since_first_run_ms(&st, t - 30000ull) == 0,
          "elapsed time never goes negative");
    return 0;
}
int main(void)
{
    CHECK(mkdir(ROOT, 0700) == 0 || access(ROOT, F_OK) == 0, "mkdir root");
    if (load_vectors() != 0) {
        printf("FATAL: %s missing (run gen_vectors.py first)\n", VFILE);
        return 2;
    }

    RUN(test_sha_selftest);
    RUN(test_hmac_selftest);
    RUN(test_key_selftest);
    RUN(test_vectors_sha);
    RUN(test_vectors_keys);
    RUN(test_vectors_hmac);
    RUN(test_vectors_chain_zero);
    RUN(test_create_and_layout);
    RUN(test_first_run_stable);
    RUN(test_roundtrip);
    RUN(test_tamper_every_byte);
    RUN(test_tamper_structural);
    RUN(test_truncate_and_extend);
    RUN(test_silence_on_tamper);
    RUN(test_ring_wrap);
    RUN(test_ring_dt_saturate);
    RUN(test_ring_window_order);
    RUN(test_chain_changes);
    RUN(test_only_state_file_written);

    RUN(test_layout_constants);
    RUN(test_future_stamp_resets);
    RUN(test_wrong_flag_bits_are_per_stage);
    RUN(test_clock_moving_backwards);

    run_part2_tests();

    printf("\n%d tests run, %d failed\n", g_run, g_fail);
    wipe();
    return g_fail ? 1 : 0;
}
