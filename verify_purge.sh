#!/bin/bash
# After kill: five checks, written to ~/PrivateRedactor/evidence/PURGE_REPORT_<time>.txt.
# The purge counts only if the report ends with RESULT: PURGED.
# Usage: verify_purge.sh [--outputs]     (--outputs also deletes the redacted copies in /tmp)
set -uo pipefail
KIT="$(cd "$(dirname "$0")" && pwd)"
. "$KIT/config.sh"
umask 077
mkdir -p "$EVIDENCE"

report="$EVIDENCE/PURGE_REPORT_$(date +%Y%m%d-%H%M%S).txt"
fails=0
say()  { echo "$*" | tee -a "$report"; }
pass() { say "PASS  $1  $2"; }
fail() { say "FAIL  $1  $2"; fails=$((fails + 1)); }
info() { say "INFO  $1  $2"; }

say "Purge report $(date -u +%Y-%m-%dT%H:%M:%SZ) session=${SESSION:-unknown}"

# 1. the session container is gone, and with it the RAM-only /work
if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
    fail 1 "container $CONTAINER still exists"
else
    pass 1 "container $CONTAINER does not exist; its RAM-only /work (inbox, originals, outbox, identifiers, notes) is gone"
fi

# 2. no other container from this kit
left="$(docker ps -aq --filter "label=$LABEL" 2>/dev/null | wc -l | tr -d ' ')"
if [ "$left" = "0" ]; then pass 2 "no container with the $LABEL label exists"; else fail 2 "$left labelled container(s) survived"; fi

# 3. copies of the inputs on the Mac (same size and SHA-256). Paths go to the report only.
inputs="$EVIDENCE/inputs_${SESSION:-none}.sha256"
if [ -s "$inputs" ]; then
    # Spotlight finds same-size files across the home folder in seconds; temp folders and the
    # Trash are not indexed, so those are walked. (A full walk of the home folder took 10 minutes.)
    n=0
    for s in $(awk '{print $2}' "$inputs" | sort -u); do
        while IFS= read -r f; do
            [ -f "$f" ] || continue
            h="$(shasum -a 256 < "$f" 2>/dev/null | awk '{print $1}')"
            if grep -q "^$h " "$inputs"; then
                n=$((n + 1))
                echo "INFO  3    identical to an input: $f" >> "$report"
            fi
        done < <( { mdfind -onlyin "$HOME" "kMDItemFSSize == $s" 2>/dev/null
                    find /private/tmp "${TMPDIR%/}" "$HOME/.Trash" -type f -size "${s}c" 2>/dev/null; } | sort -u )
    done
    info 3 "$n file(s) on the Mac are identical to an input; paths are in the report. Searched: Spotlight index of the home folder, temp folders, Trash. Expect one per original, where you keep it."
else
    info 3 "no input fingerprints recorded for this session"
fi

# 4. redacted copies on the Mac
outputs() { find "$OUT_DIR" -maxdepth 1 -type f -name 'REDACTED_*' \( -name '*.pdf' -o -name '*.xlsx' -o -name '*.csv' -o -name '*.tsv' \) -user "$(id -un)" 2>/dev/null; }
if [ "${1:-}" = "--outputs" ]; then
    outputs | while IFS= read -r f; do rm -f "$f"; done
    if [ -n "$(outputs)" ]; then fail 4 "redacted copies still in /tmp after --outputs"; else pass 4 "/tmp/REDACTED_* (pdf, xlsx, csv, tsv) deleted"; fi
elif [ -n "$(outputs)" ]; then
    info 4 "redacted copies kept as /tmp/REDACTED_* ($(outputs | wc -l | tr -d ' ') file(s): pdf, xlsx, csv, tsv); delete with: ./ephemeral-llm clean --host"
else
    pass 4 "no redacted copies on the Mac"
fi

# 5. disk encryption covers the Docker VM disk and deleted SSD blocks
if fdesetup status 2>/dev/null | grep -q "FileVault is On"; then pass 5 "FileVault is On"; else fail 5 "FileVault is not On"; fi

if docker image inspect "$IMAGE" >/dev/null 2>&1; then
    info -  "image $IMAGE kept (model and code only, no documents)"
fi

if [ "$fails" -eq 0 ]; then say "RESULT: PURGED"; else say "RESULT: NOT PURGED ($fails check(s) failed)"; fi
echo "report: $report"
[ "$fails" -eq 0 ]
