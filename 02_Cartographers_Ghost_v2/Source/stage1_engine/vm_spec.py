#!/usr/bin/env python3
"""Stage 1 generator.

Builds the engine's two programs, pins their traces to the constant the spec
demands, and writes the artefacts the binary compiles in:

  stage1_blob.h        -- opcode bytes, the encrypted image, the decoy record
                          and the masked alternate key
  stage1_program.json  -- the shipped image in the clear, for the model

Both profiles must land on exactly the same 32 bytes.  The generator gets
there honestly: it runs each program with the model, then appends a fixed
correction table so the trace ends on the pinned constant.
"""
import hashlib
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_vm as M

K_ENGINE = bytes.fromhex(
    "1513351e85d8b50a145e1d23feac393264c4ad4ea9c403191fe981d5c92e67ef")
DECOY_KEY = hashlib.sha256(b"ghost2:stage1:decoy:key:v1").digest()
DEBUG_KEY = hashlib.sha256(b"ghost2:stage1:debug:key:v1").digest()
ENGINE_INK = K_ENGINE[8:16].hex()
CHECKPOINT = "CARTO{%s}" % K_ENGINE[16:24].hex()
DECOY_TOKEN = "CARTO{%s}" % DECOY_KEY[:8].hex()
DEBUG_TOKEN = "CARTO{%s}" % DEBUG_KEY[16:24].hex()

ITER = {"coast": 5120, "interior": 5632}
BASE = {"coast": 0x080, "interior": 0x600}
MIN_STEPS = 150000
SMC_WORDS = 5
POOL = M.permutation()
OPB = M.opbytes(POOL)


def smc_stream(name):
    """The bytes the SMC block is stored under, and the words the program
    XORs back in before it calls the block.  One stream, two uses."""
    out = b""
    i = 0
    while len(out) < 4 * SMC_WORDS:
        out += hashlib.sha256(
            ("ghost2:stage1:smcmask:%s:%d" % (name, i)).encode()).digest()
        i += 1
    return out[:4 * SMC_WORDS]


def smc_words(name):
    stream = smc_stream(name)
    return [struct.unpack_from("<I", stream, 4 * k)[0]
            for k in range(SMC_WORDS)]


def profile_seed(name):
    return hashlib.sha256(("ghost2:stage1:seed:" + name).encode()).digest()


def build(name, fixup=None, smc_addr=None):
    """Assemble one profile.

    fixup=None means 'no correction' (the generator's first pass).
    smc_addr=None means 'work out where the masked block goes': the block sits
    directly after the program, so the first pass learns the length and the
    second pass bakes in the address (every instruction keeps its size, so the
    second pass has exactly the same layout).
    """
    if smc_addr is None:
        probe, _p, _n = build(name, fixup, 0)
        return build(name, fixup,
                     ((BASE[name] + len(probe) + 3) // 4) * 4)
    seed = profile_seed(name)
    base = BASE[name]
    patch_addr = base + 0x40
    a = M.Asm(OPB)

    # ---- prologue: 32 masked bytes into the output region ----------------
    a.ins("MOVI", 0, M.OUT)
    for i in range(32):
        a.ins("MOVI", 1, seed[i] ^ 0x5A)
        a.ins("XORI", 1, 0x5A)
        a.ins("STB", 1, M.OUT + i)

    a.ins("MOVI", 2, M.OUT)        # r2 walks the region by absolute address
    a.ins("MOVI", 6, M.OUT + 32)   # the wrap limit
    a.ins("MOVI", 3, (0x1234ABCD + ITER[name]) & 0xFFFFFFFF)
    a.ins("MOVI", 5, ITER[name])   # loop counter
    a.ins("MOVI", 4, 0x00000000)   # a constant the loop keeps rotating
    for k in range(SMC_WORDS):
        a.ins("MOVI", 1, smc_words(name)[k])
        a.ins("SMXX", 1, smc_addr + 4 * k)   # unmask the block that follows
    a.label("loop")

    # ---- body: arithmetic over the region, plus live self-modification ---
    a.ins("LDIND", 1, 2)
    a.ins("ADDI", 1, 0x5A5A0101)
    a.ins("MIX", 1)
    a.ins("ROL", 1, 7)
    a.ins("XOR", 1, 3)
    a.ins("ADD", 3, 1)
    a.ins("AVAL", 1)
    a.ins("LDW", 7, M.OUT)
    a.ins("XOR3", 1, 3, 7)
    a.ins("ADD3", 1, 3, 7)
    a.ins("TWEAK32", 1, 0x7F4A7C15)
    a.ins("FMIX", 7)
    a.ins("XCHG", 1, 7)
    a.ins("STIND", 2, 1)
    a.ins("MOVRR", 4, 3)
    a.ins("CALL", smc_addr)        # the unmasked block runs
    a.ins("MOVRR", 4, 3)
    a.ins("SMXX", 4, patch_addr)   # the loop rewrites bytes it never runs
    a.ins("SMCR", 7, patch_addr)   # and then reads them back in
    a.ins("XOR", 3, 7)
    a.ins("TICK", 4)
    a.ins("ROTX", 3, 4)
    a.ins("PROBE", 3, base + 12)
    a.ins("MIXREG", 3, 1)
    a.ins("XORA", 4, 0x00C0FFEE)
    a.ins("ADDA", 4, 0x0BADF00D)
    a.ins("DEC", 1)
    a.ins("JNZ", 1, "loop_body_end")
    a.ins("SMXX", 4, patch_addr + 4)   # a one-off extra patch on step zero
    a.label("loop_body_end")

    a.ins("ADDI", 2, 1)
    a.ins("MOVRR", 7, 2)
    a.ins("SUB", 7, 6)
    a.ins("JZ", 7, "no_wrap")
    a.ins("MOVI", 2, M.OUT)
    a.label("no_wrap")
    a.ins("DEC", 5)
    a.ins("JNZ", 5, "loop")

    # ---- epilogue: correction table, then hand the 32 bytes out ----------
    for i in range(8):
        a.ins("LDW", 1, M.OUT + 4 * i)
        a.ins("XORI", 1, (fixup[i] if fixup else 0))
        a.ins("STW", 1, M.OUT + 4 * i)
    for i in range(8):
        a.ins("LDW", 1, M.OUT + 4 * i)
        a.ins("EMITW", 1)
    a.ins("HALT")

    # ---- the block the program unmasks and calls -------------------------
    block = M.Asm(OPB)
    block.ins("SMCR", 7, base + 12)
    block.ins("ADDI", 7, 0x13579BDF)
    block.ins("MIX", 7)
    block.ins("XOR", 3, 7)
    block.ins("RET")
    block_bytes = block.assemble(base=smc_addr)

    code = bytearray(a.assemble(base=base))
    while len(code) < smc_addr - base:
        code.append(OPB[M.OP_ID["NOP"]])
    code += block_bytes
    return bytes(code), smc_addr, len(block_bytes)


DECOY_RECORD_NOTE = "1971 resurvey index key -- kept for the old frame only"


def decoy_record():
    raw = hashlib.sha256(b"ghost2:mask:stage1:decoy").digest()
    return bytes(a ^ b for a, b in zip(DECOY_KEY, raw))


def debug_record():
    raw = hashlib.sha256(b"ghost2:mask:stage1:debug").digest()
    return bytes(a ^ b for a, b in zip(DEBUG_KEY, raw))


def build_image(fixups=None):
    """One image: both profiles and the decoy entry block."""
    image = bytearray(M.CODE_SIZE)
    for name in ("coast", "interior"):
        base = BASE[name]
        code, smc_addr, blen = build(name, (fixups or {}).get(name))
        stream = smc_stream(name)
        code = bytearray(code)
        for i in range(blen):
            code[smc_addr - base + i] ^= stream[i]
        image[base:base + len(code)] = code

    decoy = M.Asm(OPB)
    decoy.ins("MOVI", 0, M.OUT)
    decoy.ins("MOVI", 1, 0xDEADBEEF)
    decoy.ins("MIX", 1)
    decoy.ins("STB", 1, M.OUT)
    decoy.ins("HALT")
    db = decoy.assemble(base=0)
    image[0:len(db)] = db
    return bytes(image)


def simulate(image, name):
    vm = M.Vm(image, OPB, entry=BASE[name])
    steps = vm.run()
    return steps, vm.outputs()


def pin():
    """Two passes: measure, then correct so the trace lands on K_ENGINE."""
    first = build_image()
    raw = {name: simulate(first, name) for name in BASE}
    fixups = {}
    for name in BASE:
        got = raw[name][1]
        fixups[name] = [struct.unpack_from("<I", got, 4 * i)[0] ^
                        struct.unpack_from("<I", K_ENGINE, 4 * i)[0]
                        for i in range(8)]
    second = build_image(fixups)
    final = {name: simulate(second, name) for name in BASE}
    for name, (steps, out) in final.items():
        if out != K_ENGINE:
            raise SystemExit("profile %s does not land on the constant" % name)
        if steps < MIN_STEPS:
            raise SystemExit("profile %s is too short: %d steps" % (name, steps))
    return second, fixups, raw, final


def c_bytes(name, data, per=12):
    lines = ["static const uint8_t %s[%d] = {" % (name, len(data))]
    for i in range(0, len(data), per):
        lines.append("    " + " ".join("0x%02x," % b for b in data[i:i + per]))
    lines.append("};")
    return "\n".join(lines)


def write_json(image, path):
    with open(path, "w", newline="\n") as fh:
        json.dump({"opb": OPB, "pool": POOL, "plain": image.hex(),
                   "profiles": BASE, "iter": ITER}, fh, indent=1)
        fh.write("\n")


def write_blob(image, path):
    ct = bytes(a ^ b for a, b in zip(image, M.keystream(len(image))))
    parts = []
    parts.append("/* generated by vm_spec.py -- do not edit by hand */")
    parts.append("#ifndef CARTO_STAGE1_BLOB_H")
    parts.append("#define CARTO_STAGE1_BLOB_H\n")
    parts.append("#include <stdint.h>\n")
    parts.append(c_bytes("kOpByte", bytes(OPB)))
    parts.append("")
    parts.append(c_bytes("kImage", ct))
    parts.append("")
    parts.append("#define kImageLen %d" % len(ct))
    parts.append("#define kProfileCoast 0x%03x" % BASE["coast"])
    parts.append("#define kProfileInterior 0x%03x" % BASE["interior"])
    parts.append("")
    parts.append(c_bytes("kDecoyMasked", decoy_record()))
    parts.append("")
    parts.append(c_bytes("kDebugMasked", debug_record()))
    parts.append("")
    parts.append("/* %s */" % DECOY_RECORD_NOTE)
    parts.append('static const char kDecoyLure[] = "%s";' % DECOY_RECORD_NOTE)
    parts.append("")
    parts.append("#endif /* CARTO_STAGE1_BLOB_H */")
    with open(path, "w", newline="\n") as fh:
        fh.write("\n".join(parts) + "\n")


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    image, fixups, raw, final = pin()
    for name in ("coast", "interior"):
        print("profile %-9s raw steps=%-8d raw out=%s" %
              (name, raw[name][0], raw[name][1].hex()))
        print("profile %-9s final steps=%-8d out=%s%s" %
              (name, final[name][0], final[name][1].hex(),
               "  MATCH" if final[name][1] == K_ENGINE else "  MISMATCH"))
    write_json(image, os.path.join(out_dir, "stage1_program.json"))
    write_blob(image, os.path.join(out_dir, "stage1_blob.h"))
    print("engine ink      %s (never printed by the tool)" % ENGINE_INK)
    print("checkpoint      %s" % CHECKPOINT)
    print("decoy token     %s" % DECOY_TOKEN)
    print("alternate token %s" % DEBUG_TOKEN)
    print("image %d bytes; opcodes %d" % (len(image), len(OPB)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
