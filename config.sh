# Shared settings for build.sh, ephemeral-llm and verify_purge.sh. Sourced, not run.

IMAGE="ephemeral-llm:latest"
CONTAINER="${CONTAINER:-ephemeral-llm}"
LABEL="org.ephemeral-llm.session"

# Model baked into the image. Largest current Qwen that fits a 16 GB Mac inside the VM (6.6 GB of weights).
# Faster and weaker: MODEL=qwen3.5:4b-q4_K_M ./build.sh
MODEL="${MODEL:-qwen3.5:9b-q4_K_M}"
NUM_CTX="${NUM_CTX:-16384}"

# Base image tag used the first time; build.sh then pins its digest in container/base.lock.
BASE_TAG="${BASE_TAG:-ollama/ollama:latest}"

# Container limits. The RAM work area (/work) counts against CONTAINER_MEM.
# Sized for a 16 GB Mac with the Docker VM at 12 GB (see README).
CONTAINER_MEM="${CONTAINER_MEM:-10g}"
WORK_SIZE="${WORK_SIZE:-1g}"

# On the Mac
HOST_DIR="$HOME/PrivateRedactor"
IDENTIFIERS="$HOST_DIR/identifiers.txt"
EVIDENCE="$HOST_DIR/evidence"
# Redacted PDFs are written straight into OUT_DIR as REDACTED_*.pdf (mode 600); their reports go to REPORTS.
OUT_DIR="/private/tmp"
REPORTS="$EVIDENCE/reports"
