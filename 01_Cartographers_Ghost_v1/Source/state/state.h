#ifndef CARTO_STATE_H
#define CARTO_STATE_H

#include <stdint.h>

/* Stage indices used across all cartographer binaries. */
#define CARTO_STAGE0 0
#define CARTO_STAGE1 1
#define CARTO_STAGE2 2
#define CARTO_STAGE3 3
#define CARTO_STAGE4 4
#define CARTO_NUM_STAGES 5

/* On-disk interaction ring: last N interaction timestamps (ms since epoch). */
#define CARTO_RING_SIZE 32

/* Exact on-disk size of .cartographer_state (352 = 0x160 bytes). */
#define CARTO_STATE_FILE_SIZE 352

/* carto_state_load() result codes. */
#define CARTO_LOAD_OK       0  /* existing valid state loaded                     */
#define CARTO_LOAD_CREATED  1  /* no state file: fresh defaults created + saved   */
#define CARTO_LOAD_TAMPERED 2  /* corrupt/bad HMAC: silent reset to fresh + saved */

/* Reason bitmask returned by carto_should_escalate(). */
#define CARTO_ESC_TIME_FAST      0x1u
#define CARTO_ESC_TIMING_UNIFORM 0x2u
#define CARTO_ESC_DEBUGGER       0x4u

typedef struct {
    uint64_t first_run_ms;                     /* ms since epoch, first Stage 0 run */
    uint32_t attempt_count[CARTO_NUM_STAGES];  /* per-stage run/attempt counter     */
    uint32_t decoy_mask[CARTO_NUM_STAGES];     /* bit N set = decoy N submitted     */
    uint64_t ring_ts[CARTO_RING_SIZE];         /* interaction timestamps, ms        */
    uint16_t ring_count;                       /* entries currently in ring (<=32)  */
    uint16_t ring_head;                        /* next write index                  */
    uint8_t  debugger_detected;                /* set by Stage 1 anti-debug         */
} carto_state_t;

/* ---- lifecycle ---------------------------------------------------------- */

int carto_state_load(const char *path, carto_state_t *st, uint64_t now_ms);
int carto_state_save(const char *path, const carto_state_t *st);

/* ---- mutators ----------------------------------------------------------- */
void carto_bump_attempt(carto_state_t *st, int stage);
void carto_mark_decoy(carto_state_t *st, int stage, uint32_t decoy_bit);
void carto_record_interaction(carto_state_t *st, uint64_t now_ms);
void carto_set_debugger_detected(carto_state_t *st, int v);

/* ---- queries ------------------------------------------------------------ */
int      carto_decoy_submitted(const carto_state_t *st, int stage, uint32_t decoy_bit);
int      carto_get_debugger_detected(const carto_state_t *st);
uint64_t carto_time_since_first_run_ms(const carto_state_t *st, uint64_t now_ms);
double   carto_timing_stddev_ms(const carto_state_t *st);
unsigned carto_should_escalate(const carto_state_t *st, int stage, uint64_t now_ms);

/* Returns branch id (>=1) if submitted_flag is a registered decoy for stage,
 * else -1. Exact string match. */
int carto_lookup_decoy(int stage, const char *submitted_flag);

/* Wall-clock helper: ms since epoch. */
uint64_t carto_now_ms(void);

/* ---- self-tests (known-answer vectors; used by the test harness) -------- */
int carto_sha_selftest(void);
int carto_hmac_selftest(void);
int carto_key_selftest(void);

/*
 * On-disk format (little-endian, fixed offsets), total 0x160 = 352 bytes:
 *   0x000  magic "CART"
 *   0x004  format_version u8 = 1
 *   0x005  flags u8 = 0
 *   0x006  reserved u16 = 0
 *   0x008  first_run_ms    u64
 *   0x010  attempt_count[5] u32
 *   0x024  decoy_mask[5]    u32
 *   0x038  ring_count u16
 *   0x03A  ring_head  u16
 *   0x03C  debugger_detected u8, reserved u8[3]
 *   0x040  ring_ts[32] u64
 *   0x140  HMAC-SHA256(key, bytes[0x000..0x140))
 *   0x160  END
 * The HMAC key is never stored in plaintext: two independently masked copies
 * of the canonical key live in state_core.c; the mask is re-derived at runtime
 * into stack buffers only.
 */
#endif /* CARTO_STATE_H */
