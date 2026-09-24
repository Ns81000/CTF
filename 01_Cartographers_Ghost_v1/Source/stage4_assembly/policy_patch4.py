#!/usr/bin/env python3
"""policy_patch4.py -- normalize the state-library decoy registry for Phase 5.

Registers exactly ONE stage-4 decoy row: the struck "first draft" title
(kStage4DraftFlag from the generated stage4_blob.h / stage4_layout.json,
minted from its own seed "cartographer-ghost:stage4:decoy:first-draft:v1")
and keeps test_part2.c's row assertions in step (26->27 tests stay; the
row assertions gain stage 4). Idempotent: safe to re-run.

DESIGN NOTE (PHASE_5_LOG D58, D50 lesson): the decoy reveals nothing about
any real answer. The natural wrong-assembly candidates (e.g. the naive
stage-order title) contain REAL component values -- the engine ink (bytes
16..23 of the Stage-1 real key) and the oracle ink (the Stage-3 master K) --
so registering them would leak real answer material into every stage binary
via policy.h, exactly the leak PHASE_4_LOG D50 caught and rejected. The
struck draft is synthetic (own seed) and safe to ship.

MUST run AFTER stage3's policy_patch.py in any verify chain (that script
normalizes to 3 rows; this one establishes the 4-row end state).
INTERNAL, not shipped."""
import json
import pathlib
import re

R = pathlib.Path("/home/manish/cartographer-build")
POLICY = R / "src/state/policy.h"
TEST2 = R / "src/state/test_part2.c"
LAYOUT = R / "src/stage4_assembly/stage4_layout.json"

DRAFT = json.loads(LAYOUT.read_text())["draft_flag"]

TABLE_RE = re.compile(
    r"static const carto_decoy_entry_t carto_decoy_table\[\] = \{.*?\};",
    re.S)
LEN_RE = re.compile(r"#define CARTO_DECOY_TABLE_LEN \d+")

TABLE_WANT = (
    "static const carto_decoy_entry_t carto_decoy_table[] = {\n"
    '    { 1, "CARTO{12f8a367b772817e805725e7292acfb6}", 1u },\n'
    '    { 2, "CARTO{twice_over_the_coast_before_the_interior}", 1u },\n'
    '    { 3, "CARTO{b27692a0d5f63d4f1a0c3fb79afbf81b}", 1u },\n'
    '    { 4, "%s", 1u },\n'
    "};\n" % DRAFT
)
LEN_WANT = "#define CARTO_DECOY_TABLE_LEN 4\n"

T2_NEW = (
    '    CHECK(CARTO_DECOY_TABLE_LEN >= 4, "stage 1, 2, 3 and 4 decoys registered");\n'
    '    CHECK(carto_decoy_table[0].stage == 1, "row 0 is the stage 1 decoy");\n'
    '    CHECK(carto_decoy_table[1].stage == 2, "row 1 is the stage 2 decoy");\n'
    '    CHECK(carto_decoy_table[2].stage == 3, "row 2 is the stage 3 decoy (stage-2 checkpoint token fed back as reading)");\n'
    '    CHECK(carto_decoy_table[3].stage == 4, "row 3 is the stage 4 decoy (struck first-draft title)");\n'
)

T2_RE = re.compile(
    r"    CHECK\(CARTO_DECOY_TABLE_LEN >= \d+, \"[^\"]*decoys registered\"\);\n"
    r"    CHECK\(carto_decoy_table\[0\]\.stage == 1[^\n]*\n"
    r"    CHECK\(carto_decoy_table\[1\]\.stage == 2[^\n]*\n"
    r"    CHECK\(carto_decoy_table\[2\]\.stage == 3[^\n]*\n"
    r"(    CHECK\(carto_decoy_table\[3\]\.stage == 3[^\n]*\n)?"
    r"(    CHECK\(carto_decoy_table\[3\]\.stage == 4[^\n]*\n)?"
)


def patch_policy():
    s = POLICY.read_text()
    m = TABLE_RE.search(s)
    if not m:
        raise SystemExit("cannot locate decoy table in policy.h")
    if TABLE_WANT in s and LEN_WANT in s:
        print("policy.h already normalized (4 rows)")
        return False
    s = TABLE_RE.sub(TABLE_WANT.rstrip("\n"), s, count=1)
    s = LEN_RE.sub(LEN_WANT.rstrip("\n"), s)
    POLICY.write_text(s)
    print("policy.h normalized: 4 rows (stage-4 decoy = struck first-draft title)")
    return True


def patch_test2():
    s = TEST2.read_text()
    if T2_NEW in s:
        print("test_part2.c already normalized (LEN>=4, rows 0..3 asserted)")
        return False
    s2, n = T2_RE.subn(T2_NEW, s, count=1)
    if n != 1:
        raise SystemExit("cannot locate test_decoy_count row assertions")
    TEST2.write_text(s2)
    print("test_part2.c normalized: LEN>=4, rows 0..3 asserted")
    return True


if __name__ == "__main__":
    a = patch_policy()
    b = patch_test2()
    if not a and not b:
        print("nothing to do (already normalized)")
