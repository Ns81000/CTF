#!/bin/bash
# report_hashes.sh -- Phase FINAL section 9: file tables with sizes and
# SHA-256 hashes for BOTH deliverable folders.
set -e
R=/home/manish/cartographer-build
for d in drive-upload organizer-private; do
    echo "=============================================================="
    echo "== $d"
    echo "=============================================================="
    cd "$R/$d"
    find . -type f | sed 's|^\./||' | sort | while read -r f; do
        printf '%10d  %s  %s\n' "$(stat -c%s "$f")" \
            "$(sha256sum "$f" | cut -c1-64)" "$f"
    done
    echo "files: $(find . -type f | wc -l)"
done
echo
echo "== the shipped zip, itemised =="
cd "$R/drive-upload" && unzip -l cartographer.zip
