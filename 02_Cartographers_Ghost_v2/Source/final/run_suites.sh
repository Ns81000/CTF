#!/bin/bash
# Run the given stage suites in series and keep the logs.  SERIAL ONLY.
set -u
REPO=/home/ns8pc/ghost-build
cd "$REPO"
mkdir -p organizer-private/runs
rc=0
run_one() {
    script="$1"
    label="$(basename "$(dirname "$script")")"
    log="organizer-private/runs/${label}.log"
    bash "$script" > "$log" 2>&1
    status=$?
    printf '%-16s %-28s %s\n' "$label" \
        "$(grep -E '[0-9]+ checks, [0-9]+ failed' "$log" | tail -1)" \
        "$([ $status -eq 0 ] && echo OK || echo NOTOK)"
    [ $status -eq 0 ] || rc=1
    return 0
}
for suite in "$@"; do
    run_one "$suite"
done
exit $rc
