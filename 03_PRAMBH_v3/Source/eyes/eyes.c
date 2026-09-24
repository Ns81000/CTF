/*
 * stage5_eyes/eyes - the surveyor's eyes (spec 4.7).
 *
 *   ./eyes                        banner + usage + canary notice
 *   ./eyes seal <vector-hex>      settle chain #2 and open the viewing
 *                                 notes with K_eyes (75-minute walk)
 *   ./eyes plates                 list what the depot shipped
 *
 * rc 0 always; stderr silent always; the only file written is the state
 * file in the package root.
 */
#include "../chain/chain.h"
#include "../core/carto_sha256.h"
#include "../core/sha256ctr.h"
#include "../core/canary.h"
#include "../core/notice.h"
#include "../state/state.h"
#include "eyes_consts.h"

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define SEED_LABEL "prambh:eyes:seed:v1"
#define NOTES_MARK "SURVEYOR'S EYES"

static void usage(void)
{
    printf("the surveyor's eyes - first survey field station\n"
           "usage:\n"
           "  ./eyes                        this marker\n"
           "  ./eyes seal <vector-hex>      settle the seal and read the notes\n"
           "  ./eyes plates                 what the depot shipped\n"
           "\nstation canary: %s\n\n%s\n", PRAMBH_CANARY, PRAMBH_NOTICE);
}

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

static int seal(const char *root, const char *vec_hex)
{
    uint8_t vec[32], seed[32], out[32], buf[EYES_NOTES_MAX];
    uint8_t label[32 + 19];
    prambh_state st;
    char path[4096], dir[4096];
    int fd;
    ssize_t got;

    prambh_state_load(root, &st);
    if (!(prambh_state_get64(&st, ST_OFF_STAGE) & PRAMBH_BIT_DOORS_REAL)) {
        printf("the plates have not been handed over yet.\n");
        prambh_state_save(root, &st);
        return 0;
    }
    if (parse_hex32(vec_hex, vec) != 0) {
        printf("the seal does not settle.\n");
        return 0;
    }
    memcpy(label, SEED_LABEL, 19);
    memcpy(label + 19, vec, 32);
    carto_sha256(label, sizeof label, seed);
    if (prambh_chain_run(seed, EYES_TABLE_BYTES, EYES_STEPS, out) != 0) {
        printf("the seal does not settle.\n");
        return 0;
    }
    prambh_state_set64(&st, ST_OFF_STAGE,
                       prambh_state_get64(&st, ST_OFF_STAGE)
                       | PRAMBH_BIT_CHAIN2_DONE);
    memcpy(st.bytes + ST_OFF_CHAIN2_SEED, vec, 32);
    memcpy(st.bytes + ST_OFF_CHAIN2_OUT, out, 32);
    prambh_state_save(root, &st);

    if (self_dir(dir, sizeof dir) != 0) {
        printf("the plates do not read.\n");
        return 0;
    }
    path[0] = 0;
    strncat(path, dir, sizeof(path) - strlen(path) - 1);
    strncat(path, "/eyes_notes.bin", sizeof(path) - strlen(path) - 1);
    fd = open(path, O_RDONLY);
    if (fd < 0) {
        printf("the plates do not read.\n");
        return 0;
    }
    got = read(fd, buf, sizeof buf);
    close(fd);
    if (got <= 0) {
        printf("the plates do not read.\n");
        return 0;
    }
    prambh_sha256ctr_xor(out, buf, (size_t)got);
    buf[got - 1] = 0;
    if (memcmp(buf, NOTES_MARK, strlen(NOTES_MARK)) == 0)
        printf("%s\n", (char *)buf);
    else
        printf("the plates do not read.\n");
    memset(seed, 0, sizeof seed);
    memset(out, 0, sizeof out);
    memset(buf, 0, sizeof buf);
    return 0;
}

int main(int argc, char **argv)
{
    char root[4096];
    prambh_state st;

    if (prambh_package_root(root, sizeof root) != 0)
        strcpy(root, ".");
    prambh_state_load(root, &st);
    prambh_state_save(root, &st);

    if (argc >= 3 && strcmp(argv[1], "seal") == 0)
        return seal(root, argv[2]);
    if (argc >= 2 && strcmp(argv[1], "plates") == 0) {
        printf("the depot shipped four plates: depth.png, hue.png,\n"
               "sheet_a.png and sheet_b.png.\n");
        return 0;
    }
    usage();
    return 0;
}
