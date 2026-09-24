#!/usr/bin/env python3
"""Generate the MERU-8 cartridges (spec 4.4).

Outputs (deterministic: same inputs -> same bytes):
  params.h        chain #1 defaults for loom.c, from ../chain/chain_params.json
  debug_rom.h     the diagnostic cartridge (anti-debug lane), as a C array
  <out>/loom.rom      the real survey cartridge (chain #1 in emulated cycles)
  <out>/roms/{tide_merc6,star_merc3,grav_merc9}.rom   the decoy collection

usage: gen_rom.py <outdir> [--T steps] [--S bytes] [--decoy-T steps] [--no-params]

--T/--S shrink the REAL cartridge's chain for test builds only; the
shipped ROM always uses the calibrated values from chain_params.json.
--no-params leaves src/loom/params.h untouched (test builds must never
clobber the production defaults the shipped loom is compiled with).
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "gen"))
from asm import assemble  # noqa: E402
import mint  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PARAMS = os.path.join(HERE, "..", "chain", "chain_params.json")

HEADER = """; %s
; MERU-8 survey loom cartridge - assembled by gen_rom.py (deterministic)
        .org $8000

        .equ CLAIM,   $F002
        .equ CART,    $F010
        .equ USE_CART, $F030
        .equ IN0,     $F040
        .equ IN1,     $F060
        .equ TAIL,    $F080
        .equ GO,      $F088
        .equ OUTB,    $F090
        .equ XIDX,    $F0B0
        .equ XFETCH,  $F0B8
        .equ S0WIN,   $F0C0
        .equ XWIN,    $F0E0

        .equ STATE,   $0200
        .equ COUNT,   $0220
        .equ SCRATCH, $00
"""

# Decoy cartridges carry their own constant in the CART window; the real
# cartridge takes the survey vector from the host (--vector) instead.
SETCART = """        ldx #0
_setcart:
        lda cart,x
        sta CART,x
        inx
        cpx #$20
        bne _setcart
        lda #1
        sta USE_CART
"""

COMMON = """        ldx #0
_sett:  lda tval,x
        sta CHAIN_T,x
        inx
        cpx #8
        bne _sett
        ldx #0
_sets:  lda sval,x
        sta CHAIN_S,x
        inx
        cpx #4
        bne _sets
        lda #1
        sta CHAIN_INIT
        ldhl #S0WIN
        ldde #STATE
        ldbc #$0020
        ldir
        lda #0
        ldx #0
_zero:  sta COUNT,x
        inx
        cpx #8
        bne _zero
_walk:
        ldhl #STATE
        ldde #IN0
        ldbc #$0020
        ldir
        ldhl #STATE
        ldde #XIDX
        ldbc #$0008
        ldir
        lda #1
        sta XFETCH
        ldhl #XWIN
        ldde #IN1
        ldbc #$0020
        ldir
        ldx #0
_inc:   lda COUNT,x
        clc
        adc #1
        sta COUNT,x
        bne _cd
        inx
        cpx #8
        bne _inc
_cd:
        ldhl #COUNT
        ldde #TAIL
        ldbc #$0008
        ldir
        lda #1
        sta GO
        ldhl #OUTB
        ldde #STATE
        ldbc #$0020
        ldir
"""


def cmp_block(T):
    """Loop-exit test, unrolled with immediate constants (no EOR abs,X
    in the MERU-8 ISA).  Falls through at _done when COUNT == T."""
    tb = struct.pack("<Q", T)
    out = []
    for i in range(8):
        out.append("        lda $%04X" % (0x220 + i))
        out.append("        eor #$%02X" % tb[i])
        if i == 0:
            out.append("        sta SCRATCH")
        else:
            out.append("        ora SCRATCH")
            out.append("        sta SCRATCH")
    out.append("        lda SCRATCH")
    out.append("        beq _done")
    out.append("        jmp _walk")
    out.append("_done:")
    return "\n".join(out) + "\n"



# Teleprinter helpers and exit, shared by every cartridge.  The caller
# enters at _pstr with X=0, banner:/suffix: defined, and the 8 token
# bytes staged at STATE..STATE+7.
PHEX = """_pstr:
        lda banner,x
        beq _tok
        sta PUTCHAR
        inx
        bra _pstr
_tok:
        ldx #0
_tokl:  lda STATE,x
        jsr _phex
        inx
        cpx #8
        bne _tokl
        ldx #0
_sufl:  lda suffix,x
        beq _fin
        sta PUTCHAR
        inx
        bra _sufl
_fin:
        lda #1
        sta EXIT
        hlt
_phex:
        sta SCRATCH
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
"""

# Real cartridge: token = hex(out[8:16]) (loom ink = out[0:8], never shown).
EPILOGUE_REAL = """        lda #1
        sta CLAIM
        ldhl #$0208
        ldde #STATE
        ldbc #$0008
        ldir
        ldx #0
        bra _pstr
"""

# Decoy cartridges: token = hex(out[0:8]).
EPILOGUE_DECOY = """        lda #1
        sta CLAIM
        ldx #0
        bra _pstr
"""


def _bytes_label(name, data):
    return "%s: .byte %s\n" % (name, ",".join("$%02X" % b for b in data))


def _tables(T, S, cart):
    out = _bytes_label("tval", struct.pack("<Q", T))
    out += _bytes_label("sval", struct.pack("<I", S))
    if cart is not None:
        out += _bytes_label("cart", cart)
    return out


def _texts(banner, suffix):
    return ('banner: .ascii "%s"\n        .byte 0\n'
            'suffix: .ascii "%s"\n        .byte 0\n') % (banner, suffix)

# The diagnostic cartridge (anti-debug lane, trap catalogue D-DBG).
# Prints a plausible self-test and a format-valid calibration token
# derived from a fixed pan through the SHA mixer.  IN1 and TAIL stay at
# their power-on zeros, so token = hex(SHA-256(pan || 0^32 || 0^8)[0:8]).
DEBUG_BODY = """start:
        ldx #0
_pan:   lda cart,x
        sta IN0,x
        inx
        cpx #$20
        bne _pan
        lda #1
        sta GO
        ldhl #OUTB
        ldde #STATE
        ldbc #$0008
        ldir
        ldx #0
        bra _pstr
"""


def real_source(T, S):
    return (HEADER % "survey stitch cartridge - the chain of record"
            + "start:\n" + COMMON + cmp_block(T) + EPILOGUE_REAL + PHEX
            + _texts("the loom settles.\\nchain checkpoint token: PRAMBH{",
                     "}\\nkeep the ink to yourself, the survey continues.\\n")
            + _tables(T, S, None))


def debug_source():
    return (HEADER % "field diagnostic cartridge 7C (debug lane)"
            + DEBUG_BODY + PHEX
            + _texts("MERU-8 field diagnostic 7C\\n"
                     "carriage ok / spool ok / drums ok\\n"
                     "calibration token: PRAMBH{",
                     "}\\ndiagnostic cartridge - not a survey record.\\n")
            + _bytes_label("cart", mint.loom_debug_pan()))


DECOYS = [
    ("tide_merc6",
     "MERC-6 TIDE RECORDER - valley survey issue\\n"
     "readings stitched and filed.\\nfield token: PRAMBH{",
     "}\\nduplicate folio filed at the valley depot.\\n"),
    ("star_merc3",
     "MERC-3 STAR CAMERA - valley survey issue\\n"
     "plates exposed and counted.\\nfield token: PRAMBH{",
     "}\\nduplicate folio filed at the valley depot.\\n"),
    ("grav_merc9",
     "MERC-9 GRAVIMETER - valley survey issue\\n"
     "stations levelled and weighed.\\nfield token: PRAMBH{",
     "}\\nduplicate folio filed at the valley depot.\\n"),
]


def decoy_source(k, T, S):
    name, banner, suffix = DECOYS[k]
    return (HEADER % ("decoy instrument cartridge %d (%s)" % (k + 1, name))
            + "start:\n" + SETCART + COMMON + cmp_block(T) + EPILOGUE_DECOY + PHEX
            + _texts(banner, suffix)
            + _tables(T, S, mint.loom_decoy_cart(k)))


def write_params_h(T, S):
    with open(os.path.join(HERE, "params.h"), "w") as f:
        f.write("/* generated by gen_rom.py from ../chain/chain_params.json */\n"
                "#ifndef PRAMBH_LOOM_PARAMS_H\n#define PRAMBH_LOOM_PARAMS_H\n"
                "#define PRAMBH_CHAIN_T_DEFAULT %dull\n"
                "#define PRAMBH_CHAIN_S_DEFAULT %du\n"
                "#endif\n" % (T, S))


def write_debug_rom_h(image):
    with open(os.path.join(HERE, "debug_rom.h"), "w") as f:
        f.write("/* generated by gen_rom.py: the diagnostic cartridge */\n"
                "#ifndef PRAMBH_DEBUG_ROM_H\n#define PRAMBH_DEBUG_ROM_H\n"
                "static const uint8_t DEBUG_ROM[] = {\n")
        for i in range(0, len(image), 12):
            f.write("    "
                    + ",".join("0x%02x" % b for b in image[i:i + 12]) + ",\n")
        f.write("};\n#define DEBUG_ROM_LEN %du\n#endif\n" % len(image))


def main(argv):
    if len(argv) < 2:
        sys.stderr.write(__doc__)
        return 2
    outdir = argv[1]
    params = json.load(open(PARAMS))
    T = params["budgets"]["chain1"]["T"]
    S = params["table_bytes"]
    dT = params["budgets"]["decoy_rom"]["T"]
    dS = 4 * 1024 * 1024
    i = 2
    skip_params = False
    while i < len(argv):
        if argv[i] == "--T":
            T = int(argv[i + 1], 0)
            i += 2
        elif argv[i] == "--S":
            S = int(argv[i + 1], 0)
            i += 2
        elif argv[i] == "--decoy-T":
            dT = int(argv[i + 1], 0)
            i += 2
        elif argv[i] == "--no-params":
            skip_params = True
            i += 1
        else:
            sys.stderr.write("gen_rom.py: unknown arg %r\n" % argv[i])
            return 2

    if not skip_params:
        write_params_h(T, S)
    os.makedirs(os.path.join(outdir, "roms"), exist_ok=True)

    org, image = assemble(real_source(T, S))
    assert org == 0x8000
    with open(os.path.join(outdir, "loom.rom"), "wb") as f:
        f.write(image)

    org, image = assemble(debug_source())
    assert org == 0x8000
    write_debug_rom_h(image)

    for k, (name, _b, _s) in enumerate(DECOYS):
        org, image = assemble(decoy_source(k, dT, dS))
        assert org == 0x8000
        with open(os.path.join(outdir, "roms", name + ".rom"), "wb") as f:
            f.write(image)
    sys.stderr.write("gen_rom: loom.rom + 3 decoys + params.h + debug_rom.h "
                     "(T=%d S=%d decoy-T=%d)\n" % (T, S, dT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))


