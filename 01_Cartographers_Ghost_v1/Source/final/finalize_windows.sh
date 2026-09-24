#!/bin/bash
# finalize_windows.sh -- Phase FINAL section 8: copy the two SEPARATE output
# folders to the Windows surface as top-level folders, and sweep stray build
# droppings out of the repo tree first.
set -e
R=/home/manish/cartographer-build
W=/mnt/d/gandu

echo "--- sweep __pycache__ / *.pyc out of the repo tree ---"
find "$R" -name '__pycache__' -type d -not -path '*/.git/*' -exec rm -rf {} + 2>/dev/null || true
find "$R" -name '*.pyc' -not -path '*/.git/*' -delete 2>/dev/null || true
echo "  remaining: $(find "$R" -name '__pycache__' -o -name '*.pyc' | grep -v '/.git/' | wc -l)"

for d in drive-upload organizer-private; do
    [ -d "$R/$d" ] || { echo "MISSING $R/$d (run build_package.sh first)"; exit 1; }
done

rm -rf "$W/drive-upload" "$W/organizer-private"
cp -r "$R/drive-upload"      "$W/"
cp -r "$R/organizer-private" "$W/"

echo "--- D:\\gandu\\ now holds ---"
ls -1 "$W" | sed 's/^/    /'
echo "--- drive-upload ---"
find "$W/drive-upload" -type f -printf '    %10s  %P\n' | sort -k2
echo "--- organizer-private ---"
find "$W/organizer-private" -type f -printf '    %10s  %P\n' | sort -k2
echo "WINDOWS-COPY-OK"
