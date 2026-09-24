#!/bin/bash
# Shared acceptance harness for the stage suites.  SERIAL ONLY: every stage
# shares one record, so these scripts must never be parallelised.

FAILED=0
CHECKS=0
WORK=""
PKG="${PKG:-}"
OUT=""
ERR=""

t_init() {   # t_init <short-name> [package-dir]
    local name="$1"
    local src="${2:-}"
    WORK="/tmp/carto_${name}"
    PKG="$src"
    rm -rf "$WORK"
    mkdir -p "$WORK"
    if [ -n "$src" ] && [ -d "$src" ]; then cp -a "$src/." "$WORK/"; fi
    rm -f "$WORK/.cartographer_state" "$WORK/.cartographer_state.tmp"
    OUT="$WORK/.t_out"
    ERR="$WORK/.t_err"
    FAILED=0
    CHECKS=0
    printf '== %s ==\n' "$name"
}

ok()  { CHECKS=$((CHECKS+1)); printf '  PASS %s\n' "$1"; }
bad() { CHECKS=$((CHECKS+1)); FAILED=$((FAILED+1)); printf '  FAIL %s\n' "$1"; }

# run a tool from the scratch package root, capturing both streams
t_run() {    # t_run <cmd...>
    ( cd "$WORK" && "$@" ) >"$OUT" 2>"$ERR"
    return $?
}

t_expect_ok() {   # t_expect_ok <desc> <cmd...>
    local d="$1"; shift
    t_run "$@"
    local rc=$?
    if [ $rc -eq 0 ] && [ ! -s "$ERR" ]; then
        ok "$d (rc 0, stderr silent)"
    else
        bad "$d (rc=$rc, stderr $(wc -c <"$ERR") bytes)"
    fi
}

t_has() {    # t_has <desc> <fixed-string>
    if grep -qF -- "$2" "$OUT"; then ok "$1"; else bad "$1"; fi
}

t_lacks() {
    if grep -qF -- "$2" "$OUT"; then bad "$1"; else ok "$1"; fi
}

t_count() {  # t_count <desc> <fixed-string> <expected-count>
    local n
    n=$(grep -oF -- "$2" "$OUT" | wc -l)
    if [ "$n" = "$3" ]; then ok "$1"; else bad "$1 (found $n, want $3)"; fi
}

t_verify_state() {   # the independent python implementation weighs in
    if python3 "$PKGTOOLS/gen_vectors.py" "$WORK/.cartographer_state" \
            >"$WORK/.verify" 2>&1; then
        ok "independent python check of the record"
    else
        bad "independent python check of the record"
        cat "$WORK/.verify"
    fi
}

t_state_size() {
    local n
    n=$(stat -c %s "$WORK/.cartographer_state" 2>/dev/null || echo 0)
    if [ "$n" = "1168" ]; then ok "record is 1168 bytes"; else bad "record size $n"; fi
}

t_only_record() {
    local n
    n=$(ls -A "$WORK" | grep -vc '^\.t_\|^\.verify$')
    if [ "$n" = "1" ]; then ok "the record is the only file here"; else bad "extra files present ($n)"; fi
}

t_nm_empty() {   # t_nm_empty <binary>
    local out
    out=$(nm -a "$1" 2>/dev/null | wc -l)
    if [ "$out" = "0" ]; then ok "nm is empty ($1)"; else bad "nm shows $out lines ($1)"; fi
}

t_strings_clean() {   # t_strings_clean <binary>
    local hits
    hits=$(strings -n 5 "$1" | grep -Ei 'gcc|clang|musl|/home/|ns8pc|\.c$' | wc -l)
    if [ "$hits" = "0" ]; then ok "no build provenance in strings ($1)"; else
        bad "build provenance in strings ($1)"
        strings -n 5 "$1" | grep -Ei 'gcc|clang|musl|/home/|ns8pc' | head -5
    fi
}

t_absent() {   # t_absent <desc> <binary> <fixed-string>
    if strings -n 4 "$2" | grep -qF -- "$3" || grep -qF -- "$3" "$2" 2>/dev/null; then
        bad "$1 (found)"
    else
        ok "$1"
    fi
}

t_summary() {
    printf '  %d checks, %d failed\n' "$CHECKS" "$FAILED"
    if [ "$FAILED" = "0" ]; then printf '  OK\n'; exit 0; else printf '  NOT OK\n'; exit 1; fi
}
