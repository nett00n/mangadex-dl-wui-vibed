#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

# Makefile — Developer shortcuts for mangadex-dl-wui.
#
# All targets run inside an ephemeral Docker container backed by a persistent
# pip-cache volume (mangadex-dl-wui-pip-cache). No local Python environment
# needed — only Docker.

.PHONY: ci ci-fix test lint fmt clean

REPORTS := reports

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

## Auto-format with black + isort in Docker.
fmt:
	./scripts/ci.sh --step=fmt --fix

# ── Housekeeping ──────────────────────────────────────────────────────────────

## Remove generated reports and tool caches.
clean:
	rm -rf $(REPORTS) .coverage .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
