#!/usr/bin/env python3
r"""vm_spec.py -- single source of truth for the Stage 1 custom VM (Phase 2).

INTERNAL build-time tool. NOT shipped to solvers.

This file owns:
  * the ISA table (mnemonic, operand form, per-build flexibility)
  * the per-build randomized opcode mapping (seeded RNG; the seed value lives
    in DEFAULT_SEED below and is recorded in logs/PHASE_2_LOG.md only)
  * the assembler used to emit the embedded bytecode programs
  * generation of vm_tables.h / vm_program.h / vm_layout.json

Usage:
    python3 vm_spec.py              # regenerate the headers (deterministic)
    python3 vm_spec.py --listing    # also write disassembly listings

The VM itself (vm.c) and the independent Python model (model_vm.py) both read
the generated artifacts, so the ISA has exactly one author (this file).
"""

import json
import pathlib
import random
import sys

# --- the per-build opcode-mapping seed (INTERNAL: logs/PHASE_2_LOG.md only) ---
DEFAULT_SEED = 0xCA4705E1

CODE_SIZE = 1024
CODE_MASK = CODE_SIZE - 1
NREG = 12
STACK_SIZE = 256
DATA_SIZE = 64

# operand-form ids (encoded in kOpForm, consumed by the data-driven decoder)
FORM_ORDER = [
    "none",   # 0
    "i8",     # 1
    "i16",    # 2
    "i32",    # 3
    "i64",    # 4
    "r",      # 5
    "rr",     # 6
    "r3",     # 7
    "ri8",    # 8
    "ri32",   # 9
    "i32r",   # 10  (irregular: immediate BEFORE the register)
    "ri64",   # 11
    "rel8",   # 12
    "rel16",  # 13
    "rrel16", # 14  (register + relative operand, for LOOP)
    "a8",     # 15
]

# forms whose 16/32-bit operands honour the per-op endianness bit
ENDIAN16_FORMS = {"i16", "rel16", "rrel16"}
ENDIAN32_FORMS = {"i32", "i32r", "ri32"}

# ---- the ISA ---------------------------------------------------------------
# (mnemonic, form, alternative forms the build seed may pick instead)
ISA = [
    # padding / no-op family: distinct encodings that consume odd-width bytes
    ("NOP",     "none",  None),
    ("HALT",    "none",  None),
    ("NOPA",    "i8",    None),
    ("NOPB",    "i16",   None),
    ("ENC",     "r",     None),
    ("ENCS",    "rr",    None),
    # data movement
    ("MOV",     "rr",    None),
    ("MOVI8",   "ri8",   None),
    ("MOVI32",  "ri32",  ("i32r",)),
    ("MOVI64",  "ri64",  None),
    ("XCHG",    "rr",    None),
    ("MOVM",    "r3",    None),
    ("MOVL",    "r3",    None),
    ("MOVB",    "r3",    None),
    ("STOREB",  "r3",    None),
    # code space -- the self-modifying family
    ("CLOAD",   "rr",    None),
    ("CSTORE",  "rr",    None),
    ("CXOR",    "rr",    None),
    ("CADD",    "ri8",   None),
    ("CREAD",   "r",     None),
    ("SKIPC",   "i8",    None),
    # arithmetic / logic
    ("ADD",     "rr",    None),
    ("ADDI",    "ri32",  ("i32r",)),
    ("SUB",     "rr",    None),
    ("SUBI",    "ri32",  ("i32r",)),
    ("MUL",     "rr",    None),
    ("MULI",    "ri32",  ("i32r",)),
    ("UMULH",   "rr",    None),
    ("DIV",     "rr",    None),
    ("MOD",     "rr",    None),
    ("AND",     "rr",    None),
    ("ANDI",    "ri32",  ("i32r",)),
    ("OR",      "rr",    None),
    ("ORI",     "ri32",  ("i32r",)),
    ("XOR",     "rr",    None),
    ("XORI",    "ri32",  ("i32r",)),
    ("SHL",     "rr",    None),
    ("SHLI",    "ri8",   None),
    ("SHR",     "rr",    None),
    ("SHRI",    "ri8",   None),
    ("SAR",     "rr",    None),
    ("ROTL",    "rr",    None),
    ("ROTLI",   "ri8",   None),
    ("ROTR",    "rr",    None),
    ("NOT",     "r",     None),
    ("NEG",     "r",     None),
    ("INC",     "r",     None),
    ("DEC",     "r",     None),
    # wide / modular (the modexp workhorses)
    ("MULMOD",  "r3",    None),
    ("ADDMM",   "r3",    None),
    ("SUBMM",   "r3",    None),
    ("POWM",    "r3",    None),   # never called by the embedded program (bait)
    # compare / select
    ("CMP",     "rr",    None),
    ("CMPI",    "ri32",  ("i32r",)),
    ("TEST",    "rr",    None),
    ("SEL",     "r3",    None),
    # ledger (accumulator) family
    ("ACC",     "r",     None),
    ("ACCC",    "r",     None),
    ("ACRM",    "r",     None),
    ("ACCS",    "r",     None),
    # control flow
    ("JMP",     "rel16", None),
    ("JMP8",    "rel8",  None),
    ("JMPR",    "r",     None),
    ("JZ",      "rel16", None),
    ("JNZ",     "rel16", None),
    ("JL",      "rel16", None),
    ("JGE",     "rel16", None),
    ("JGT",     "rel16", None),
    ("JLE",     "rel16", None),
    ("JC",      "rel16", None),
    ("JNC",     "rel16", None),
    ("JOV",     "rel16", None),
    ("CALL",    "rel16", None),
    ("CALLR",   "r",     None),
    ("RET",     "none",  None),
    ("LOOP",    "rrel16",None),
    # stack
    ("PUSH",    "r",     None),
    ("POP",     "r",     None),
    ("PUSHI",   "i32",   None),
    ("DUP",     "none",  None),
    ("SWAP",    "none",  None),
    ("PICK",    "r",     None),
    ("DROP",    "none",  None),
    # oblique: anti-static-analysis noise surfaces
    ("OPAQUE",  "none",  None),
    ("POKE",    "r",     None),
    ("PEEK",    "r",     None),
]

assert 60 <= len(ISA) <= 90, "opcode count outside the spec's 60..90 band: %d" % len(ISA)
assert len({m for m, _, _ in ISA}) == len(ISA), "duplicate mnemonic"


class Ref(str):
    """Marks a label reference inside an assembler operand list."""
    def __new__(cls, name):
        return super().__new__(cls, name)


def build_tables(seed=DEFAULT_SEED):
    """Deterministically derive the per-build mapping from the seed."""
    rng = random.Random(seed)

    op = {}
    for idx, (name, form, alts) in enumerate(ISA):
        flex = list(alts) if alts else [form]
        chosen = rng.choice(flex)

        if chosen in ENDIAN16_FORMS or chosen in ENDIAN32_FORMS:
            endian = rng.randrange(2)          # 0 = little, 1 = big
        else:
            endian = 0

        op[name] = {"index": idx, "form": chosen, "endian": endian}

    # Distinct opcode bytes drawn from the FULL 0..255 space, so invalid bytes
    # are scattered and instruction boundaries are not guessable from a
    # "byte >= opcode_count" heuristic.
    byte_pool = list(range(256))
    rng.shuffle(byte_pool)
    for name, info in op.items():
        info["byte"] = byte_pool[info["index"]]

    return {"seed": seed, "ops": op}

FORM_SIZE = {
    "none": 0, "i8": 1, "i16": 2, "i32": 4, "i64": 8, "r": 1, "rr": 1,
    "r3": 3, "ri8": 2, "ri32": 5, "i32r": 5, "ri64": 9, "rel8": 1,
    "rel16": 2, "rrel16": 3, "a8": 1,
}


def enc16(v, be):
    v &= 0xFFFF
    return [v >> 8, v & 0xFF] if be else [v & 0xFF, v >> 8]


def enc32(v, be):
    v &= 0xFFFFFFFF
    b = [v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF]
    return b[::-1] if be else b


def enc64(v):
    v &= 0xFFFFFFFFFFFFFFFF
    return [(v >> (8 * i)) & 0xFF for i in range(8)]


class Asm:
    """Tiny two-pass assembler that honours the per-build form table."""

    def __init__(self, tables, base=0):
        self.ops = tables["ops"]
        self.base = base
        self.code = bytearray()
        self.labels = {}
        self.fixups = []      # (offset, kind, label, insn_end, be)
        self.listing = []     # (addr, mnemonic, form, args, length)

    # -- emission ----------------------------------------------------------
    def label(self, name):
        if name in self.labels:
            raise ValueError("duplicate label %s" % name)
        self.labels[name] = self.base + len(self.code)

    def raw(self, *bs):
        for b in bs:
            self.code.append(b & 0xFF)

    def data(self, blob):
        self.code.extend(bytes(blob))

    def emit(self, mnem, *args):
        info = self.ops[mnem]
        form, be = info["form"], info["endian"]
        length = 1 + FORM_SIZE[form]
        start = self.base + len(self.code)
        insn_end = start + length
        self.code.append(info["byte"])
        self._encode(form, be, args, insn_end)
        self.listing.append((start, mnem, form, args, length))
        return start

    # -- operand encoding --------------------------------------------------
    def _encode(self, form, be, args, insn_end):
        a = list(args)

        if form == "none":
            return
        if form in ("i8", "a8"):
            self.raw(int(a[0]))
        elif form == "i16":
            self.raw(*enc16(int(a[0]), be))
        elif form in ("i32", "i32r", "ri32"):
            # source operand order is (reg, imm) for reg forms and (imm,) for
            # the bare immediate form; the encoded order for "i32r" is the
            # irregular imm-then-reg layout.
            if form == "i32":
                reg, v = None, a[0]
            else:
                reg, v = int(a[0]), a[1]
            if form == "ri32":
                self.raw(reg)
            if isinstance(v, Ref):
                self.fixups.append((len(self.code), "abs32", str(v), insn_end, be))
                self.raw(0, 0, 0, 0)
            else:
                self.raw(*enc32(int(v), be))
            if form == "i32r":
                self.raw(reg)
        elif form == "i64":
            self.raw(*enc64(int(a[0])))
        elif form == "r":
            self.raw(int(a[0]))
        elif form == "rr":
            self.raw((int(a[0]) & 0xF) | ((int(a[1]) & 0xF) << 4))
        elif form == "r3":
            self.raw(int(a[0]), int(a[1]), int(a[2]))
        elif form == "ri8":
            self.raw(int(a[0]), int(a[1]) & 0xFF)
        elif form == "ri64":
            self.raw(int(a[0]))
            v = a[1]
            if isinstance(v, Ref):
                self.fixups.append((len(self.code), "abs64", str(v), insn_end, False))
                self.raw(*([0] * 8))
            else:
                self.raw(*enc64(int(v)))
        elif form == "rel8":
            v = a[0]
            if isinstance(v, Ref):
                self.fixups.append((len(self.code), "rel8", str(v), insn_end, False))
                self.raw(0)
            else:
                self.raw(int(v) & 0xFF)
        elif form in ("rel16", "rrel16"):
            if form == "rrel16":
                self.raw(int(a[0]))
                v = a[1]
            else:
                v = a[0]
            if isinstance(v, Ref):
                self.fixups.append((len(self.code), "rel16", str(v), insn_end, be))
                self.raw(0, 0)
            else:
                self.raw(*enc16(int(v), be))
        else:
            raise ValueError("unhandled form " + form)

    # -- resolution --------------------------------------------------------
    def resolve(self):
        for off, kind, label, insn_end, be in self.fixups:
            if label not in self.labels:
                raise ValueError("unknown label %s" % label)
            target = self.labels[label]
            if kind == "abs32":
                self.code[off:off + 4] = bytes(enc32(target, be))
            elif kind == "abs64":
                self.code[off:off + 8] = bytes(enc64(target))
            elif kind == "rel16":
                rel = target - insn_end
                if not -32768 <= rel <= 32767:
                    raise ValueError("rel16 out of range for %s" % label)
                self.code[off:off + 2] = bytes(enc16(rel & 0xFFFF, be))
            elif kind == "rel8":
                rel = target - insn_end
                if not -128 <= rel <= 127:
                    raise ValueError("rel8 out of range for %s" % label)
                self.code[off] = rel & 0xFF
        return bytes(self.code)


# ---- embedded program constants (all recorded in logs/PHASE_2_LOG.md) ------
ACC_A     = 0x9E3779B97F4A7C15   # ACC fold additive
ACC_B     = 0xC2B2AE3D27D4EB4F   # ACCC fold additive
ACC_C     = 0xBF58476D1CE4E5B9   # ACRM fold multiplier
ACC_D     = 0x94D049BB133111EB   # ACCS fold multiplier
MIX_A     = 0xD6E8FEB86659FD93   # exponent fold xorshift
DETECT_SEED  = 0xDEADBEEFCAFEF00D  # ledger perturbation on detection
DETECT_SEED2 = 0x5EEDDEADBEEF1234  # second perturbation on detection
TWIST_K   = 0x2545F4914F6CDD1D   # per-round xor perturbation step
NOISE_A   = 0x243F6A8885A308D3   # noise loop seeds (inert)
NOISE_B   = 0x13198A2E03707344
MASK63    = 0x7FFFFFFFFFFFFFFF
MASK62    = 0x3FFFFFFFFFFFFFFF
FORCE_HI  = 0x4000000000000001   # forces modulus bit62 + oddness
BASE_HI   = 0x2000000000000001   # forces base bit61 + oddness
ROUNDS    = 62                   # exponent bit slots (coprime-stride order)
MIX_ROUNDS= 8
NOISE_ITERS   = 0x0180           # inert survey-noise loop (identical in both
                                 # profiles: it feeds no key register)
MUT_PASSES    = 0x000C           # self-modifying pad sweep (same reasoning)
HN_ITERS      = 0x0180           # profile-1-only hardening loop
DATA_BLK   = bytes([0x69, 0x3f, 0xd1, 0x07, 0xbb, 0x52, 0x2c, 0xe4])


def build_program(tables, profile):
    """Assemble the embedded Stage 1 bytecode.

    profile 0 = standard trace, profile 1 = escalated/hardened trace.
    Both MUST derive the identical key (profile 1 only adds inert work that
    touches registers excluded from the key packing).
    """
    a = Asm(tables)

    # --- phase 0: detection gate -----------------------------------------
    # The host seeds R10: 0 = clean run, 1 = debugger/automation detected.
    # A detected run perturbs the ledger through fixed corruption seeds and
    # then rejoins the identical trace, so it still yields a well-formed but
    # WRONG key (same shape, same length) -- "silently corrupted constant".
    a.emit("ANDI", 10, 1)
    a.emit("JNZ", Ref("dbg_path"))
    a.emit("JMP", Ref("eng_start"))
    a.label("dbg_path")
    a.emit("MOVI64", 8, DETECT_SEED)
    a.emit("ACC", 8)
    a.emit("ACRM", 8)
    a.emit("ACCS", 8)
    a.emit("MOVI64", 8, DETECT_SEED2)
    a.emit("ANDI", 8, 0x3FFFFFFF)
    a.emit("ACC", 8)
    a.emit("JMP", Ref("eng_start"))
    a.label("eng_start")
    a.emit("MOVI8", 10, 0)

    # --- phase A: idiomatic dec/compare/jump bait (inert, R6 only) --------
    a.emit("MOVI32", 6, 12)
    a.label("bait_a")
    a.emit("DEC", 6)
    a.emit("JNZ", Ref("bait_a"))
    a.emit("CMPI", 6, 0)
    a.emit("JZ", Ref("bait_done"))
    a.emit("MOVI32", 6, 0x11111111)      # dead: the JZ above is always taken
    a.emit("JMP", Ref("bait_done"))
    a.label("bait_done")

    # --- phase B: seed the ledger (R7) from raw code bytes ---------------
    a.emit("MOVI64", 8, Ref("mut_echo"))
    a.emit("CLOAD", 4, 8)
    a.emit("ACC", 4)
    a.emit("MOVI64", 8, Ref("bait_a"))
    a.emit("ACCC", 8)                    # folds code[bait_a] directly

    # --- phase C: CREAD sweep -- bytes consumed as data, never decoded ----
    for b in DATA_BLK:
        a.emit("CREAD", 4)
        a.raw(b)
        a.emit("ACC", 4)

    # --- phase D: indirect dispatch (jump from a register value) ---------
    a.emit("MOVI64", 8, Ref("dead_land"))
    a.emit("MOVI64", 9, Ref("disp_ok"))
    a.emit("CMPI", 10, 0)                # R10 == 0, so this JZ is taken
    a.emit("JZ", Ref("via_reg"))
    a.emit("JMPR", 8)                    # unreachable bait landing
    a.label("via_reg")
    a.emit("JMPR", 9)
    a.label("dead_land")                 # bait block: dec/compare loop, rejoins
    a.emit("MOVI32", 8, 0x200)
    a.label("dead_loop")
    a.emit("DEC", 8)
    a.emit("JNZ", Ref("dead_loop"))
    a.emit("JMP", Ref("disp_ok"))
    a.label("disp_ok")

    # --- phase E: indirect call + return ---------------------------------
    a.emit("MOVI64", 8, Ref("survey_sub"))
    a.emit("CALLR", 8)
    a.emit("JMP", Ref("seed_done"))
    a.label("survey_sub")
    a.emit("MOVI64", 10, Ref("sub_data"))
    a.emit("CLOAD", 11, 10)
    a.emit("ACCS", 11)
    a.emit("CLOAD", 11, 10)
    a.emit("ACC", 11)
    a.emit("MOVI64", 11, ACC_A)
    a.emit("PUSH", 11)
    a.emit("POP", 10)
    a.emit("ACC", 10)
    a.emit("RET")
    a.label("seed_done")

    # --- phase F: self-modify code bytes, then fold them into the ledger --
    a.emit("MOVI64", 8, Ref("mut_echo"))
    a.emit("MOVI8", 9, 0x5A)
    a.emit("CSTORE", 8, 9)
    a.emit("MOVI8", 9, 0xA5)
    a.emit("CXOR", 8, 9)
    a.emit("CADD", 8, 0x01)
    a.emit("MOVI8", 9, 0x37)
    a.emit("CXOR", 8, 9)
    a.emit("CLOAD", 4, 8)
    a.emit("ACC", 4)
    a.emit("MOVI64", 8, Ref("nop_slot"))
    a.emit("INC", 8)                     # target the operand byte, not opcode
    a.emit("MOVI8", 9, 0x11)
    a.emit("CXOR", 8, 9)                 # pre-mutation: 0x00 -> 0x11
    a.emit("CLOAD", 4, 8)
    a.emit("ACCS", 4)
    return _program_tail(a, tables, profile)


def _program_tail(a, tables, profile):
    # --- phase G: derive modulus / base / exponent / stride / index -------
    a.emit("MOV", 1, 7)                          # R1 = ledger
    a.emit("MOVI64", 8, FORCE_HI)
    a.emit("OR", 1, 8)
    a.emit("MOVI64", 9, MASK63)
    a.emit("AND", 1, 9)                          # R1 = modulus
    a.emit("MOV", 2, 7)
    a.emit("ROTLI", 2, 29)
    a.emit("MOVI64", 8, ACC_A)
    a.emit("XOR", 2, 8)
    a.emit("MOVI64", 8, BASE_HI)
    a.emit("OR", 2, 8)
    a.emit("AND", 2, 9)
    a.emit("MOD", 2, 1)                          # R2 = base
    a.emit("CMPI", 2, 3)
    a.emit("JGE", Ref("base_ok"))
    a.emit("MOVI8", 2, 3)
    a.label("base_ok")
    a.emit("MOV", 3, 7)
    a.emit("ROTLI", 3, 47)
    a.emit("MOVI64", 8, MIX_A)
    a.emit("XOR", 3, 8)
    a.emit("MOVI64", 8, MASK62)
    a.emit("AND", 3, 8)
    a.emit("ORI", 3, 1)                          # R3 = exponent (odd)
    a.emit("MOV", 4, 7)
    a.emit("SHRI", 4, 8)
    a.emit("MOVI8", 8, 30)
    a.emit("MOD", 4, 8)
    a.emit("SHLI", 4, 1)
    a.emit("INC", 4)                             # odd stride
    a.emit("CMPI", 4, 31)                        # 31 shares a factor with 62
    a.emit("JNZ", Ref("stride_ok"))
    a.emit("MOVI8", 4, 33)
    a.label("stride_ok")
    a.emit("MOV", 5, 7)
    a.emit("SHRI", 5, 16)
    a.emit("MOVI8", 8, 62)
    a.emit("MOD", 5, 8)                          # R5 = start bit index

    # --- phase H: permuted-bit-order modexp with an xor twist -------------
    a.emit("MOVI8", 6, 1)                        # res = 1
    a.emit("MOVI8", 0, ROUNDS)
    a.emit("MOVI8", 11, 62)                      # index wrap constant
    a.emit("MOVI64", 9, TWIST_K)
    a.label("rnd")
    a.emit("MULMOD", 6, 6, 1)                    # res = res*res % m
    a.emit("MOV", 8, 3)
    a.emit("SHR", 8, 5)
    a.emit("ANDI", 8, 1)
    a.emit("JZ", Ref("rskip"))
    a.emit("MULMOD", 6, 6, 2)                    # res = res*base % m
    a.emit("MOV", 10, 0)
    a.emit("MUL", 10, 9)
    a.emit("XOR", 6, 10)                         # the irregular twist
    a.emit("MOD", 6, 1)
    a.label("rskip")
    a.emit("ADD", 5, 4)
    a.emit("MOD", 5, 11)
    a.emit("DEC", 0)
    a.emit("JNZ", Ref("rnd"))

    # --- phase I: final mixing rounds ------------------------------------
    a.emit("MOVI8", 0, MIX_ROUNDS)
    a.label("mix")
    a.emit("MOV", 8, 7)
    a.emit("ROTL", 8, 0)
    a.emit("ORI", 8, 1)
    a.emit("MULMOD", 6, 8, 1)
    a.emit("DEC", 0)
    a.emit("JNZ", Ref("mix"))

    # --- phase J: inert survey noise (dummy registers only) --------------
    a.emit("MOVI64", 10, NOISE_A)
    a.emit("MOVI64", 11, NOISE_B)
    a.emit("MOVI32", 0, NOISE_ITERS)
    a.label("noise")
    a.emit("ROTLI", 10, 3)
    a.emit("MUL", 10, 11)
    a.emit("XOR", 10, 0)
    a.emit("POKE", 10)
    a.emit("PEEK", 11)
    a.emit("ADD", 11, 10)
    a.emit("OPAQUE")
    a.emit("LOOP", 0, Ref("noise"))

    # --- phase K: self-modifying sweep over pad0 -------------------------
    a.emit("MOVI8", 0, MUT_PASSES)
    a.label("mut")
    a.emit("MOVI64", 8, Ref("pad0"))
    a.emit("ADD", 8, 0)
    a.emit("MOV", 10, 0)
    a.emit("ADDI", 10, 0x9D)
    a.emit("CXOR", 8, 10)
    a.emit("CLOAD", 10, 8)
    a.emit("ACC", 10)                            # mutated byte -> ledger
    a.emit("DEC", 0)
    a.emit("JNZ", Ref("mut"))

    # --- phase L (profile 1 only): escalated hardening noise -------------
    if profile == 1:
        a.emit("MOVI64", 9, NOISE_A)
        a.emit("MOVI32", 0, HN_ITERS)
        a.label("hnoise")
        a.emit("ROTLI", 9, 7)
        a.emit("MUL", 9, 11)
        a.emit("POKE", 9)
        a.emit("PEEK", 10)
        a.emit("XOR", 9, 10)
        a.emit("OPAQUE")
        a.emit("OPAQUE")
        a.emit("LOOP", 0, Ref("hnoise"))
        a.emit("MOVI8", 0, MUT_PASSES)
        a.label("hmut")
        a.emit("MOVI64", 8, Ref("pad1"))
        a.emit("ADD", 8, 0)
        a.emit("MOV", 10, 0)
        a.emit("ADDI", 10, 0x3B)
        a.emit("CXOR", 8, 10)
        a.emit("CLOAD", 10, 8)
        a.emit("XOR", 11, 10)                    # dummy fold only
        a.emit("DEC", 0)
        a.emit("JNZ", Ref("hmut"))

    # --- phase M: mutate an EXECUTED instruction's operand ---------------
    a.emit("MOVI64", 8, Ref("nop_slot"))
    a.emit("INC", 8)
    a.emit("MOVI8", 10, 0x63)
    a.emit("CXOR", 8, 10)
    a.label("nop_slot")
    a.emit("NOPA", 0x00)
    a.emit("CLOAD", 10, 8)
    a.emit("ACC", 10)                            # mutated operand -> ledger

    # --- phase N: canonical final ledger --------------------------------
    for r in (0, 8, 9, 10, 11):
        a.emit("MOVI8", r, 0)
    a.emit("HALT")

    # --- data regions (never executed; addressed only by label refs) -----
    a.label("mut_echo")
    a.data(bytes(i & 0xFF for i in range(16)))
    a.label("pad0")
    a.data(bytes((0x5A ^ (i * 3)) & 0xFF for i in range(16)))
    a.label("pad1")
    a.data(bytes((0xC3 - (i * 5)) & 0xFF for i in range(16)))
    a.label("sub_data")
    a.data(bytes([0x7E, 0x15, 0x91, 0x4B, 0x2D, 0xF0, 0x38, 0xA6]))

    return a.resolve(), a


def _hex_rows(blob, per=12):
    return ["    " + ", ".join("0x%02x" % b for b in blob[i:i + per]) + ","
            for i in range(0, len(blob), per)]


def emit_tables_header(tables, path):
    ops = tables["ops"]
    by_index = sorted(ops.items(), key=lambda kv: kv[1]["index"])

    L = []
    L.append("/* vm_tables.h -- GENERATED by vm_spec.py; do not edit by hand.")
    L.append(" *")
    L.append(" * Stage 1 custom VM: per-build randomized opcode mapping,")
    L.append(" * operand forms and operand endianness.")
    L.append(" * Build seed: 0x%08X (recorded in logs/PHASE_2_LOG.md only)." % tables["seed"])
    L.append(" */")
    L.append("#ifndef CARTO_VM_TABLES_H")
    L.append("#define CARTO_VM_TABLES_H")
    L.append("")
    L.append("#define VM_OP_COUNT %d" % len(ISA))
    L.append("#define VM_CODE_SIZE %d" % CODE_SIZE)
    L.append("#define VM_NREG %d" % NREG)
    L.append("#define VM_STACK_SIZE %d" % STACK_SIZE)
    L.append("#define VM_DATA_SIZE %d" % DATA_SIZE)
    L.append("#define VM_CODE_MASK (VM_CODE_SIZE - 1)")
    L.append("")
    for i, fname in enumerate(FORM_ORDER):
        L.append("#define VM_F_%-7s %d" % (fname.upper(), i))
    L.append("")
    L.append("/* logical opcodes (enum order == assembler order) */")
    L.append("enum {")
    for name, _ in by_index:
        L.append("    VM_OP_%s = %d," % (name, ops[name]["index"]))
    L.append("};")
    L.append("")
    L.append("/* encoded opcode byte for each logical opcode */")
    L.append("static const unsigned char kOpByte[VM_OP_COUNT] = {")
    L.extend(_hex_rows(bytes(ops[n]["byte"] for n, _ in by_index)))
    L.append("};")
    L.append("")
    L.append("/* operand form id for each logical opcode */")
    L.append("static const unsigned char kOpForm[VM_OP_COUNT] = {")
    L.extend(_hex_rows(bytes(FORM_ORDER.index(ops[n]["form"]) for n, _ in by_index)))
    L.append("};")
    L.append("")
    L.append("/* 0 = little-endian operands, 1 = big-endian (per logical opcode) */")
    L.append("static const unsigned char kOpEndian[VM_OP_COUNT] = {")
    L.extend(_hex_rows(bytes(ops[n]["endian"] for n, _ in by_index)))
    L.append("};")
    L.append("")
    L.append("#endif /* CARTO_VM_TABLES_H */")
    path.write_text("\n".join(L) + "\n", newline="\n")


def emit_program_header(prog0, prog1, path):
    L = []
    L.append("/* vm_program.h -- GENERATED by vm_spec.py; do not edit by hand.")
    L.append(" *")
    L.append(" * Embedded Stage 1 bytecode. No key material is compiled in here:")
    L.append(" * the real Stage 2 key material exists only after the trace runs.")
    L.append(" * Internal listing: logs/PHASE_2_LOG.md + listings/.")
    L.append(" */")
    L.append("#ifndef CARTO_VM_PROGRAM_H")
    L.append("#define CARTO_VM_PROGRAM_H")
    L.append("")
    L.append("#define VM_PROG0_LEN %d" % len(prog0))
    L.append("static const unsigned char kProgram0[VM_PROG0_LEN] = {")
    L.extend(_hex_rows(prog0))
    L.append("};")
    L.append("")
    L.append("#define VM_PROG1_LEN %d" % len(prog1))
    L.append("static const unsigned char kProgram1[VM_PROG1_LEN] = {")
    L.extend(_hex_rows(prog1))
    L.append("};")
    L.append("")
    L.append("#endif /* CARTO_VM_PROGRAM_H */")
    path.write_text("\n".join(L) + "\n", newline="\n")


def _render_listing(asm):
    out = []
    for addr, mnem, form, args, length in asm.listing:
        shown = ", ".join(("%s" % a) if not isinstance(a, Ref) else ("->%s" % a)
                          for a in args)
        out.append("%04x  %-8s %-7s %s" % (addr, mnem, form, shown))
    return out


def main(argv):
    out = pathlib.Path(__file__).resolve().parent
    tables = build_tables(DEFAULT_SEED)
    prog0, asm0 = build_program(tables, 0)
    prog1, asm1 = build_program(tables, 1)

    if len(prog0) > CODE_SIZE or len(prog1) > CODE_SIZE:
        raise SystemExit("program exceeds VM_CODE_SIZE")

    emit_tables_header(tables, out / "vm_tables.h")
    emit_program_header(prog0, prog1, out / "vm_program.h")

    ops_sorted = sorted(tables["ops"].items(), key=lambda kv: kv[1]["index"])
    layout = {
        "seed": tables["seed"],
        "op_count": len(ISA),
        "code_size": CODE_SIZE,
        "nreg": NREG,
        "stack_size": STACK_SIZE,
        "data_size": DATA_SIZE,
        "forms": FORM_ORDER,
        "ops": [{"name": n, "index": i["index"], "byte": i["byte"],
                 "form": i["form"], "endian": i["endian"]} for n, i in ops_sorted],
        "programs": {
            "0": {"hex": prog0.hex()},
            "1": {"hex": prog1.hex()},
        },
    }
    (out / "vm_layout.json").write_text(json.dumps(layout, indent=1) + "\n",
                                        newline="\n")

    if "--listing" in argv:
        ldir = out / "listings"
        ldir.mkdir(exist_ok=True)
        for idx, asm in ((0, asm0), (1, asm1)):
            (ldir / ("vm_profile%d.txt" % idx)).write_text(
                "\n".join(_render_listing(asm)) + "\n", newline="\n")

    print("seed=0x%08X ops=%d prog0=%d bytes prog1=%d bytes"
          % (tables["seed"], len(ISA), len(prog0), len(prog1)))
    print("wrote vm_tables.h, vm_program.h, vm_layout.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))