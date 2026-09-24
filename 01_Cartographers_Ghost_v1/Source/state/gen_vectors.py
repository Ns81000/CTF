#!/usr/bin/env python3
"""Generate HMAC-SHA256 differential test vectors for test_state.

Uses the OS-provided reference implementation (hashlib/hmac) so the C library
is verified against an independent implementation, not against hardcoding.
Deterministic (fixed seed) so every session/phase regenerates identical bytes.
Output: /tmp/carto_vectors.txt, one case per line: keyhex msghex machex
"""
import hashlib
import hmac
import random

SEED = 777001
random.seed(SEED)

cases = []
# Well-known HMAC-SHA256 cases (RFC 4231 TC1/TC2 shapes; hashlib is the judge).
cases.append((bytes([0x0B]) * 20, b"Hi There"))
cases.append((b"Jefe", b"what do ya want for nothing?"))
cases.append((bytes(range(1, 25)), bytes([0xCD]) * 50))
# Larger-than-block-size key exercises the key-hashed-first path.
cases.append((b"\xaa" * 131, b"Test Using Larger Than Block-Size Key - Hash Key First"))

# Deterministic random cases; key lengths straddle the 64-byte block boundary.
for _ in range(64):
    klen = random.choice([1, 2, 3, 16, 20, 32, 63, 64, 65, 100, 131, 200])
    mlen = random.randrange(1, 65)
    cases.append((
        bytes(random.randrange(256) for _ in range(klen)),
        bytes(random.randrange(256) for _ in range(mlen)),
    ))

with open("/tmp/carto_vectors.txt", "w") as f:
    for k, m in cases:
        mac = hmac.new(k, m, hashlib.sha256).hexdigest()
        f.write(k.hex() + " " + m.hex() + " " + mac + "\n")

# Canonical-key probe: HMAC of a fixed message under the DOCUMENTED Phase-0
# canonical key. The C harness must reproduce this via carto_unmask_key(),
# which proves the masked key blob in state_core.c decodes to the real key.
CANON_KEY = bytes.fromhex("f03ea6b5c1b869482723c0d11d635f8e9966c43a0a8def87fd1e2e950c10a7de")
probe_mac = hmac.new(CANON_KEY, b"cartographer-key-probe", hashlib.sha256).hexdigest()
with open("/tmp/carto_selftest.txt", "w") as f:
    f.write(probe_mac + "\n")

print(str(len(cases)) + " vectors written; canonical probe: " + probe_mac)
