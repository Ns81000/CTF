/*
 * stage3_doors/doors - the hall of doors (spec 4.5).
 *
 *  - no args: banner + usage + canary notice; creates/keeps state.
 *  - "open <phrase>": tries the phrase against all eight doors.  The
 *    door whose chamber the phrase opens is printed; every other
 *    outcome prints one fixed line, byte-identical for every failure
 *    class (no counts, no verdict words).
 *  - "riddle <claim-hex>": opens riddle.bin with the loom claim key
 *    and prints the survey verse.
 *  - rc 0 always; stderr silent always; the only file ever written is
 *    the state file in the package root.
 */
#include "../core/carto_sha256.h"
#include "../core/sha256ctr.h"
#include "../core/canary.h"
#include "../core/notice.h"
#include "../state/state.h"
#include "doors_consts.h"

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define DOOR_COUNT 8
#define DOOR_SEED 32
#define CHAMBER_MAX 2048
#define DOOR_REC (DOOR_SEED + CHAMBER_MAX)
#define RIDDLE_MAX 2048
#define MARK "HALL "

static void usage(void)
{
    printf("the hall of doors - first survey field station\n"
           "usage:\n"
           "  ./doors                       this marker\n"
           "  ./doors open <phrase>         offer a word to the halls\n"
           "  ./doors riddle <claim-hex>    open the hall riddle\n"
           "\nstation canary: %s\n\n%s\n", PRAMBH_CANARY, PRAMBH_NOTICE);
}

/* directory holding this executable (doors.bin / riddle.bin sit there) */
static int self_dir(char *out, size_t outlen)
{
    char path[4096];
    ssize_t n = readlink("/proc/self/exe", path, sizeof path - 1);
    char *slash;
    if (n <= 0 || (size_t)n >= sizeof path)
        return -1;
    path[n] = 0;
    slash = strrchr(path, '/');
    if (!slash)
        return -1;
    *slash = 0;
    if (strlen(path) + 1 > outlen)
        return -1;
    strcpy(out, path);
    return 0;
}

static long read_file(const char *path, uint8_t *buf, size_t max, size_t *len)
{
    int fd = open(path, O_RDONLY);
    ssize_t got;
    if (fd < 0)
        return -1;
    got = read(fd, buf, max);
    close(fd);
    if (got <= 0)
        return -1;
    *len = (size_t)got;
    return 0;
}

static int parse_hex32(const char *s, uint8_t out[32])
{
    size_t i;
    if (strlen(s) != 64)
        return -1;
    for (i = 0; i < 32; i++) {
        unsigned v;
        if (sscanf(s + 2 * i, "%2x", &v) != 1)
            return -1;
        out[i] = (uint8_t)v;
    }
    return 0;
}

static void door_key(const uint8_t seed[32], uint64_t i, const char *phrase,
                     uint8_t out[32])
{
    uint8_t buf[14 + 32 + 8 + 512];
    size_t plen = strlen(phrase);
    if (plen > 512)
        plen = 512;
    memcpy(buf, "prambh:door:v1", 14);   /* the full label, all 14 bytes */
    memcpy(buf + 14, seed, 32);
    memcpy(buf + 46, &i, 8);            /* host is little-endian x86-64 */
    memcpy(buf + 54, phrase, plen);
    carto_sha256(buf, 54 + plen, out);
    memset(buf, 0, sizeof buf);
}

static int try_doors(const char *root, const uint8_t *doors, size_t len,
                     const char *phrase)
{
    uint8_t key[32], plain[CHAMBER_MAX];
    size_t i;
    int opened = -1;

    for (i = 0; i < DOOR_COUNT; i++) {
        size_t off = i * DOOR_REC;
        if (off + DOOR_REC > len)
            break;
        door_key(doors + off, (uint64_t)i, phrase, key);
        memcpy(plain, doors + off + DOOR_SEED, CHAMBER_MAX);
        prambh_sha256ctr_xor(key, plain, CHAMBER_MAX);
        memset(key, 0, sizeof key);
        plain[CHAMBER_MAX - 1] = 0;
        if (memcmp(plain, MARK, strlen(MARK)) == 0) {
            opened = (int)i;
            break;
        }
        memset(plain, 0, sizeof plain);
    }
    if (opened < 0) {
        printf("the halls do not answer to that word.\n");
        return 0;
    }
    if (opened == PRAMBH_REAL_DOOR_INDEX) {
        prambh_state st;
        prambh_state_load(root, &st);
        prambh_state_set64(&st, ST_OFF_STAGE,
                           prambh_state_get64(&st, ST_OFF_STAGE)
                           | PRAMBH_BIT_DOORS_REAL);
        prambh_state_save(root, &st);
    }
    printf("%s\n", (char *)plain);
    memset(plain, 0, sizeof plain);
    return 0;
}

static int show_riddle(const char *root, const char *claim_hex)
{
    char path[4096];
    uint8_t key[32], buf[RIDDLE_MAX];
    size_t len = 0;

    if (parse_hex32(claim_hex, key) != 0) {
        printf("the riddle does not open.\n");
        return 0;
    }
    if (self_dir(path, sizeof path) != 0) {
        printf("the riddle does not open.\n");
        return 0;
    }
    strncat(path, "/riddle.bin", sizeof(path) - strlen(path) - 1);
    if (read_file(path, buf, sizeof buf, &len) != 0) {
        printf("the riddle does not open.\n");
        return 0;
    }
    prambh_sha256ctr_xor(key, buf, len);
    buf[len - 1] = 0;
    if (memcmp(buf, "FIRST SURVEY", 12) == 0) {
        prambh_state st;
        prambh_state_load(root, &st);
        prambh_state_set64(&st, ST_OFF_STAGE,
                           prambh_state_get64(&st, ST_OFF_STAGE)
                           | PRAMBH_BIT_LOOM_DONE);
        memcpy(st.bytes + ST_OFF_LOOM_OUT, key, 32);
        prambh_state_save(root, &st);
        printf("%s\n", (char *)buf);
    } else {
        printf("the riddle does not open.\n");
    }
    memset(key, 0, sizeof key);
    memset(buf, 0, sizeof buf);
    return 0;
}

int main(int argc, char **argv)
{
    char root[4096], dir[4096], path[4096];
    uint8_t *blob = NULL;
    size_t len = 0;
    prambh_state st;

    if (prambh_package_root(root, sizeof root) != 0)
        strcpy(root, ".");
    prambh_state_load(root, &st);
    prambh_state_save(root, &st);

    if (argc >= 3 && strcmp(argv[1], "riddle") == 0)
        return show_riddle(root, argv[2]);

    if (argc >= 3 && strcmp(argv[1], "open") == 0) {
        char phrase[1024];
        int i;
        phrase[0] = 0;
        for (i = 2; i < argc; i++) {
            if (i > 2)
                strncat(phrase, " ", sizeof(phrase) - strlen(phrase) - 1);
            strncat(phrase, argv[i], sizeof(phrase) - strlen(phrase) - 1);
        }
        if (self_dir(dir, sizeof dir) != 0) {
            printf("the halls do not answer to that word.\n");
            return 0;
        }
        if (strlen(dir) + 11 >= sizeof path) {
            printf("the halls do not answer to that word.\n");
            return 0;
        }
        snprintf(path, sizeof path, "%s/doors.bin", dir);
        blob = malloc(DOOR_REC * DOOR_COUNT + 1);
        if (!blob || read_file(path, blob, DOOR_REC * DOOR_COUNT, &len) != 0) {
            printf("the halls do not answer to that word.\n");
            free(blob);
            return 0;
        }
        try_doors(root, blob, len, phrase);
        free(blob);
        return 0;
    }

    usage();
    return 0;
}

