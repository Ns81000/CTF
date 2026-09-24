/*
 * prambh_chain - organizer-side chain tool (calibration, mint, tests).
 * NOT shipped in the player package.
 *
 * usage:
 *   prambh_chain walk --seed-hex H --s BYTES --t STEPS [--table-file F]
 *                     [--dump-table F]
 *   prambh_chain measure --s BYTES --seconds N
 *   prambh_chain fillbench --s BYTES
 */
#include "chain.h"
#include "../core/carto_sha256.h"
#include "../core/sha256ctr.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static double now_s(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}

static int hex2bin(const char *hex, uint8_t *out, size_t n)
{
    size_t i;
    if (strlen(hex) != 2 * n)
        return -1;
    for (i = 0; i < n; i++)
        if (sscanf(hex + 2 * i, "%2hhx", &out[i]) != 1)
            return -1;
    return 0;
}

static const char *argval(int argc, char **argv, const char *key)
{
    int i;
    for (i = 0; i + 1 < argc; i++)
        if (strcmp(argv[i], key) == 0)
            return argv[i + 1];
    return NULL;
}

int main(int argc, char **argv)
{
    const char *mode = argc > 1 ? argv[1] : NULL;

    if (mode && strcmp(mode, "walk") == 0) {
        const char *sh = argval(argc, argv, "--seed-hex");
        const char *ss = argval(argc, argv, "--s");
        const char *st = argval(argc, argv, "--t");
        const char *tf = argval(argc, argv, "--table-file");
        const char *dt = argval(argc, argv, "--dump-table");
        uint8_t seed[32], out[32], *table;
        uint64_t nbytes, nblocks, steps;
        FILE *f;
        int i;

        if (!sh || !ss || !st || hex2bin(sh, seed, 32) != 0)
            return 2;
        nbytes = strtoull(ss, NULL, 10);
        steps = strtoull(st, NULL, 10);
        nblocks = nbytes / 32;
        if (nblocks == 0)
            return 2;
        table = malloc((size_t)nbytes);
        if (!table)
            return 2;
        if (tf) {
            f = fopen(tf, "rb");
            if (!f) return 2;
            if (fread(table, 1, (size_t)nbytes, f) != (size_t)nbytes) {
                fclose(f);
                return 2;   /* withheld/truncated table: refuse */
            }
            fclose(f);
        } else {
            prambh_chain_fill(seed, table, nblocks, nbytes, steps);
        }
        if (dt) {
            f = fopen(dt, "wb");
            if (!f) return 2;
            fwrite(table, 1, (size_t)nbytes, f);
            fclose(f);
        }
        prambh_chain_walk(seed, table, nblocks, steps, out);
        for (i = 0; i < 32; i++)
            printf("%02x", out[i]);
        printf("\n");
        memset(table, 0, (size_t)nbytes);
        free(table);
        return 0;
    }

    if (mode && strcmp(mode, "measure") == 0) {
        const char *ss = argval(argc, argv, "--s");
        const char *sn = argval(argc, argv, "--seconds");
        uint64_t nbytes, nblocks, steps = 0, t;
        double t0, t1, budget;
        uint8_t seed[32], s[32], in[83], *table;
        uint64_t idx;

        if (!ss || !sn) return 2;
        nbytes = strtoull(ss, NULL, 10);
        budget = (double)atoll(sn);
        nblocks = nbytes / 32;
        if (nblocks == 0 || budget <= 0) return 2;
        memset(seed, 0x11, 32);
        table = malloc((size_t)nbytes);
        if (!table) return 2;
        t0 = now_s();
        prambh_chain_fill(seed, table, nblocks, nbytes, 0);
        t1 = now_s();
        fprintf(stderr, "fill %.2fs\n", t1 - t0);

        /* spec-exact walk loop, stopped by wall time */
        memcpy(in, "prambh:chain:run:v1", 19);
        memcpy(in + 19, seed, 32);
        memcpy(in + 51, table + (nblocks - 1) * 32, 32);
        carto_sha256(in, 83, s);
        t = 1;
        t0 = now_s();
        while (now_s() - t0 < budget) {
            idx = prambh_get_le64(s) % nblocks;
            memcpy(in, s, 32);
            memcpy(in + 32, table + idx * 32, 32);
            prambh_put_le64(in + 64, t);
            carto_sha256(in, 72, s);
            t++;
        }
        steps = t - 1;
        t1 = now_s();
        printf("%llu %.3f\n", (unsigned long long)steps, t1 - t0);
        memset(table, 0, (size_t)nbytes);
        free(table);
        return 0;
    }

    if (mode && strcmp(mode, "fillbench") == 0) {
        const char *ss = argval(argc, argv, "--s");
        uint64_t nbytes, nblocks;
        double t0, t1;
        uint8_t seed[32], *table;
        if (!ss) return 2;
        nbytes = strtoull(ss, NULL, 10);
        nblocks = nbytes / 32;
        if (nblocks == 0) return 2;
        memset(seed, 0x22, 32);
        table = malloc((size_t)nbytes);
        if (!table) return 2;
        t0 = now_s();
        prambh_chain_fill(seed, table, nblocks, nbytes, 0);
        t1 = now_s();
        printf("%.3f\n", t1 - t0);
        memset(table, 0, (size_t)nbytes);
        free(table);
        return 0;
    }

    fprintf(stderr, "usage\n");
    return 2;
}
