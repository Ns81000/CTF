#ifndef CARTO_STATE_H
#define CARTO_STATE_H

#include <stdint.h>

/* Stage slots used across every cartographer binary. */
#define CARTO_STAGE_LEDGER  0
#define CARTO_STAGE_ENGINE  1
#define CARTO_STAGE_SHEET   2
#define CARTO_STAGE_ORACLE  3
#define CARTO_STAGE_SEAL    4
#define CARTO_STAGE_TITLE   5
#define CARTO_NUM_STAGES    6

/* Ring: the last CARTO_RING_SIZE interactions, 16 bytes each. */
#define CARTO_RING_SIZE 64

/* Exact on-disk size of .cartographer_state (1168 = 0x490). */
#define CARTO_STATE_FILE_SIZE 1168

/* carto_state_load() results. */
#define CARTO_LOAD_OK       0
#define CARTO_LOAD_CREATED  1
#define CARTO_LOAD_TAMPERED 2

/* The state file always lives directly beside the package root. */
#define CARTO_STATE_NAME ".cartographer_state"

/* Ring entry field offsets (16-byte record). */
#define CARTO_RING_OFF_TS     0   /* u64 ms since epoch      */
#define CARTO_RING_OFF_STAGE  8   /* u8                      */
#define CARTO_RING_OFF_OP     9   /* u8                      */
#define CARTO_RING_OFF_DT     10  /* u16 ms since prev entry */
#define CARTO_RING_OFF_AUX    12  /* u32                     */
#define CARTO_RING_ENTRY_SIZE 16

typedef struct {
    uint64_t first_run_ms;
    uint32_t attempt_count[CARTO_NUM_STAGES];
    uint32_t wrong_flag_mask[CARTO_NUM_STAGES];
    uint32_t gate_state[CARTO_NUM_STAGES];
    uint16_t ring_count;        /* cumulative appends, saturating at 0xFFFF  */
    uint16_t ring_head;         /* next slot to write (0..63)                */
    uint8_t  debugger_flag;     /* set by the engine's anti-debug            */
    uint32_t distinct_figures;  /* saturating distinct-figure counter        */
    uint8_t  ring[CARTO_RING_SIZE][CARTO_RING_ENTRY_SIZE];
    uint8_t  chain[16];         /* rolling chain over the record             */
} carto_state_t;

/* ---- lifecycle --------------------------------------------------------- */

/* Resolves ROOT + "/.cartographer_state".  Any load failure (missing,
 * wrong size, bad magic/version/flags, bad HMAC, out-of-bounds counters)
 * yields a silent fresh-state reset, never a diagnostic. */
int carto_state_load(const char *root, carto_state_t *st, uint64_t now_ms);
int carto_state_save(const char *root, const carto_state_t *st);

/* ---- mutators ---------------------------------------------------------- */
void carto_bump_attempt(carto_state_t *st, int stage);
void carto_mark_wrong_flag(carto_state_t *st, int stage, uint32_t branch_bit);
void carto_ring_append(carto_state_t *st, uint64_t ts_ms, int stage, int op,
                       uint32_t aux);
void carto_set_debugger_flag(carto_state_t *st, int v);
void carto_note_figure(carto_state_t *st, uint16_t fingerprint);

/* ---- queries ----------------------------------------------------------- */
int      carto_wrong_flag_seen(const carto_state_t *st, int stage, uint32_t bit);
int      carto_get_debugger_flag(const carto_state_t *st);
uint64_t carto_time_since_first_run_ms(const carto_state_t *st, uint64_t now_ms);
uint32_t carto_state_chain_digest32(const carto_state_t *st);
uint32_t carto_gate_tag(const carto_state_t *st, int stage);
const uint8_t *carto_ring_entry(const carto_state_t *st, int i);
uint64_t carto_now_ms(void);

/* Unmask the canonical master into a 32-byte stack buffer (never stored
 * plaintext anywhere in any binary). */
void carto_unmask_master(uint8_t out[32]);

/* K_state = SHA256(master || "ghost2:state"): the one key every tool must
 * share so a single state record is readable by all of them. */
void carto_state_key(uint8_t out[32]);

/* K_stage_i = SHA256(master || "ghost2:stage:i").  Exposed so unit tests can
 * prove the derivation; binaries keep their own masked blobs. */
void carto_derive_stage_key(int stage, uint8_t out[32]);

/* Generic reversal of a 32-byte masked blob under a named mask seed. */
void carto_unmask_blob(const uint8_t masked[32], const char *mask_seed,
                       uint8_t out[32]);

/* ---- self-tests -------------------------------------------------------- */
int carto_sha_selftest(void);
int carto_hmac_selftest(void);
int carto_key_selftest(void);

/* On-disk layout (little-endian, 1168 = 0x490 bytes):
 *   0x000  magic "CGV2"
 *   0x004  version u16 = 2
 *   0x006  flags   u16 = 0
 *   0x008  first_run_ms u64
 *   0x010  attempt_count[6]   u32
 *   0x028  wrong_flag_mask[6] u32
 *   0x040  gate_state[6]      u32
 *   0x058  ring_count u16 | ring_head u16 | debugger_flag u8
 *   0x05D  distinct-figure counter u32 (uses the four reserved bytes)
 *   0x060  ring[64] of 16-byte records
 *   0x460  chain[16]
 *   0x470  HMAC-SHA256(K_state, bytes[0x000..0x470))
 *   0x490  END
 */
#endif /* CARTO_STATE_H */
