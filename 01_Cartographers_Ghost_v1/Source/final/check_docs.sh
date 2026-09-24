#!/bin/bash
# check_docs.sh -- sanity-check the synced Phase FINAL documents.
set -e
R=/home/manish/cartographer-build
cd "$R"
echo "--- line counts + CRLF check (CRLF must be 0) ---"
for f in SOLVE_PATH_PRIVATE.md HINTS.md TRYHACKME_ROOM_TEXT.md \
         src/final/README_FOR_SOLVER.txt logs/PHASE_FINAL_LOG.md; do
    printf '%-34s lines=%-5s CR=%s\n' "$f" "$(wc -l < "$f")" \
        "$(tr -cd '\r' < "$f" | wc -c)"
done
echo "--- HINTS.md: exactly 5 hints ---"
grep -c '^\*\*HINT [0-9]' HINTS.md
grep -n '^\*\*HINT [0-9]' HINTS.md
echo "--- TRYHACKME: the two scored answers ---"
grep -n 'Answer:\*\*' TRYHACKME_ROOM_TEXT.md
echo "--- SOLVE_PATH_PRIVATE.md: section headers ---"
grep -n '^## ' SOLVE_PATH_PRIVATE.md
echo "--- the real values, spot-checked ---"
grep -c '73070925a159f9e2_a5d66f1b2b5f596e_no_figure_sits_in_every_pixel' SOLVE_PATH_PRIVATE.md
grep -c 'no_figure_sits_in_every_pixel' SOLVE_PATH_PRIVATE.md
grep -c '0fab297110c73e9f' SOLVE_PATH_PRIVATE.md
grep -c 'stride 39, start 1512' SOLVE_PATH_PRIVATE.md
echo "DOCS-OK"
