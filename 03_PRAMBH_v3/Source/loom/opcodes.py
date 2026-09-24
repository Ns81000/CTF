#!/usr/bin/env python3
"""MERU-8 survey loom ISA - single source of truth.
Shared by asm.py (assembler), model_loom.py (Python model) and
gen_datasheet.py (field-notes datasheet). 96 documented opcodes.

Operand kinds: none imm zp zpx abs absx absy indy rel imm16 ind
"""

MACHINE_NAME = "MERU-8"

OPS = [
    (0x00, "NOP",  "none",  1, "-",     "no operation"),
    (0x01, "HLT",  "none",  1, "-",     "halt the loom"),
    (0x02, "LDA",  "imm",   2, "ZN",    "A = immediate"),
    (0x03, "LDA",  "zp",    2, "ZN",    "A = (zp)"),
    (0x04, "LDA",  "zpx",   2, "ZN",    "A = (zp+X)"),
    (0x05, "LDA",  "abs",   3, "ZN",    "A = (addr)"),
    (0x06, "LDA",  "absx",  3, "ZN",    "A = (addr+X)"),
    (0x07, "LDA",  "absy",  3, "ZN",    "A = (addr+Y)"),
    (0x08, "LDA",  "indy",  2, "ZN",    "A = ((zp):Y)"),
    (0x09, "STA",  "zp",    2, "-",     "(zp) = A"),
    (0x0A, "STA",  "zpx",   2, "-",     "(zp+X) = A"),
    (0x0B, "STA",  "abs",   3, "-",     "(addr) = A"),
    (0x0C, "STA",  "absx",  3, "-",     "(addr+X) = A"),
    (0x0D, "STA",  "absy",  3, "-",     "(addr+Y) = A"),
    (0x0E, "STA",  "indy",  2, "-",     "((zp):Y) = A"),
    (0x0F, "LDX",  "imm",   2, "ZN",    "X = immediate"),
    (0x10, "LDX",  "zp",    2, "ZN",    "X = (zp)"),
    (0x11, "LDX",  "abs",   3, "ZN",    "X = (addr)"),
    (0x12, "LDY",  "imm",   2, "ZN",    "Y = immediate"),
    (0x13, "LDY",  "zp",    2, "ZN",    "Y = (zp)"),
    (0x14, "LDY",  "abs",   3, "ZN",    "Y = (addr)"),
    (0x15, "STX",  "zp",    2, "-",     "(zp) = X"),
    (0x16, "STX",  "abs",   3, "-",     "(addr) = X"),
    (0x17, "STY",  "zp",    2, "-",     "(zp) = Y"),
    (0x18, "STY",  "abs",   3, "-",     "(addr) = Y"),
    (0x19, "TAX",  "none",  1, "ZN",    "X = A"),
    (0x1A, "TXA",  "none",  1, "ZN",    "A = X"),
    (0x1B, "TAY",  "none",  1, "ZN",    "Y = A"),
    (0x1C, "TYA",  "none",  1, "ZN",    "A = Y"),
    (0x1D, "TSX",  "none",  1, "ZN",    "X = SP"),
    (0x1E, "TXS",  "none",  1, "-",     "SP = X"),
    (0x1F, "ADC",  "imm",   2, "ZNVC",  "A += immediate + C"),
    (0x20, "ADC",  "zp",    2, "ZNVC",  "A += (zp) + C"),
    (0x21, "ADC",  "abs",   3, "ZNVC",  "A += (addr) + C"),
    (0x22, "SBC",  "imm",   2, "ZNVC",  "A -= immediate + !C"),
    (0x23, "SBC",  "zp",    2, "ZNVC",  "A -= (zp) + !C"),
    (0x24, "SBC",  "abs",   3, "ZNVC",  "A -= (addr) + !C"),
    (0x25, "AND",  "imm",   2, "ZN",    "A &= immediate"),
    (0x26, "AND",  "zp",    2, "ZN",    "A &= (zp)"),
    (0x27, "AND",  "abs",   3, "ZN",    "A &= (addr)"),
    (0x28, "ORA",  "imm",   2, "ZN",    "A |= immediate"),
    (0x29, "ORA",  "zp",    2, "ZN",    "A |= (zp)"),
    (0x2A, "ORA",  "abs",   3, "ZN",    "A |= (addr)"),
    (0x2B, "EOR",  "imm",   2, "ZN",    "A ^= immediate"),
    (0x2C, "EOR",  "zp",    2, "ZN",    "A ^= (zp)"),
    (0x2D, "EOR",  "abs",   3, "ZN",    "A ^= (addr)"),
    (0x2E, "ASL",  "none",  1, "ZNC",   "A <<= 1"),
    (0x2F, "LSR",  "none",  1, "ZNC",   "A >>= 1"),
    (0x30, "ROL",  "none",  1, "ZNC",   "rotate A left through C"),
    (0x31, "ROR",  "none",  1, "ZNC",   "rotate A right through C"),
    (0x32, "CMP",  "imm",   2, "ZNC",   "compare A, immediate"),
    (0x33, "CMP",  "zp",    2, "ZNC",   "compare A, (zp)"),
    (0x34, "CMP",  "abs",   3, "ZNC",   "compare A, (addr)"),
    (0x35, "CPX",  "imm",   2, "ZNC",   "compare X, immediate"),
    (0x36, "CPY",  "imm",   2, "ZNC",   "compare Y, immediate"),
    (0x37, "INC",  "zp",    2, "ZN",    "(zp) += 1"),
    (0x38, "INC",  "abs",   3, "ZN",    "(addr) += 1"),
    (0x39, "DEC",  "zp",    2, "ZN",    "(zp) -= 1"),
    (0x3A, "DEC",  "abs",   3, "ZN",    "(addr) -= 1"),
    (0x3B, "INX",  "none",  1, "ZN",    "X += 1"),
    (0x3C, "INY",  "none",  1, "ZN",    "Y += 1"),
    (0x3D, "DEX",  "none",  1, "ZN",    "X -= 1"),
    (0x3E, "DEY",  "none",  1, "ZN",    "Y -= 1"),
    (0x3F, "BRA",  "rel",   2, "-",     "branch always"),
    (0x40, "BNE",  "rel",   2, "-",     "branch if Z=0"),
    (0x41, "BEQ",  "rel",   2, "-",     "branch if Z=1"),
    (0x42, "BCC",  "rel",   2, "-",     "branch if C=0"),
    (0x43, "BCS",  "rel",   2, "-",     "branch if C=1"),
    (0x44, "BMI",  "rel",   2, "-",     "branch if N=1"),
    (0x45, "BPL",  "rel",   2, "-",     "branch if N=0"),
    (0x46, "BVC",  "rel",   2, "-",     "branch if V=0"),
    (0x47, "BVS",  "rel",   2, "-",     "branch if V=1"),

    (0x48, "JMP",  "abs",   3, "-",     "PC = addr"),
    (0x49, "JSR",  "abs",   3, "-",     "call subroutine"),
    (0x4A, "RTS",  "none",  1, "-",     "return from subroutine"),
    (0x4B, "JMP",  "ind",   3, "-",     "PC = (addr), corrected"),
    (0x4C, "PHA",  "none",  1, "-",     "push A"),
    (0x4D, "PLA",  "none",  1, "ZN",    "pull A"),
    (0x4E, "PHP",  "none",  1, "-",     "push flags"),
    (0x4F, "PLP",  "none",  1, "ZNVC",  "pull flags"),
    (0x50, "CLC",  "none",  1, "C",     "clear carry"),
    (0x51, "SEC",  "none",  1, "C",     "set carry"),
    (0x52, "CLV",  "none",  1, "V",     "clear overflow"),
    (0x53, "SKP",  "imm",   2, "-",     "skip one byte (operand inert)"),
    (0x54, "LDHL", "imm16", 3, "-",     "HL = immediate"),
    (0x55, "LDDE", "imm16", 3, "-",     "DE = immediate"),
    (0x56, "LDBC", "imm16", 3, "-",     "BC = immediate"),
    (0x57, "LDIR", "none",  1, "-",     "block move BC bytes (HL)->(DE)"),
    (0x58, "LDHL", "abs",   3, "-",     "HL = (addr)"),
    (0x59, "STHL", "abs",   3, "-",     "(addr) = HL"),
    (0x5A, "ADDHL","none",  1, "ZNC",   "HL += A"),
    (0x5B, "XCRC", "none",  1, "ZN",    "A ^= each of BC bytes at (HL)"),
    (0x5C, "MUL8", "none",  1, "ZN",    "A*X -> A low, Y high"),
    (0x5D, "SWP",  "none",  1, "ZN",    "swap nibbles of A"),
    (0x5E, "CMA",  "none",  1, "ZN",    "A ^= $FF"),
    (0x5F, "XCH",  "none",  1, "-",     "exchange A and X"),
]

FLAG_C = 0x01
FLAG_Z = 0x02
FLAG_V = 0x40
FLAG_N = 0x80
FLAG_FIXED = 0x30

RESET_PC = 0x8000
ROM_MAX = 0x7000          # ROM occupies $8000-$EFFF
MMIO_BASE = 0xF000        # MMIO page $F000-$F0FF; open bus above

# MMIO offsets from $F000 (host services; documented in the datasheet)
MMIO = {
    "PUTCHAR":       0x00,   # W: print byte to the station teleprinter
    "EXIT":          0x01,   # W: halt (same as HLT)
    "CHAIN_CLAIM":   0x02,   # W: lodge the mixer output as survey result
    "CART_SEED":     0x10,   # W: 32 bytes $F010-$F02F, cartridge load vector
    "SEED_USE_CART": 0x30,   # W: next CHAIN_INIT uses the cartridge vector
    "CHAIN_T":       0x31,   # W: 8 bytes LE $F031-$F038, stitch count
    "CHAIN_S":       0x39,   # W: 4 bytes LE $F039-$F03C, table size in bytes
    "CHAIN_INIT":    0x3D,   # W: fill the extended stitch table (slow)
    "SHA_IN0":       0x40,   # W: 32 bytes $F040-$F05F, mixer pan 0
    "SHA_IN1":       0x60,   # W: 32 bytes $F060-$F07F, mixer pan 1
    "SHA_TAIL":      0x80,   # W: 8 bytes LE $F080-$F087, stitch number
    "SHA_GO":        0x88,   # W: run the mixer; digest appears at $F090
    "SHA_OUT":       0x90,   # R: 32 bytes $F090-$F0AF
    "XMEM_IDX":      0xB0,   # W: 8 bytes LE $F0B0-$F0B7, table block number
    "XMEM_FETCH":    0xB8,   # W: fetch table block (idx mod nblocks)
    "CHAIN_S0":      0xC0,   # R: 32 bytes $F0C0-$F0DF, initial stitch state
    "XMEM_WIN":      0xE0,   # R: 32 bytes $F0E0-$F0FF, fetched block window
}

BY_MNEM = {}
for code, mnem, kind, size, flags, desc in OPS:
    BY_MNEM.setdefault(mnem, {})[kind] = code

