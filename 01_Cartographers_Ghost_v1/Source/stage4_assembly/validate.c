/* validate.c -- Stage 4: The Title Block (final assembly validator).
 *
 * CLI (run from the cartographer/ package root):
 *     ./stage4_assembly/validate                    -> usage + the riddle
 *     ./stage4_assembly/validate '<the title, whole>'  -> verdict
 *
 * D38/D40 pattern (inherited from Stage 2): the tool holds the expected
 * final flag ONLY as a SHA-256 digest + length (generated header); the
 * comparison is constant-time; the length test is unconditional; every
 * wrong input gets byte-identical refusal text -- no partial-match
 * feedback of any kind (no "2 of 3 inks are right"), no error path,
 * rc 0 always, stderr always silent. A wrong Stage-2 reading (hence a
 * wrong Stage-3 K) assembles a wrong title that is simply REFUSED.
 *
 * No means-of-derivation constant lives here: no component ink, no seed
 * string, no flag. The Stage-4 decoy row arrives via policy.h (linked);
 * the struck first-draft decoy string arrives via the generated header.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include "carto_sha256.h"
#include "state.h"
#include "stage4_blob.h"

#define CARTO_S4_MAX_ARG 256u

/* The one and only refusal: byte-identical for every wrong input. */
static const char kRefusal[] =
    "  the title block does not take that ink. The survey holds its line.\n"
    "\n"
    "  The block keeps no grudge and gives no measure: it says the same\n"
    "  thing to every draft that is not the finished title. Re-read the\n"
    "  verse; the three inks and their seats do not move.\n";

static const char kUsage[] =
    "======================================================================\n"
    "  THE CARTOGRAPHER'S GHOST\n"
    "  Stage 4 -- The Title Block\n"
    "======================================================================\n"
    "\n"
    "Three inks, one line, under the old man's frame. He left the\n"
    "order of them in a verse he recited to the mirror:\n"
    "\n"
    "    The oracle, though it spoke last of the three,\n"
    "    sits at the head of the line -- so wrote he.\n"
    "    The engine came first in the survey, they say,\n"
    "    yet never at the front in the title's display:\n"
    "    it takes the middle seat it never held.\n"
    "    The sheet, which was drawn between the two,\n"
    "    is written below them both, last of the few.\n"
    "\n"
    "    Between neighbours set a single mark of the ground (an\n"
    "    underscore), and shut the line in the usual frame:\n"
    "    CARTO{...}.\n"
    "\n"
    "Each ink, as he meant it:\n"
    "\n"
    "  - the oracle ink: the key the oracle turned for the sheet's\n"
    "    own reading, sixteen lowercase hex letters, recovered as\n"
    "    it stands.\n"
    "  - the engine ink: the half of the engine's key material that\n"
    "    the engine's token never showed, sixteen lowercase hex\n"
    "    letters in the order the ledger prints them.\n"
    "  - the sheet ink: the sheet's reading, skinned of its frame.\n"
    "\n"
    "An earlier draft the old man struck out is still legible on\n"
    "the desk, though he abandoned it -- the mirror confused him:\n"
    "\n"
    "    %s\n"
    "\n"
    "  ./stage4_assembly/validate '<the title, whole>'\n"
    "      lay the title in the block. The ledger knows the finished\n"
    "      title and no other; it will not say how close a draft is.\n"
    "\n"
    "Nothing about a wrong title is an error -- the block simply does\n"
    "not take it, and says the same thing to every draft.\n"
    "======================================================================\n";

/* Escalation presentation (D44/D49 pattern): reasons != 0 selects the
 * "witnessed" presentation -- one extra flavor line. The verdict is
 * bit-identical in both variants (answer invariance). */
static const char kWitnessed[] =
    "  witnessed: the ledger takes the title whether you watch it or not.\n";

int main(int argc, char **argv)
{
    uint64_t now = carto_now_ms();
    carto_state_t st;
    int rc = carto_state_load("./.cartographer_state", &st, now);
    /* Runtime rule (PHASE_0 D14): CREATED and TAMPERED are identical. */
    (void)rc;
    carto_bump_attempt(&st, CARTO_STAGE4);
    carto_record_interaction(&st, now);
    unsigned reasons = carto_should_escalate(&st, CARTO_STAGE4, now);
    carto_state_save("./.cartographer_state", &st);

    if (argc < 2) {
        printf(kUsage, kStage4DraftFlag);
        return 0;
    }

    /* Decoy routing (D26/D41/D50 pattern): a registered stage-4 decoy is
     * never an error -- it routes into the extended branch, framed as new
     * information, rc 0, stderr silent, real flag never printed. Branch 1
     * persists bit 1u << (1 - 1) of decoy_mask[CARTO_STAGE4]. */
    int branch = carto_lookup_decoy(CARTO_STAGE4, argv[1]);
    if (branch >= 1) {
        carto_state_t st2;
        uint64_t now2 = carto_now_ms();
        carto_state_load("./.cartographer_state", &st2, now2);
        carto_mark_decoy(&st2, CARTO_STAGE4, 1u << (branch - 1));
        carto_record_interaction(&st2, now2);
        carto_bump_attempt(&st2, CARTO_STAGE4);
        carto_state_save("./.cartographer_state", &st2);

        printf("  the struck line matches the ink you carried in. The\n"
               "  block takes it as a corroborated draft and re-inks the\n"
               "  title the old man first set down for the closing page:\n"
               "\n"
               "    %s\n"
               "\n",
               kStage4DraftFlag);
        if (reasons != 0)
            fputs(kWitnessed, stdout);
        printf("  extended audit: a struck line is ink that never dried\n"
               "  into the block. The mirror's confusion is not yours to\n"
               "  inherit; the verse still names the seats.\n"
               "\n"
               "  Nothing here needs re-drawing.\n");
        return 0;
    }

    /* Verdict: the digest compare runs on EVERY input (constant path);
     * the length test is folded in bitwise, never short-circuited (D40).
     * Every wrong input -- malformed, wrong length, wrong order, wrong
     * ink, extra arguments -- prints the SAME refusal, rc 0, stderr
     * silent, and nothing about the input is diagnosed. */
    uint8_t got[32];
    size_t n = strlen(argv[1]);
    carto_sha256((const uint8_t *)argv[1], n, got);
    int eq = carto_ct_equal(got, kStage4ExpectedDigest, 32);
    int ok = eq & (n == (size_t)CARTO_S4_EXPECTED_LEN) & (argc == 2);

    if (ok) {
        if (reasons != 0)
            fputs(kWitnessed, stdout);
        printf("  the ledger takes the title:\n"
               "\n"
               "    %s\n"
               "\n"
               "  The survey is closed. The figure stands, the engine's\n"
               "  circuit is run, and the title block carries the whole\n"
               "  journey in one line.\n"
               "\n"
               "  Stage 4 complete -- the assembled flag is the answer.\n"
               "  Bank it; it is the last thing the old man hid.\n"
               "======================================================================\n",
               argv[1]);
    } else {
        fputs(kRefusal, stdout);
    }
    return 0;
}
