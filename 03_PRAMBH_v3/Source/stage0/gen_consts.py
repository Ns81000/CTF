#!/usr/bin/env python3
"""Generate stage0_consts.h from the mint (single source of truth)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "gen"))
import mint

HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "stage0_consts.h"), "w") as f:
    f.write("#ifndef PRAMBH_STAGE0_CONSTS_H\n#define PRAMBH_STAGE0_CONSTS_H\n\n")
    f.write('#define STAGE0_TOKEN "%s"\n' % mint.stage0_token())
    f.write('#define CANARY_TOKEN "%s"\n' % mint.canary_token())
    f.write("\n#endif\n")
print("stage0_consts.h written")
