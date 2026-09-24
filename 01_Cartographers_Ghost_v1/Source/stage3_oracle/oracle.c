/*
 * oracle.c -- "The Cartographer's Ghost", Stage 3: The Cipher Oracle.
 * Phase 4 deliverable.  Full design record: logs/PHASE_4_LOG.md (D46-D52).
 *
 * A local chosen-plaintext cipher oracle.  It holds a hand-rolled 4-round
 * Feistel-ish network (alternating keyed round functions, no final swap)
 * whose round functions carry a deliberate statistical bias (planted
 * collision sets in per-byte fold tables, D47); the key is
 * derived at RUNTIME from the Stage 2 reading handed in with -r (D46) --
 * never from a submittable token, and nothing here is gated on the reading
 * being "correct": a wrong reading yields a wrong, well-formed answer that
 * fails further up the survey (never an error).
 *
 * Automation response (D48): when the shared interaction ring shows
 * suspiciously uniform call spacing (CARTO_ESC_TIMING_UNIFORM only), the
 * oracle answers with ciphertexts from a DIFFERENT internal key -- silently,
 * well-formed, self-consistent, falsifiable, never a coin flip.
 *
 * What it deliberately does NOT hold (D38 pattern):
 *   - the KDF derivation seeds (only their masked forms ship);
 *   - any "is this the right reading" oracle: verification of a recovered
 *     key happens offline against collected pairs, not through this binary;
 *   - no key-check mode: a candidate key is verified by reproducing the
 *     oracle's own answers, which keeps brute force from feeding on
 *     cheap yes/no feedback.
 *
 * Run from the cartographer/ package root:
 *   ./stage3_oracle/oracle -r '<reading>' <figure>
 *   ./stage3_oracle/oracle                 (usage)
 */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <string.h>

#include "carto_sha256.h"
#include "oracle_blob.h"
#include "state.h"

#define STATE_PATH "./.cartographer_state"
#define READING_MAX 512
#define FIGURE_HEX_LEN 16               /* 64-bit block as written */

static const uint8_t *const kTabsA[4] = { kFoldA0, kFoldA1, kFoldA2, kFoldA3 };
static const uint8_t *const kTabsB[4] = { kFoldB0, kFoldB1, kFoldB2, kFoldB3 };

/* ---------------------------------------------------------------- helpers */

static uint32_t rotl32(uint32_t x, unsigned n)
{
    return (x << n) | (x >> (32u - n));
}

static uint32_t mix_a(uint32_t x)
{
    x ^= x >> 16;
    x *= 0x85EBCA6Bu;
    x ^= x >> 13;
    x *= 0xC2B2AE35u;
    x ^= x >> 16;
    return rotl32(x, 7u);
}

static uint32_t mix_b(uint32_t x)
{
    x = rotl32(x, 17u);
    x ^= x >> 15;
    x *= 0x2545F491u;
    x ^= x >> 14;
    x *= 0x9E3779B1u;
    x ^= x >> 16;
    return x;
}

/* fold_Z(y): one 256-entry table per window byte of y, XOR-folded in place.
 * A difference confined to byte j cancels the fold exactly when the j-th
 * table says so -- the planted 2^-2 collision sets live here (D47). */
static uint32_t fold_of(const uint8_t *const *t, uint32_t y)
{
    return (uint32_t)t[0][y & 0xFFu]
         | ((uint32_t)t[1][(y >> 8) & 0xFFu] << 8)
         | ((uint32_t)t[2][(y >> 16) & 0xFFu] << 16)
         | ((uint32_t)t[3][(y >> 24) & 0xFFu] << 24);
}

static uint32_t g_a(uint32_t y)
{
    return mix_a((y ^ fold_of(kTabsA, y)) & 0xFFFFFFFFu);
}

static uint32_t g_b(uint32_t y)
{
    return mix_b((y ^ fold_of(kTabsB, y)) & 0xFFFFFFFFu);
}

/* 64-bit block, 4 rounds, alternating round functions, no final swap. */
static uint64_t encrypt_block(uint32_t kA, uint32_t kB, uint64_t p)
{
    uint32_t l = (uint32_t)(p >> 32);
    uint32_t r = (uint32_t)p;
    unsigned rnd;

    for (rnd = 0; rnd < 4; rnd++) {
        uint32_t t = (rnd % 2u == 0u)
                   ? g_a((uint32_t)(r ^ kA))
                   : g_b((uint32_t)(r ^ kB));
        uint32_t nl = r;
        uint32_t nr = l ^ t;
        l = nl;
        r = nr;
    }
    return ((uint64_t)l << 32) | (uint64_t)r;
}

/* ------------------------------------------------------------- key set-up */

static void compute_table_mask(int variant, uint8_t mask[32])
{
    uint8_t buf[2048];
    if (variant == 0) {
        memcpy(buf + 0, kFoldA0, 256);
        memcpy(buf + 256, kFoldA1, 256);
        memcpy(buf + 512, kFoldA2, 256);
        memcpy(buf + 768, kFoldA3, 256);
        memcpy(buf + 1024, kFoldB0, 256);
        memcpy(buf + 1280, kFoldB1, 256);
        memcpy(buf + 1536, kFoldB2, 256);
        memcpy(buf + 1792, kFoldB3, 256);
    } else {
        memcpy(buf + 0, kFoldB0, 256);
        memcpy(buf + 256, kFoldB1, 256);
        memcpy(buf + 512, kFoldB2, 256);
        memcpy(buf + 768, kFoldB3, 256);
        memcpy(buf + 1024, kFoldA0, 256);
        memcpy(buf + 1280, kFoldA1, 256);
        memcpy(buf + 1536, kFoldA2, 256);
        memcpy(buf + 1792, kFoldA3, 256);
    }
    carto_sha256(buf, sizeof buf, mask);
    memset(buf, 0, sizeof buf);
}

static void unmask_seed(const uint8_t masked[32], int variant, uint8_t out[32])
{
    uint8_t mask[32];
    int i;

    compute_table_mask(variant, mask);
    for (i = 0; i < 32; i++)
        out[i] = (uint8_t)(masked[i] ^ mask[i]);
    memset(mask, 0, sizeof mask);
}

/* KDF (D46): kA,kB = first 8 bytes of SHA-256(seed || reading), big-endian.
 * The full digest is returned for the poison derivation. */
static void derive_keys(const char *reading, size_t rlen,
                        uint32_t *kA, uint32_t *kB, uint8_t digest[32])
{
    uint8_t seed[32];
    uint8_t buf[32 + READING_MAX];
    uint32_t kv[2];
    int i;

    unmask_seed(kMaskedSeedReal, 0, seed);
    memcpy(buf, seed, 32);
    memcpy(buf + 32, reading, rlen);
    carto_sha256(buf, 32 + rlen, digest);
    memset(buf, 0, sizeof buf);
    memset(seed, 0, sizeof seed);
    for (i = 0; i < 2; i++) {
        kv[i] = ((uint32_t)digest[4 * i] << 24)
              | ((uint32_t)digest[4 * i + 1] << 16)
              | ((uint32_t)digest[4 * i + 2] << 8)
              | (uint32_t)digest[4 * i + 3];
    }
    *kA = kv[0];
    *kB = kv[1];
}

/* The poison key set (D48): a different internal key, deterministically
 * derived from the real one, so poisoned answers stay self-consistent. */
static void poison_keys(const uint8_t real_digest[32],
                        uint32_t *kA, uint32_t *kB)
{
    uint8_t seed[32];
    uint8_t buf[64];
    uint8_t pd[32];
    uint32_t kv[2];
    int i;

    unmask_seed(kMaskedSeedPoison, 1, seed);
    memcpy(buf, seed, 32);
    memcpy(buf + 32, real_digest, 32);
    carto_sha256(buf, sizeof buf, pd);
    memset(buf, 0, sizeof buf);
    memset(seed, 0, sizeof seed);
    for (i = 0; i < 2; i++) {
        kv[i] = ((uint32_t)pd[4 * i] << 24)
              | ((uint32_t)pd[4 * i + 1] << 16)
              | ((uint32_t)pd[4 * i + 2] << 8)
              | (uint32_t)pd[4 * i + 3];
    }
    *kA = kv[0];
    *kB = kv[1];
}

/* ------------------------------------------------------------ hex figures */

static int hex_nib(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

/* The figure is read AS WRITTEN: the first hex pair is the most significant
 * byte of the block.  (The usage text states this in the ledger's own
 * sideways manner -- D51 -- but the parse is this plain rule.) */
static int parse_figure(const char *s, uint64_t *out)
{
    uint64_t v = 0;
    size_t i, n = strlen(s);

    if (n != FIGURE_HEX_LEN)
        return -1;
    for (i = 0; i < n; i++) {
        int h = hex_nib(s[i]);
        if (h < 0)
            return -1;
        v = (v << 4) | (uint64_t)h;
    }
    *out = v;
    return 0;
}

static void print_hex_block(uint64_t v)
{
    static const char hx[] = "0123456789abcdef";
    int i;

    for (i = 15; i >= 0; i--)
        putchar(hx[(v >> (4 * i)) & 0xFu]);
}

/* ------------------------------------------------------------- presentation */

static void banner(void)
{
    printf("======================================================================\n");
    printf("  THE CARTOGRAPHER'S GHOST\n");
    printf("  Stage 3 -- The Cipher Oracle\n");
    printf("======================================================================\n");
    printf("\n");
}

static void usage(void)
{
    printf("The oracle answers figures with figures. Hand it a reading and\n");
    printf("a figure:\n\n");
    printf("    ./stage3_oracle/oracle -r '<reading>' <figure>\n\n");
    printf("  <reading>  what the interior sheet yielded, handed over whole.\n");
    printf("             The oracle keeps no reading of its own; the reading\n");
    printf("             you carry in is the one it works from.\n\n");
    printf("  <figure>   sixteen hex letters, eight bytes to the block, one\n");
    printf("             byte to a pair as the sheet wrote them. Hand them\n");
    printf("             over as they stand -- the head pair opens the block.\n");
    printf("             The ledger files every figure under the tail it came\n");
    printf("             in with, and the oracle does not swap your letters:\n");
    printf("             it answers in the same order you handed them over.\n\n");
    printf("Every figure receives an answer, and no answer is ever refused;\n");
    printf("nothing about a wrong reading is an error here. The oracle only\n");
    printf("turns figures. What an answer is worth is decided further up the\n");
    printf("survey, where figures are read.\n");
}

static void report_decoy_branch(const char *reading, int branch)
{
    printf("  the ledger knows this ink. It is a checkpoint, not a reading --\n");
    printf("  struck earlier in the survey and handed back here. The oracle\n");
    printf("  will still turn figures for it, but under the ink you handed\n");
    printf("  over, not under the sheet's.\n\n");
    printf("  re-inked checkpoint (branch %d):\n\n    %s\n\n", branch, reading);
}

int main(int argc, char **argv)
{
    const char *reading = NULL, *figure = NULL;
    carto_state_t st;
    uint8_t digest[32];
    uint32_t kA, kB;
    uint64_t p = 0, c;
    uint64_t now;
    unsigned reasons;
    size_t rlen;
    int fresh, esc, poison, branch = -1, i;

    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-r") == 0 && i + 1 < argc)
            reading = argv[++i];
        else if (argv[i][0] != '-' && figure == NULL)
            figure = argv[i];
    }

    now = carto_now_ms();
    fresh = (carto_state_load(STATE_PATH, &st, now) != CARTO_LOAD_OK);
    carto_bump_attempt(&st, CARTO_STAGE3);
    carto_record_interaction(&st, now);
    reasons = carto_should_escalate(&st, CARTO_STAGE3, now);
    esc = (reasons != 0);
    poison = (reasons & CARTO_ESC_TIMING_UNIFORM) != 0;

    banner();
    if (fresh) {
        printf("Past the sheet, the survey turns to figures. Somewhere in\n");
        printf("the dark of the map room an engine answers every figure with\n");
        printf("a figure, and keeps its own counsel about what they mean.\n\n");
    } else {
        printf("The oracle is warm. It has been answering while you were away.\n\n");
    }
    printf("  oracle mode : %s\n\n", esc ? "witnessed" : "plain");

    if (reading == NULL) {
        printf("  the oracle answers only what is handed a reading.\n\n");
        usage();
    } else if (figure == NULL) {
        printf("  the oracle waits for a figure. Hand it one:\n\n");
        usage();
    } else {
        rlen = strlen(reading);
        branch = carto_lookup_decoy(CARTO_STAGE3, reading);
        if (rlen > READING_MAX) {
            printf("  the page holds no more ink: hand the reading over whole\n");
            printf("  and not by the yard.\n\n");
        } else if (parse_figure(figure, &p) != 0) {
            printf("  the figure does not read: sixteen hex letters, handed\n");
            printf("  over as they stand. The oracle keeps no grudge.\n\n");
        } else {
            derive_keys(reading, rlen, &kA, &kB, digest);
            if (poison)
                poison_keys(digest, &kA, &kB);
            memset(digest, 0, 32);
            c = encrypt_block(kA, kB, p);
            memset(&kA, 0, sizeof kA);
            memset(&kB, 0, sizeof kB);
            if (branch >= 1) {
                report_decoy_branch(reading, branch);
            }
            if (esc) {
                printf("  witnessed: the engine turns whether you watch it or\n");
                printf("  not.\n\n");
            }
            printf("  the oracle answers:\n\n    ");
            print_hex_block(c);
            printf("\n\n");
        }
    }

    if (reading != NULL && branch >= 1)
        carto_mark_decoy(&st, CARTO_STAGE3, 1u << (branch - 1));
    (void)carto_state_save(STATE_PATH, &st);
    fflush(stdout);
    return 0;
}


