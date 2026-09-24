#ifndef PRAMBH_STATE_H
#define PRAMBH_STATE_H

#include <stddef.h>
#include <stdint.h>

/*
 * prambh state file law (spec 4.9):
 *  - one file, <package_root>/prambh.survey, fixed size 512 bytes
 *  - the ONLY file any player tool ever writes
 *  - HMAC-SHA256 over bytes [0,480) with a device-bound key:
 *      key = SHA-256("prambh:state:key:v1" || machine_id || root_realpath)
 *    machine_id from /etc/machine-id (fallbacks: dbus machine-id, hostname)
 *  - any tamper / truncation / downgrade / foreign state -> SILENT reset
 *  - monotonic counter, stage bits, poison flags, pacing timestamps
 */

#define PRAMBH_STATE_SIZE 512
#define PRAMBH_STATE_NAME "prambh.survey"
#define PRAMBH_STATE_VERSION 3u

/* stage bits (LE64 at ST_OFF_STAGE) */
#define PRAMBH_BIT_LOOM_DONE       0x1ull
#define PRAMBH_BIT_DOORS_REAL      0x2ull
#define PRAMBH_BIT_CHAIN2_DONE     0x4ull
#define PRAMBH_BIT_TITLE_ASSEMBLED 0x8ull

/* poison flags (LE64 at ST_OFF_POISON) */
#define PRAMBH_POISON_DEBUGGER     0x1ull

/* field offsets */
enum {
    ST_OFF_MAGIC = 0,          /* 8  "PRMBHSV1" */
    ST_OFF_VERSION = 8,        /* 4  LE32 */
    ST_OFF_FIRST_RUN = 12,     /* 8  LE64 wall ms of first creation */
    ST_OFF_COUNTER = 20,       /* 8  LE64 monotonic write counter */
    ST_OFF_STAGE = 28,         /* 8  LE64 stage bits */
    ST_OFF_POISON = 36,        /* 8  LE64 poison flags */
    ST_OFF_VAL_WALL = 44,      /* 8  LE64 ms, last validate attempt (wall) */
    ST_OFF_VAL_MONO = 52,      /* 8  LE64 ms, last validate attempt (mono) */
    ST_OFF_LOOM_OUT = 60,      /* 32 chain #1 output (K_loom) */
    ST_OFF_CHAIN2_SEED = 92,   /* 32 chain #2 seed from the real chamber */
    ST_OFF_DOOR_INK = 124,     /* 16 door ink raw bytes (8 used) */
    ST_OFF_CHAIN2_OUT = 140,   /* 32 chain #2 output (K_eyes) */
    ST_OFF_RESERVED = 172,     /* zero-filled up to 480 */
    ST_OFF_HMAC = 480          /* 32 */
};

typedef struct {
    uint8_t bytes[PRAMBH_STATE_SIZE];
} prambh_state;

/* wall (CLOCK_REALTIME) and monotonic (CLOCK_MONOTONIC) time in ms. */
void prambh_now_ms(uint64_t *wall_ms, uint64_t *mono_ms);

/* package root = dirname(dirname(/proc/self/exe)); 0 on success. */
int prambh_package_root(char *out, size_t outlen);

/* device-bound HMAC key for a given package root. */
void prambh_device_key(const char *root, uint8_t out[32]);

void prambh_state_init_fresh(prambh_state *st);

/*
 * Load state for root.  Returns 1 if a valid existing state was loaded,
 * 0 if the state was (silently) fresh-initialised for ANY reason
 * (missing, short, long, bad magic, bad version, bad HMAC).
 */
int prambh_state_load(const char *root, prambh_state *st);

/* counter++, re-seal, write under flock(LOCK_EX).  0 on success. */
int prambh_state_save(const char *root, prambh_state *st);

/* LE64 field helpers */
uint64_t prambh_state_get64(const prambh_state *st, size_t off);
void prambh_state_set64(prambh_state *st, size_t off, uint64_t v);

/*
 * Pacing gate (pure function, unit-tested without faketime):
 * an attempt is allowed iff this is the first attempt (last_wall == 0)
 * or BOTH clocks advanced at least pace_ms and neither went backwards.
 */
int prambh_pacing_allow(uint64_t now_wall, uint64_t now_mono,
                        uint64_t last_wall, uint64_t last_mono,
                        uint64_t pace_ms);

#endif
