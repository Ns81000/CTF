#!/bin/bash
# finalize_docs.sh -- Phase FINAL: publish the phase log + the measured
# calibration numbers, then rebuild BOTH deliverable folders from the updated
# documents and re-verify end to end.
set -e
R=/home/manish/cartographer-build
STAGE=/mnt/d/gandu/_stage/s5_final

echo "--- 1. sync the two documents (CRLF-normalised) ---"
tr -d '\r' < "$STAGE/PHASE_FINAL_LOG.md"   > "$R/logs/PHASE_FINAL_LOG.md"
tr -d '\r' < "$STAGE/SOLVE_PATH_PRIVATE.md" > "$R/SOLVE_PATH_PRIVATE.md"
for f in "$R/logs/PHASE_FINAL_LOG.md" "$R/SOLVE_PATH_PRIVATE.md"; do
    printf '  %-40s lines=%-5s CR=%s\n' "${f#$R/}" "$(wc -l < "$f")" \
        "$(tr -cd '\r' < "$f" | wc -c)"
done

echo "--- 2. the measured numbers, as now recorded ---"
grep -n '5066.07\|84.43\|850.2 ms\|0.989' "$R/SOLVE_PATH_PRIVATE.md" | head -6
grep -n '5066.07\|84.43\|850.2 ms' "$R/logs/PHASE_FINAL_LOG.md" | head -4

echo "--- 3. tree sweep ---"
find "$R" -name '__pycache__' -type d -not -path '*/.git/*' -exec rm -rf {} + 2>/dev/null || true
find "$R" -name '*.pyc' -not -path '*/.git/*' -delete 2>/dev/null || true
echo "  remaining: $(find "$R" -name '__pycache__' -o -name '*.pyc' | grep -v '/.git/' | wc -l)"

echo "--- 4. section 6: rebuild both deliverable folders ---"
bash "$R/src/final/build_package.sh" 2>&1 | tail -6

echo "--- 5. section 7: isolated-package re-verification ---"
bash "$R/src/final/verify_isolated.sh" 2>&1 | tail -4

echo "--- 6. section 8: refresh the Windows copy ---"
bash "$R/src/final/finalize_windows.sh" 2>&1 | tail -4

echo "--- 7. organizer-private must now carry the phase log ---"
ls -la "$R/organizer-private/logs/PHASE_FINAL_LOG.md"
grep -c '5066.07' "$R/organizer-private/logs/PHASE_FINAL_LOG.md"
grep -c '5066.07' "$R/organizer-private/SOLVE_PATH_PRIVATE.md"
echo "FIN-DOCS-OK"
