#!/usr/bin/env python3
"""policy_patch.py -- normalize the state-library decoy registry for Phase 4.

Registers exactly ONE stage-3 decoy row (the Stage-2 checkpoint token fed
back as the oracle reading) and keeps test_part2.c's row assertions in step.
Idempotent: safe to re-run; repairs any earlier 4-row attempt.

DESIGN NOTE (PHASE_4_LOG D50): the Stage-1 token
(CARTO{fd3e8049dfdfc32efe22fe823822b8c0}) was considered and REJECTED as a
stage-3 decoy: policy.h rows are compiled into every stage binary, so
registering it would ship the first half of the REAL Stage-1 key material
into solver-facing material (a genuine answer leak, caught by the stage-1
and stage-2 suites' own absence assertions). The Stage-2 checkpoint token is
safe: it is a one-way digest checkpoint (PHASE_3_LOG D42) that reveals
nothing about the reading, and feeding it back to the oracle is precisely
the lazy path the decoy exists to catch. INTERNAL, not shipped."""

import pathlib
import re

R = pathlib.Path("/home/manish/cartographer-build")
POLICY = R / "src/state/policy.h"
TEST2 = R / "src/state/test_part2.c"

TABLE_RE = re.compile(
    r"static const carto_decoy_entry_t carto_decoy_table\[\] = \{.*?\};",
    re.S)
LEN_RE = re.compile(r"#define CARTO_DECOY_TABLE_LEN \d+")

TABLE_WANT = (
    "static const carto_decoy_entry_t carto_decoy_table[] = {\n"
    '    { 1, "CARTO{12f8a367b772817e805725e7292acfb6}", 1u },\n'
    '    { 2, "CARTO{twice_over_the_coast_before_the_interior}", 1u },\n'
    '    { 3, "CARTO{b27692a0d5f63d4f1a0c3fb79afbf81b}", 1u },\n'
    "};\n"
)
LEN_WANT = "#define CARTO_DECOY_TABLE_LEN 3\n"

T2_NEW = (
    '    CHECK(CARTO_DECOY_TABLE_LEN >= 3, "stage 1, 2 and 3 decoys registered");\n'
    '    CHECK(carto_decoy_table[0].stage == 1, "row 0 is the stage 1 decoy");\n'
    '    CHECK(carto_decoy_table[1].stage == 2, "row 1 is the stage 2 decoy");\n'
    '    CHECK(carto_decoy_table[2].stage == 3, "row 2 is the stage 3 decoy (stage-2 checkpoint token fed back as reading)");\n'
)

T2_RE = re.compile(
    r"    CHECK\(CARTO_DECOY_TABLE_LEN >= \d+, \"[^\"]*decoys registered\"\);\n"
    r"    CHECK\(carto_decoy_table\[0\]\.stage == 1[^\n]*\n"
    r"    CHECK\(carto_decoy_table\[1\]\.stage == 2[^\n]*\n"
    r"(    CHECK\(carto_decoy_table\[2\]\.stage == 3[^\n]*\n)?"
    r"(    CHECK\(carto_decoy_table\[3\]\.stage == 3[^\n]*\n)?"
    r"(    CHECK\(carto_decoy_table\[3\]\.stage == 4[^\n]*\n)?"
)


def patch_policy():
    s = POLICY.read_text()
    m = TABLE_RE.search(s)
    if not m:
        raise SystemExit("cannot locate decoy table in policy.h")
    if TABLE_WANT in s and LEN_WANT in s:
        print("policy.h already normalized (3 rows)")
        return False
    s = TABLE_RE.sub(TABLE_WANT.rstrip("\n"), s, count=1)
    s = LEN_RE.sub(LEN_WANT.rstrip("\n"), s)
    POLICY.write_text(s)
    print("policy.h normalized: 3 rows (stage-3 decoy = stage-2 checkpoint token)")
    return True


def patch_test2():
    s = TEST2.read_text()
    if T2_NEW in s:
        print("test_part2.c already normalized (LEN>=3, row 2 stage==3)")
        return False
    s2, n = T2_RE.subn(T2_NEW, s, count=1)
    if n != 1:
        raise SystemExit("cannot locate test_decoy_count row assertions")
    TEST2.write_text(s2)
    print("test_part2.c normalized: LEN>=3, rows 0..2 asserted")
    return True


if __name__ == "__main__":
    a = patch_policy()
    b = patch_test2()
    if not a and not b:
        print("nothing to do (already normalized)")
