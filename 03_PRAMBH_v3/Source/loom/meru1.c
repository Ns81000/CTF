/*
 * MERU-1 CPU core - direct-threaded interpreter.
 * Semantics must match model_loom.py bit-exactly; the selftest ROM
 * exercises every opcode and both implementations must agree.
 */
#include "meru1.h"

#include <string.h>
#ifdef MERU1_TRACE
#include <stdio.h>
#endif

void meru1_init(meru1 *m)
{
    memset(m, 0, sizeof *m);
    m->sp = 0xFF;
    m->f = MERU1_F_FIXED;
    m->pc = MERU1_RESET_PC;
}

int meru1_load_rom(meru1 *m, const uint8_t *rom, uint32_t len)
{
    if (len == 0 || len > MERU1_ROM_MAX)
        return -1;
    memcpy(m->mem + MERU1_RESET_PC, rom, len);
    m->rom_end = MERU1_RESET_PC + (uint32_t)len;
    return 0;
}

static inline void wr(meru1 *m, uint16_t a, uint8_t v)
{
    m->mem[a] = v;
    if (a >= MERU1_MMIO && a < MERU1_MMIO + 0x100 && m->mmio_write)
        m->mmio_write(m, a, v);
}

void meru1_run(meru1 *m)
{
    static void *const dt[0x60] = {
        [0x00] = &&l_nop,  [0x01] = &&l_hlt,  [0x02] = &&l_lda_imm,
        [0x03] = &&l_lda_zp, [0x04] = &&l_lda_zpx, [0x05] = &&l_lda_abs,
        [0x06] = &&l_lda_absx, [0x07] = &&l_lda_absy, [0x08] = &&l_lda_indy,
        [0x09] = &&l_sta_zp, [0x0A] = &&l_sta_zpx, [0x0B] = &&l_sta_abs,
        [0x0C] = &&l_sta_absx, [0x0D] = &&l_sta_absy, [0x0E] = &&l_sta_indy,
        [0x0F] = &&l_ldx_imm, [0x10] = &&l_ldx_zp, [0x11] = &&l_ldx_abs,
        [0x12] = &&l_ldy_imm, [0x13] = &&l_ldy_zp, [0x14] = &&l_ldy_abs,
        [0x15] = &&l_stx_zp, [0x16] = &&l_stx_abs,
        [0x17] = &&l_sty_zp, [0x18] = &&l_sty_abs,
        [0x19] = &&l_tax, [0x1A] = &&l_txa, [0x1B] = &&l_tay,
        [0x1C] = &&l_tya, [0x1D] = &&l_tsx, [0x1E] = &&l_txs,
        [0x1F] = &&l_adc_imm, [0x20] = &&l_adc_zp, [0x21] = &&l_adc_abs,
        [0x22] = &&l_sbc_imm, [0x23] = &&l_sbc_zp, [0x24] = &&l_sbc_abs,
        [0x25] = &&l_and_imm, [0x26] = &&l_and_zp, [0x27] = &&l_and_abs,
        [0x28] = &&l_ora_imm, [0x29] = &&l_ora_zp, [0x2A] = &&l_ora_abs,
        [0x2B] = &&l_eor_imm, [0x2C] = &&l_eor_zp, [0x2D] = &&l_eor_abs,
        [0x2E] = &&l_asl, [0x2F] = &&l_lsr, [0x30] = &&l_rol,
        [0x31] = &&l_ror,
        [0x32] = &&l_cmp_imm, [0x33] = &&l_cmp_zp, [0x34] = &&l_cmp_abs,
        [0x35] = &&l_cpx, [0x36] = &&l_cpy,
        [0x37] = &&l_inc_zp, [0x38] = &&l_inc_abs,
        [0x39] = &&l_dec_zp, [0x3A] = &&l_dec_abs,
        [0x3B] = &&l_inx, [0x3C] = &&l_iny, [0x3D] = &&l_dex,
        [0x3E] = &&l_dey,
        [0x3F] = &&l_bra, [0x40] = &&l_bne, [0x41] = &&l_beq,
        [0x42] = &&l_bcc, [0x43] = &&l_bcs, [0x44] = &&l_bmi,
        [0x45] = &&l_bpl, [0x46] = &&l_bvc, [0x47] = &&l_bvs,
        [0x48] = &&l_jmp, [0x49] = &&l_jsr, [0x4A] = &&l_rts,
        [0x4B] = &&l_jmpi,
        [0x4C] = &&l_pha, [0x4D] = &&l_pla, [0x4E] = &&l_php,
        [0x4F] = &&l_plp, [0x50] = &&l_clc, [0x51] = &&l_sec,
        [0x52] = &&l_clv, [0x53] = &&l_skp,
        [0x54] = &&l_ldhl_i, [0x55] = &&l_ldde_i, [0x56] = &&l_ldbc_i,
        [0x57] = &&l_ldir, [0x58] = &&l_ldhl_a, [0x59] = &&l_sthl_a,
        [0x5A] = &&l_addhl, [0x5B] = &&l_xcrc, [0x5C] = &&l_mul8,
        [0x5D] = &&l_swp, [0x5E] = &&l_cma, [0x5F] = &&l_xch,
    };
    register uint16_t pc = m->pc;
    register uint8_t a = m->a, x = m->x, y = m->y, sp = m->sp, f = m->f;
    register uint8_t h = m->h, l = m->l, d = m->d, e = m->e;
    register uint8_t b = m->b, c = m->c;
    uint8_t t8;
    uint16_t t16, u16;
    uint32_t t32;
    uint32_t runaway = 0;

#define MEM(i)      (m->mem[(uint16_t)(i)])
#define FETCH()     MEM(pc++)
#define FETCH16()   (t16 = MEM(pc) | (MEM(pc + 1) << 8), pc += 2, t16)
#define SZN(v)      ({ uint8_t _v = (uint8_t)(v);                          \
                        f &= ~(MERU1_F_Z | MERU1_F_N);                     \
                        if (!_v)       f |= MERU1_F_Z;                     \
                        if (_v & 0x80) f |= MERU1_F_N;                     \
                        _v; })
#define PUSH(v)     (MEM(0x100 + sp) = (v), sp--)
#define PULL()      MEM(0x100 + (++sp))
#ifdef MERU1_TRACE
#define NEXT()      do { if (m->halted) goto done;                      \
                         m->cycles++;                                   \
                         t8 = FETCH();                                  \
                         if (t8 >= 0x60                                  \
                             || (m->cycles < 40 &&                       \
                                 fprintf(stderr,                         \
                                     "PC=%04X OP=%02X a=%02X x=%02X "   \
                                     "y=%02X f=%02X hl=%02X%02X "       \
                                     "bc=%02X%02X\n",                   \
                                     (uint16_t)(pc - 1), t8,            \
                                     a, x, y, f, h, l, b, c), 0)) {     \
                             fprintf(stderr, "BADOP $%02X at $%04X\n",  \
                                     t8, (uint16_t)(pc - 1));           \
                             goto done;                                 \
                         }                                              \
                         goto *dt[t8]; } while (0)
#else
#define NEXT()      do { if (m->halted) goto done;                      \
                         m->cycles++;                                   \
                         t8 = FETCH();                                  \
                         if (t8 >= 0x60) goto done;                     \
                         if (t8 == 0x00) { if (++runaway > 4096)         \
                                               goto done; }              \
                         else runaway = 0;                               \
                         if ((uint16_t)(pc - 1) < MERU1_RESET_PC         \
                             || (uint16_t)(pc - 1) >= m->rom_end)        \
                             goto done;                                  \
                         goto *dt[t8]; } while (0)
#endif
#define BRANCH(cond) do { int8_t off = (int8_t)FETCH();                 \
                          if (cond) pc = (uint16_t)(pc + off);          \
                          NEXT(); } while (0)

    NEXT();

l_nop: NEXT();
l_hlt: goto done;

l_lda_imm:  a = SZN(FETCH()); NEXT();
l_lda_zp:   a = SZN(MEM(FETCH())); NEXT();
l_lda_zpx:  a = SZN(MEM((uint8_t)(FETCH() + x))); NEXT();
l_lda_abs:  a = SZN(MEM(FETCH16())); NEXT();
l_lda_absx: a = SZN(MEM((uint16_t)(FETCH16() + x))); NEXT();
l_lda_absy: a = SZN(MEM((uint16_t)(FETCH16() + y))); NEXT();
l_lda_indy: t8 = FETCH();
            t16 = MEM(t8) | (MEM((uint8_t)(t8 + 1)) << 8);
            a = SZN(MEM((uint16_t)(t16 + y))); NEXT();

l_sta_zp:   wr(m, FETCH(), a); NEXT();
l_sta_zpx:  wr(m, (uint8_t)(FETCH() + x), a); NEXT();
l_sta_abs:  wr(m, FETCH16(), a); NEXT();
l_sta_absx: wr(m, (uint16_t)(FETCH16() + x), a); NEXT();
l_sta_absy: wr(m, (uint16_t)(FETCH16() + y), a); NEXT();
l_sta_indy: t8 = FETCH();
            t16 = MEM(t8) | (MEM((uint8_t)(t8 + 1)) << 8);
            wr(m, (uint16_t)(t16 + y), a); NEXT();

l_ldx_imm:  x = SZN(FETCH()); NEXT();
l_ldx_zp:   x = SZN(MEM(FETCH())); NEXT();
l_ldx_abs:  x = SZN(MEM(FETCH16())); NEXT();
l_ldy_imm:  y = SZN(FETCH()); NEXT();
l_ldy_zp:   y = SZN(MEM(FETCH())); NEXT();
l_ldy_abs:  y = SZN(MEM(FETCH16())); NEXT();
l_stx_zp:   wr(m, FETCH(), x); NEXT();
l_stx_abs:  wr(m, FETCH16(), x); NEXT();
l_sty_zp:   wr(m, FETCH(), y); NEXT();
l_sty_abs:  wr(m, FETCH16(), y); NEXT();

l_tax: x = SZN(a); NEXT();
l_txa: a = SZN(x); NEXT();
l_tay: y = SZN(a); NEXT();
l_tya: a = SZN(y); NEXT();
l_tsx: x = SZN(sp); NEXT();
l_txs: sp = x; NEXT();

l_adc_imm: t8 = FETCH(); goto adc_common;
l_adc_zp:  t8 = MEM(FETCH()); goto adc_common;
l_adc_abs: t8 = MEM(FETCH16()); goto adc_common;
adc_common:
    t32 = a + t8 + ((f & MERU1_F_C) ? 1 : 0);
    f &= ~(MERU1_F_C | MERU1_F_V | MERU1_F_Z | MERU1_F_N);
    if (~(a ^ t8) & (a ^ t32) & 0x80) f |= MERU1_F_V;
    if (t32 > 0xFF) f |= MERU1_F_C;
    a = SZN((uint8_t)t32); NEXT();

l_sbc_imm: t8 = FETCH(); goto sbc_common;
l_sbc_zp:  t8 = MEM(FETCH()); goto sbc_common;
l_sbc_abs: t8 = MEM(FETCH16()); goto sbc_common;
sbc_common:
    t32 = (int)a - t8 - ((f & MERU1_F_C) ? 0 : 1);
    f &= ~(MERU1_F_C | MERU1_F_V | MERU1_F_Z | MERU1_F_N);
    if ((a ^ t8) & (a ^ t32) & 0x80) f |= MERU1_F_V;
    if (!(t32 & 0x100)) f |= MERU1_F_C;
    a = SZN((uint8_t)t32); NEXT();


l_and_imm: a = SZN(a & FETCH()); NEXT();
l_and_zp:  a = SZN(a & MEM(FETCH())); NEXT();
l_and_abs: a = SZN(a & MEM(FETCH16())); NEXT();
l_ora_imm: a = SZN(a | FETCH()); NEXT();
l_ora_zp:  a = SZN(a | MEM(FETCH())); NEXT();
l_ora_abs: a = SZN(a | MEM(FETCH16())); NEXT();
l_eor_imm: a = SZN(a ^ FETCH()); NEXT();
l_eor_zp:  a = SZN(a ^ MEM(FETCH())); NEXT();
l_eor_abs: a = SZN(a ^ MEM(FETCH16())); NEXT();

l_asl: t8 = (a >> 7) & 1; a = SZN((uint8_t)(a << 1));
       f = (f & ~MERU1_F_C) | t8; NEXT();
l_lsr: t8 = a & 1; a = SZN(a >> 1);
       f = (f & ~MERU1_F_C) | t8; NEXT();
l_rol: t8 = (a >> 7) & 1;
       a = SZN((uint8_t)((a << 1) | ((f & MERU1_F_C) ? 1 : 0)));
       f = (f & ~MERU1_F_C) | t8; NEXT();
l_ror: t8 = a & 1;
       a = SZN((a >> 1) | ((f & MERU1_F_C) ? 0x80 : 0));
       f = (f & ~MERU1_F_C) | t8; NEXT();

l_cmp_imm: t8 = FETCH(); goto cmp_common;
l_cmp_zp:  t8 = MEM(FETCH()); goto cmp_common;
l_cmp_abs: t8 = MEM(FETCH16()); goto cmp_common;
cmp_common:
    t32 = (uint32_t)a - t8;
    f &= ~(MERU1_F_C | MERU1_F_Z | MERU1_F_N);
    if (a >= t8) f |= MERU1_F_C;
    SZN((uint8_t)t32); NEXT();
l_cpx: t32 = (uint32_t)x - (t8 = FETCH());
       f &= ~(MERU1_F_C | MERU1_F_Z | MERU1_F_N);
       if (x >= t8) f |= MERU1_F_C;
       SZN((uint8_t)t32); NEXT();
l_cpy: t32 = (uint32_t)y - (t8 = FETCH());
       f &= ~(MERU1_F_C | MERU1_F_Z | MERU1_F_N);
       if (y >= t8) f |= MERU1_F_C;
       SZN((uint8_t)t32); NEXT();

l_inc_zp:  t8 = FETCH(); wr(m, t8, SZN((uint8_t)(MEM(t8) + 1))); NEXT();
l_inc_abs: t16 = FETCH16();
           wr(m, t16, SZN((uint8_t)(MEM(t16) + 1))); NEXT();
l_dec_zp:  t8 = FETCH(); wr(m, t8, SZN((uint8_t)(MEM(t8) - 1))); NEXT();
l_dec_abs: t16 = FETCH16();
           wr(m, t16, SZN((uint8_t)(MEM(t16) - 1))); NEXT();
l_inx: x = SZN((uint8_t)(x + 1)); NEXT();
l_iny: y = SZN((uint8_t)(y + 1)); NEXT();
l_dex: x = SZN((uint8_t)(x - 1)); NEXT();
l_dey: y = SZN((uint8_t)(y - 1)); NEXT();

l_bra: BRANCH(1);
l_bne: BRANCH(!(f & MERU1_F_Z));
l_beq: BRANCH(f & MERU1_F_Z);
l_bcc: BRANCH(!(f & MERU1_F_C));
l_bcs: BRANCH(f & MERU1_F_C);
l_bmi: BRANCH(f & MERU1_F_N);
l_bpl: BRANCH(!(f & MERU1_F_N));
l_bvc: BRANCH(!(f & MERU1_F_V));
l_bvs: BRANCH(f & MERU1_F_V);

l_jmp:  pc = FETCH16(); NEXT();
l_jsr:  t16 = FETCH16();
        t16++; pc--; PUSH((uint8_t)(pc >> 8)); PUSH((uint8_t)pc);
        pc = (uint16_t)(t16 - 1); NEXT();
l_rts:  t8 = PULL(); t16 = PULL();
        pc = (uint16_t)((t16 << 8 | t8) + 1); NEXT();
l_jmpi: t16 = FETCH16();
        pc = MEM(t16) | (MEM((uint16_t)(t16 + 1)) << 8); NEXT();


l_pha: PUSH(a); NEXT();
l_pla: a = SZN(PULL()); NEXT();
l_php: PUSH(f | MERU1_F_FIXED); NEXT();
l_plp: f = PULL() | MERU1_F_FIXED; NEXT();
l_clc: f &= ~MERU1_F_C; NEXT();
l_sec: f |= MERU1_F_C; NEXT();
l_clv: f &= ~MERU1_F_V; NEXT();
l_skp: (void)FETCH(); NEXT();

l_ldhl_i: t16 = FETCH16(); h = (uint8_t)(t16 >> 8); l = (uint8_t)t16;
          NEXT();
l_ldde_i: t16 = FETCH16(); d = (uint8_t)(t16 >> 8); e = (uint8_t)t16;
          NEXT();
l_ldbc_i: t16 = FETCH16(); b = (uint8_t)(t16 >> 8); c = (uint8_t)t16;
          NEXT();
l_ldir:
    t16 = (uint16_t)((h << 8) | l);
    u16 = (uint16_t)((d << 8) | e);
    t32 = (uint32_t)((b << 8) | c);
    while (t32--) {
        wr(m, u16, MEM(t16));
        t16++; u16++;
    }
    h = (uint8_t)(t16 >> 8); l = (uint8_t)t16;
    d = (uint8_t)(u16 >> 8); e = (uint8_t)u16;
    b = 0; c = 0;
    NEXT();
l_ldhl_a: t16 = FETCH16();
          l = MEM(t16); h = MEM((uint16_t)(t16 + 1)); NEXT();
l_sthl_a: t16 = FETCH16();
          wr(m, t16, l); wr(m, (uint16_t)(t16 + 1), h); NEXT();
l_addhl:
    t32 = (uint32_t)((h << 8) | l) + a;
    f &= ~(MERU1_F_C | MERU1_F_Z | MERU1_F_N);
    if (t32 > 0xFFFF) f |= MERU1_F_C;
    h = (uint8_t)(t32 >> 8); l = (uint8_t)t32;
    if ((t32 & 0xFFFF) == 0) f |= MERU1_F_Z;
    if (t32 & 0x8000) f |= MERU1_F_N;
    NEXT();
l_xcrc:
    t16 = (uint16_t)((h << 8) | l);
    t32 = (uint32_t)((b << 8) | c);
    t8 = a;
    while (t32--)
        t8 ^= MEM(t16++);
    h = (uint8_t)(t16 >> 8); l = (uint8_t)t16;
    b = 0; c = 0;
    a = SZN(t8);
    NEXT();
l_mul8: t32 = (uint32_t)a * x;
        a = SZN((uint8_t)t32); y = (uint8_t)(t32 >> 8); NEXT();
l_swp:  a = SZN((uint8_t)((a << 4) | (a >> 4))); NEXT();
l_cma:  a = SZN((uint8_t)(a ^ 0xFF)); NEXT();
l_xch:  t8 = a; a = x; x = t8; NEXT();

done:
    m->pc = pc; m->a = a; m->x = x; m->y = y; m->sp = sp; m->f = f;
    m->h = h; m->l = l; m->d = d; m->e = e; m->b = b; m->c = c;
}

