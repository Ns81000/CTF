#!/usr/bin/env python3
"""MERU-8 selftest cartridge generator (organizer-side; never ships).

Exercises all 96 opcodes plus the SHA mixer and extended-table MMIO.
Every opcode leaves a result byte at $0400+op and a flags byte at
$0440+op; the cartridge prints both buffers, the mixer digest, the
chain S0 window and one fetched table block as hex.  The suite runs
the ROM under loom (C) and model_loom.py (Python) and diffs the
output byte-exactly.

usage: selftest.py <out.rom>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from asm import assemble  # noqa: E402

HDR = """; MERU-8 selftest cartridge (organizer-side parity harness)
        .org $8000

        .equ PTR,     $20
        .equ SCRATCH, $00
        .equ E1,      $04C0
        .equ E2,      $04C1
        .equ E3,      $04C2
        .equ SHABUF,  $0580
        .equ S0BUF,   $05A0
        .equ XWBUF,   $05C0
"""


def equs():
    out = []
    for i in range(0x60):
        out.append("        .equ R%02X, $%04X" % (i, 0x0400 + i))
        out.append("        .equ F%02X, $%04X" % (i, 0x0460 + i))
    return "\n".join(out) + "\n"


def rec(op):
    """Record A -> R<op>, then flags -> F<op>.  Clobbers flags."""
    return ("        sta R%02X\n        php\n        pla\n"
            "        sta F%02X\n" % (op, op))


def recf_only(op):
    """Record only the current flags into F<op>; A untouched."""
    return "        php\n        pla\n        sta F%02X\n" % op


def btaken(op, mnem, setup):
    """R<op> = 1 iff the branch is taken."""
    t, d = "_tk%02X" % op, "_dn%02X" % op
    return ("        lda #$00\n        sta R%02X\n" % op
            + setup
            + "        %s %s\n" % (mnem.lower(), t)
            + "        bra %s\n" % d
            + "%s:  lda #$01\n        sta R%02X\n" % (t, op)
            + "%s:\n" % d)


TESTS = []
A = TESTS.append

A("; --- 0x00 NOP\n        lda #$A5\n        nop\n" + rec(0x00))
A("; --- 0x02 LDA imm\n        lda #$00\n" + rec(0x02))
A("; --- 0x03 LDA zp\n        lda #$5A\n        sta $10\n"
  "        lda #$01\n        lda $10\n" + rec(0x03))
A("; --- 0x04 LDA zpx\n        lda #$66\n        sta $12\n"
  "        ldx #$02\n        lda <$10,x\n" + rec(0x04))
A("; --- 0x05 LDA abs\n        lda #$77\n        sta $0300\n"
  "        lda #$01\n        lda $0300\n" + rec(0x05))
A("; --- 0x06 LDA absx\n        lda #$88\n        sta $0303\n"
  "        ldx #$03\n        lda $0300,x\n" + rec(0x06))
A("; --- 0x07 LDA absy\n        lda #$99\n        sta $0304\n"
  "        ldy #$04\n        lda $0300,y\n" + rec(0x07))
A("; --- 0x08 LDA indy\n        lda #$AA\n        sta $0305\n"
  "        lda #$05\n        sta PTR\n        lda #$03\n        sta $21\n"
  "        ldy #$00\n        lda (PTR),y\n" + rec(0x08))
A("; --- 0x09 STA zp\n        lda #$11\n        sta $30\n"
  "        lda #$00\n        lda $30\n" + rec(0x09))
A("; --- 0x0A STA zpx\n        ldx #$01\n        lda #$22\n        sta $30,x\n"
  "        lda $31\n" + rec(0x0A))
A("; --- 0x0B STA abs\n        lda #$33\n        sta $0380\n"
  "        lda $0380\n" + rec(0x0B))
A("; --- 0x0C STA absx\n        ldx #$02\n        lda #$44\n        sta $0380,x\n"
  "        lda $0382\n" + rec(0x0C))
A("; --- 0x0D STA absy\n        ldy #$03\n        lda #$55\n        sta $0380,y\n"
  "        lda $0383\n" + rec(0x0D))
A("; --- 0x0E STA indy\n        lda #$66\n        sta $0392\n"
  "        lda #$90\n        sta PTR\n        lda #$03\n        sta $21\n"
  "        ldy #$02\n        lda #$77\n        sta (PTR),y\n"
  "        lda $0392\n" + rec(0x0E))
A("; --- 0x0F LDX imm\n        ldx #$7E\n        txa\n" + rec(0x0F))
A("; --- 0x10 LDX zp\n        lda #$12\n        sta $40\n        ldx $40\n        txa\n"
  + rec(0x10))
A("; --- 0x11 LDX abs\n        lda #$34\n        sta $0340\n        ldx $0340\n"
  "        txa\n" + rec(0x11))
A("; --- 0x12 LDY imm\n        ldy #$56\n        tya\n" + rec(0x12))
A("; --- 0x13 LDY zp\n        lda #$78\n        sta $41\n        ldy $41\n        tya\n"
  + rec(0x13))
A("; --- 0x14 LDY abs\n        lda #$55\n        sta $0341\n        ldy $0341\n"
  "        tya\n" + rec(0x14))
A("; --- 0x15 STX zp\n        ldx #$66\n        stx $42\n        lda $42\n" + rec(0x15))
A("; --- 0x16 STX abs\n        ldx #$77\n        stx $0342\n        lda $0342\n"
  + rec(0x16))
A("; --- 0x17 STY zp\n        ldy #$11\n        sty $43\n        lda $43\n" + rec(0x17))
A("; --- 0x18 STY abs\n        ldy #$22\n        sty $0343\n        lda $0343\n"
  + rec(0x18))
A("; --- 0x19 TAX\n        lda #$42\n        tax\n        txa\n" + rec(0x19))
A("; --- 0x1A TXA\n        ldx #$24\n        txa\n" + rec(0x1A))
A("; --- 0x1B TAY\n        lda #$99\n        tay\n        tya\n" + rec(0x1B))
A("; --- 0x1C TYA\n        ldy #$66\n        tya\n" + rec(0x1C))
A("; --- 0x1D TSX (no jsr yet: SP=$FF)\n        tsx\n        txa\n" + rec(0x1D))
A("; --- 0x1E TXS (restore SP after)\n        ldx #$FE\n        txs\n        tsx\n"
  "        txa\n" + rec(0x1E) + "        ldx #$FF\n        txs\n")
A("; --- 0x1F ADC imm\n        clc\n        lda #$10\n        adc #$05\n" + rec(0x1F))
A("; --- 0x20 ADC zp\n        lda #$20\n        sta $50\n"
  "        sec\n        lda #$01\n        adc $50\n" + rec(0x20))
A("; --- 0x21 ADC abs\n        lda #$30\n        sta $0350\n"
  "        clc\n        lda #$F0\n        adc $0350\n" + rec(0x21))
A("; --- 0x22 SBC imm\n        sec\n        lda #$10\n        sbc #$01\n" + rec(0x22))
A("; --- 0x23 SBC zp\n        lda #$05\n        sta $51\n"
  "        sec\n        lda #$10\n        sbc $51\n" + rec(0x23))
A("; --- 0x24 SBC abs\n        lda #$01\n        sta $0351\n"
  "        clc\n        lda #$00\n        sbc $0351\n" + rec(0x24))
A("; --- 0x25 AND imm\n        lda #$F0\n        and #$3C\n" + rec(0x25))
A("; --- 0x26 AND zp\n        lda #$0F\n        sta $52\n"
  "        lda #$F0\n        and $52\n" + rec(0x26))
A("; --- 0x27 AND abs\n        lda #$FF\n        sta $0352\n"
  "        lda #$81\n        and $0352\n" + rec(0x27))
A("; --- 0x28 ORA imm\n        lda #$50\n        ora #$05\n" + rec(0x28))
A("; --- 0x29 ORA zp\n        lda #$01\n        sta $53\n"
  "        lda #$80\n        ora $53\n" + rec(0x29))
A("; --- 0x2A ORA abs\n        lda #$00\n        sta $0353\n"
  "        lda #$00\n        ora $0353\n" + rec(0x2A))
A("; --- 0x2B EOR imm\n        lda #$FF\n        eor #$0F\n" + rec(0x2B))
A("; --- 0x2C EOR zp\n        lda #$FF\n        sta $54\n"
  "        lda #$FF\n        eor $54\n" + rec(0x2C))
A("; --- 0x2D EOR abs\n        lda #$0F\n        sta $0354\n"
  "        lda #$F0\n        eor $0354\n" + rec(0x2D))
A("; --- 0x2E ASL\n        clc\n        lda #$81\n        asl\n" + rec(0x2E))
A("; --- 0x2F LSR\n        clc\n        lda #$03\n        lsr\n" + rec(0x2F))
A("; --- 0x30 ROL\n        sec\n        lda #$80\n        rol\n" + rec(0x30))
A("; --- 0x31 ROR\n        sec\n        lda #$01\n        ror\n" + rec(0x31))
A("; --- 0x32 CMP imm\n        lda #$10\n        cmp #$10\n" + rec(0x32))
A("; --- 0x33 CMP zp\n        lda #$20\n        sta $55\n"
  "        lda #$10\n        cmp $55\n" + rec(0x33))
A("; --- 0x34 CMP abs\n        lda #$05\n        sta $0355\n"
  "        lda #$10\n        cmp $0355\n" + rec(0x34))
A("; --- 0x35 CPX\n        ldx #$09\n        cpx #$09\n        txa\n" + rec(0x35))
A("; --- 0x36 CPY\n        ldy #$01\n        cpy #$02\n        tya\n" + rec(0x36))
A("; --- 0x37 INC zp\n        lda #$7F\n        sta $60\n        inc $60\n"
  + recf_only(0x37) + "        lda $60\n        sta R37\n")
A("; --- 0x38 INC abs\n        lda #$FF\n        sta $0360\n        inc $0360\n"
  + recf_only(0x38) + "        lda $0360\n        sta R38\n")
A("; --- 0x39 DEC zp\n        lda #$00\n        sta $61\n        dec $61\n"
  + recf_only(0x39) + "        lda $61\n        sta R39\n")
A("; --- 0x3A DEC abs\n        lda #$01\n        sta $0361\n        dec $0361\n"
  + recf_only(0x3A) + "        lda $0361\n        sta R3A\n")
A("; --- 0x3B INX\n        ldx #$7F\n        inx\n" + recf_only(0x3B)
  + "        txa\n        sta R3B\n")
A("; --- 0x3C INY\n        ldy #$FF\n        iny\n" + recf_only(0x3C)
  + "        tya\n        sta R3C\n")
A("; --- 0x3D DEX\n        ldx #$00\n        dex\n" + recf_only(0x3D)
  + "        txa\n        sta R3D\n")
A("; --- 0x3E DEY\n        ldy #$01\n        dey\n" + recf_only(0x3E)
  + "        tya\n        sta R3E\n")
A(btaken(0x3F, "bra", ""))
A(btaken(0x40, "bne", "        lda #$01\n"))
A(btaken(0x41, "beq", "        lda #$00\n"))
A(btaken(0x42, "bcc", "        clc\n"))
A(btaken(0x43, "bcs", "        sec\n"))
A(btaken(0x44, "bmi", "        lda #$80\n"))
A(btaken(0x45, "bpl", "        lda #$01\n"))
A(btaken(0x46, "bvc", "        clv\n"))
A(btaken(0x47, "bvs", "        clc\n        lda #$40\n        adc #$40\n"))
A("; --- not-taken gauntlet G1: beq/bcc/bmi/bvs must fall through\n"
  "        lda #$01\n        sta E1\n"
  "        sec\n        lda #$01\n        clv\n"
  "        beq _g1bad\n        bcc _g1bad\n        bmi _g1bad\n"
  "        bvs _g1bad\n        bra _g1ok\n"
  "_g1bad: lda #$00\n        sta E1\n_g1ok:\n")
A("; --- not-taken gauntlet G2: bne/bcs must fall through\n"
  "        lda #$01\n        sta E2\n"
  "        clc\n        lda #$00\n"
  "        bne _g2bad\n        bcs _g2bad\n        bra _g2ok\n"
  "_g2bad: lda #$00\n        sta E2\n_g2ok:\n")
A("; --- not-taken gauntlet G3: bpl/bvc must fall through\n"
  "        lda #$01\n        sta E3\n"
  "        clc\n        lda #$40\n        adc #$40\n"
  "        bpl _g3bad\n        bvc _g3bad\n        bra _g3ok\n"
  "_g3bad: lda #$00\n        sta E3\n_g3ok:\n")
A("; --- 0x48 JMP abs\n        lda #$00\n        sta R48\n"
  "        jmp _j48\n        bra _j48bad\n"
  "_j48: lda #$48\n        sta R48\n_j48bad:\n")
A("; --- 0x49 JSR / 0x4A RTS\n        jsr _sub49\n"
  "        lda #$4A\n        sta R4A\n        bra _d4a\n"
  "_sub49: lda #$49\n        sta R49\n        rts\n_d4a:\n")
A("; --- 0x4B JMP ind\n        lda #$00\n        sta R4B\n"
  "        jmp (ptr4b)\n        bra _j4bbad\n"
  "_j4b: lda #$4B\n        sta R4B\n_j4bbad:\n")
A("; --- 0x4C PHA / 0x4D PLA\n        lda #$5C\n        pha\n        lda #$00\n"
  "        pla\n" + rec(0x4C)
  + "        php\n        pla\n        sta R4D\n")
A("; --- 0x4E PHP / 0x4F PLP: flags round-trip\n"
  "        sec\n        lda #$80\n        php\n"
  "        clc\n        lda #$01\n        plp\n"
  "        php\n        pla\n        sta R4E\n")
A("; --- 0x50 CLC\n        sec\n        clc\n        php\n        pla\n"
  "        sta R50\n")
A("; --- 0x51 SEC\n        clc\n        sec\n        php\n        pla\n"
  "        sta R51\n")
A("; --- 0x52 CLV\n        clc\n        lda #$40\n        adc #$40\n        clv\n"
  "        php\n        pla\n        sta R52\n")
A("; --- 0x53 SKP (consumes one inert operand byte)\n"
  "        skp #$FF\n        lda #$42\n" + rec(0x53))
A("; --- 0x54 LDHL imm16\n        ldhl #$BEEF\n        sthl $70\n"
  "        lda $70\n        sta R54\n        lda $71\n        sta F54\n")
A("; --- 0x55 LDDE imm16 (via LDIR)\n        ldde #$0500\n"
  "        ldhl #pat55\n        ldbc #$0004\n        ldir\n"
  "        lda $0500\n" + rec(0x55))
A("; --- 0x56 LDBC imm16 (count of 2)\n        ldbc #$0002\n"
  "        ldde #$0504\n        ldhl #pat55\n        ldir\n"
  "        lda $0505\n" + rec(0x56))
A("; --- 0x57 LDIR block move\n        ldhl #pat57\n        ldde #$0508\n"
  "        ldbc #$0008\n        ldir\n        lda $050F\n" + rec(0x57))
A("; --- 0x58 LDHL abs (HL = (ptr58) = $0600), verify HL after LDIR\n"
  "        lda #$66\n        sta $0600\n"
  "        ldhl ptr58\n        ldde #$0510\n        ldbc #$0001\n        ldir\n"
  "        lda $0510\n        sta R58\n"
  "        sthl $74\n        lda $74\n        sta F58\n")
A("; --- 0x59 STHL abs\n        ldhl #$1234\n        sthl $76\n"
  "        lda $76\n        sta R59\n        lda $77\n        sta F59\n")
A("; --- 0x5A ADDHL\n        ldhl #$00FF\n        lda #$02\n        addhl\n"
  + recf_only(0x5A)
  + "        sthl $78\n        lda $78\n        sta R5A\n")
A("; --- 0x5B XCRC\n        ldhl #pat5b\n        ldbc #$0004\n        lda #$00\n"
  "        xcrc\n" + rec(0x5B))
A("; --- 0x5C MUL8\n        lda #$12\n        ldx #$10\n        mul8\n"
  "        sta R5C\n        tya\n        sta F5C\n")
A("; --- 0x5D SWP\n        lda #$3C\n        swp\n" + rec(0x5D))
A("; --- 0x5E CMA\n        lda #$0F\n        cma\n" + rec(0x5E))
A("; --- 0x5F XCH\n        lda #$AA\n        ldx #$55\n        xch\n"
  "        sta R5F\n        txa\n        sta F5F\n")
MMIO_PART = """; --- MMIO: SHA mixer on IN0 = 00..1F, IN1/TAIL zero
        ldx #$00
_mmix:  txa
        sta SHA_IN0,x
        inx
        cpx #$20
        bne _mmix
        lda #1
        sta SHA_GO
        ldhl #SHA_OUT
        ldde #SHABUF
        ldbc #$0020
        ldir
; --- MMIO: tiny chain (T=4, S=64 -> 2 blocks), S0 window + XFETCH
        lda #$04
        sta CHAIN_T
        lda #$40
        sta CHAIN_S
        lda #1
        sta CHAIN_INIT
        ldhl #CHAIN_S0
        ldde #S0BUF
        ldbc #$0020
        ldir
        lda #$01
        sta XMEM_IDX
        lda #1
        sta XMEM_FETCH
        ldhl #XMEM_WIN
        ldde #XWBUF
        ldbc #$0020
        ldir
"""


def dump_loop(n, label, count):
    return ("        ldx #$00\n_dmp%d: lda %s,x\n        jsr _phex\n"
            "        inx\n        cpx #$%02X\n        bne _dmp%d\n"
            "        lda #$0A\n        sta PUTCHAR\n"
            % (n, label, count, n))


DUMP = ("; --- dump results: banner, RB, FB, E1..E3, SHA, S0, XWIN\n"
        "        ldx #$00\n"
        "_ban:   lda banner,x\n        beq _ban_done\n"
        "        sta PUTCHAR\n        inx\n        bra _ban\n"
        "_ban_done:\n"
        + dump_loop(1, "R00", 0x60)
        + dump_loop(2, "F00", 0x60)
        + dump_loop(3, "E1", 0x03)
        + dump_loop(4, "SHABUF", 0x20)
        + dump_loop(5, "S0BUF", 0x20)
        + dump_loop(6, "XWBUF", 0x20))

EPILOGUE = """; --- 0x01 HLT: marker, halt, trailing garbage must never execute
        lda #$01
        sta R01
        hlt
        .byte $FF, $FE, $FD

_phex:  sta SCRATCH
        lsr
        lsr
        lsr
        lsr
        jsr _pnib
        lda SCRATCH
        and #$0F
_pnib:  cmp #10
        bcc _dig
        clc
        adc #87
        bra _pout
_dig:   clc
        adc #48
_pout:  sta PUTCHAR
        rts

banner: .ascii "MERU-8 SELFTEST\\n"
        .byte 0
pat55:  .byte $D5, $55, $AA, $5A
pat57:  .byte $01, $02, $03, $04, $05, $06, $07, $08
pat5b:  .byte $01, $02, $04, $08
ptr4b:  .word _j4b
ptr58:  .word $0600
"""


def selftest_source():
    return (HDR + equs() + "start:\n" + "".join(TESTS)
            + MMIO_PART + DUMP + EPILOGUE)


def main(argv):
    if len(argv) != 2:
        sys.stderr.write(__doc__)
        return 2
    org, image = assemble(selftest_source())
    assert org == 0x8000
    with open(argv[1], "wb") as f:
        f.write(image)
    sys.stderr.write("selftest: %d bytes at $%04X -> %s\n"
                     % (len(image), org, argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

