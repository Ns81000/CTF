/*
 * PRAMBH loom emulator host (spec 4.4): ./loom <command> ...
 *
 *   loom run    <file.rom> [--vector 0x<64hex>]   run a cartridge
 *   loom claim  <file.rom> [--vector 0x<64hex>]   run; print lodged claim
 *   loom verify [--vector 0x<64hex>] [--T n] [--S bytes]
 *                                                 native chain #1 walk
 *
 * The MERU-8 CPU core is in meru1.c; the ISA is documented in
 * field-notes/meru1_datasheet.txt.  Host services on the $F000 page:
 * teleprinter, stitch-table fill, SHA mixer, extended table window.
 * rc 0 and silent stderr on every clean run, including debug lanes.
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <sys/ptrace.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#include "../chain/chain.h"
#include "../core/carto_sha256.h"
#include "../core/canary.h"
#include "../core/notice.h"
#include "meru1.h"
#include "params.h"
#include "debug_rom.h"

#define SEED_LABEL "prambh:loom:seed:v1"   /* 19 bytes */
#define RUN_LABEL  "prambh:chain:run:v1"   /* 19 bytes */

#define OFF_PUTCHAR   0x00
#define OFF_EXIT      0x01
#define OFF_CLAIM     0x02
#define OFF_CART      0x10
#define OFF_USE_CART  0x30
#define OFF_CHAIN_T   0x31
#define OFF_CHAIN_S   0x39
#define OFF_CHAIN_INIT 0x3D
#define OFF_IN0       0x40
#define OFF_IN1       0x60
#define OFF_TAIL      0x80
#define OFF_GO        0x88
#define OFF_OUT       0x90
#define OFF_XIDX      0xB0
#define OFF_XFETCH    0xB8
#define OFF_S0        0xC0
#define OFF_XWIN      0xE0

typedef struct {
    uint8_t vector[32];
    uint8_t cart[32];
    int use_cart;
    uint64_t chain_t;
    uint32_t chain_s;
    uint64_t nblocks;
    uint64_t xidx;
    uint8_t *table;
    uint64_t table_bytes;
    uint64_t table_steps;
    uint8_t table_seed[32];
    int claimed;
    uint8_t claim[32];
    int debugger_flag;
} hostctx;

static void derive_seed(hostctx *h, uint8_t out[32])
{
    uint8_t buf[19 + 32];
    memcpy(buf, SEED_LABEL, 19);
    memcpy(buf + 19, h->use_cart ? h->cart : h->vector, 32);
    carto_sha256(buf, sizeof buf, out);
    memset(buf, 0, sizeof buf);
}

static void host_chain_init(meru1 *m, hostctx *h)
{
    uint8_t seed[32], buf[19 + 32 + 32];
    uint64_t T = h->chain_t ? h->chain_t : PRAMBH_CHAIN_T_DEFAULT;
    uint64_t S = h->chain_s ? h->chain_s : (uint64_t)PRAMBH_CHAIN_S_DEFAULT;

    derive_seed(h, seed);
    if (!h->table || h->table_bytes != S || h->table_steps != T
        || memcmp(h->table_seed, seed, 32) != 0) {
        free(h->table);
        h->table = malloc((size_t)S);
        if (!h->table) {      /* cannot fill: machine sees a zero table */
            h->nblocks = 0;
            memset(m->mem + MERU1_MMIO + OFF_S0, 0, 32);
            return;
        }
        prambh_chain_fill(seed, h->table, S / 32, S, T);
        h->table_bytes = S;
        h->table_steps = T;
        memcpy(h->table_seed, seed, 32);
    }
    h->nblocks = S / 32;
    /* s0 = SHA-256(run label || seed || table[n-1]) */
    memcpy(buf, RUN_LABEL, 19);
    memcpy(buf + 19, seed, 32);
    memcpy(buf + 51, h->table + (h->nblocks - 1) * 32, 32);
    carto_sha256(buf, sizeof buf, m->mem + MERU1_MMIO + OFF_S0);
    memset(buf, 0, sizeof buf);
    memset(seed, 0, sizeof seed);
}

static void host_sha_go(meru1 *m)
{
    uint8_t buf[72];
    memcpy(buf, m->mem + MERU1_MMIO + OFF_IN0, 32);
    memcpy(buf + 32, m->mem + MERU1_MMIO + OFF_IN1, 32);
    memcpy(buf + 64, m->mem + MERU1_MMIO + OFF_TAIL, 8);
    carto_sha256(buf, sizeof buf, m->mem + MERU1_MMIO + OFF_OUT);
    memset(buf, 0, sizeof buf);
}

static void host_xfetch(meru1 *m, hostctx *h)
{
    uint64_t idx;
    if (!h->table || h->nblocks == 0)
        return;
    idx = h->xidx % h->nblocks;
    memcpy(m->mem + MERU1_MMIO + OFF_XWIN, h->table + idx * 32, 32);
}

static void mmio_write(meru1 *m, uint16_t addr, uint8_t v)
{
    hostctx *h = (hostctx *)m->host;
    unsigned off = addr - MERU1_MMIO;

    if (off == OFF_PUTCHAR) {
        putchar(v);
        fflush(stdout);
    } else if (off == OFF_EXIT) {
        m->halted = 1;
    } else if (off == OFF_CLAIM) {
        memcpy(h->claim, m->mem + MERU1_MMIO + OFF_OUT, 32);
        h->claimed = 1;
    } else if (off >= OFF_CART && off < OFF_CART + 32) {
        h->cart[off - OFF_CART] = v;
    } else if (off == OFF_USE_CART) {
        h->use_cart = 1;
    } else if (off >= OFF_CHAIN_T && off < OFF_CHAIN_T + 8) {
        unsigned i = off - OFF_CHAIN_T;
        h->chain_t = (h->chain_t & ~(0xFFull << (8 * i)))
                     | ((uint64_t)v << (8 * i));
    } else if (off >= OFF_CHAIN_S && off < OFF_CHAIN_S + 4) {
        unsigned i = off - OFF_CHAIN_S;
        h->chain_s = (h->chain_s & ~(0xFFu << (8 * i)))
                     | ((uint32_t)v << (8 * i));
    } else if (off == OFF_CHAIN_INIT) {
        host_chain_init(m, h);
    } else if (off == OFF_GO) {
        host_sha_go(m);
    } else if (off >= OFF_XIDX && off < OFF_XIDX + 8) {
        unsigned i = off - OFF_XIDX;
        h->xidx = (h->xidx & ~(0xFFull << (8 * i))) | ((uint64_t)v << (8 * i));
    } else if (off == OFF_XFETCH) {
        host_xfetch(m, h);
    }
}

/*
 * Anti-debug (spec 4.4): TracerPid in /proc/self/status is authoritative
 * (Linux has no /proc/self/TracerPid file; the field lives in status and
 * is set by the kernel for ANY ptrace-based tracer: gdb, strace, ltrace).
 * The PTRACE_TRACEME/EPERM probe is the fallback for kernels without
 * procfs.  The probe runs in a disposable child so that a SUCCESSFUL
 * TRACEME never marks the emulator itself traced.  On detection the
 * caller silently swaps in the documented debug cartridge lane.
 */
static int debugger_present(void)
{
    FILE *f = fopen("/proc/self/status", "r");
    if (f) {
        char line[256];
        while (fgets(line, sizeof line, f)) {
            if (strncmp(line, "TracerPid:", 10) == 0) {
                long tpid = strtol(line + 10, NULL, 10);
                fclose(f);
                return tpid > 0;
            }
        }
        fclose(f);
    }
    {
        pid_t pid = fork();
        if (pid == 0) {
            if (ptrace(PTRACE_TRACEME, 0, 0, 0) == -1 && errno == EPERM)
                _exit(42);
            _exit(0);
        }
        if (pid > 0) {
            int st = 0;
            if (waitpid(pid, &st, 0) == pid && WIFEXITED(st)
                && WEXITSTATUS(st) == 42)
                return 1;
        }
    }
    return 0;
}

static int parse_hex(const char *s, uint8_t *out, size_t n)
{
    size_t i;
    if (s[0] == '0' && (s[1] == 'x' || s[1] == 'X'))
        s += 2;
    if (strlen(s) != 2 * n)
        return -1;
    for (i = 0; i < n; i++) {
        unsigned v;
        if (sscanf(s + 2 * i, "%2x", &v) != 1)
            return -1;
        out[i] = (uint8_t)v;
    }
    return 0;
}

static uint8_t *read_rom(const char *path, uint32_t *len)
{
    FILE *f = fopen(path, "rb");
    long sz;
    uint8_t *buf;

    if (!f)
        return NULL;
    if (fseek(f, 0, SEEK_END) != 0 || (sz = ftell(f)) < 0
        || fseek(f, 0, SEEK_SET) != 0) {
        fclose(f);
        return NULL;
    }
    if (sz == 0 || sz > (long)MERU1_ROM_MAX) {
        fclose(f);
        return NULL;
    }
    buf = malloc((size_t)sz);
    if (!buf || fread(buf, 1, (size_t)sz, f) != (size_t)sz) {
        fclose(f);
        free(buf);
        return NULL;
    }
    fclose(f);
    *len = (uint32_t)sz;
    return buf;
}

static void usage(void)
{
    printf("MERU-8 survey loom - field station emulator\n"
           "usage:\n"
           "  ./loom run   <file.rom> [--vector 0x<64hex>]\n"
           "  ./loom claim <file.rom> [--vector 0x<64hex>]\n"
           "  ./loom verify [--vector 0x<64hex>] [--T n] [--S bytes]\n"
           "\nstation canary: %s\n\n%s\n", PRAMBH_CANARY, PRAMBH_NOTICE);
}

static int run_rom(int argc, char **argv, int want_claim)
{
    hostctx h;
    meru1 m;
    uint8_t *rom;
    uint32_t romlen = 0;
    const char *path = NULL;
    int i;

    memset(&h, 0, sizeof h);
    for (i = 0; i < argc; i++) {
        if (strcmp(argv[i], "--vector") == 0 && i + 1 < argc) {
            if (parse_hex(argv[++i], h.vector, 32) != 0) {
                usage();
                return 0;
            }
        } else if (!path) {
            path = argv[i];
        } else {
            usage();
            return 0;
        }
    }
    if (!path) {
        usage();
        return 0;
    }
    rom = read_rom(path, &romlen);
    if (!rom) {
        printf("the cartridge does not read.\n");
        return 0;
    }
    if (debugger_present()) {
        /* documented debug lane: the diagnostic cartridge, never an error */
        free(rom);
        rom = (uint8_t *)DEBUG_ROM;
        romlen = DEBUG_ROM_LEN;
        h.debugger_flag = 1;
    }
    meru1_init(&m);
    m.host = &h;
    m.mmio_write = mmio_write;
    if (meru1_load_rom(&m, rom, romlen) != 0) {
        printf("the cartridge does not read.\n");
        if (rom != (uint8_t *)DEBUG_ROM)
            free(rom);
        return 0;
    }
    meru1_run(&m);
    if (want_claim) {
        if (!h.claimed) {
            printf("the loom lodged no claim.\n");
            free(h.table);
            if (rom != (uint8_t *)DEBUG_ROM)
                free(rom);
            return 0;
        }
        for (i = 0; i < 32; i++)
            printf("%02x", h.claim[i]);
        printf("\n");
    }
    free(h.table);
    if (rom != (uint8_t *)DEBUG_ROM)
        free(rom);
    return 0;
}

static int verify_chain(int argc, char **argv)
{
    uint8_t vector[32], seed[32], out[32], buf[51];
    uint64_t T = PRAMBH_CHAIN_T_DEFAULT;
    uint64_t S = PRAMBH_CHAIN_S_DEFAULT;
    int i;

    memset(vector, 0, sizeof vector);
    for (i = 0; i < argc; i++) {
        if (strcmp(argv[i], "--vector") == 0 && i + 1 < argc) {
            if (parse_hex(argv[++i], vector, 32) != 0) {
                usage();
                return 0;
            }
        } else if (strcmp(argv[i], "--T") == 0 && i + 1 < argc) {
            T = strtoull(argv[++i], NULL, 0);
        } else if (strcmp(argv[i], "--S") == 0 && i + 1 < argc) {
            S = strtoull(argv[++i], NULL, 0);
        } else {
            usage();
            return 0;
        }
    }
    memcpy(buf, SEED_LABEL, 19);
    memcpy(buf + 19, vector, 32);
    carto_sha256(buf, sizeof buf, seed);
    if (prambh_chain_run(seed, S, T, out) != 0) {
        printf("the survey table cannot be raised.\n");
        return 0;
    }
    printf("loom ink   : ");
    for (i = 0; i < 8; i++)
        printf("%02x", out[i]);
    printf("\ncheckpoint : PRAMBH{");
    for (i = 8; i < 16; i++)
        printf("%02x", out[i]);
    printf("}\n");
    memset(buf, 0, sizeof buf);
    memset(seed, 0, sizeof seed);
    return 0;
}

int main(int argc, char **argv)
{
    /*
     * Exit-code policy (spec 4.4 + 7 lane 6): the station always reports
     * success to the shell - usage screens, unreadable cartridges and
     * refusals included - so that no outcome can be told apart by rc.
     */
    if (argc < 2) {
        usage();
        return 0;
    }
    if (strcmp(argv[1], "run") == 0)
        return run_rom(argc - 2, argv + 2, 0);
    if (strcmp(argv[1], "claim") == 0)
        return run_rom(argc - 2, argv + 2, 1);
    if (strcmp(argv[1], "verify") == 0)
        return verify_chain(argc - 2, argv + 2);
    usage();
    return 0;
}

