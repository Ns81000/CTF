#!/usr/bin/env python3
"""MERU-1 two-pass assembler.  Deterministic: same source -> same ROM bytes.

Syntax:
  label:            before an instruction or alone on a line
  .org $8000        set origin (default $8000)
  .equ NAME, expr   define constant
  .byte 1, $FF, sym / .word nnnn, sym / .ascii "text"
  LDA #$2A / LDA $10 / LDA <$10 / LDA $1234 / LDA $1234,X / LDA ($10),Y
  LDHL #$1234       16-bit immediate loads
  BNE label         relative branches;  JMP (ptr)  indirect
Numbers: $hex, 0xhex, %bin, decimal.  ';' starts a comment.
zp/abs: '<expr' forces zero page, '>' forces absolute, bare numbers < 256
use zero page, bare numbers >= 256 and bare symbols use absolute.
MMIO names from opcodes.MMIO are pre-defined at $F000+offset.
"""
import re
import sys

from opcodes import BY_MNEM, MMIO, RESET_PC

BRANCHES = ("BRA", "BNE", "BEQ", "BCC", "BCS", "BMI", "BPL", "BVC", "BVS")

def parse_num(tok, syms):
    tok = tok.strip()
    if tok.startswith("$"):
        return int(tok[1:], 16)
    if tok.startswith("0x") or tok.startswith("0X"):
        return int(tok, 16)
    if tok.startswith("%"):
        return int(tok[1:], 2)
    if re.fullmatch(r"[0-9]+", tok):
        return int(tok)
    if tok in syms:
        return syms[tok]
    raise SystemExit("asm: unknown symbol/number: %r" % tok)

def split_operands(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return [x.strip() for x in out]

class Line:
    def __init__(self, mnem, arg, addr, size, kind=None, lineno=0):
        self.mnem, self.arg, self.addr, self.size = mnem, arg, addr, size
        self.kind, self.lineno = kind, lineno

def operand_kind(mnem, arg):
    a = arg.strip()
    if a == "":
        return ("none", None, None)
    if a.startswith("#"):
        return ("imm16" if mnem in ("LDHL", "LDDE", "LDBC") else "imm",
                a[1:].strip(), None)
    m = re.fullmatch(r"\((.+)\),([Yy])", a)
    if m:
        return ("indy", m.group(1), None)
    m = re.fullmatch(r"\((.+)\)", a)
    if m:
        return ("ind", m.group(1), None)
    m = re.fullmatch(r"(.+),([XxYy])", a)
    if m:
        expr, reg = m.group(1).strip(), m.group(2).upper()
        force = None
        if expr.startswith("<"):
            force, expr = "zp", expr[1:]
        elif expr.startswith(">"):
            force, expr = "abs", expr[1:]
        if reg == "X":
            if force == "zp":
                return ("zpx", expr, force)
            if force == "abs":
                return ("absx", expr, force)
            return ("anyx", expr, None)
        return ("absy", expr, None)
    force = None
    expr = a
    if a.startswith("<"):
        force, expr = "zp", a[1:]
    elif a.startswith(">"):
        force, expr = "abs", a[1:]
    return ("any", expr, force)

def pick_kind(mnem, kind, expr, force, syms):
    if kind in ("any", "anyx"):
        zp_ok = kind == "any"
        v = None
        try:
            v = parse_num(expr, syms)
        except SystemExit:
            v = None
        if force == "zp":
            kind = "zp" if zp_ok else "zpx"
        elif force == "abs":
            kind = "abs" if zp_ok else "absx"
        elif v is not None and v < 0x100:
            kind = "zp" if zp_ok else "zpx"
        else:
            kind = "abs" if zp_ok else "absx"
    if kind == "zp" and kind not in BY_MNEM.get(mnem, {}) \
            and "abs" in BY_MNEM.get(mnem, {}):
        kind = "abs"
    if kind not in BY_MNEM.get(mnem, {}):
        raise SystemExit("asm: %s has no %s addressing" % (mnem, kind))
    return kind

SIZES = {"none": 1, "imm": 2, "zp": 2, "zpx": 2, "indy": 2, "rel": 2,
         "abs": 3, "absx": 3, "absy": 3, "ind": 3, "imm16": 3}

def assemble(src, defines=None):
    syms = {}
    for k in MMIO:
        syms[k] = 0xF000 + MMIO[k]
    if defines:
        syms.update(defines)
    raw = []
    for ln, text in enumerate(src.splitlines(), 1):
        text = text.split(";", 1)[0].rstrip()
        if text.strip():
            raw.append((ln, text.strip()))
    lines = []
    pc = RESET_PC
    for ln, text in raw:                       # pass 1: labels + sizes
        while True:
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):", text)
            if not m:
                break
            syms[m.group(1)] = pc
            text = text[m.end():].strip()
        if not text:
            continue
        if text.startswith("."):
            parts = text.split(None, 1)
            d = parts[0]
            arg = parts[1] if len(parts) > 1 else ""
            if d == ".org":
                pc = parse_num(arg, syms)
            elif d == ".equ":
                name, expr = arg.split(",", 1)
                syms[name.strip()] = parse_num(expr, syms)
            elif d == ".byte":
                n = len(split_operands(arg))
                lines.append(Line(".byte", arg, pc, n, lineno=ln))
                pc += n
            elif d == ".word":
                n = 2 * len(split_operands(arg))
                lines.append(Line(".word", arg, pc, n, lineno=ln))
                pc += n
            elif d == ".ascii":
                m = re.fullmatch(r'"(.*)"', arg)
                if not m:
                    raise SystemExit("asm line %d: bad .ascii" % ln)
                body = m.group(1).encode().decode("unicode_escape")
                lines.append(Line(".ascii", body, pc, len(body), lineno=ln))
                pc += len(body)
            else:
                raise SystemExit("asm line %d: bad directive %r" % (ln, d))
            continue
        parts = text.split(None, 1)
        mnem = parts[0].upper()
        arg = parts[1] if len(parts) > 1 else ""
        if mnem not in BY_MNEM:
            raise SystemExit("asm line %d: unknown mnemonic %r" % (ln, mnem))
        if mnem in BRANCHES:
            kind, expr, force = "rel", arg.strip(), None
        else:
            kind, expr, force = operand_kind(mnem, arg)
        kind = pick_kind(mnem, kind, expr, force, syms)
        lines.append(Line(mnem, expr, pc, SIZES[kind], kind=kind, lineno=ln))
        pc += SIZES[kind]
    if pc > RESET_PC + 0x7000:
        raise SystemExit("asm: ROM image exceeds $7000 bytes")

    out = {}                                   # pass 2: emit bytes
    for L in lines:
        a = L.addr
        if L.mnem == ".byte":
            vals = [parse_num(t, syms) for t in split_operands(L.arg)]
            for i, v in enumerate(vals):
                out[a + i] = v & 0xFF
        elif L.mnem == ".word":
            vals = [parse_num(t, syms) for t in split_operands(L.arg)]
            for i, v in enumerate(vals):
                out[a + 2 * i] = v & 0xFF
                out[a + 2 * i + 1] = (v >> 8) & 0xFF
        elif L.mnem == ".ascii":
            for i, ch in enumerate(L.arg):
                out[a + i] = ord(ch) & 0xFF
        else:
            out[a] = BY_MNEM[L.mnem][L.kind]
            if L.kind in ("imm", "zp", "zpx", "indy"):
                out[a + 1] = parse_num(L.arg, syms) & 0xFF
            elif L.kind == "rel":
                tgt = parse_num(L.arg, syms)
                off = tgt - (a + 2)
                if not -128 <= off <= 127:
                    raise SystemExit("asm line %d: branch out of range"
                                     % L.lineno)
                out[a + 1] = off & 0xFF
            elif L.kind in ("abs", "absx", "absy", "ind", "imm16"):
                v = parse_num(L.arg, syms)
                out[a + 1] = v & 0xFF
                out[a + 2] = (v >> 8) & 0xFF
    if not out:
        raise SystemExit("asm: empty ROM")
    lo, hi = min(out), max(out)
    image = bytearray(hi - lo + 1)
    for a, v in out.items():
        image[a - lo] = v
    return lo, bytes(image)

def main(argv):
    if len(argv) < 3:
        sys.stderr.write("usage: asm.py <src.asm> <out.rom> "
                         "[-DNAME=VALUE ...]\n")
        return 2
    defines = {}
    for a in argv[3:]:
        if a.startswith("-D"):
            kv = a[2:].split("=", 1)
            defines[kv[0]] = int(kv[1], 0)
    org, image = assemble(open(argv[1]).read(), defines)
    if org != RESET_PC:
        sys.stderr.write("asm: warning: origin $%04X != $8000\n" % org)
    with open(argv[2], "wb") as f:
        f.write(image)
    sys.stderr.write("asm: %s -> %s (%d bytes at $%04X)\n"
                     % (argv[1], argv[2], len(image), org))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))