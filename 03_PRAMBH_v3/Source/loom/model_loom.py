#!/usr/bin/env python3
"""Independent Python model of the MERU-1 loom (spec 4.4 acceptance:
the Python model reproduces ROM output bit-exactly).

Implements all 96 opcodes and the MMIO host services (mixer = SHA-256,
extended stitch table = PRAMBH-CHAIN fill).  Slow but exact; used with
small-T test ROMs.
"""
import hashlib
import struct
import sys

from opcodes import (FLAG_C, FLAG_Z, FLAG_V, FLAG_N, FLAG_FIXED,
                     RESET_PC, MMIO_BASE, MMIO)

FILL_LABEL = b"prambh:chain:fill:v1"
RUN_LABEL = b"prambh:chain:run:v1"

def sha(b):
    return hashlib.sha256(b).digest()

class Machine:
    def __init__(self, rom, vector=None, max_steps=200000000):
        self.mem = bytearray(65536)
        self.mem[RESET_PC:RESET_PC + len(rom)] = rom
        self.a = self.x = self.y = 0
        self.h = self.l = self.d = self.e = self.b = self.c = 0
        self.sp = 0xFF
        self.f = FLAG_FIXED
        self.pc = RESET_PC
        self.halted = False
        self.out = bytearray()
        self.max_steps = max_steps
        # host services
        self.vector = vector if vector is not None else bytes(32)
        self.cart_seed = bytearray(32)
        self.use_cart = False
        self.chain_t = 0
        self.chain_s = 0
        self.table = None
        self.nblocks = 0
        self.xmem_idx = 0
        self.claimed = None

    # -- flags ---------------------------------------------------------
    def setzn(self, v):
        self.f &= ~(FLAG_Z | FLAG_N)
        if v & 0xFF == 0:
            self.f |= FLAG_Z
        if v & 0x80:
            self.f |= FLAG_N
        return v & 0xFF

    # -- memory --------------------------------------------------------
    def rd(self, a):
        return self.mem[a & 0xFFFF]

    def wr(self, a, v):
        a &= 0xFFFF
        v &= 0xFF
        self.mem[a] = v
        if MMIO_BASE <= a < MMIO_BASE + 0x100:
            self.mmio(a - MMIO_BASE, v)

    def mmio(self, off, v):
        if off == MMIO["PUTCHAR"]:
            self.out.append(v)
        elif off == MMIO["EXIT"]:
            self.halted = True
        elif off == MMIO["CHAIN_CLAIM"]:
            self.claimed = bytes(self.mem[MMIO_BASE + MMIO["SHA_OUT"]:
                                          MMIO_BASE + MMIO["SHA_OUT"] + 32])
        elif MMIO["CART_SEED"] <= off < MMIO["CART_SEED"] + 32:
            self.cart_seed[off - MMIO["CART_SEED"]] = v
        elif off == MMIO["SEED_USE_CART"]:
            self.use_cart = True
        elif MMIO["CHAIN_T"] <= off < MMIO["CHAIN_T"] + 8:
            i = off - MMIO["CHAIN_T"]
            self.chain_t = (self.chain_t & ~(0xFF << (8 * i))) | (v << (8 * i))
        elif MMIO["CHAIN_S"] <= off < MMIO["CHAIN_S"] + 4:
            i = off - MMIO["CHAIN_S"]
            self.chain_s = (self.chain_s & ~(0xFF << (8 * i))) | (v << (8 * i))
        elif off == MMIO["CHAIN_INIT"]:
            self.chain_init()
        elif off == MMIO["SHA_GO"]:
            in0 = bytes(self.mem[MMIO_BASE + 0x40:MMIO_BASE + 0x60])
            in1 = bytes(self.mem[MMIO_BASE + 0x60:MMIO_BASE + 0x80])
            tail = bytes(self.mem[MMIO_BASE + 0x80:MMIO_BASE + 0x88])
            dig = sha(in0 + in1 + tail)
            self.mem[MMIO_BASE + 0x90:MMIO_BASE + 0xB0] = dig
        elif MMIO["XMEM_IDX"] <= off < MMIO["XMEM_IDX"] + 8:
            i = off - MMIO["XMEM_IDX"]
            self.xmem_idx = ((self.xmem_idx & ~(0xFF << (8 * i)))
                             | (v << (8 * i)))
        elif off == MMIO["XMEM_FETCH"]:
            if self.table is not None and self.nblocks:
                idx = self.xmem_idx % self.nblocks
                blk = self.table[idx * 32:(idx + 1) * 32]
                self.mem[MMIO_BASE + 0xE0:MMIO_BASE + 0x100] = blk

    def chain_init(self):
        vec = bytes(self.cart_seed) if self.use_cart else self.vector
        seed = sha(b"prambh:loom:seed:v1" + vec)
        nbytes = self.chain_s or (512 * 1024 * 1024)
        n = nbytes // 32
        tbl = bytearray(n * 32)
        prev = sha(FILL_LABEL + seed + struct.pack("<Q", nbytes)
                   + struct.pack("<Q", self.chain_t))
        tbl[0:32] = prev
        for i in range(1, n):
            prev = sha(prev + struct.pack("<Q", i))
            tbl[i * 32:(i + 1) * 32] = prev
        self.table = tbl
        self.nblocks = n
        s0 = sha(RUN_LABEL + seed + bytes(tbl[(n - 1) * 32:n * 32]))
        self.mem[MMIO_BASE + 0xC0:MMIO_BASE + 0xE0] = s0

    # -- stack ---------------------------------------------------------
    def push(self, v):
        self.mem[0x100 + self.sp] = v & 0xFF
        self.sp = (self.sp - 1) & 0xFF

    def pull(self):
        self.sp = (self.sp + 1) & 0xFF
        return self.mem[0x100 + self.sp]

    # -- helpers ---------------------------------------------------------
    def hl(self):
        return (self.h << 8) | self.l

    def set_hl(self, v):
        self.h = (v >> 8) & 0xFF
        self.l = v & 0xFF

    def de(self):
        return (self.d << 8) | self.e

    def set_de(self, v):
        self.d = (v >> 8) & 0xFF
        self.e = v & 0xFF

    def bc(self):
        return (self.b << 8) | self.c

    def set_bc(self, v):
        self.b = (v >> 8) & 0xFF
        self.c = v & 0xFF

    def fetch(self):
        v = self.mem[self.pc]
        self.pc = (self.pc + 1) & 0xFFFF
        return v

    def fetch16(self):
        lo = self.fetch()
        return lo | (self.fetch() << 8)

    def adc(self, m):
        c = 1 if self.f & FLAG_C else 0
        r = self.a + m + c
        self.f &= ~(FLAG_C | FLAG_V | FLAG_Z | FLAG_N)
        if (~(self.a ^ m) & (self.a ^ r) & 0x80):
            self.f |= FLAG_V
        if r > 0xFF:
            self.f |= FLAG_C
        self.a = self.setzn(r)

    def sbc(self, m):
        c = 0 if self.f & FLAG_C else 1
        r = self.a - m - c
        self.f &= ~(FLAG_C | FLAG_V | FLAG_Z | FLAG_N)
        if ((self.a ^ m) & (self.a ^ r) & 0x80):
            self.f |= FLAG_V
        if r >= 0:
            self.f |= FLAG_C
        self.a = self.setzn(r)

    def cmp(self, reg, m):
        r = (reg - m) & 0x1FF
        self.f &= ~(FLAG_C | FLAG_Z | FLAG_N)
        if reg >= m:
            self.f |= FLAG_C
        self.setzn(r & 0xFF)

    def branch(self, cond):
        off = self.fetch()
        if cond:
            if off & 0x80:
                off -= 0x100
            self.pc = (self.pc + off) & 0xFFFF

    # -- execution -------------------------------------------------------
    def run(self):
        steps = 0
        while not self.halted:
            steps += 1
            if steps > self.max_steps:
                raise SystemExit("model: step limit exceeded")
            self.step()
        return steps

    def step(self):
        op = self.fetch()
        m = self.mem
        if op == 0x00:            # NOP
            pass
        elif op == 0x01:          # HLT
            self.halted = True
        elif op == 0x02:          # LDA imm
            self.a = self.setzn(self.fetch())
        elif op == 0x03:          # LDA zp
            self.a = self.setzn(self.rd(self.fetch()))
        elif op == 0x04:          # LDA zp,X
            self.a = self.setzn(self.rd((self.fetch() + self.x) & 0xFF))
        elif op == 0x05:          # LDA abs
            self.a = self.setzn(self.rd(self.fetch16()))
        elif op == 0x06:          # LDA abs,X
            self.a = self.setzn(self.rd(self.fetch16() + self.x))
        elif op == 0x07:          # LDA abs,Y
            self.a = self.setzn(self.rd(self.fetch16() + self.y))
        elif op == 0x08:          # LDA (zp),Y
            zp = self.fetch()
            ptr = m[zp] | (m[(zp + 1) & 0xFF] << 8)
            self.a = self.setzn(self.rd(ptr + self.y))
        elif op == 0x09:          # STA zp
            self.wr(self.fetch(), self.a)
        elif op == 0x0A:          # STA zp,X
            self.wr((self.fetch() + self.x) & 0xFF, self.a)
        elif op == 0x0B:          # STA abs
            self.wr(self.fetch16(), self.a)
        elif op == 0x0C:          # STA abs,X
            self.wr(self.fetch16() + self.x, self.a)
        elif op == 0x0D:          # STA abs,Y
            self.wr(self.fetch16() + self.y, self.a)
        elif op == 0x0E:          # STA (zp),Y
            zp = self.fetch()
            ptr = m[zp] | (m[(zp + 1) & 0xFF] << 8)
            self.wr(ptr + self.y, self.a)
        elif op == 0x0F:          # LDX imm
            self.x = self.setzn(self.fetch())
        elif op == 0x10:
            self.x = self.setzn(self.rd(self.fetch()))
        elif op == 0x11:
            self.x = self.setzn(self.rd(self.fetch16()))
        elif op == 0x12:          # LDY imm
            self.y = self.setzn(self.fetch())
        elif op == 0x13:
            self.y = self.setzn(self.rd(self.fetch()))
        elif op == 0x14:
            self.y = self.setzn(self.rd(self.fetch16()))
        elif op == 0x15:
            self.wr(self.fetch(), self.x)
        elif op == 0x16:
            self.wr(self.fetch16(), self.x)
        elif op == 0x17:
            self.wr(self.fetch(), self.y)
        elif op == 0x18:
            self.wr(self.fetch16(), self.y)
        elif op == 0x19:          # TAX
            self.x = self.setzn(self.a)
        elif op == 0x1A:
            self.a = self.setzn(self.x)
        elif op == 0x1B:
            self.y = self.setzn(self.a)
        elif op == 0x1C:
            self.a = self.setzn(self.y)
        elif op == 0x1D:
            self.x = self.setzn(self.sp)
        elif op == 0x1E:
            self.sp = self.x
        elif op == 0x1F:
            self.adc(self.fetch())
        elif op == 0x20:
            self.adc(self.rd(self.fetch()))
        elif op == 0x21:
            self.adc(self.rd(self.fetch16()))
        elif op == 0x22:
            self.sbc(self.fetch())
        elif op == 0x23:
            self.sbc(self.rd(self.fetch()))
        elif op == 0x24:
            self.sbc(self.rd(self.fetch16()))
        elif op == 0x25:
            self.a = self.setzn(self.a & self.fetch())
        elif op == 0x26:
            self.a = self.setzn(self.a & self.rd(self.fetch()))
        elif op == 0x27:
            self.a = self.setzn(self.a & self.rd(self.fetch16()))
        elif op == 0x28:
            self.a = self.setzn(self.a | self.fetch())
        elif op == 0x29:
            self.a = self.setzn(self.a | self.rd(self.fetch()))
        elif op == 0x2A:
            self.a = self.setzn(self.a | self.rd(self.fetch16()))
        elif op == 0x2B:
            self.a = self.setzn(self.a ^ self.fetch())
        elif op == 0x2C:
            self.a = self.setzn(self.a ^ self.rd(self.fetch()))
        elif op == 0x2D:
            self.a = self.setzn(self.a ^ self.rd(self.fetch16()))
        elif op == 0x2E:          # ASL
            c = (self.a >> 7) & 1
            self.a = self.setzn(self.a << 1)
            self.f = (self.f & ~FLAG_C) | c
        elif op == 0x2F:          # LSR
            c = self.a & 1
            self.a = self.setzn(self.a >> 1)
            self.f = (self.f & ~FLAG_C) | c
        elif op == 0x30:          # ROL
            c = (self.a >> 7) & 1
            old = 1 if self.f & FLAG_C else 0
            self.a = self.setzn((self.a << 1) | old)
            self.f = (self.f & ~FLAG_C) | c
        elif op == 0x31:          # ROR
            c = self.a & 1
            old = 0x80 if self.f & FLAG_C else 0
            self.a = self.setzn((self.a >> 1) | old)
            self.f = (self.f & ~FLAG_C) | c
        elif op == 0x32:
            self.cmp(self.a, self.fetch())
        elif op == 0x33:
            self.cmp(self.a, self.rd(self.fetch()))
        elif op == 0x34:
            self.cmp(self.a, self.rd(self.fetch16()))
        elif op == 0x35:
            self.cmp(self.x, self.fetch())
        elif op == 0x36:
            self.cmp(self.y, self.fetch())
        elif op == 0x37:          # INC zp
            a = self.fetch()
            self.wr(a, self.setzn(m[a] + 1))
        elif op == 0x38:          # INC abs
            a = self.fetch16()
            self.wr(a, self.setzn(m[a] + 1))
        elif op == 0x39:
            a = self.fetch()
            self.wr(a, self.setzn(m[a] - 1))
        elif op == 0x3A:
            a = self.fetch16()
            self.wr(a, self.setzn(m[a] - 1))
        elif op == 0x3B:
            self.x = self.setzn(self.x + 1)
        elif op == 0x3C:
            self.y = self.setzn(self.y + 1)
        elif op == 0x3D:
            self.x = self.setzn(self.x - 1)
        elif op == 0x3E:
            self.y = self.setzn(self.y - 1)
        elif 0x3F <= op <= 0x47:  # branches
            conds = {
                0x3F: True,
                0x40: not (self.f & FLAG_Z),
                0x41: bool(self.f & FLAG_Z),
                0x42: not (self.f & FLAG_C),
                0x43: bool(self.f & FLAG_C),
                0x44: bool(self.f & FLAG_N),
                0x45: not (self.f & FLAG_N),
                0x46: not (self.f & FLAG_V),
                0x47: bool(self.f & FLAG_V),
            }
            self.branch(conds[op])
        elif op == 0x48:          # JMP abs
            self.pc = self.fetch16()
        elif op == 0x49:          # JSR
            a = self.fetch16()
            ret = (self.pc - 1) & 0xFFFF
            self.push(ret >> 8)
            self.push(ret & 0xFF)
            self.pc = a
        elif op == 0x4A:          # RTS
            lo = self.pull()
            hi = self.pull()
            self.pc = ((hi << 8) | lo) + 1 & 0xFFFF
        elif op == 0x4B:          # JMP (ind)
            a = self.fetch16()
            self.pc = m[a] | (m[(a + 1) & 0xFFFF] << 8)
        elif op == 0x4C:          # PHA
            self.push(self.a)
        elif op == 0x4D:          # PLA
            self.a = self.setzn(self.pull())
        elif op == 0x4E:          # PHP
            self.push(self.f | FLAG_FIXED)
        elif op == 0x4F:          # PLP
            self.f = self.pull() | FLAG_FIXED
        elif op == 0x50:
            self.f &= ~FLAG_C
        elif op == 0x51:
            self.f |= FLAG_C
        elif op == 0x52:
            self.f &= ~FLAG_V
        elif op == 0x53:          # SKP
            self.fetch()
        elif op == 0x54:
            self.set_hl(self.fetch16())
        elif op == 0x55:
            self.set_de(self.fetch16())
        elif op == 0x56:
            self.set_bc(self.fetch16())
        elif op == 0x57:          # LDIR
            hl, de, bc = self.hl(), self.de(), self.bc()
            while bc:
                self.wr(de, self.rd(hl))
                hl = (hl + 1) & 0xFFFF
                de = (de + 1) & 0xFFFF
                bc -= 1
            self.set_hl(hl)
            self.set_de(de)
            self.set_bc(0)
        elif op == 0x58:          # LDHL abs
            a = self.fetch16()
            self.set_hl(m[a] | (m[(a + 1) & 0xFFFF] << 8))
        elif op == 0x59:          # STHL abs
            a = self.fetch16()
            self.wr(a, self.l)
            self.wr((a + 1) & 0xFFFF, self.h)
        elif op == 0x5A:          # ADDHL
            r = self.hl() + self.a
            self.f &= ~(FLAG_C | FLAG_Z | FLAG_N)
            if r > 0xFFFF:
                self.f |= FLAG_C
            self.set_hl(r & 0xFFFF)
            if self.hl() == 0:
                self.f |= FLAG_Z
            if self.hl() & 0x8000:
                self.f |= FLAG_N
        elif op == 0x5B:          # XCRC
            hl, bc = self.hl(), self.bc()
            a = self.a
            while bc:
                a ^= self.rd(hl)
                hl = (hl + 1) & 0xFFFF
                bc -= 1
            self.set_hl(hl)
            self.set_bc(0)
            self.a = self.setzn(a)
        elif op == 0x5C:          # MUL8
            r = self.a * self.x
            self.a = self.setzn(r & 0xFF)
            self.y = (r >> 8) & 0xFF
        elif op == 0x5D:          # SWP
            self.a = self.setzn(((self.a << 4) | (self.a >> 4)) & 0xFF)
        elif op == 0x5E:          # CMA
            self.a = self.setzn(self.a ^ 0xFF)
        elif op == 0x5F:          # XCH
            self.a, self.x = self.x, self.a
        else:
            raise SystemExit("model: bad opcode $%02X at $%04X"
                             % (op, (self.pc - 1) & 0xFFFF))

def main(argv):
    if len(argv) < 2:
        sys.stderr.write("usage: model_loom.py <rom> [vector_hex]\n")
        return 2
    rom = open(argv[1], "rb").read()
    vec = bytes.fromhex(argv[2]) if len(argv) > 2 else bytes(32)
    m = Machine(rom, vec)
    m.run()
    sys.stdout.write(m.out.decode("ascii", "replace"))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
