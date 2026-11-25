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

if [ "${LLM_API:-ollama}" = "openai" ]; then
    # GPU image: llama.cpp's server with the Vulkan backend, model offloaded to the GPU
    llama-server -m /opt/model.gguf --host 127.0.0.1 --port 11434 -c "${NUM_CTX:-16384}" \
        -ngl 999 --jinja --parallel 1 >/tmp/llama.log 2>&1 &
    for i in $(seq 1 170); do
        python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:11434/health', timeout=2).status == 200 else 1)" 2>/dev/null && break
        sleep 1
    done
    if ! python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:11434/health', timeout=2)" 2>/dev/null; then
        echo "model server did not become ready"
        grep -iE "error|failed|vulkan" /tmp/llama.log | tail -5
        exit 5
    fi
    # which device the model really landed on (no document content in these lines)
    gpu="$(llama-server --list-devices 2>/dev/null | grep -iE "^ *vulkan[0-9]+:" | head -1)"
    echo "model device:${gpu:- none found, running on CPU}"
else
    ollama serve >/tmp/ollama.log 2>&1 &
    for i in $(seq 1 120); do
        ollama list >/dev/null 2>&1 && break
        sleep 1
    done
    if ! ollama list 2>/dev/null | grep -q "${MODEL%%:*}"; then
        echo "model server did not become ready or model $MODEL is missing"
        exit 5
    fi
fi
echo "model server ready: $MODEL"
touch /work/.ready

exec python /app/redact.py watch
