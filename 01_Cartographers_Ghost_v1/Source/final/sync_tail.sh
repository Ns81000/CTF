#!/bin/bash
# sync_tail.sh -- Phase FINAL: publish the remaining helper drivers used this
# session and commit them, so the repo holds every tool the phase ran.
set -e
R=/home/manish/cartographer-build
STAGE=/mnt/d/gandu/_stage/s5_final
cd "$R"
for f in finalize_docs.sh report_windows.sh check_docs.sh watch_runA.py \
         after_runA.sh finalize_windows.sh commit_final.sh report_hashes.sh; do
    if [ -f "$STAGE/$f" ]; then
        tr -d '\r' < "$STAGE/$f" > "src/final/$f"
        echo "  src/final/$f"
    fi
done
find "$R" -name '__pycache__' -type d -not -path '*/.git/*' -exec rm -rf {} + 2>/dev/null || true
find "$R" -name '*.pyc' -not -path '*/.git/*' -delete 2>/dev/null || true
git add -A
if git --no-pager diff --cached --quiet; then
    echo "  nothing to commit"
else
    git --no-pager commit -q -m "phase FINAL: publish the remaining verification drivers used this session"
fi
git --no-pager log --oneline -4
echo "--- working tree ---"
git --no-pager status --short
echo "TAIL-SYNC-OK"
