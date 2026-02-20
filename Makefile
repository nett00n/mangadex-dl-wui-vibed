#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

# Makefile — Developer shortcuts for mangadex-dl-wui.
#
# All targets run inside an ephemeral Docker container backed by a persistent
# pip-cache volume (mangadex-dl-wui-pip-cache). Only Docker is required.

.PHONY: ci ci-fix test lint fmt pre-commit clean check-minified check-cache-minified

REPORTS          := reports
PYTHON_IMAGE     := python:3.12-slim
PIP_CACHE_VOLUME := mangadex-dl-wui-pip-cache
CONTAINER_CMD    := $(shell command -v docker >/dev/null 2>&1 && echo "sudo docker" || echo "podman")

# Minimal app runtime install (no dev tools, no mangadex-downloader).
DOCKER_APP_RUN = $(CONTAINER_CMD) run --rm \
  -v "$(CURDIR)":/app \
  -v "$(PIP_CACHE_VOLUME)":/pip-cache \
  -w /app \
  "$(PYTHON_IMAGE)" \
  bash -c "pip install --quiet --root-user-action=ignore --cache-dir /pip-cache \
    'flask>=3.1,<4' 'rq>=2.0,<3' 'redis>=5.0,<6' 'gunicorn>=23.0,<24' 'minify-html>=0.15,<1' \
  && pip install --quiet --root-user-action=ignore --no-deps -e . \
  && python3

# ── Full pipeline ─────────────────────────────────────────────────────────────

## Run all CI checks in Docker (fmt-check → lint → mypy → test + coverage).
ci:
	./scripts/ci.sh

## Auto-format files, then run all CI checks in Docker.
ci-fix:
	./scripts/ci.sh --fix

# ── Individual steps ──────────────────────────────────────────────────────────

## Run tests with coverage in Docker (XML + HTML reports written to reports/).
test:
	./scripts/ci.sh --step=test

## Run ruff + mypy in Docker (report written to reports/mypy/index.txt).
lint:
	./scripts/ci.sh --step=lint

## Auto-format with ruff in Docker.
fmt:
	./scripts/ci.sh --step=fmt --fix

## Run pre-commit hooks against all files in Docker.
## Pass ARGS to run a specific hook: make pre-commit ARGS="ruff"
pre-commit:
	./scripts/pre-commit.sh $(ARGS)

# ── Debug helpers ─────────────────────────────────────────────────────────────

## Inspect minified index page output (attribute forms, data URIs, script content).
check-minified:
	$(DOCKER_APP_RUN) scripts/check_minified.py"

## Inspect minified cache page output (attribute forms per class).
check-cache-minified:
	$(DOCKER_APP_RUN) scripts/check_cache_minified.py"

# ── Housekeeping ──────────────────────────────────────────────────────────────

## Remove generated reports and tool caches.
clean:
	rm -rf $(REPORTS) .coverage .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
