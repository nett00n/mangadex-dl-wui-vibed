#!/usr/bin/env bash
#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#


# scripts/pre-commit.sh — Run pre-commit in an isolated Docker container.
#
# Usage:
#   ./scripts/pre-commit.sh              # run --all-files (default)
#   ./scripts/pre-commit.sh --hook-stage=manual
#   ./scripts/pre-commit.sh ruff         # run a specific hook on all files
#
# Named Docker volumes:
#   mangadex-dl-wui-pip-cache        — pip download cache (shared with ci.sh)
#   mangadex-dl-wui-precommit-cache  — pre-commit hook environments

set -euo pipefail

PYTHON_IMAGE="python:3.12-slim"
PIP_CACHE_VOLUME="mangadex-dl-wui-pip-cache"
PRECOMMIT_CACHE_VOLUME="mangadex-dl-wui-precommit-cache"

# Pass any extra arguments through to pre-commit (e.g. hook ids, --hook-stage)
EXTRA_ARGS="${*}"

if command -v docker &>/dev/null; then
    CONTAINER_CMD="sudo docker"
elif command -v podman &>/dev/null; then
    CONTAINER_CMD="podman"
else
    echo "error: neither docker nor podman found in PATH" >&2; exit 1
fi

${CONTAINER_CMD} volume create "${PIP_CACHE_VOLUME}" > /dev/null
${CONTAINER_CMD} volume create "${PRECOMMIT_CACHE_VOLUME}" > /dev/null

# git is required by pre-commit; not present in python:3.12-slim by default
PREREQS_CMD="apt-get update -qq && apt-get install -y -qq --no-install-recommends git 2>/dev/null"

INSTALL_CMD="pip install --quiet --root-user-action=ignore --cache-dir /pip-cache pre-commit"

RUN_CMD="pre-commit run --all-files ${EXTRA_ARGS}"

${CONTAINER_CMD} run --rm \
    -v "$(pwd)":/app \
    -v "${PIP_CACHE_VOLUME}":/pip-cache \
    -v "${PRECOMMIT_CACHE_VOLUME}":/root/.cache/pre-commit \
    -w /app \
    "${PYTHON_IMAGE}" \
    bash -c "set -euo pipefail; ${PREREQS_CMD} && ${INSTALL_CMD} && ${RUN_CMD}"
