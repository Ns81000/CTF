#!/usr/bin/env python3
"""Write a reduced-T mirror_consts.h for the P7 suite's scripted solve.

usage: reduced_consts.py <out.h> <steps> <milestone-token> [title]

With a title, the digest of that title is embedded (the suite rewrites the
header once the reduced walk has produced its own title).
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

TEMPLATE = """#ifndef PRAMBH_MIRROR_CONSTS_H
#define PRAMBH_MIRROR_CONSTS_H

/* reduced-T header written by src/mirror/reduced_consts.py (P7 suite only) */
#define MIRROR_MILESTONE_TOKEN "%(token)s"
#define MIRROR_TABLE_BYTES %(s)d
#define MIRROR_STEPS %(t)d

static const unsigned char MIRROR_TITLE_DIGEST[32] = {
%(digest)s
};

#endif
"""


def main(argv):
    if len(argv) < 4:
        sys.stderr.write(__doc__)
        return 2
    out, steps, token = argv[1], int(argv[2]), argv[3]
    title = argv[4] if len(argv) > 4 else ""
    params = json.load(open(os.path.join(ROOT, "src", "chain",
                                         "chain_params.json")))
    digest = hashlib.sha256(title.encode()).digest() if title else bytes(32)
    body = TEMPLATE % {
        "token": token, "s": params["table_bytes"], "t": steps,
        "digest": "\n".join("    " + ", ".join("0x%02x" % b
                                               for b in digest[i:i + 8]) + ","
                            for i in range(0, 32, 8)),
    }
    with open(out, "w") as f:
        f.write(body)
    print("wrote %s (steps=%d, title=%s)" % (out, steps, title or "(none)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
