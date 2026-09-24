/*
 * stage2_stego.c -- "The Cartographer's Ghost", Stage 2: The Interior Sheet.
 * Phase 3 deliverable.  Full design record: logs/PHASE_3_LOG.md.
 *
 * This tool is a VERIFIER and a PRESS, never an extractor.  It deliberately
 * does NOT hold:
 *   - the sweep (the pixel stride / first mark that Stage 1's REAL key
 *     material derives -- PHASE_2_LOG D23/D27): the solver derives it, so no
 *     means-of-derivation constant reaches a shipped binary;
 *   - the press formula (the sheet's zlib preset dictionary): it lives only as
 *     raw bytes in the tape's metadata, so a naive decompression cannot
 *     silently succeed with the wrong bytes;
 *   - the reading itself: only its SHA-256 digest is compiled in.
 *
 * What it does:
 *   - audits the two carriers beside it against their fingerprints (SHA-256
 *     of the shipped files) and says so plainly;
 *   - presses a re-supplied ink through a re-supplied press mark and reports
 *     the reading (s2_inflate: hand-rolled inflate with preset-dictionary
 *     support), then verdicts it;
 *   - accepts or refuses a claimed reading with a constant-time digest
 *     comparison and NO partial-match feedback of any kind;
 *   - routes a registered decoy reading into the extended branch (new
 *     information, never an error) and records the branch bit.
 *
 * Run from the cartographer/ package root:
 *   ./stage2_stego/stage2_stego
 *   ./stage2_stego/stage2_stego -c 'CARTO{...}'
 *   ./stage2_stego/stage2_stego -p <mark-file|hex> -R <ink-file>
 */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <string.h>

#include "carto_sha256.h"
#include "s2_inflate.h"
#include "stage2_blob.h"
#include "state.h"

#define STATE_PATH "./.cartographer_state"
#define SHEET_PATH "./stage2_stego/survey_frame.png"
#define TAPE_PATH  "./stage2_stego/survey_tape.wav"

#define TOKEN_LEN  40                     /* "CARTO{" + 32 hex + "}" + NUL */
#define CLAIM_MAX  512
#define FILE_MAX   (1u << 20)             /* carrier / ink read cap         */
#define MARK_MAX   (1u << 16)             /* press mark cap                 */
#define OUT_MAX    (1u << 16)             /* inflate output cap             */

static unsigned char g_file[FILE_MAX];
static unsigned char g_mark[MARK_MAX];
static unsigned char g_out[OUT_MAX];

/* The ".rodata spent press" advertisement, kept live by a never-taken branch
 * (the same idiom PHASE_2_LOG D27 used: a volatile gate GCC must honor). */
static volatile int keep_decoy;               /* never set: never-taken branch */

/* ------------------------------------------------------------------ output */

static void banner(void)
{
    printf("======================================================================\n");
    printf("  THE CARTOGRAPHER'S GHOST\n");
    printf("  Stage 2 -- The Interior Sheet\n");
    printf("======================================================================\n");
    printf("\n");
}

static void hex_of(const unsigned char *buf, size_t len)
{
    size_t i;

    for (i = 0; i < len; i++)
        printf("%02x", buf[i]);
}

/* Read at most FILE_MAX bytes; returns the length or (size_t)-1. */
static size_t read_file(const char *path, unsigned char *dst, size_t cap)
{
    FILE *f = fopen(path, "rb");
    size_t n;

    if (f == NULL)
        return (size_t)-1;
    n = fread(dst, 1, cap, f);
    fclose(f);
    return n;
}
/* -------------------------------------------------------------- the ledger */

static void mint_token(const unsigned char digest[32], char out[TOKEN_LEN])
{
    static const char hx[] = "0123456789abcdef";
    size_t i, o = 0;

    out[o++] = 'C'; out[o++] = 'A'; out[o++] = 'R'; out[o++] = 'T';
    out[o++] = 'O'; out[o++] = '{';
    for (i = 0; i < 16; i++) {
        out[o++] = hx[digest[i] >> 4];
        out[o++] = hx[digest[i] & 0x0Fu];
    }
    out[o++] = '}';
    out[o] = 0;
}

/* Audit one carrier against its fingerprint. Returns 1 = known, 0 = present
 * but not the ledger's, -1 = not beside the tool. Never an error. */
static int audit_carrier(const char *label, const char *path,
                         const unsigned char want[32])
{
    unsigned char got[32];
    size_t n = read_file(path, g_file, sizeof g_file);

    if (n == (size_t)-1) {
        printf("  %s : %s -- not beside the tool; the verdict stands on the\n"
               "            reading alone\n", label, path);
        return -1;
    }
    carto_sha256(g_file, n, got);
    if (carto_ct_equal(got, want, 32)) {
        printf("  %s : %s -- the ledger knows this one\n", label, path);
        return 1;
    }
    printf("  %s : %s -- this is not the ledger's %s\n", label, path, label);
    return 0;
}

/*
 * Verdict on a reading. Returns 1 = the figure, 2 = a registered decoy branch
 * (branch id in *branch_out), 0 = not the figure. The digest comparison is
 * constant time and the length test is evaluated unconditionally, so no
 * partial-match information leaks through timing or through wording.
 */
static int verdict(const unsigned char *reading, size_t len, int *branch_out)
{
    unsigned char digest[32];
    int is_real, len_ok;

    *branch_out = -1;
    carto_sha256(reading, len, digest);
    is_real = carto_ct_equal(digest, kStage2ExpectedDigest, 32);
    len_ok = (len == (size_t)CARTO_S2_EXPECTED_LEN);
    if (is_real & len_ok)
        return 1;
    if (len > 0 && len <= CLAIM_MAX) {
        char claim[CLAIM_MAX + 1];

        memcpy(claim, reading, len);
        claim[len] = 0;
        *branch_out = carto_lookup_decoy(CARTO_STAGE2, claim);
        if (*branch_out >= 1)
            return 2;
    }
    return 0;
}

static void report_real(const unsigned char *reading, size_t len, int esc)
{
    char token[TOKEN_LEN];

    mint_token(kStage2ExpectedDigest, token);
    printf("  the ledger takes this reading:\n\n    ");
    fwrite(reading, 1, len, stdout);
    printf("\n\n");
    printf("  the interior figure stands. Stage 2 checkpoint token -- bank it:\n\n");
    printf("    %s\n\n", token);
    if (esc)
        printf("  extended audit: the second pass agrees with the first; sheet and\n"
               "  tape were struck from the same press.\n\n");
    printf("  Carry it to the oracle. It answers in figures, not in ink.\n");
}

static void report_decoy(const char *claim, int esc)
{
    printf("  the ledger knows this ink. It accepts it as a corroborated reading\n");
    printf("  and re-inks the checkpoint the old man left for the coast survey:\n\n");
    printf("    %s\n\n", claim);
    if (esc)
        printf("  extended audit: this mark was struck from the coast press, not the\n"
               "  interior one.\n\n");
    printf("  Nothing here needs re-drawing.\n");
}

static void report_unknown(void)
{
    printf("  the ledger does not know that reading: it is not the interior figure.\n");
    printf("  Nothing about a wrong reading is an error. Keep the mark; the sweep is\n");
    printf("  somewhere on the sheet, and the press is on the tape.\n");
}
/* --------------------------------------------------------------- the press */

static int looks_hex(const char *s)
{
    size_t i, n = strlen(s);

    if (n < 8 || (n % 2) != 0)
        return 0;
    for (i = 0; i < n; i++) {
        char c = s[i];
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')
              || (c >= 'A' && c <= 'F')))
            return 0;
    }
    return 1;
}

static int hex_nib(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return c - 'A' + 10;
}

/* The press mark may be handed over as raw bytes in a file, or as hex. */
static size_t load_mark(const char *arg, unsigned char *dst, size_t cap)
{
    size_t n, i;

    if (looks_hex(arg)) {
        n = strlen(arg) / 2;
        if (n > cap)
            return (size_t)-1;
        for (i = 0; i < n; i++)
            dst[i] = (unsigned char)((hex_nib(arg[2 * i]) << 4)
                                     | hex_nib(arg[2 * i + 1]));
        return n;
    }
    return read_file(arg, dst, cap);
}

/*
 * Press mode: the solver hands over the press mark (raw, as it stands on the
 * tape) and the ink drawn from the sheet, packed eight marks to a letter as it
 * came.  A refusal is never an error and never diagnoses which side was wrong.
 * Returns the verdict code, or -1 when no reading could be pressed.
 */
static int press_mode(const char *mark_arg, const char *ink_arg,
                      const unsigned char **reading, size_t *reading_len,
                      int *branch)
{
    size_t mark_len, ink_len, framed, got;

    mark_len = load_mark(mark_arg, g_mark, sizeof g_mark);
    if (mark_len == (size_t)-1 || mark_len == 0) {
        printf("  the press mark does not read. Hand it over as the bytes that stand\n");
        printf("  on the tape, or as hex letters; the press keeps no mark of its own.\n\n");
        return -1;
    }
    ink_len = read_file(ink_arg, g_file, sizeof g_file);
    if (ink_len == (size_t)-1) {
        printf("  the ink is not beside the tool.\n\n");
        return -1;
    }
    if (ink_len < 4) {
        printf("  the ink does not read to its own length: too few marks.\n\n");
        return -1;
    }
    framed = (size_t)g_file[0] | ((size_t)g_file[1] << 8);
    if (framed + 2 > ink_len) {
        printf("  the ink does not read to its own length: %zu marks framed,\n"
               "  %zu drawn.\n\n", framed + 2, ink_len);
        return -1;
    }
    got = s2_inflate(g_file + 2, framed, g_mark, mark_len, g_out, sizeof g_out);
    if (got == (size_t)-1) {
        printf("  the press does not accept this ink -- it reads as noise at the head.\n");
        printf("  The marks are drawn; the press mark may not be the tape's.\n\n");
        return -1;
    }
    printf("  the press accepts this ink, %zu letters:\n\n    ", got);
    fwrite(g_out, 1, got > 240 ? 240 : got, stdout);
    printf("\n\n");
    *reading = g_out;
    *reading_len = got;
    return verdict(g_out, got, branch);
}

/*
 * Derives the graticule sweep from the survey key material (PHASE_3_LOG D31):
 *   stride = 3 + (LE64(key[0:8]) % 61)
 *   start  = 512 + (LE64(key[8:16]) % 9000)
 *
 * Solvers who reverse this tool obtain the sweep algorithm from code disassembly
 * rather than plain-text carrier metadata.
 */
static void carto_s2_derive_sweep(const unsigned char key[16],
                                  unsigned int *stride, unsigned int *start)
{
    uint64_t r6 = 0, r7 = 0;
    int i;

    for (i = 0; i < 8; i++) {
        r6 |= ((uint64_t)key[i]) << (8 * i);
        r7 |= ((uint64_t)key[8 + i]) << (8 * i);
    }
    if (stride != NULL)
        *stride = 3u + (unsigned int)(r6 % 61u);
    if (start != NULL)
        *start = 512u + (unsigned int)(r7 % 9000u);
}

static void usage(void)
{
    printf("The ledger will take a reading, or press an ink.\n\n");
    printf("    ./stage2_stego/stage2_stego -c '<reading>'\n");
    printf("        hand over what you read out of the sheet\n\n");
    printf("    ./stage2_stego/stage2_stego -p <mark|mark-file> -R <ink-file>\n");
    printf("        hand over the sheet's press mark (raw bytes in a file, or as\n");
    printf("        hex letters) and the ink drawn from the sheet, packed eight\n");
    printf("        marks to a letter as it came\n\n");
    printf("Nothing about a wrong reading is an error -- the ledger says plainly\n");
    printf("that it does not know it, and keeps no grudge.\n");
}
int main(int argc, char **argv)
{
    const unsigned char *reading = NULL;
    const char *claim = NULL, *mark_arg = NULL, *ink_arg = NULL;
    carto_state_t st;
    uint64_t now;
    unsigned reasons;
    size_t reading_len = 0;
    int fresh, esc, branch = -1, v = 0, i;

    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-c") == 0 && i + 1 < argc)
            claim = argv[++i];
        else if (strcmp(argv[i], "-p") == 0 && i + 1 < argc)
            mark_arg = argv[++i];
        else if (strcmp(argv[i], "-R") == 0 && i + 1 < argc)
            ink_arg = argv[++i];
        else if (argv[i][0] != '-' && claim == NULL)
            claim = argv[i];
    }

    now = carto_now_ms();
    fresh = (carto_state_load(STATE_PATH, &st, now) != CARTO_LOAD_OK);
    carto_bump_attempt(&st, CARTO_STAGE2);
    carto_record_interaction(&st, now);
    reasons = carto_should_escalate(&st, CARTO_STAGE2, now);
    esc = (reasons != 0);

    banner();
    if (fresh) {
        printf("The coast is behind you. This is the interior: a sheet of survey\n");
        printf("marks, and the tape the old man spoke his field note onto. Neither\n");
        printf("of them is a map with the figure drawn on it plainly.\n");
    } else {
        printf("The ledger is warm. It has kept this page open since your last visit.\n");
    }
    printf("\n");
    (void)audit_carrier("sheet", SHEET_PATH, kStage2SheetSha256);
    (void)audit_carrier("tape", TAPE_PATH, kStage2TapeSha256);
    printf("  ledger mode : %s\n\n", esc ? "extended audit" : "plain audit");

    if (ink_arg != NULL && mark_arg != NULL) {
        v = press_mode(mark_arg, ink_arg, &reading, &reading_len, &branch);
    } else if (claim != NULL) {
        reading = (const unsigned char *)claim;
        reading_len = strlen(claim);
        v = verdict(reading, reading_len, &branch);
    } else {
        usage();
    }

    if (branch >= 1)
        carto_mark_decoy(&st, CARTO_STAGE2, 1u << (branch - 1));
    (void)carto_state_save(STATE_PATH, &st);

    if (v == 1)
        report_real(reading, reading_len, esc);
    else if (v == 2)
        report_decoy(claim != NULL ? claim : "(the pressed ink)", esc);
    else
        report_unknown();

    /* Never-taken branch: keeps the spent-press advertisement live in .rodata
     * and the sweep derivation arithmetic live in code disassembly. */
    if (keep_decoy && v == -1 && sizeof kStage2SpentPress == 32) {
        unsigned int st = 0, sp = 0;
        carto_s2_derive_sweep(g_file, &st, &sp);
        printf("  (%s)\n    ", kStage2SpentPressNote);
        hex_of(kStage2SpentPress, 32);
        printf("\n");
        if (st == 0 && sp == 0) printf("%u", st);
    }
    printf("======================================================================\n");
    fflush(stdout);
    return 0;
}
