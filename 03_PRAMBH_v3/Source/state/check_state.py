#!/usr/bin/env python3
"""Independent Python verification of the prambh state layer.

Subcommands:
  hmac <root>   - recompute the device key + HMAC of <root>/prambh.survey
                  with hashlib/hmac and compare against the sealed state.
  ctr <keyhex> <len> <hexfile> - recompute SHA256ctr keystream and compare
                  against the C implementation's output stored in hexfile.
Prints PASS/FAIL lines. Exit 0 iff all PASS.
"""
import hashlib
import hmac
import os
import socket
import struct
import sys

FAILS = 0


def check(ok, name):
    global FAILS
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        FAILS += 1


def machine_id():
    for p in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            v = open(p).read().strip()
            if v:
                return v
        except OSError:
            pass
    return socket.gethostname() or "prambh-unknown-machine"


def device_key(root):
    label = b"prambh:state:key:v1"
    rp = os.path.realpath(root)
    return hashlib.sha256(label + machine_id().encode() + rp.encode()).digest()


def cmd_hmac(root):
    data = open(os.path.join(root, "prambh.survey"), "rb").read()
    check(len(data) == 512, "py: state file exactly 512 bytes")
    check(data[0:8] == b"PRMBHSV1", "py: magic bytes")
    check(struct.unpack("<I", data[8:12])[0] == 3, "py: version 3")
    mac = hmac.new(device_key(root), data[:480], hashlib.sha256).digest()
    check(mac == data[480:512], "py: independent HMAC-SHA256 verifies")
    check(data[172:480] == b"\x00" * (480 - 172), "py: reserved region zero")


def cmd_ctr(keyhex, length, hexfile):
    key = bytes.fromhex(keyhex)
    n = int(length)
    want = bytes.fromhex(open(hexfile).read().strip())
    stream = bytearray()
    ctr = 0
    while len(stream) < n:
        stream += hashlib.sha256(key + struct.pack("<Q", ctr)).digest()
        ctr += 1
    check(stream[:n] == want, "py: sha256ctr keystream matches C implementation")


if __name__ == "__main__":
    if sys.argv[1] == "hmac":
        cmd_hmac(sys.argv[2])
    elif sys.argv[1] == "ctr":
        cmd_ctr(sys.argv[2], sys.argv[3], sys.argv[4])
    sys.exit(1 if FAILS else 0)
