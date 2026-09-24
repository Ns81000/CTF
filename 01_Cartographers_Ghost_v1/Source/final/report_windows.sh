#!/bin/bash
# report_windows.sh -- hash tables for the two folders ON THE WINDOWS SURFACE,
# plus the zero-organizer-content assertion against the shipped zip.
set -e
W=/mnt/d/gandu
for d in drive-upload organizer-private; do
    echo "=============================================================="
    echo "== D:\\gandu\\$d"
    echo "=============================================================="
    cd "$W/$d"
    find . -type f | sed 's|^\./||' | sort | while read -r f; do
        printf '%10d  %s  %s\n' "$(stat -c%s "$f")" \
            "$(sha256sum "$f" | cut -c1-64)" "$f"
    done
    echo "files: $(find . -type f | wc -l)"
done
echo
echo "== the shipped zip, itemised =="
cd "$W/drive-upload" && unzip -l cartographer.zip
echo
echo "== zero-organizer-content assertion, on the WINDOWS copy of the zip =="
if unzip -l "$W/drive-upload/cartographer.zip" | grep -Eqi 'SOLVE_PATH|HINTS|TRYHACKME|BUILD_SPEC|PHASE_|KICKOFF|\.md$'; then
    echo "  LEAK: organizer content inside the Drive zip"; exit 1
fi
echo "  -> no organizer content in the Drive zip"
echo
echo "== CARTO_TEST_TIME_SCALE must be absent from the Windows-side binaries =="
cd "$W/drive-upload" && rm -rf /tmp/winchk && mkdir -p /tmp/winchk \
    && unzip -q cartographer.zip -d /tmp/winchk
for b in $(cd /tmp/winchk/cartographer && find . -type f -not -name 'README_FOR_SOLVER.txt' \
        -not -name '*.png' -not -name '*.wav' | sed 's|^\./||'); do
    if strings "/tmp/winchk/cartographer/$b" | grep -q CARTO_TEST_TIME_SCALE; then
        echo "  LEAK in $b"; exit 1
    fi
    echo "  clean: $b"
done
rm -rf /tmp/winchk
echo "WINDOWS-REPORT-OK"
