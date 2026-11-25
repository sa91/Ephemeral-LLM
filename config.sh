# Shared settings for build.sh, ephemeral-llm and verify_purge.sh. Sourced, not run.

IMAGE="${IMAGE:-ephemeral-llm:latest}"
CONTAINER="${CONTAINER:-ephemeral-llm}"
LABEL="org.ephemeral-llm.session"

# Which Docker VM this kit talks to. Pinned by name, so starting another Colima profile
# (the GPU one) cannot silently redirect the CPU kit. ephemeral-llm-gpu overrides these.
export DOCKER_CONTEXT="${DOCKER_CONTEXT:-colima}"
DOCKERFILE="${DOCKERFILE:-Dockerfile}"
EXTRA_RUN_ARGS="${EXTRA_RUN_ARGS:-}"      # extra `docker run` flags (the GPU device)
EXPECT_DEVICES="${EXPECT_DEVICES:-0}"     # how many host devices the sealed container may have

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
