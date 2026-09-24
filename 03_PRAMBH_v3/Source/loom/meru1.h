#ifndef PRAMBH_MERU1_H
#define PRAMBH_MERU1_H

#include <stdint.h>

/*
 * MERU-1 survey loom CPU core (spec 4.4). 8-bit accumulator machine,
 * 96 documented opcodes (see field-notes/meru1_datasheet.txt), 64 KiB
 * address space. ROM loads at $8000 (max $7000 bytes). The $F000 page
 * is memory-mapped I/O served by the host (stitch engine, extended
 * stitch table banks, teleprinter).
 */

#define MERU1_RESET_PC 0x8000u
#define MERU1_ROM_MAX  0x7000u
#define MERU1_MMIO     0xF000u

#define MERU1_F_C 0x01
#define MERU1_F_Z 0x02
#define MERU1_F_V 0x40
#define MERU1_F_N 0x80
#define MERU1_F_FIXED 0x30

typedef struct meru1 meru1;
struct meru1 {
    uint8_t mem[65536];
    uint8_t a, x, y, sp, f;
    uint8_t h, l, d, e, b, c;
    uint16_t pc;
    uint32_t rom_end;   /* one past the last cartridge byte */
    int halted;
    uint64_t cycles;
    void *host;
    void (*mmio_write)(meru1 *m, uint16_t addr, uint8_t val);
};

void meru1_init(meru1 *m);
int  meru1_load_rom(meru1 *m, const uint8_t *rom, uint32_t len);
void meru1_run(meru1 *m);          /* until HLT / EXIT */

#endif
