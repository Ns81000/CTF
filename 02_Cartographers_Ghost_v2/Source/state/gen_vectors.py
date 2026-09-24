#!/usr/bin/env python3
"""Independent verifier / vector generator for the v2 state record.

`gen_vectors.py` (no arguments) writes the known-answer vectors the C unit
tests compare against.  `gen_vectors.py <state-file>` re-implements the
format from scratch in Python and checks a record produced by the C code:
size, magic, version, flags, chain (with the derived tags absent) and the
HMAC.  The C code never tells this script what it wrote; the two
implementations have to agree.
"""
import hashlib
import hmac
import os
import struct
import sys

STAGES = 6
RING_SIZE = 64
RING_ENTRY = 16
SIZE = 1168
OFF = {
    "magic": 0x000, "version": 0x004, "flags": 0x006, "first_run": 0x008,
    "attempts": 0x010, "wrongs": 0x028, "gates": 0x040,
    "ring_count": 0x058, "ring_head": 0x05A, "debug": 0x05C,
    "distinct": 0x05D, "ring": 0x060, "chain": 0x460, "hmac": 0x470,
}


def sha(b):
    return hashlib.sha256(b).digest()


def sha_hex(s):
    return hashlib.sha256(s.encode()).hexdigest()


def master():
    return sha(b"ghost2:master:v2")


def state_key():
    return sha(master() + b"ghost2:state")


def stage_key(i):
    return sha(master() + ("ghost2:stage:%d" % i).encode())


def chain_of(body):
    view = bytearray(body[:OFF["chain"]])
    for i in range(STAGES):
        view[OFF["gates"] + 4 * i + 2] = 0
        view[OFF["gates"] + 4 * i + 3] = 0
    return sha(bytes(view))[:16]


def gate_tag(body, stage):
    salt = struct.unpack("<I", sha(("ghost2:gtag:%d" % stage).encode())[:4])[0]
    digest32 = struct.unpack("<I", chain_of(body)[:4])[0]
    return (digest32 ^ salt) & 0xFFFF


def verify(path):
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        print("FAIL cannot read %s: %s" % (path, exc))
        return 2
    fails = []
    if len(data) != SIZE:
        fails.append("size %d != %d" % (len(data), SIZE))
    if data[:4] != b"CGV2":
        fails.append("magic %r" % data[:4])
    if struct.unpack("<H", data[4:6])[0] != 2:
        fails.append("version")
    if struct.unpack("<H", data[6:8])[0] != 0:
        fails.append("flags")
    want_mac = hmac.new(state_key(), data[:OFF["hmac"]], hashlib.sha256).digest()
    if want_mac != data[OFF["hmac"]:OFF["hmac"] + 32]:
        fails.append("hmac")
    if chain_of(data) != data[OFF["chain"]:OFF["chain"] + 16]:
        fails.append("chain")
    for i in range(STAGES):
        got = struct.unpack("<H", data[OFF["gates"] + 4 * i + 2:
                                        OFF["gates"] + 4 * i + 4])[0]
        want = gate_tag(data, i)
        if got != want:
            fails.append("gate tag %d (0x%04x != 0x%04x)" % (i, got, want))
    rc = struct.unpack("<H", data[OFF["ring_count"]:OFF["ring_count"] + 2])[0]
    rh = struct.unpack("<H", data[OFF["ring_head"]:OFF["ring_head"] + 2])[0]
    distinct = int.from_bytes(data[OFF["distinct"]:OFF["distinct"] + 3], "little")
    print("ring_count=%u ring_head=%u first_run=%u distinct=%u (3-byte field)" %
          (rc, rh, struct.unpack("<Q", data[OFF["first_run"]:
                                          OFF["first_run"] + 8])[0], distinct))
    if fails:
        print("FAIL %s: %s" % (path, ", ".join(fails)))
        return 1
    print("PASS %s: 1168 bytes, hmac ok, chain ok, tags ok" % path)
    return 0


def gen_vectors():
    lines = []
    lines.append("K_state %s" % state_key().hex())
    for i in range(STAGES):
        lines.append("K_stage_%d %s" % (i, stage_key(i).hex()))
    msg100 = bytes(range(100))
    lines.append("SHA_100 %s" % sha(msg100).hex())
    lines.append("HMAC_state_100 %s" % hmac.new(state_key(), msg100,
                                                hashlib.sha256).hexdigest())
    for i in range(STAGES):
        lines.append("HMAC_stage_%d_100 %s" %
                     (i, hmac.new(stage_key(i), msg100,
                                  hashlib.sha256).hexdigest()))
    body = bytearray(SIZE)
    body[0:4] = b"CGV2"
    struct.pack_into("<H", body, 4, 2)
    struct.pack_into("<H", body, 6, 0)
    struct.pack_into("<Q", body, OFF["first_run"], 1700000000000)
    lines.append("CHAIN_zero_body %s" % chain_of(bytes(body)).hex())
    text = "\n".join(lines) + "\n"
    out = "/tmp/carto_v2_vectors.txt"
    with open(out, "w", newline="\n") as fh:
        fh.write(text)
    print("wrote %s (%d vectors)" % (out, len(lines)))


def main():
    if len(sys.argv) > 1:
        return verify(sys.argv[1])
    gen_vectors()
    return 0


if __name__ == "__main__":
    sys.exit(main())
