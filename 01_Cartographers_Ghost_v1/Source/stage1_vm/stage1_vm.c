/*
 * stage1_vm.c -- "The Cartographer's Ghost", Stage 1: The Survey Engine.
 * Phase 2 deliverable.  Full design record: logs/PHASE_2_LOG.md.
 *
 * Behaviour:
 *   - loads/creates ./.cartographer_state through the shared state library,
 *     bumps the Stage 1 attempt counter and records the interaction
 *   - selects one of two PRE-BUILT engine variants from the escalation
 *     reasons (fast arrival / uniform timing / persisted debugger flag);
 *     both variants compute the identical Stage 2 key material
 *   - runs the embedded bytecode in the custom VM (vm.c) and packs the key
 *     material from the final ledger (R6,R7,R1,R2)
 *   - anti-debug: ptrace(PTRACE_TRACEME) self-attach check plus a timing
 *     ratio check against a fixed calibration loop.  On detection it does
 *     NOT error: it flips debugger_detected in the state file and the
 *     engine silently perturbs its ledger, so the printed key and token are
 *     well-formed but wrong
 *   - decoy routing: passing a registered decoy token routes into the
 *     extended branch (framed as new information) instead of erroring
 *   - the ".rodata forgotten debug constant" (decoy_blob.h) is a plausible
 *     but wrong Stage 2 key, kept live by a never-taken branch so a static
 *     reader can find it
 *
 * Run from the cartographer/ package root:   ./stage1_vm/stage1_vm [token]
 */
#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <sys/ptrace.h>

#include "decoy_blob.h"
#include "state.h"
#include "vm.h"
#include "vm_debug.h"
#include "vm_program.h"

#define STATE_PATH "./.cartographer_state"
#define KEY_LEN 32
#define TOKEN_LEN 40                    /* "CARTO{" + 32 hex + "}" + NUL */

/* ---------------------------------------------------------------------------
 * The decoy surface.  A static reader who goes looking for "the key" finds
 * this record instead of running the engine.  It is deliberately not hidden:
 * it is a plausible value, it mints a plausible (and registered) Stage 1
 * decoy token, and it only fails later, at Stage 3.
 * ------------------------------------------------------------------------- */
static const struct {
    const char *note;
    unsigned char key[CARTO_S1_DECOY_KEY_LEN];
} kStage1ForgottenRecord = {
    kStage1ForgottenNote,
    CARTO_S1_DECOY_KEY_INIT
};

/* ------------------------------------------------------------------ timing */

static double mono_seconds(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

/* Fixed calibration loop: scales with the machine, not with the trace. */
static double calibration_seconds(void)
{
    volatile unsigned long long sink = 0x123456789ABCDEFull;
    unsigned long long x = 0x9E3779B97F4A7C15ull;
    unsigned i;
    double t0, t1;

    t0 = mono_seconds();
    for (i = 0; i < 2000000u; i++) {
        x = x * 6364136223846793005ull + 1442695040888963407ull;
        sink ^= x;
    }
    t1 = mono_seconds();
    return t1 - t0;
}

/*
 * Reads TracerPid from /proc/self/status.
 *   > 0  a tracer is attached (gdb, strace, ...)
 *   == 0 no tracer is attached
 *   < 0  inconclusive (no /proc, or the field was not found)
 */
static int tracer_pid_from_proc(void)
{
    FILE *f = fopen("/proc/self/status", "r");
    char  line[256];
    int   pid = -1;

    if (f == NULL)
        return -1;
    while (fgets(line, (int)sizeof line, f) != NULL) {
        if (strncmp(line, "TracerPid:", 10) == 0) {
            pid = (int)strtol(line + 10, NULL, 10);
            break;
        }
    }
    fclose(f);
    return pid;
}

/*
 * Debugger detection.  Phase FINAL fairness fix -- see the patch header in
 * d:/gandu/_stage/s5_final/p3_tracerpid.py and PHASE_2_LOG open question 5.
 * The authoritative signal is /proc TracerPid; the ptrace probe is only a
 * fallback and only EPERM (a genuine "you are already traced") counts.
 */
static int detect_via_ptrace(void)
{
    int tracer = tracer_pid_from_proc();

    if (tracer > 0)
        return 1;                 /* a real tracer: confirmed attached       */
    if (tracer == 0)
        return 0;                 /* /proc says no tracer: trust it          */

    errno = 0;
    if (ptrace(PTRACE_TRACEME, 0, 0, 0) < 0)
        return (errno == EPERM) ? 1 : 0;
    return 0;
}

/* ------------------------------------------------------------------ output */

static void mint_token(const unsigned char key[KEY_LEN], char out[TOKEN_LEN])
{
    static const char *hexd = "0123456789abcdef";
    int i;

    out[0] = 'C'; out[1] = 'A'; out[2] = 'R'; out[3] = 'T'; out[4] = 'O';
    out[5] = '{';
    for (i = 0; i < 16; i++) {
        out[6 + 2 * i]     = hexd[(key[i] >> 4) & 0xF];
        out[6 + 2 * i + 1] = hexd[key[i] & 0xF];
    }
    out[38] = '}';
    out[39] = '\0';
}

static void banner(void)
{
    printf("======================================================================\n");
    printf("  THE CARTOGRAPHER'S GHOST\n");
    printf("  Stage 1 -- The Survey Engine\n");
    printf("======================================================================\n");
    printf("\n");
}

int main(int argc, char **argv)
{
    carto_state_t st;
    vm_result_t   res;
    unsigned char key[KEY_LEN];
    char          token[TOKEN_LEN];
    const unsigned char *prog;
    unsigned int  plen;
    uint64_t      now;
    unsigned      reasons;
    int           fresh, pre_detected, timing_detected, detected, profile;
    int           decoy_branch = -1;
    int           recognised = 0;
    double        t_base, t0, t_vm;
    volatile int  keep_decoy = 0;

    now   = carto_now_ms();
    fresh = (carto_state_load(STATE_PATH, &st, now) != CARTO_LOAD_OK);

    carto_bump_attempt(&st, CARTO_STAGE1);
    carto_record_interaction(&st, now);

    reasons = carto_should_escalate(&st, CARTO_STAGE1, now);
    profile = (reasons & (CARTO_ESC_TIME_FAST | CARTO_ESC_TIMING_UNIFORM |
                          CARTO_ESC_DEBUGGER)) ? 1 : 0;

    if (argc > 1)
        decoy_branch = carto_lookup_decoy(CARTO_STAGE1, argv[1]);

    pre_detected = detect_via_ptrace();

    prog = profile ? kProgram1 : kProgram0;
    plen = profile ? (unsigned int)VM_PROG1_LEN : (unsigned int)VM_PROG0_LEN;

    t_base = calibration_seconds();
    t0 = mono_seconds();
    if (vm_run(prog, plen, pre_detected, &res) != 0)
        res.fault = 1;
    t_vm = mono_seconds() - t0;

    timing_detected = carto_timing_verdict(t_base, t_vm);
    detected = pre_detected || timing_detected;

    /* Re-run on the detected path so the served ledger is genuinely the one
     * the program itself produced for that branch (no output patching). */
    if (timing_detected && !pre_detected) {
        if (vm_run(prog, plen, 1, &res) != 0)
            res.fault = 1;
    }

    if (detected)
        carto_set_debugger_detected(&st, 1);

    if (decoy_branch >= 1)
        carto_mark_decoy(&st, CARTO_STAGE1, 1u << (decoy_branch - 1));
    (void)carto_state_save(STATE_PATH, &st);

    vm_pack_key(&res, key);
    mint_token(key, token);

    banner();

    if (fresh) {
        printf("Past the ledger's first page there is no map at all -- only an\n");
        printf("engine: a survey instrument the old man built to keep drawing\n");
        printf("after his hand stopped. Its rules are not written down anywhere;\n");
        printf("it re-inks them itself as it turns, so no reading of it can be\n");
        printf("taken from a standing start.\n");
    } else {
        printf("The engine is warm. It has kept drawing since you were last here.\n");
    }
    printf("\n");
    printf("A second hand, in the margin -- smaller, and not the keeper's:\n");
    printf("  \"The true figure lies not on the coast but at the third survey\n");
    printf("   mark, westward; count them and the ledger will open.\"\n");
    printf("\n");

    if (decoy_branch >= 1) {
        const unsigned char *dk = kStage1ForgottenRecord.key;
        char dtoken[TOKEN_LEN];
        mint_token(dk, dtoken);
        printf("The margin note matches the ink you carried in. The survey\n");
        printf("engine accepts it as a corroborated reading and re-inks the\n");
        printf("checkpoint the old man left behind for the 0.4 survey:\n");
        printf("\n");
        printf("  engine variant : %s\n", profile ? "interior" : "coastal");
        printf("\n  confirmed token:\n    %s\n", dtoken);
        printf("\n");
        printf("Take it into the interior. Nothing here needs re-drawing.\n");
        printf("======================================================================\n");
        memset(dtoken, 0, sizeof dtoken);
        memset(key, 0, sizeof key);
        return 0;
    }

    printf("  engine variant : %s\n", profile ? "interior" : "coastal");
    printf("  engine steps   : %llu\n", (unsigned long long)res.steps);
    printf("\n");
    printf("Stage 1 token -- bank it, it is yours:\n");
    printf("\n    %s\n", token);
    printf("\n");
    printf("Carry it forward. The interior is not surveyed by daylight.\n");

    if (argc > 1) {
        if (strlen(argv[1]) == (size_t)(TOKEN_LEN - 1) &&
            memcmp(argv[1], token, (size_t)(TOKEN_LEN - 1)) == 0)
            recognised = 1;
        printf("  (the ledger %s that ink)\n",
               recognised ? "recognises" : "does not recognise");
    }
    printf("======================================================================\n");

    /* Never-taken branch: keeps the decoy record live in .rodata. */
    if (keep_decoy && res.fault == 2)
        printf("%s\n", kStage1ForgottenRecord.note);

    memset(key, 0, sizeof key);
    memset(token, 0, sizeof token);
    return 0;
}