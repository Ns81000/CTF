#!/usr/bin/env python3
"""Loom decoy registry (spec 4.4 / trap catalogue 4.11): the four
registered decoy lanes - three decoy cartridges plus the diagnostic
(anti-debug) lane.

Values are HARVESTED from organizer-private/runs/p5_decoy_tokens.txt,
computed once against the production parameters.  This module only reads
them, so the registry can never drift from what the shipped cartridges
print.  One lane IS independently re-derivable: the diagnostic cartridge
is a bare SHA mixer (no chain), so debug_token_from_pan() recomputes its
token from its pan and the suite asserts the two agree.
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import mint  # noqa: E402

HARVEST = os.path.join(ROOT, "organizer-private", "runs", "p5_decoy_tokens.txt")

# registry id -> cartridge file inside the package (spec 4.4 "roms/")
ROM_FILES = {
    "D-ROM-1": "roms/tide_merc6.rom",
    "D-ROM-2": "roms/star_merc3.rom",
    "D-ROM-3": "roms/grav_merc9.rom",
    "D-DBG": None,          # embedded diagnostic cartridge, no file
}

LANE_NAME = {
    "D-ROM-1": "MERC-6 tide recorder",
    "D-ROM-2": "MERC-3 star camera",
    "D-ROM-3": "MERC-9 gravimeter",
    "D-DBG": "diagnostic cartridge 7C (debug lane)",
}


def _fields(line):
    out = {}
    for tok in line.split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            out[k] = v
    return out


def rows():
    """[(id, rom_file, key_hex, out_hex, token, rc)] in harvest order.

    `key_hex` is what the harvest recorded for the lane:
      D-ROM-*  the cartridge's CHAIN SEED, i.e. SHA256("prambh:loom:seed:v1"
               || cartridge pan) - the value the cartridge walks.  The pan
               itself is mint-derived; check it with check_pan().
      D-DBG    the diagnostic cartridge's PAN (that lane is a bare SHA
               mixer - no chain seed exists).
    `out_hex` is the full 32-byte claim; for the decoy ROMs the printed
    token is its head (out[0:8]), for the diagnostic lane it is empty.
    """
    out = []
    with open(HARVEST) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            fld = _fields(line)
            rid = line.split()[0]
            key = fld.get("seed") or fld.get("pan")
            if rid not in ROM_FILES or key is None or "token" not in fld:
                raise SystemExit("loom_decoys: unparsable harvest line %r" % line)
            out.append((rid, ROM_FILES[rid], key, fld.get("out", ""),
                        fld["token"], fld.get("rc", "")))
    return out


def cart_pan(k):
    """Cartridge pan for decoy ROM k: SHA256("prambh:loom:decoy:v1" || LE32(k)).

    The pan is what the cartridge carries in its CART window (gen_rom.py);
    the harvest records the seed it derives, not the pan.
    """
    return mint.loom_decoy_cart(k).hex()


def chain_seed(pan_hex):
    """The chain seed a cartridge's pan derives: SHA256(label || pan)."""
    return hashlib.sha256(b"prambh:loom:seed:v1"
                          + bytes.fromhex(pan_hex)).hexdigest()


def check_pan(rid, key_hex):
    """True when the harvested key is what the mint says the lane must be:
    the derived chain seed for the ROM lanes, the pan for the diagnostic
    lane."""
    if rid == "D-DBG":
        return key_hex == mint.loom_debug_pan().hex()
    k = int(rid.rsplit("-", 1)[1]) - 1
    return key_hex == chain_seed(cart_pan(k))


def debug_token_from_pan(pan_hex):
    """Diagnostic lane: token = hex(SHA-256(pan || 0^32 || 0^8)[0:8]).

    The cartridge stages the pan in IN0 and leaves IN1/TAIL at their
    power-on zeros (gen_rom.DEBUG_BODY), so one SHA mixer pass derives it.
    """
    pan = bytes.fromhex(pan_hex)
    if len(pan) != 32:
        raise SystemExit("loom_decoys: pan must be 32 bytes")
    return "PRAMBH{%s}" % hashlib.sha256(pan + bytes(40)).hexdigest()[:16]


if __name__ == "__main__":
    for r in rows():
        print("%-8s %-24s pad=%s token=%s rc=%s"
              % (r[0], r[1] or "(embedded)", r[2][:16] + "...", r[4], r[5]))
    dbg = [r for r in rows() if r[0] == "D-DBG"][0]
    print("D-DBG independent re-derivation:",
          debug_token_from_pan(dbg[2]), "==", dbg[4],
          debug_token_from_pan(dbg[2]) == dbg[4])
