UV ?= $(shell command -v uv 2>/dev/null || printf '%s' "$(HOME)/.local/bin/uv")
PACKAGE ?= mqtt_mcp

.PHONY: ensure-uv install run test check lint format type-check coverage audit build-check ci

ensure-uv:
	@command -v uv >/dev/null 2>&1 || test -x "$(UV)" || { \
		echo "uv not found; installing to $(HOME)/.local/bin"; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	}

install: ensure-uv
	$(UV) sync

run: ensure-uv
	$(UV) run python -m $(PACKAGE)

test: ensure-uv
	$(UV) run pytest

check: ensure-uv
	$(UV) run python -m compileall src tests

tree:
	find src tests -maxdepth 3 | sort

lint: ensure-uv
	$(UV) run ruff check src tests
	$(UV) run ruff format --check src tests

format: ensure-uv
	$(UV) run ruff format src tests
	$(UV) run ruff check --fix src tests

type-check: ensure-uv
	$(UV) run mypy src

coverage: ensure-uv
	$(UV) run pytest --cov --cov-report=term-missing

audit:
	# CVE-2026-4539 (pygments) has no fix release; ignored until upstream patch lands
	# PYSEC-2026-196 (pip) is a build-environment tool, not a project dependency
	$(UV) run pip-audit --ignore-vuln CVE-2026-4539 --ignore-vuln PYSEC-2026-196

build-check: ensure-uv
	$(UV) build

ci: lint type-check coverage audit build-check
