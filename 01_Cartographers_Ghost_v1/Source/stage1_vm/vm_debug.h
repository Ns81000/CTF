/*
 * vm_debug.h -- detection verdict helpers for Stage 1 (Phase 2).
 *
 * Split out of stage1_vm.c so the decision logic can be unit-tested by the
 * internal test build (test_detect.c) without embedding a test hook in the
 * shipped binary.
 */
#ifndef CARTO_VM_DEBUG_H
#define CARTO_VM_DEBUG_H

/*
 * Suspicious-slowdown ratio: a single-stepped trace is orders of magnitude
 * slower than the machine calibrated by the fixed baseline loop, while a
 * slow machine (or valgrind/qemu) slows both loops together and keeps the
 * ratio near 1. 20.0 is a deliberately generous margin: the clean ratio is
 * ~0.03, a stepped trace is ~100+. Phase 6 may calibrate this constant.
 */
#define CARTO_VM_DEBUG_RATIO_LIMIT 20.0

static inline int carto_timing_verdict(double base_sec, double vm_sec)
{
    if (base_sec <= 0.0 || vm_sec <= 0.0)
        return 0;                       /* no usable evidence */
    return (vm_sec / base_sec) > CARTO_VM_DEBUG_RATIO_LIMIT ? 1 : 0;
}

#endif /* CARTO_VM_DEBUG_H */