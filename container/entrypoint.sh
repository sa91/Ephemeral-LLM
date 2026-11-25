#!/bin/bash
# Runs inside the container: prove the airgap, start the model, watch the inbox.
# Nothing printed here may contain a file name or document content.
set -u
umask 077

if ! python /app/redact.py airgap; then
    rm -rf /work/* /work/.[!.]* 2>/dev/null
    exit 3
fi

fs=$(awk '$2=="/work"{print $3}' /proc/mounts)
if [ "$fs" != "tmpfs" ]; then
    echo "work area is not RAM-only ($fs); refusing to start"
    exit 4
fi
echo "work area: tmpfs (RAM only); root filesystem read-only; user $(id -u)"

mkdir -p /work/staging /work/inbox /work/docs /work/redacted /work/notes "$HOME"

ollama serve >/tmp/ollama.log 2>&1 &
for i in $(seq 1 120); do
    ollama list >/dev/null 2>&1 && break
    sleep 1
done
if ! ollama list 2>/dev/null | grep -q "${MODEL%%:*}"; then
    echo "model server did not become ready or model $MODEL is missing"
    exit 5
fi
echo "model server ready: $MODEL"
touch /work/.ready

exec python /app/redact.py watch
