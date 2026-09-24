/*
 * test_detect.c -- internal unit tests for the pure detection verdict.
 * Not shipped to solvers; built only by `make test`.
 */
#include <stdio.h>

#include "vm_debug.h"

static int fails;

#define CHECK(cond) do { \
        if (!(cond)) { printf("[FAIL] %s\n", #cond); fails++; } \
    } while (0)

int main(void)
{
    printf("== vm_debug timing-verdict unit tests ==\n");

    /* ordinary runs: trace is far faster than the calibration loop */
    CHECK(carto_timing_verdict(0.010, 0.0001) == 0);
    /* slow machine / valgrind: both loops scale together */
    CHECK(carto_timing_verdict(0.500, 0.5000) == 0);
    /* mildly slower trace, still under the margin */
    CHECK(carto_timing_verdict(0.010, 0.1900) == 0);
    /* single-stepped trace: orders of magnitude over the margin */
    CHECK(carto_timing_verdict(0.010, 0.2100) == 1);
    CHECK(carto_timing_verdict(0.010, 5.0000) == 1);
    /* unusable evidence never accuses */
    CHECK(carto_timing_verdict(0.0, 1.0) == 0);
    CHECK(carto_timing_verdict(0.010, 0.0) == 0);
    CHECK(carto_timing_verdict(-1.0, 5.0) == 0);

    printf("== 8 checks, %d failed ==\n", fails);
    if (fails == 0) {
        printf("ALL CHECKS PASSED\n");
        return 0;
    }
    printf("FAILURES PRESENT\n");
    return 1;
}