#include "state.h"
#include "../core/carto_sha256.h"
#include "../core/sha256ctr.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/wait.h>

static int checks = 0, fails = 0;

static void check(int ok, const char *name)
{
    checks++;
    if (ok) printf("PASS %s\n", name);
    else { printf("FAIL %s\n", name); fails++; }
}

static char ROOT_A[256], ROOT_B[256];

static void state_file(const char *root, char *out, size_t n)
{
    snprintf(out, n, "%s/%s", root, PRAMBH_STATE_NAME);
}

static int write_file(const char *path, const uint8_t *buf, size_t len)
{
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (fd < 0) return -1;
    if (write(fd, buf, len) != (ssize_t)len) { close(fd); return -1; }
    close(fd);
    return 0;
}

static int read_file(const char *path, uint8_t *buf, size_t len)
{
    int fd = open(path, O_RDONLY);
    ssize_t got;
    if (fd < 0) return -1;
    got = read(fd, buf, len);
    close(fd);
    return got == (ssize_t)len ? 0 : -1;
}

static void sweep_flips(void)
{
    char path[512];
    uint8_t good[PRAMBH_STATE_SIZE], mutant[PRAMBH_STATE_SIZE];
    prambh_state st;
    int region, i, bad;

    state_file(ROOT_A, path, sizeof path);
    prambh_state_init_fresh(&st);
    prambh_state_save(ROOT_A, &st);
    read_file(path, good, PRAMBH_STATE_SIZE);

    for (region = 0; region < PRAMBH_STATE_SIZE / 32; region++) {
        char name[64];
        bad = 0;
        for (i = region * 32; i < region * 32 + 32; i++) {
            prambh_state m;
            memcpy(mutant, good, PRAMBH_STATE_SIZE);
            mutant[i] ^= 0x5A;
            write_file(path, mutant, PRAMBH_STATE_SIZE);
            if (prambh_state_load(ROOT_A, &m) != 0)
                bad++;
        }
        snprintf(name, sizeof name, "byteflip-region-%02d all 32 reset", region);
        check(bad == 0, name);
    }
    write_file(path, good, PRAMBH_STATE_SIZE);
}

static void run_checks(void)
{
    prambh_state st, st2;
    char path[512], aside[512];
    uint8_t buf[PRAMBH_STATE_SIZE + 512];
    uint8_t k1[32], k2[32], k3[32];
    struct stat sb;
    int i;

    snprintf(ROOT_A, sizeof ROOT_A, "/tmp/prambh_st_a_%d", (int)getpid());
    snprintf(ROOT_B, sizeof ROOT_B, "/tmp/prambh_st_b_%d", (int)getpid());
    mkdir(ROOT_A, 0700);
    mkdir(ROOT_B, 0700);
    state_file(ROOT_A, path, sizeof path);

    check(PRAMBH_STATE_SIZE == 512, "state size constant is 512");

    prambh_state_init_fresh(&st);
    check(memcmp(st.bytes + ST_OFF_MAGIC, "PRMBHSV1", 8) == 0, "fresh magic");
    check(prambh_state_get64(&st, ST_OFF_FIRST_RUN) != 0, "fresh first_run nonzero");
    check((uint32_t)prambh_get_le64(st.bytes + ST_OFF_VERSION) == PRAMBH_STATE_VERSION,
          "fresh version");

    check(prambh_state_load(ROOT_A, &st2) == 0, "missing file -> fresh");

    check(prambh_state_save(ROOT_A, &st) == 0, "save ok");
    check(stat(path, &sb) == 0 && sb.st_size == PRAMBH_STATE_SIZE, "file exactly 512 bytes");
    check((sb.st_mode & 0777) == 0600, "file mode 0600");

    memset(&st2, 0, sizeof st2);
    check(prambh_state_load(ROOT_A, &st2) == 1, "load valid state");
    check(prambh_state_get64(&st2, ST_OFF_FIRST_RUN) ==
          prambh_state_get64(&st, ST_OFF_FIRST_RUN), "first_run_ms stable");

    {
        uint64_t c0 = prambh_state_get64(&st2, ST_OFF_COUNTER);
        prambh_state_save(ROOT_A, &st2);
        prambh_state_load(ROOT_A, &st2);
        check(prambh_state_get64(&st2, ST_OFF_COUNTER) == c0 + 1, "counter monotonic");
    }

    prambh_state_set64(&st2, ST_OFF_STAGE, PRAMBH_BIT_LOOM_DONE | PRAMBH_BIT_DOORS_REAL);
    prambh_state_set64(&st2, ST_OFF_POISON, PRAMBH_POISON_DEBUGGER);
    for (i = 0; i < 32; i++) st2.bytes[ST_OFF_LOOM_OUT + i] = (uint8_t)(0xA0 + i);
    for (i = 0; i < 32; i++) st2.bytes[ST_OFF_CHAIN2_SEED + i] = (uint8_t)(0x40 + i);
    for (i = 0; i < 16; i++) st2.bytes[ST_OFF_DOOR_INK + i] = (uint8_t)(0x10 + i);
    for (i = 0; i < 32; i++) st2.bytes[ST_OFF_CHAIN2_OUT + i] = (uint8_t)(0x70 + i);
    prambh_state_save(ROOT_A, &st2);
    memset(&st, 0, sizeof st);
    prambh_state_load(ROOT_A, &st);
    check((prambh_state_get64(&st, ST_OFF_STAGE) &
           (PRAMBH_BIT_LOOM_DONE | PRAMBH_BIT_DOORS_REAL)) ==
          (PRAMBH_BIT_LOOM_DONE | PRAMBH_BIT_DOORS_REAL), "stage bits roundtrip");
    check(prambh_state_get64(&st, ST_OFF_POISON) == PRAMBH_POISON_DEBUGGER,
          "poison bits roundtrip");
    check(st.bytes[ST_OFF_LOOM_OUT + 31] == 0xBF, "loom_out slot roundtrip");
    check(st.bytes[ST_OFF_CHAIN2_SEED + 31] == 0x5F, "chain2_seed slot roundtrip");
    check(st.bytes[ST_OFF_DOOR_INK + 15] == 0x1F, "door_ink slot roundtrip");
    check(st.bytes[ST_OFF_CHAIN2_OUT + 31] == 0x8F, "chain2_out slot roundtrip");

    sweep_flips();

    read_file(path, buf, PRAMBH_STATE_SIZE);
    write_file(path, buf, 256);
    check(prambh_state_load(ROOT_A, &st) == 0, "truncated state -> reset");
    memset(buf + PRAMBH_STATE_SIZE, 0x41, 512);
    write_file(path, buf, PRAMBH_STATE_SIZE + 512);
    check(prambh_state_load(ROOT_A, &st) == 0, "extended state -> reset");
    memset(buf, 0x99, PRAMBH_STATE_SIZE);
    write_file(path, buf, PRAMBH_STATE_SIZE);
    check(prambh_state_load(ROOT_A, &st) == 0, "garbage state -> reset");
    write_file(path, buf, 0);
    check(prambh_state_load(ROOT_A, &st) == 0, "empty state -> reset");

    /* foreign state: A's state copied into B's package root */
    prambh_state_init_fresh(&st);
    prambh_state_save(ROOT_A, &st);
    state_file(ROOT_A, path, sizeof path);
    read_file(path, buf, PRAMBH_STATE_SIZE);
    state_file(ROOT_B, aside, sizeof aside);
    write_file(aside, buf, PRAMBH_STATE_SIZE);
    check(prambh_state_load(ROOT_B, &st2) == 0, "foreign state swapped in -> reset");

    /* replay: older validly sealed state loads as valid (documented call) */
    prambh_state_load(ROOT_A, &st);
    prambh_state_save(ROOT_A, &st);
    state_file(ROOT_A, path, sizeof path);
    read_file(path, buf, PRAMBH_STATE_SIZE);
    prambh_state_save(ROOT_A, &st);
    write_file(path, buf, PRAMBH_STATE_SIZE);
    check(prambh_state_load(ROOT_A, &st2) == 1, "replay of sealed state -> valid (documented)");

    prambh_device_key(ROOT_A, k1);
    prambh_device_key(ROOT_A, k2);
    prambh_device_key(ROOT_B, k3);
    check(carto_ct_equal(k1, k2, 32), "device key stable");
    check(!carto_ct_equal(k1, k3, 32), "device key bound to root");

    check(prambh_pacing_allow(100000, 50000, 0, 0, 60000) == 1, "pacing first attempt free");
    check(prambh_pacing_allow(115000, 85000, 50000, 20000, 60000) == 1, "pacing both clocks pass");
    check(prambh_pacing_allow(109999, 79999, 50000, 20000, 60000) == 0, "pacing 1ms early refused");
    check(prambh_pacing_allow(110000, 80000, 50000, 20000, 60000) == 1, "pacing exact boundary");
    check(prambh_pacing_allow(40000, 90000, 50000, 20000, 60000) == 0, "pacing wall backwards refused");
    check(prambh_pacing_allow(200000, 25000, 50000, 20000, 60000) == 0, "pacing wall jump + mono small refused");
    check(prambh_pacing_allow(200000, 10000, 50000, 20000, 60000) == 0, "pacing mono backwards refused");
    check(prambh_pacing_allow(50000, 20000, 50000, 20000, 0) == 1, "pacing zero pace allows");

    /* read-only directory: O_CREAT fails cleanly, no crash */
    {
        char rodir[256];
        prambh_state rs;
        snprintf(rodir, sizeof rodir, "%s/ro", ROOT_A);
        mkdir(rodir, 0700);
        chmod(rodir, 0500);
        prambh_state_init_fresh(&rs);
        check(prambh_state_save(rodir, &rs) == -1, "save in read-only dir fails cleanly");
        chmod(rodir, 0700);
    }

    /* concurrent writers: state stays valid */
    {
        pid_t kids[2];
        int k;
        for (k = 0; k < 2; k++) {
            kids[k] = fork();
            if (kids[k] == 0) {
                prambh_state cs;
                int j;
                for (j = 0; j < 25; j++) {
                    prambh_state_load(ROOT_A, &cs);
                    prambh_state_save(ROOT_A, &cs);
                }
                _exit(0);
            }
        }
        for (k = 0; k < 2; k++) waitpid(kids[k], NULL, 0);
        check(prambh_state_load(ROOT_A, &st) == 1, "concurrent writers -> state valid");
    }

    printf("CHECKS %d FAILS %d\n", checks, fails);
}

static void hexprint(const uint8_t *b, size_t n)
{
    size_t i;
    for (i = 0; i < n; i++) printf("%02x", b[i]);
    printf("\n");
}

int main(int argc, char **argv)
{
    if (argc >= 2 && strcmp(argv[1], "run") == 0) {
        run_checks();
        return fails ? 1 : 0;
    }
    if (argc >= 3 && strcmp(argv[1], "make") == 0) {
        prambh_state st;
        prambh_state_load(argv[2], &st);
        return prambh_state_save(argv[2], &st) == 0 ? 0 : 1;
    }
    if (argc >= 3 && strcmp(argv[1], "keyhex") == 0) {
        uint8_t k[32];
        prambh_device_key(argv[2], k);
        hexprint(k, 32);
        return 0;
    }
    if (argc >= 4 && strcmp(argv[1], "ctr") == 0) {
        uint8_t key[32], buf[8192];
        size_t len = (size_t)atol(argv[3]);
        int i;
        if (len > sizeof buf) return 1;
        for (i = 0; i < 32; i++)
            sscanf(argv[2] + 2 * i, "%2hhx", &key[i]);
        memset(buf, 0, len);
        prambh_sha256ctr_xor(key, buf, len);
        hexprint(buf, len);
        return 0;
    }
    fprintf(stderr, "usage\n");
    return 2;
}
