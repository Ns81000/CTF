#!/usr/bin/env python3
"""model_vm.py -- an independent model of the engine's machine.

This file is written from the ISA description alone: it shares no code with
the C engine.  It is used two ways:

  * the generator calls it to pin the trace (so the shipped programs land on
    the pinned constant), and
  * the acceptance suite calls it to prove that the *shipped* image, once
    decrypted with the nonce the tool prints, runs step-for-step and byte-for
    -byte identically to the binary.

Machine shape: 8 general registers, a writable code buffer (self-modifying
code is allowed), a writable data buffer, an integer stack, one flags word.
"""
import hashlib
import struct

SEED_MAP = "ghost2:stage1:vm:map:v1"
SEED_OTP = "ghost2:stage1:otp:v1"
NONCE_SEED = "ghost2:stage1:nonce:v1"
OUT = 0x100
DATA_SIZE = 0x800
CODE_SIZE = 0x1000
STACK_SIZE = 512

# logical opcode -> operand form
#   N (none)  R (reg)  R8 (reg,imm8)  R32 (reg,imm32)  RR  RRR  A32 (imm32)
#   RAR (reg,imm32,reg)
ISA = [
    ("NOP", "N"), ("HALT", "N"), ("MOVI", "R32"), ("MOVRR", "RR"),
    ("ADD", "RR"), ("SUB", "RR"), ("MUL", "RR"), ("AND", "RR"),
    ("OR", "RR"), ("XOR", "RR"), ("SHL", "R8"), ("SHR", "R8"),
    ("ROL", "R8"), ("ROR", "R8"), ("NOT", "R"), ("NEG", "R"),
    ("INC", "R"), ("DEC", "R"), ("ADDI", "R32"), ("SUBI", "R32"),
    ("XORI", "R32"), ("ANDI", "R32"), ("ORI", "R32"), ("MULI", "R32"),
    ("DIVU", "RR"), ("MODU", "RR"), ("ROTL", "R8"), ("ROTR", "R8"),
    ("JMP", "A32"), ("JZ", "R32"), ("JNZ", "R32"), ("JLT", "R32"),
    ("JGE", "R32"), ("JMPR", "R"), ("CALL", "A32"), ("CALLR", "R"),
    ("RET", "N"), ("PUSH", "R"), ("POP", "R"), ("DUP", "R"),
    ("XCHG", "RR"), ("PUSHF", "N"), ("POPF", "N"), ("PEEK", "R8"),
    ("DISCARD", "R8"), ("LDW", "R32"), ("STW", "R32"), ("LDB", "R32"),
    ("STB", "R32"), ("LDSB", "R32"), ("STSB", "R32"), ("LDIND", "RR"),
    ("STIND", "RR"), ("LDX", "RR"), ("STX", "RR"), ("CMP", "RR"),
    ("TEST", "RR"), ("MIN", "RR"), ("MAX", "RR"), ("ABS", "R"),
    ("SIGN", "R"), ("CLZ", "R"), ("CTZ", "R"), ("POPCNT", "R"),
    ("BSWAP", "R"), ("SWAP16", "R"), ("EXT8", "R"), ("SEXT8", "R"),
    ("EXT16", "R"), ("SEXT16", "R"), ("MIX", "R"), ("LCG", "R8"),
    ("AVAL", "R"), ("FMIX", "R"), ("ADD3", "RRR"), ("XOR3", "RRR"),
    ("ROTX", "RR"), ("SBOX", "R"), ("TWEAK32", "R32"), ("WHITEN", "R"),
    ("CROSSR", "R32"), ("SMCW", "R32"), ("SMCR", "R32"), ("SMXX", "R32"),
    ("EMITB", "R"), ("EMITW", "R"), ("KEYADV", "R"), ("TICK", "R"),
    ("PROBE", "R32"), ("MIXREG", "RR"), ("XORA", "R32"), ("ADDA", "R32"),
]
OP_ID = {name: i for i, (name, _) in enumerate(ISA)}
FORMS = {name: form for name, form in ISA}
OPLEN = {"N": 0, "R": 1, "R8": 2, "R32": 5, "RR": 2, "RRR": 3,
         "A32": 4, "RAR": 6}


def permutation():
    """A permutation of 0..255 from the map seed: the wire byte of every
    logical opcode is different in a rebuild that uses a different seed."""
    stream = b""
    key = hashlib.sha256(SEED_MAP.encode()).digest()
    while len(stream) < 512:
        key = hashlib.sha256(key + b"map").digest()
        stream += key
    pool = list(range(256))
    for index in range(256):
        pos = index + (stream[index] % (256 - index))
        pool[index], pool[pos] = pool[pos], pool[index]
    return pool


def opbytes(pool, count=None):
    return pool[:count or len(ISA)]


def nonce():
    return hashlib.sha256(NONCE_SEED.encode()).digest()[:8]


def keystream(n):
    nb = nonce()
    out = bytearray()
    i = 0
    while len(out) < n:
        out += hashlib.sha256(SEED_OTP.encode() + nb +
                              struct.pack("<I", i)).digest()
        i += 1
    return bytes(out[:n])


class Asm:
    """Two-pass assembler with symbolic labels."""

    def __init__(self, opb):
        self.opb = opb
        self.items = []
        self.labels = {}

    def label(self, name):
        self.items.append(("LABEL", [name]))
        return self

    def ins(self, name, *ops):
        self.items.append((name, list(ops)))
        return self

    def val(self, x):
        if isinstance(x, str):
            return self.labels[x] & 0xFFFFFFFF
        return x & 0xFFFFFFFF

    def assemble(self, base=0):
        self.labels = {}
        addr = base
        sizes = []
        for name, ops in self.items:
            if name == "LABEL":
                self.labels[ops[0]] = addr
                sizes.append(0)
            else:
                sizes.append(1 + OPLEN[FORMS[name]])
                addr += sizes[-1]
        code = bytearray()
        for (name, ops), _ in zip(self.items, sizes):
            if name == "LABEL":
                continue
            form = FORMS[name]
            code.append(self.opb[OP_ID[name]])
            if form == "N":
                pass
            elif form == "R":
                code.append(ops[0])
            elif form == "R8":
                code += bytes([ops[0], ops[1] & 0xFF])
            elif form == "RR":
                code += bytes([ops[0], ops[1]])
            elif form == "RRR":
                code.append(ops[0])
                code += bytes([ops[1], ops[2]])
            elif form == "A32":
                code += struct.pack("<I", self.val(ops[0]))
            elif form == "R32":
                code += bytes([ops[0]]) + struct.pack("<I", self.val(ops[1]))
        return bytes(code)


class Vm:
    """The reference machine.  Self-modifying code is permitted; nothing here
    assumes the instruction stream stays as it was loaded."""

    def __init__(self, code, opb, entry=0, limit=5000000):
        self.code = bytearray(code)
        if len(self.code) < CODE_SIZE:
            self.code += bytearray(CODE_SIZE - len(self.code))
        self.inv = {}
        for i, b in enumerate(opb):
            self.inv.setdefault(b, i)
        self.r = [0] * 8
        self.pc = entry
        self.sp = 0
        self.flags = 0
        self.data = bytearray(DATA_SIZE)
        self.stack = [0] * STACK_SIZE
        self.steps = 0
        self.limit = limit
        self.halt = False
        self.out = 0

    def u32(self, v):
        return v & 0xFFFFFFFF

    def s32(self, v):
        v &= 0xFFFFFFFF
        return v - 0x100000000 if v & 0x80000000 else v

    def push(self, v):
        if self.sp < STACK_SIZE - 1:
            self.stack[self.sp] = v & 0xFFFFFFFF
            self.sp += 1

    def pop(self):
        if self.sp <= 0:
            return 0
        self.sp -= 1
        return self.stack[self.sp]

    def run(self):
        while not self.halt and self.steps < self.limit:
            self.step()
        return self.steps

    def fetch(self):
        """Returns (name, operands) for the instruction at pc, or None."""
        if self.pc < 0 or self.pc >= len(self.code):
            return None
        wire = self.code[self.pc]
        lid = self.inv.get(wire)
        if lid is None:
            return None
        name, form = ISA[lid]
        p = self.pc + 1
        val = lambda: int.from_bytes(bytes(self.code[p:p + 4]), "little")
        if form == "N":
            ops = []
        elif form == "R":
            ops = [self.code[p]]
        elif form == "R8":
            ops = [self.code[p], self.code[p + 1]]
        elif form == "RR":
            ops = [self.code[p], self.code[p + 1]]
        elif form == "RRR":
            ops = [self.code[p], self.code[p + 1], self.code[p + 2]]
        elif form == "A32":
            ops = [val()]
        else:  # R32: register byte, then a little-endian 32-bit immediate
            ops = [self.code[p],
                   int.from_bytes(bytes(self.code[p + 1:p + 5]), "little")]
        return name, ops, 1 + OPLEN[form]

    def step(self):
        self.steps += 1
        fr = self.fetch()
        if fr is None:
            self.halt = True
            return
        name, o, size = fr
        nxt = self.pc + size
        r = self.r
        a = o[0] if o else 0
        b = o[1] if len(o) > 1 else 0
        c = o[2] if len(o) > 2 else 0
        d = self.data

        if name == "NOP":
            pass
        elif name == "HALT":
            self.halt = True
        elif name == "MOVI":
            r[a] = b & 0xFFFFFFFF
        elif name == "MOVRR":
            r[a] = r[b] & 0xFFFFFFFF
        elif name == "ADD":
            r[a] = self.u32(r[a] + r[b])
        elif name == "SUB":
            r[a] = self.u32(r[a] - r[b])
        elif name == "MUL":
            r[a] = self.u32(r[a] * r[b])
        elif name == "AND":
            r[a] = self.u32(r[a] & r[b])
        elif name == "OR":
            r[a] = self.u32(r[a] | r[b])
        elif name == "XOR":
            r[a] = self.u32(r[a] ^ r[b])
        elif name == "SHL":
            r[a] = self.u32(r[a] << (b & 31))
        elif name == "SHR":
            r[a] = self.u32(r[a]) >> (b & 31)
        elif name == "ROL" or name == "ROTL":
            s = b & 31
            r[a] = self.u32((r[a] << s) | (self.u32(r[a]) >> ((32 - s) & 31)))
        elif name == "ROR" or name == "ROTR":
            s = b & 31
            r[a] = self.u32((self.u32(r[a]) >> s) | (r[a] << ((32 - s) & 31)))
        elif name == "NOT":
            r[a] = self.u32(~r[a])
        elif name == "NEG":
            r[a] = self.u32(-r[a])
        elif name == "INC":
            r[a] = self.u32(r[a] + 1)
        elif name == "DEC":
            r[a] = self.u32(r[a] - 1)
        elif name == "ADDI":
            r[a] = self.u32(r[a] + b)
        elif name == "SUBI":
            r[a] = self.u32(r[a] - b)
        elif name == "XORI":
            r[a] = self.u32(r[a] ^ b)
        elif name == "ANDI":
            r[a] = self.u32(r[a] & b)
        elif name == "ORI":
            r[a] = self.u32(r[a] | b)
        elif name == "MULI":
            r[a] = self.u32(r[a] * b)
        elif name == "DIVU":
            r[a] = self.u32(r[a] // r[b]) if r[b] else 0
        elif name == "MODU":
            r[a] = self.u32(r[a] % r[b]) if r[b] else 0
        elif name == "ABS":
            r[a] = self.u32(abs(self.s32(r[a])))
        elif name == "SIGN":
            v = self.s32(r[a])
            r[a] = 0 if v == 0 else (1 if v > 0 else 0xFFFFFFFF)
        elif name == "CLZ":
            v = self.u32(r[a])
            r[a] = 32 if v == 0 else 32 - v.bit_length()
        elif name == "CTZ":
            v = self.u32(r[a])
            r[a] = 32 if v == 0 else (v & -v).bit_length() - 1
        elif name == "POPCNT":
            r[a] = bin(self.u32(r[a])).count("1")
        elif name == "BSWAP":
            r[a] = int.from_bytes(self.u32(r[a]).to_bytes(4, "little"), "big")
        elif name == "SWAP16":
            v = self.u32(r[a])
            r[a] = self.u32(((v & 0xFFFF) << 16) | (v >> 16))
        elif name == "EXT8":
            r[a] = self.u32(r[a]) & 0xFF
        elif name == "SEXT8":
            v = self.u32(r[a]) & 0xFF
            r[a] = self.u32(v - 256 if v & 0x80 else v)
        elif name == "EXT16":
            r[a] = self.u32(r[a]) & 0xFFFF
        elif name == "SEXT16":
            v = self.u32(r[a]) & 0xFFFF
            r[a] = self.u32(v - 65536 if v & 0x8000 else v)
        elif name == "MIX":
            v = self.u32(r[a])
            v ^= self.u32(v << 13)
            v ^= v >> 17
            v ^= self.u32(v << 5)
            r[a] = self.u32(v)
        elif name == "LCG":
            r[a] = self.u32(r[a] * 1103515245 + 12345 + (b & 0xFF))
        elif name == "AVAL":
            v = self.u32(r[a])
            v ^= v >> 16
            v = (v * 0x7FEB352D) & 0xFFFFFFFF
            v ^= v >> 15
            v = (v * 0x846CA68B) & 0xFFFFFFFF
            v ^= v >> 16
            r[a] = v
        elif name == "FMIX":
            v = self.u32(r[a])
            v ^= v >> 16
            v = (v * 0x85EBCA6B) & 0xFFFFFFFF
            v ^= v >> 13
            v = (v * 0xC2B2AE35) & 0xFFFFFFFF
            v ^= v >> 16
            r[a] = v
        elif name == "ADD3":
            r[a] = self.u32(r[a] + r[b] + r[c])
        elif name == "XOR3":
            r[a] = self.u32(r[a] ^ r[b] ^ r[c])
        elif name == "ROTX":
            s = r[b] & 31
            r[a] = self.u32((r[a] << s) | (self.u32(r[a]) >> ((32 - s) & 31)))
        elif name == "SBOX":
            v = self.u32(r[a])
            r[a] = self.u32(((v * 0x9E3779B9) & 0xFFFFFFFF) ^ (v >> 7))
        elif name == "TWEAK32":
            v = self.u32(r[a])
            s = self.u32((v << 7) | (v >> 25))
            r[a] = self.u32(v ^ self.u32(s + b))
        elif name == "WHITEN":
            r[a] = self.u32(r[a] ^ 0x9E3779B9)
        elif name == "KEYADV":
            r[a] = self.u32((r[a] ^ 0x5BD1E995) * 0x9E3779B1)
        elif name == "TICK":
            r[a] = self.u32(r[a] + (self.steps & 0xFFFF))
        elif name == "MIXREG":
            r[a] = self.u32(r[a] ^ self.u32((r[b] * 0x9E3779B1)))
            r[b] = self.u32(r[b] + (r[a] >> 3))
        elif name == "XORA":
            r[a] = self.u32(r[a] ^ (b + self.steps))
        elif name == "ADDA":
            r[a] = self.u32(r[a] + b + (self.steps & 0xFF))

        # ---- memory ------------------------------------------------------
        elif name == "LDW":
            r[a] = int.from_bytes(bytes(d[b % DATA_SIZE:b % DATA_SIZE + 4]),
                                  "little")
        elif name == "STW":
            for k in range(4):
                d[(b + k) % DATA_SIZE] = (self.u32(r[a]) >> (8 * k)) & 0xFF
        elif name == "LDB":
            r[a] = d[b % DATA_SIZE]
        elif name == "STB":
            d[b % DATA_SIZE] = self.u32(r[a]) & 0xFF
        elif name == "LDSB":
            v = d[b % DATA_SIZE]
            r[a] = self.u32(v - 256 if v & 0x80 else v)
        elif name == "STSB":
            d[b % DATA_SIZE] = self.u32(r[a]) & 0xFF
        elif name == "LDIND":
            r[a] = d[self.u32(r[b]) % DATA_SIZE]
        elif name == "STIND":
            d[self.u32(r[b]) % DATA_SIZE] = self.u32(r[a]) & 0xFF
        elif name == "LDX":
            r[a] = d[(self.u32(r[b]) + a) % DATA_SIZE]
        elif name == "STX":
            d[(self.u32(r[b]) + a) % DATA_SIZE] = self.u32(r[a]) & 0xFF

        # ---- flags, stack ------------------------------------------------
        elif name == "CMP":
            self.flags = 0xFFFFFFFF if r[a] == r[b] else 0
        elif name == "TEST":
            self.flags = self.u32(r[a] & r[b])
        elif name == "MIN":
            r[a] = min(self.u32(r[a]), self.u32(r[b]))
        elif name == "MAX":
            r[a] = max(self.u32(r[a]), self.u32(r[b]))
        elif name == "PUSH":
            self.push(r[a])
        elif name == "POP":
            r[a] = self.pop()
        elif name == "DUP":
            self.push(self.stack[self.sp - 1] if self.sp > 0 else 0)
        elif name == "XCHG":
            r[a], r[b] = r[b], r[a]
        elif name == "PUSHF":
            self.push(self.flags)
        elif name == "POPF":
            self.flags = self.pop()
        elif name == "PEEK":
            idx = self.sp - 1 - (b & 0xFF)
            r[a] = self.stack[idx] if 0 <= idx < STACK_SIZE else 0
        elif name == "DISCARD":
            self.sp = max(0, self.sp - (b & 0xFF))

        # ---- control -----------------------------------------------------
        elif name == "JMP":
            nxt = a
        elif name == "JZ":
            if self.u32(r[a]) == 0:
                nxt = b
        elif name == "JNZ":
            if self.u32(r[a]) != 0:
                nxt = b
        elif name == "JLT":
            if self.s32(r[a]) < self.s32(r[b]):
                nxt = 0
        elif name == "JGE":
            if self.s32(r[a]) >= self.s32(r[b]):
                nxt = 0
        elif name == "JMPR":
            nxt = self.u32(r[a])
        elif name == "CALL":
            self.push(nxt)
            nxt = a
        elif name == "CALLR":
            self.push(nxt)
            nxt = self.u32(r[a])
        elif name == "RET":
            nxt = self.pop()

        # ---- code is writable -------------------------------------------
        elif name == "CROSSR":
            r[a] = int.from_bytes(bytes(self.code[b:b + 4]), "little")
        elif name == "SMCW":
            for k in range(4):
                self.code[(b + k) % len(self.code)] = \
                    (self.u32(r[a]) >> (8 * k)) & 0xFF
        elif name == "SMCR":
            r[a] = int.from_bytes(bytes(self.code[b:b + 4]), "little")
        elif name == "SMXX":
            for k in range(4):
                idx = (b + k) % len(self.code)
                self.code[idx] ^= (self.u32(r[a]) >> (8 * k)) & 0xFF
        elif name == "PROBE":
            r[a] = self.u32(r[a] ^
                            int.from_bytes(bytes(self.code[b:b + 4]), "little"))

        # ---- output ------------------------------------------------------
        elif name == "EMITB":
            d[(OUT + self.out) % DATA_SIZE] = self.u32(r[a]) & 0xFF
            self.out += 1
        elif name == "EMITW":
            for k in range(4):
                d[(OUT + self.out) % DATA_SIZE] = \
                    (self.u32(r[a]) >> (8 * k)) & 0xFF
                self.out += 1
        else:
            self.halt = True

        self.pc = nxt

    def outputs(self, n=32):
        return bytes(self.data[OUT:OUT + n])


def main(argv):
    """model_vm.py <program.json> [profile] -- run the shipped programs."""
    import json
    with open(argv[1], "r") as fh:
        prog = json.load(fh)
    pool = [int(x) for x in prog["pool"]]
    opb = pool[:len(ISA)]
    image = bytes.fromhex(prog["plain"])
    for name, entry in prog["profiles"].items():
        if len(argv) > 2 and argv[2] != name:
            continue
        vm = Vm(image, opb, entry=entry)
        steps = vm.run()
        print("%s steps=%d out=%s" % (name, steps, vm.outputs().hex()))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv))
