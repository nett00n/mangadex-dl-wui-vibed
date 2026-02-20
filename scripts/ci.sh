#!/usr/bin/env bash

#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

# scripts/ci.sh — Run CI checks in an isolated Docker container.
#
# Usage:
#   ./scripts/ci.sh                      # all checks (default)
#   ./scripts/ci.sh --fix                # auto-format, then all checks
#   ./scripts/ci.sh --step=fmt           # format check only
#   ./scripts/ci.sh --step=fmt --fix     # auto-format only
#   ./scripts/ci.sh --step=lint          # ruff + mypy only
#   ./scripts/ci.sh --step=test          # pytest + coverage only
#
# A named Docker volume (mangadex-dl-wui-pip-cache) caches pip downloads
# so subsequent runs are significantly faster.
# Report files written to reports/ are re-owned to the calling user.

set -euo pipefail

FIX=0
STEP=all

for arg in "$@"; do
    case "${arg}" in
        --fix)     FIX=1 ;;
        --step=*)  STEP="${arg#--step=}" ;;
        *)         echo "Unknown argument: ${arg}" >&2; exit 1 ;;
    esac
done

case "${STEP}" in
    all|fmt|lint|test) ;;
    *) echo "Unknown step '${STEP}' — valid values: all, fmt, lint, test" >&2; exit 1 ;;
esac

PYTHON_IMAGE="python:3.12-slim"
PIP_CACHE_VOLUME="mangadex-dl-wui-pip-cache"
REPORTS_DIR="reports"
HOST_UID="$(id -u)"
HOST_GID="$(id -g)"

if command -v docker &>/dev/null; then
    CONTAINER_CMD="sudo docker"
elif command -v podman &>/dev/null; then
    CONTAINER_CMD="podman"
else
    echo "error: neither docker nor podman found in PATH" >&2; exit 1
fi

${CONTAINER_CMD} volume create "${PIP_CACHE_VOLUME}" > /dev/null

# Install packages with version constraints matching pyproject.toml.
# mangadex-downloader is skipped — not needed for tests.
INSTALL_CMD="pip install --quiet --root-user-action=ignore --cache-dir /pip-cache \
    'flask>=3.1,<4' \
    'rq>=2.0,<3' \
    'redis>=5.0,<6' \
    'gunicorn>=23.0,<24' \
    'minify-html>=0.15,<1' \
    'pytest>=8.0,<9' \
    'pytest-cov>=6.0,<7' \
    'pytest-timeout>=2.3,<3' \
    'ruff>=0.8,<1' \
    'mypy>=1.13,<2' \
    'types-redis>=4.6,<5' \
    'fakeredis>=2.26,<3' \
  && pip install --quiet --root-user-action=ignore --no-deps -e ."

# Build the step command sequence.
STEPS_CMD=""

if [ "${STEP}" = "all" ] || [ "${STEP}" = "fmt" ]; then
    if [ "${FIX}" -eq 1 ]; then
        FMT_CMD="ruff format app/ tests/"
    else
        FMT_CMD="ruff format --check app/ tests/"
    fi
    STEPS_CMD="${STEPS_CMD:+${STEPS_CMD} && }${FMT_CMD}"
fi

if [ "${STEP}" = "all" ] || [ "${STEP}" = "lint" ]; then
    LINT_CMD="ruff check app/ tests/ \
    && mkdir -p ${REPORTS_DIR}/mypy \
    && mypy app/ 2>&1 | tee ${REPORTS_DIR}/mypy/index.txt"
    STEPS_CMD="${STEPS_CMD:+${STEPS_CMD} && }${LINT_CMD}"
fi

if [ "${STEP}" = "all" ] || [ "${STEP}" = "test" ]; then
    TEST_CMD="mkdir -p ${REPORTS_DIR} \
    && pytest -m 'not ui' -q \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=xml:${REPORTS_DIR}/coverage.xml \
    --cov-report=html:${REPORTS_DIR}/htmlcov"
    STEPS_CMD="${STEPS_CMD:+${STEPS_CMD} && }${TEST_CMD}"
fi

# Re-own any generated report files so they belong to the calling user,
# not root (the default Docker user).
CHOWN_CMD="chown -R ${HOST_UID}:${HOST_GID} /app/${REPORTS_DIR} /app/.coverage 2>/dev/null || true"

${CONTAINER_CMD} run --rm \
  -v "$(pwd)":/app \
  -v "${PIP_CACHE_VOLUME}":/pip-cache \
  -w /app \
  "${PYTHON_IMAGE}" \
  bash -c "set -euo pipefail; trap '${CHOWN_CMD}' EXIT; ${INSTALL_CMD} && ${STEPS_CMD}"
