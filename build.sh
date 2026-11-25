#!/bin/bash
# One-time, online, no documents involved: build the image with the model inside.
set -euo pipefail
KIT="$(cd "$(dirname "$0")" && pwd)"
. "$KIT/config.sh"

docker info >/dev/null 2>&1 || { echo "Docker is not running. Start it with: colima start --cpus 6 --memory 10 --mount none" >&2; exit 1; }

# Pin the base image by digest the first time, so later rebuilds cannot silently change it.
lock="$KIT/container/base.lock"
if [ -s "$lock" ]; then
    BASE="$(cat "$lock")"
    echo "base image pinned: $BASE"
else
    docker pull "$BASE_TAG"
    BASE="$(docker inspect -f '{{index .RepoDigests 0}}' "$BASE_TAG")"
    echo "$BASE" > "$lock"
    echo "base image pinned to $BASE (delete container/base.lock to move to a newer one)"
fi

docker build -f "$KIT/container/$DOCKERFILE" ${BUILD_EXTRA_ARGS:-} --build-arg BASE="$BASE" --build-arg MODEL="$MODEL" -t "$IMAGE" "$KIT/container"

umask 077
mkdir -p "$HOST_DIR" "$EVIDENCE"
chmod 700 "$HOST_DIR" "$EVIDENCE"
if [ ! -f "$IDENTIFIERS" ]; then
    install -m 600 "$KIT/identifiers.example.txt" "$IDENTIFIERS"
    echo "created $IDENTIFIERS - fill it in before the first real run"
fi
echo "built $IMAGE with $MODEL"
