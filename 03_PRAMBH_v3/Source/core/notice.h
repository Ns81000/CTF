#ifndef PRAMBH_NOTICE_H
#define PRAMBH_NOTICE_H

/*
 * The operator notice (spec 4.10): honest, non-accusatory framing.
 * ZERO secrets, ZERO verdict words, ZERO mechanism words.
 * Embedded in .rodata of every shipped binary, printed on usage,
 * and placed in PNG tEXt "Notice" chunks of the plates.
 */
#define PRAMBH_NOTICE \
    "PRAMBH is a survey, not a service. Its instruments record but never " \
    "confirm: no output here will tell you whether anything worked, and " \
    "nothing will object when it did not. The only proof of the whole " \
    "journey is the final title. Take notes. Trust timestamps, not moods."

#endif
