/*
 * probe_scale.c -- Phase FINAL section 4: direct, behavioural proof that
 * CARTO_TEST_TIME_SCALE works in the TEST build and is inert in the SHIPPED
 * build.  INTERNAL, never shipped.
 *
 * Links the shared state library and asks carto_should_escalate() two
 * questions whose answers differ ONLY if the hook is compiled in and set:
 *
 *   A. elapsed-time threshold: stage 4, elapsed 30 s, threshold 300 s
 *        scale 1  -> 30 s  < 300 s  -> CARTO_ESC_TIME_FAST
 *        scale 60 -> 30 s  <   5 s  -> no reason
 *   B. inter-arrival uniformity floor: ring of compressed deltas
 *      (0.4 ms / 6.6 ms alternating, stddev 3.1 ms)
 *        scale 1  -> 3.1 ms <= 150.0 ms -> CARTO_ESC_TIMING_UNIFORM
 *        scale 60 -> 3.1 ms >     2.5 ms -> no reason
 *
 * Build (shipped):     musl-gcc -O2 -static -I../state probe_scale.c ../state/libstate.a -o probe_scale -lm
 * Build (test build):  same, but against a library built with CARTO_TEST_BUILD=1
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "state.h"

#define NOW 1000000000000ull
#define T_FAST_S4_SEC 300u          /* mirrors policy.h's calibrated row */
#define STDDEV_FLOOR_MS 150.0

/*
 * Scenario B ring: inter-arrival deltas must have a stddev BETWEEN the scaled
 * floor (150/60 = 2.5 ms) and the unscaled floor (150 ms) or the probe proves
 * nothing.  Offsets give deltas 1,9,1,9,1,9,1 -> mean 4.43 ms, stddev 3.96 ms.
 * (A constant spacing would have stddev 0 and fire under BOTH, which is what
 * the first version of this probe got wrong.)
 */
static const uint64_t B_OFFSETS[8] = { 1, 2, 11, 12, 21, 22, 31, 32 };

int main(void)
{
    carto_state_t st;
    unsigned a, b;
    const char *scale = getenv("CARTO_TEST_TIME_SCALE");
    int i;

    /* A: reached stage 4 thirty seconds after the very first run. */
    memset(&st, 0, sizeof st);
    st.first_run_ms = NOW;
    a = carto_should_escalate(&st, 4, NOW + 30000ull);

    /* B: a ring whose inter-arrival deltas are ~60x compressed. */
    memset(&st, 0, sizeof st);
    st.first_run_ms = NOW;
    for (i = 0; i < 8; i++)
        carto_record_interaction(&st, NOW + B_OFFSETS[i]);
    b = carto_should_escalate(&st, 2, NOW + 40);

    printf("probe_scale: scale=%s\n", scale ? scale : "(unset)");
    printf("probe_scale: elapsed_fast=%s (raw=0x%x) uniform=%s (raw=0x%x)"
           " ring_stddev_ms=%.3f\n",
           (a & CARTO_ESC_TIME_FAST) ? "FIRES" : "quiet", a,
           (b & CARTO_ESC_TIMING_UNIFORM) ? "FIRES" : "quiet", b,
           carto_timing_stddev_ms(&st));
    return 0;
}
