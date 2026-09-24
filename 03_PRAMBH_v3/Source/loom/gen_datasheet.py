#!/usr/bin/env python3
"""Generate field-notes/meru1_datasheet.txt (spec 4.4): the period-flavoured
fake datasheet for the MERU-8 survey loom processor.

Generated from opcodes.py so the instruction table can never drift from
the emulator, the assembler, or the Python model.  Deterministic: same
opcodes.py -> same bytes.  Contains NO real values (no seeds, no tokens);
the ISA itself is documented on purpose - the needle folio tells the
solver that this folio lists the one true program cartridge.

usage: gen_datasheet.py <out.txt>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opcodes import OPS, MMIO, MMIO_BASE, RESET_PC, ROM_MAX  # noqa: E402

# Period cycle counts by operand kind (flavour; the emulator is
# cycle-exact only to itself, not to this table).
CYCLES = {"none": 2, "imm": 2, "zp": 3, "zpx": 4, "abs": 4, "absx": 4,
          "absy": 4, "indy": 5, "rel": 2, "imm16": 3, "ind": 5}

MODE_NAMES = {
    "none": "implied",
    "imm": "immediate",
    "zp": "zero page",
    "zpx": "zero page, X",
    "abs": "absolute",
    "absx": "absolute, X",
    "absy": "absolute, Y",
    "indy": "indirect, Y",
    "rel": "relative",
    "imm16": "immediate word",
    "ind": "indirect",
}


def rule(ch="=", n=72):
    return ch * n


def header():
    return [
        rule(),
        "MERU SYSTEMS LTD. - VALLEY INSTRUMENTS DIVISION",
        "",
        "        MERU-8 SURVEY LOOM - FIELD STATION PROCESSOR",
        "",
        "        preliminary data sheet - document 83-MS-117 rev. C",
        "",
        "        (c) 1983 MERU SYSTEMS LTD.  all rights reserved.",
        "        meru, the meru loom mark and the stitch-table logo are",
        "        trademarks of meru systems ltd., valley works, plot 14.",
        rule(),
        "",
        "This sheet is the field issue of the processor data for the MERU-8",
        "survey loom.  It supersedes document 82-MS-104 (rev. B).  Operators",
        "should note that no other manual applies to the valley-issue looms;",
        "coast-issue sheets describe a different merit badge entirely.",
        "",
    ]


def overview():
    return [
        "1.  GENERAL DESCRIPTION",
        "",
        "The MERU-8 is an 8-bit accumulator machine intended for survey",
        "record stitching.  A single cartridge slot accepts program",
        "cartridges of up to %d bytes, mapped at $%04X.  The machine"
        % (ROM_MAX, RESET_PC),
        "addresses 64 KiB in total.  The $%04X page is reserved for the"
        % MMIO_BASE,
        "host coupler registers (section 5); the station teleprinter, the",
        "stitch engine and the mixer pans are reached through it.",
        "",
        "2.  PROGRAMMER'S MODEL",
        "",
        "  A    accumulator (8 bit)",
        "  X,Y  index registers (8 bit)",
        "  SP   stack pointer (8 bit, page $0100, descends)",
        "  PC   program counter (16 bit)",
        "  HL,DE,BC  stitch pointer pairs (16 bit, block move unit)",
        "",
        "  flags:  N (negative, bit 7), V (overflow, bit 6),",
        "          Z (zero, bit 1), C (carry, bit 0).",
        "          bits 4-5 read as one and cannot be cleared.",
        "",
        "3.  MEMORY MAP",
        "",
        "  $0000-$00FF   zero page (quick stores)",
        "  $0100-$01FF   stack",
        "  $0200-$7FFF   field RAM",
        "  $%04X-$EFFF   program cartridge (ROM)" % RESET_PC,
        "  $%04X-$%04X   host coupler registers (MMIO)"
        % (MMIO_BASE, MMIO_BASE + 0xFF),
        "  $F100-$FFFF   open bus (reads return bus float)",
        "",
        "Reset begins execution at $%04X, the first cartridge byte." % RESET_PC,
        "",
    ]


def modes_section():
    out = ["4.  ADDRESSING MODES", ""]
    seen = []
    for _c, _m, kind, _s, _f, _d in OPS:
        if kind not in seen:
            seen.append(kind)
    for kind in seen:
        out.append("  %-22s %d cycle%s"
                   % (MODE_NAMES[kind], CYCLES[kind],
                      "" if CYCLES[kind] == 1 else "s"))
    out += ["",
            "Branch instructions take one further cycle when the branch is",
            "taken.  The block move (LDIR) and checksum (XCRC) instructions",
            "run until their count pair exhausts; see section 6 notes.",
            ""]
    return out


def mmio_section():
    out = ["5.  HOST COUPLER REGISTERS ($%04X PAGE)" % MMIO_BASE, ""]
    out.append("  offset  name            access  function")
    out.append("  ------  --------------  ------  " + "-" * 38)
    for name, off in sorted(MMIO.items(), key=lambda kv: kv[1]):
        c = [oc for oc in OPCODE_MMIO_COMMENTS if oc[0] == name]
        access, desc = c[0][1], c[0][2]
        out.append("  $%04X    %-14s %-6s  %s" % (MMIO_BASE + off, name, access, desc))
    out += ["",
            "Writes to the stitch engine while a fill is in progress are",
            "ignored.  The mixer pans are write-only; the digest window is",
            "read-only.  Behaviour outside these registers is unspecified",
            "and varies between field stations.",
            ""]
    return out


OPCODE_MMIO_COMMENTS = [
    ("PUTCHAR", "W", "teleprinter: prints the written byte"),
    ("EXIT", "W", "halts the loom (as HLT)"),
    ("CHAIN_CLAIM", "W", "lodges the mixer output as the survey result"),
    ("CART_SEED", "W", "cartridge load vector, 32 bytes"),
    ("SEED_USE_CART", "W", "next stitch fill uses the cartridge vector"),
    ("CHAIN_T", "W", "stitch count, 8 bytes little-endian"),
    ("CHAIN_S", "W", "table size in bytes, 4 bytes little-endian"),
    ("CHAIN_INIT", "W", "fills the extended stitch table (slow)"),
    ("SHA_IN0", "W", "mixer pan 0, 32 bytes"),
    ("SHA_IN1", "W", "mixer pan 1, 32 bytes"),
    ("SHA_TAIL", "W", "stitch number, 8 bytes little-endian"),
    ("SHA_GO", "W", "runs the mixer once; digest at SHA_OUT"),
    ("SHA_OUT", "R", "mixer digest window, 32 bytes"),
    ("XMEM_IDX", "W", "extended table block number, 8 bytes LE"),
    ("XMEM_FETCH", "W", "fetches block (number modulo table size)"),
    ("CHAIN_S0", "R", "initial stitch state window, 32 bytes"),
    ("XMEM_WIN", "R", "fetched block window, 32 bytes"),
]


def opcode_table():
    out = ["6.  INSTRUCTION SET (%d operations)" % len(OPS), ""]
    out.append("  op   mnemonic  mode              bytes  flags   cycles")
    out.append("  ---  --------  ----------------  -----  ------  ------")
    for code, mnem, kind, size, flags, desc in OPS:
        out.append("  $%02X   %-8s %-16s %-5d  %-6s  %d%s"
                   % (code, mnem, MODE_NAMES[kind], size,
                      flags, CYCLES[kind],
                      "+" if kind == "rel" else ""))
    out.append("")
    out.append("Operation summaries")
    out.append("-------------------")
    for code, mnem, kind, size, flags, desc in OPS:
        out.append("  $%02X %-6s %s" % (code, mnem, desc))
    out += ["",
            "The corrected indirect jump (op $4B) reads the target word",
            "across the page boundary as written; there is no page-wrap",
            "erratum on valley-issue silicon.",
            ""]
    return out


def cartridge_section():
    return [
        "7.  PROGRAM CARTRIDGES",
        "",
        "The valley-issue loom accepts one cartridge at a time.  Of the",
        "sample cartridges circulating with the instrument collection, the",
        "survey stitch cartridge (loom.rom) is the one true program of",
        "record for the MERU-8; it alone drives the stitch engine through",
        "a full survey walk.  The remaining samples - tide, star camera,",
        "and gravimeter issues - are demonstration programs for other",
        "instruments in the range and their output is not a survey record.",
        "A field diagnostic cartridge (issue 7C) exists for depot use and",
        "prints a calibration line only.",
        "",
        "8.  ORDERING INFORMATION",
        "",
        "  MERU-8/VAL   field station processor, valley issue, badge III",
        "  CART-STITCH  survey stitch cartridge, program of record",
        "  CART-DIAG7C  depot diagnostic cartridge (not for survey use)",
        "",
        rule(),
        "document 83-MS-117 rev. C - printed at valley works, plot 14",
        "this sheet contains no survey data; it is an instrument manual.",
        rule(),
        "",
    ]


def main(argv):
    if len(argv) != 2:
        sys.stderr.write(__doc__)
        return 2
    lines = (header() + overview() + modes_section() + mmio_section()
             + opcode_table() + cartridge_section())
    with open(argv[1], "w") as f:
        f.write("\n".join(lines))
    sys.stderr.write("datasheet: %d lines -> %s\n" % (len(lines), argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

