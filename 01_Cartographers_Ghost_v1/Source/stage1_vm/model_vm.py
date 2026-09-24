#!/usr/bin/env python3
r"""model_vm.py -- INDEPENDENT Python model of the Stage 1 VM (Phase 2).

INTERNAL verification tool. NOT shipped to solvers.

This is a second implementation of the interpreter, written against the
documented ISA (see logs/PHASE_2_LOG.md) rather than against vm.c, so that the
C VM's final ledger can be cross-checked byte-exactly.  It reads the generated
vm_layout.json (opcode bytes / forms / endianness / program bytes).

Usage:
    python3 model_vm.py --profile 0 --detect 0
    python3 model_vm.py --selftest
"""

import argparse
import json
import pathlib
import sys

M64 = 0xFFFFFFFFFFFFFFFF

ACC_A = 0x9E3779B97F4A7C15
ACC_B = 0xC2B2AE3D27D4EB4F
ACC_C = 0xBF58476D1CE4E5B9
ACC_D = 0x94D049BB133111EB

# the four registers packed into the Stage 2 key material (order matters)
KEY_REGS = (6, 7, 1, 2)


def rotl(v, n):
    n &= 63
    v &= M64
    if n == 0:
        return v
    return ((v << n) | (v >> (64 - n))) & M64


def rotr(v, n):
    n &= 63
    v &= M64
    if n == 0:
        return v
    return ((v >> n) | (v << (64 - n))) & M64


class ModelVM:
    def __init__(self, layout, program_hex):
        self.L = layout
        self.code = bytearray(bytes.fromhex(program_hex))
        self.code.extend(b"\x00" * (layout["code_size"] - len(self.code)))
        self.op_by_byte = {}
        for o in layout["ops"]:
            self.op_by_byte[o["byte"]] = o
        self.nreg = layout["nreg"]
        self.mask = layout["code_size"] - 1

    # -- decode ------------------------------------------------------------
    def _rd16(self, ip, be):
        b = self.code[ip:ip + 2]
        return (b[0] << 8 | b[1]) if be else (b[1] << 8 | b[0])

    def _rd32(self, ip, be):
        return int.from_bytes(bytes(self.code[ip:ip + 4]),
                              "big" if be else "little")

    def _rd64(self, ip):
        return int.from_bytes(bytes(self.code[ip:ip + 8]), "little")

    def decode(self, ip, op):
        form = op["form"]
        be = bool(op["endian"])
        imm = 0
        rd = rs = rt = 0
        ln = 1
        if form == "none":
            pass
        elif form in ("i8", "a8"):
            imm = self.code[ip + 1]
            ln = 2
        elif form == "i16":
            imm = self._rd16(ip + 1, be)
            ln = 3
        elif form == "i32":
            imm = self._rd32(ip + 1, be)
            ln = 5
        elif form == "i64":
            imm = self._rd64(ip + 1)
            ln = 9
        elif form == "r":
            rd = self.code[ip + 1]
            ln = 2
        elif form == "rr":
            b = self.code[ip + 1]
            rd, rs = b & 0xF, b >> 4
            ln = 2
        elif form == "r3":
            rd, rs, rt = self.code[ip + 1], self.code[ip + 2], self.code[ip + 3]
            ln = 4
        elif form == "ri8":
            rd, imm = self.code[ip + 1], self.code[ip + 2]
            ln = 3
        elif form == "ri32":
            rd = self.code[ip + 1]
            imm = self._rd32(ip + 2, be)
            ln = 6
        elif form == "i32r":
            imm = self._rd32(ip + 1, be)
            rd = self.code[ip + 5]
            ln = 6
        elif form == "ri64":
            rd = self.code[ip + 1]
            imm = self._rd64(ip + 2)
            ln = 10
        elif form == "rel8":
            imm = self.code[ip + 1]
            ln = 2
        elif form == "rel16":
            imm = self._rd16(ip + 1, be)
            ln = 3
        elif form == "rrel16":
            rd = self.code[ip + 1]
            imm = self._rd16(ip + 2, be)
            ln = 4
        else:
            raise ValueError("bad form " + form)
        return {"name": op["name"], "imm": imm, "rd": rd, "rs": rs, "rt": rt,
                "len": ln}

    # -- run ---------------------------------------------------------------
    def run(self, detect=0):
        R = [0] * self.nreg
        R[10] = detect & 1
        stack = []
        data = [0] * self.L["data_size"]
        z = s = c = 0
        port = 0
        ip = 0
        steps = 0
        fault = 0
        dmask = self.L["data_size"] - 1

        while True:
            if ip > self.mask:
                fault = 1
                break
            op = self.op_by_byte.get(self.code[ip])
            if op is None:
                fault = 1
                break
            ins = self.decode(ip, op)
            name, imm, rd, rs, rt = (ins["name"], ins["imm"], ins["rd"],
                                     ins["rs"], ins["rt"])
            end = ip + ins["len"]
            steps += 1

            if name in ("NOP", "NOPA", "NOPB", "ENC", "ENCS", "OPAQUE"):
                pass
            elif name == "HALT":
                break
            elif name == "MOV":
                R[rd] = R[rs]
            elif name == "MOVI8":
                R[rd] = imm & 0xFF
            elif name == "MOVI32":
                R[rd] = imm & 0xFFFFFFFF
            elif name == "MOVI64":
                R[rd] = imm & M64
            elif name == "XCHG":
                R[rd], R[rs] = R[rs], R[rd]
            elif name == "MOVM":
                data[rd & dmask] = R[rs] & M64
            elif name == "MOVL":
                R[rd] = data[rs & dmask]
            elif name == "MOVB":
                R[rd] = data[rs & dmask] & 0xFF
            elif name == "STOREB":
                data[rd & dmask] = R[rs] & 0xFF
            elif name == "CLOAD":
                R[rd] = self.code[R[rs] & self.mask]
            elif name == "CSTORE":
                self.code[R[rd] & self.mask] = R[rs] & 0xFF
            elif name == "CXOR":
                a = R[rd] & self.mask
                self.code[a] = (self.code[a] ^ (R[rs] & 0xFF)) & 0xFF
            elif name == "CADD":
                a = R[rd] & self.mask
                self.code[a] = (self.code[a] + imm) & 0xFF
            elif name == "CREAD":
                R[rd] = self.code[end]         # next byte, read as data
                ip = (end + 1) & self.mask     # ... and consumed by the read
                continue
            elif name == "SKIPC":
                ip = (ip + imm) & self.mask
                continue
            elif name == "ADD":
                t = R[rd] + R[rs]
                R[rd] = t & M64
                c = 1 if t > M64 else 0
                z, s = (R[rd] == 0), (R[rd] >> 63)
            elif name == "ADDI":
                t = R[rd] + (imm & 0xFFFFFFFF)
                R[rd] = t & M64
                c = 1 if t > M64 else 0
                z, s = (R[rd] == 0), (R[rd] >> 63)
            elif name in ("SUB", "SUBI"):
                b = R[rs] if name == "SUB" else (imm & 0xFFFFFFFF)
                c = 1 if R[rd] < b else 0
                R[rd] = (R[rd] - b) & M64
                z, s = (R[rd] == 0), (R[rd] >> 63)
            elif name in ("MUL", "MULI"):
                b = R[rs] if name == "MUL" else (imm & 0xFFFFFFFF)
                R[rd] = (R[rd] * b) & M64
                c = 0
                z, s = (R[rd] == 0), (R[rd] >> 63)
            elif name == "UMULH":
                R[rd] = ((R[rd] * R[rs]) >> 64) & M64
                c = 0
                z, s = (R[rd] == 0), (R[rd] >> 63)
            elif name in ("DIV", "MOD"):
                b = R[rs]
                R[rd] = 0 if b == 0 else ((R[rd] // b) if name == "DIV"
                                          else (R[rd] % b))
                c = 0
                z, s = (R[rd] == 0), (R[rd] >> 63)
            elif name in ("AND", "ANDI", "OR", "ORI", "XOR", "XORI"):
                b = R[rs] if name in ("AND", "OR", "XOR") else (imm & 0xFFFFFFFF)
                if name.startswith("AND"):
                    r = R[rd] & b
                elif name.startswith("OR"):
                    r = R[rd] | b
                else:
                    r = R[rd] ^ b
                R[rd] = r & M64
                c = 0
                z, s = (R[rd] == 0), (R[rd] >> 63)
            elif name in ("SHL", "SHLI", "SHR", "SHRI", "SAR"):
                if name in ("SHL", "SHLI"):
                    n = (R[rs] if name == "SHL" else imm) & 63
                    r = (R[rd] << n) & M64
                elif name in ("SHR", "SHRI"):
                    n = (R[rs] if name == "SHR" else imm) & 63
                    r = (R[rd] >> n) & M64
                else:
                    n = R[rs] & 63
                    sv = R[rd] - (1 << 64) if (R[rd] >> 63) else R[rd]
                    r = (sv >> n) & M64
                R[rd] = r
                c = 0
                z, s = (r == 0), (r >> 63)
            elif name in ("ROTL", "ROTLI"):
                R[rd] = rotl(R[rd], R[rs] if name == "ROTL" else imm)
            elif name == "ROTR":
                R[rd] = rotr(R[rd], R[rs])
            elif name in ("NOT", "NEG", "INC", "DEC"):
                if name == "NOT":
                    r = (~R[rd]) & M64
                elif name == "NEG":
                    r = (-R[rd]) & M64
                elif name == "INC":
                    r = (R[rd] + 1) & M64
                else:
                    r = (R[rd] - 1) & M64
                R[rd] = r
                z, s = (r == 0), (r >> 63)
            elif name in ("MULMOD", "ADDMM", "SUBMM", "POWM"):
                m = R[rt]
                if m == 0:
                    R[rd] = 0
                elif name == "MULMOD":
                    R[rd] = (R[rd] * R[rs]) % m
                elif name == "ADDMM":
                    R[rd] = (R[rd] + R[rs]) % m
                elif name == "SUBMM":
                    R[rd] = (R[rd] + m - R[rs]) % m
                else:
                    R[rd] = pow(R[rd], R[rs], m)
                c = 0
                z, s = (R[rd] == 0), (R[rd] >> 63)
            elif name in ("CMP", "CMPI"):
                b = R[rs] if name == "CMP" else (imm & 0xFFFFFFFF)
                d = (R[rd] - b) & M64
                z = 1 if d == 0 else 0
                s = d >> 63
                c = 1 if R[rd] < b else 0
            elif name == "TEST":
                t = (R[rd] & R[rs]) & M64
                z = 1 if t == 0 else 0
                s = 0
                c = 0
            elif name == "SEL":
                R[rd] = R[rs] if z else R[rt]
            elif name == "ACC":
                R[7] = rotl(R[7], 7) ^ ((R[rd] + ACC_A) & M64)
            elif name == "ACCC":
                v = self.code[R[rd] & self.mask]
                R[7] = rotl(R[7], 11) ^ ((v + ACC_B) & M64)
            elif name == "ACRM":
                R[7] = ((rotl(R[7], 17) * ACC_C) & M64) ^ R[rd]
            elif name == "ACCS":
                R[7] = rotl(R[7], 23) ^ ((R[rd] * ACC_D) & M64)
            elif name in ("JMP", "JMP8"):
                ip = (end + imm) & self.mask
                continue
            elif name == "JMPR":
                ip = R[rd] & self.mask
                continue
            elif name in ("JZ", "JNZ", "JL", "JGE", "JGT", "JLE", "JC",
                          "JNC", "JOV"):
                take = {"JZ": bool(z), "JNZ": not z, "JL": bool(s),
                        "JGE": not s, "JGT": (not z) and (not s),
                        "JLE": bool(z or s), "JC": bool(c), "JNC": not c,
                        "JOV": bool(s)}[name]
                if take:
                    ip = (end + imm) & self.mask
                    continue
            elif name == "CALL":
                stack.append(end)
                ip = (end + imm) & self.mask
                continue
            elif name == "CALLR":
                stack.append(end)
                ip = R[rd] & self.mask
                continue
            elif name == "RET":
                ip = stack.pop() if stack else 0
                continue
            elif name == "LOOP":
                R[rd] = (R[rd] - 1) & M64
                z = 1 if R[rd] == 0 else 0
                s = R[rd] >> 63
                if R[rd] != 0:
                    ip = (end + imm) & self.mask
                    continue
            elif name == "PUSH":
                stack.append(R[rd])
            elif name == "POP":
                R[rd] = stack.pop() if stack else 0
            elif name == "PUSHI":
                stack.append(imm & 0xFFFFFFFF)
            elif name == "DUP":
                stack.append(stack[-1] if stack else 0)
            elif name == "SWAP":
                if len(stack) >= 2:
                    stack[-1], stack[-2] = stack[-2], stack[-1]
            elif name == "PICK":
                idx = len(stack) - 1 - R[rd]
                R[rd] = stack[idx] if 0 <= idx < len(stack) else 0
            elif name == "DROP":
                if stack:
                    stack.pop()
            elif name == "POKE":
                port = R[rd]
            elif name == "PEEK":
                R[rd] = port
            else:
                raise ValueError("unimplemented op " + name)

            ip = end

        return {"steps": steps, "regs": R, "fault": fault}


def key_of(regs):
    """Stage 2 key material: little-endian packing of R6, R7, R1, R2."""
    return b"".join(regs[r].to_bytes(8, "little") for r in KEY_REGS)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", type=int, default=0)
    ap.add_argument("--detect", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--emit", action="store_true",
                    help="machine-readable KEY=VALUE output for test scripts")
    args = ap.parse_args(argv)

    here = pathlib.Path(__file__).resolve().parent
    layout = json.loads((here / "vm_layout.json").read_text())

    def run(profile, detect):
        vm = ModelVM(layout, layout["programs"][str(profile)]["hex"])
        return vm.run(detect)

    if args.selftest:
        rc = 0
        a, b, d = run(0, 0), run(1, 0), run(0, 1)
        ka, kb, kd = key_of(a["regs"]), key_of(b["regs"]), key_of(d["regs"])
        print("profile0: steps=%d key=%s" % (a["steps"], ka.hex()))
        print("profile1: steps=%d key=%s" % (b["steps"], kb.hex()))
        print("detect=1: steps=%d key=%s" % (d["steps"], kd.hex()))
        if a["fault"] or b["fault"] or d["fault"]:
            print("FAIL: non-zero fault")
            rc = 1
        if ka != kb:
            print("FAIL: profiles disagree on the key")
            rc = 1
        if ka == kd:
            print("FAIL: detect path produced the real key")
            rc = 1
        r = a["regs"]
        if (r[1] >> 62) != 1:
            print("FAIL: modulus missing forced bit62")
            rc = 1
        if (r[3] & 1) != 1:
            print("FAIL: exponent not odd")
            rc = 1
        if r[6] in (0, 1):
            print("FAIL: modexp result degenerate")
            rc = 1
        if r[7] == 0:
            print("FAIL: ledger register empty")
            rc = 1
        print("SELFTEST " + ("OK" if rc == 0 else "FAILED"))
        return rc

    res = run(args.profile, args.detect)
    regs = res["regs"]
    k = key_of(regs)
    if args.emit:
        print("STEPS=%d" % res["steps"])
        print("FAIL=%d" % res["fault"])
        print("KEY=%s" % k.hex())
        print("TOKEN=CARTO{%s}" % k[:16].hex())
        print("R1=0x%016x" % regs[1])
        print("R2=0x%016x" % regs[2])
        print("R6=0x%016x" % regs[6])
        print("R7=0x%016x" % regs[7])
        return 0
    print("profile=%d detect=%d steps=%d fault=%d" %
          (args.profile, args.detect, res["steps"], res["fault"]))
    for i, v in enumerate(regs):
        print("r%-2d = 0x%016x" % (i, v))
    k = key_of(regs)
    print("key = " + k.hex())
    print("token = CARTO{%s}" % k[:16].hex())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))