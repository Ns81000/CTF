/*
 * stage0_milestone/milestone - the zero milestone (spec 4.2).
 *
 *  - no args: banner + usage + canary notice; creates/keeps state;
 *    prints the scored Stage-0 token (ungated, every run, by design).
 *  - "open <phrase>": opens capsule.bin with the phrase and prints the
 *    resulting 32-byte load vector (hex).  Any phrase yields a
 *    format-valid vector; only the launch phrase yields the real one.
 *  - rc 0 always; stderr silent always; the only file ever written is
 *    the state file in the package root.
 */
#include "../core/carto_sha256.h"
#include "../core/sha256ctr.h"
#include "../core/notice.h"
#include "../state/state.h"
#include "stage0_consts.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>

static void print_banner(void)
{
    printf("PRAMBH - the first survey\n");
    printf("zero milestone station, field unit 0\n");
    printf("\n");
}

static void print_usage(void)
{
    printf("usage:\n");
    printf("  milestone                 this marker\n");
    printf("  milestone open <phrase>   open the launch capsule\n");
    printf("\n");
    printf("the first surveyor's notes are in field-notes/ - begin there.\n");
    printf("\n");
    printf("%s\n", PRAMBH_NOTICE);
    printf("station canary: %s\n", CANARY_TOKEN);
}

static void ensure_state(const char *root)
{
    prambh_state st;
    prambh_state_load(root, &st);
    prambh_state_save(root, &st);
}

static int open_capsule(const char *root, const char *phrase)
{
    char path[1024];
    uint8_t capsule[32], pad[32], content[32];
    int fd, i;
    ssize_t got;

    snprintf(path, sizeof path, "%s/capsule.bin", root);
    fd = open(path, O_RDONLY);
    if (fd < 0) {
        printf("the capsule housing is empty.\n");
        return 0;
    }
    got = read(fd, capsule, sizeof capsule);
    close(fd);
    if (got != (ssize_t)sizeof capsule) {
        printf("the capsule housing is empty.\n");
        return 0;
    }

    carto_sha256((const uint8_t *)phrase, strlen(phrase), pad);
    memcpy(content, capsule, 32);
    prambh_sha256ctr_xor(pad, content, 32);

    printf("the capsule yields a loom load vector:\n");
    for (i = 0; i < 32; i++)
        printf("%02x", content[i]);
    printf("\n");
    printf("feed it to the survey loom when you find it.\n");
    return 0;
}

int main(int argc, char **argv)
{
    char root[4096];
    char phrase[512];
    int i;

    if (prambh_package_root(root, sizeof root) != 0)
        strcpy(root, ".");

    if (argc >= 3 && strcmp(argv[1], "open") == 0) {
        phrase[0] = 0;
        for (i = 2; i < argc; i++) {
            if (i > 2)
                strncat(phrase, " ", sizeof(phrase) - strlen(phrase) - 1);
            strncat(phrase, argv[i], sizeof(phrase) - strlen(phrase) - 1);
        }
        ensure_state(root);
        return open_capsule(root, phrase);
    }

    ensure_state(root);
    print_banner();
    printf("zero milestone mark: %s\n", STAGE0_TOKEN);
    printf("\n");
    print_usage();
    return 0;
}
