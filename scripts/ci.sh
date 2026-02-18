#!/usr/bin/env bash

#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

# scripts/ci.sh — Run all CI checks in an isolated Docker container.
#
# Usage:
#   ./scripts/ci.sh              # run checks only (default)
#   ./scripts/ci.sh --fix        # auto-format files before checking
#
# Mirrors the checks enforced by pre-commit and the GitHub Actions pipeline.
# No local Python environment required — only Docker.

set -euo pipefail

FIX=0
for arg in "$@"; do
  case "$arg" in
    --fix) FIX=1 ;;
    *) echo "Unknown argument: $arg" >&2; exit 1 ;;
  esac
done

PYTHON_IMAGE="python:3.12-slim"
EXTRA_PACKAGES="flask rq redis gunicorn pytest pytest-cov pytest-timeout black isort ruff mypy types-redis fakeredis"

INSTALL_CMD="pip install -e '.[dev]' --no-deps -q && pip install ${EXTRA_PACKAGES} -q"

if [ "${FIX}" -eq 1 ]; then
  CHECK_CMD="black app/ tests/ && isort app/ tests/"
else
  CHECK_CMD="black --check app/ tests/ && isort --check app/ tests/"
fi

QUALITY_CMD="${CHECK_CMD} && ruff check app/ tests/"
TEST_CMD="pytest --ignore=tests/test_ui.py -q"

sudo docker run --rm \
  -v "$(pwd)":/app \
  -w /app \
  "${PYTHON_IMAGE}" \
  sh -c "${INSTALL_CMD} && ${QUALITY_CMD} && ${TEST_CMD}"
