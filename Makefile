# DataGuard — Developer Makefile
# Requires: GNU Make, Python 3.11+
# Usage: make <target>

.DEFAULT_GOAL := help
.PHONY: help install install-dev test lint format typecheck check clean

PYTHON := python
PIP    := pip

# ── Help ────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  DataGuard — Available Commands"
	@echo "  ──────────────────────────────────────────"
	@echo "  make install      Install runtime dependencies"
	@echo "  make install-dev  Install all dependencies including dev tools"
	@echo "  make test         Run all unit tests with coverage"
	@echo "  make lint         Check code style with ruff"
	@echo "  make format       Auto-format code with ruff"
	@echo "  make typecheck    Run mypy strict type checks"
	@echo "  make check        Run lint + typecheck + test (full CI suite)"
	@echo "  make clean        Remove build artifacts and cache"
	@echo ""

# ── Installation ─────────────────────────────────────────────────────────────
install:
	$(PIP) install .

install-dev:
	$(PIP) install -e ".[dev]"

# ── Testing ──────────────────────────────────────────────────────────────────
test:
	pytest

test-unit:
	pytest tests/unit/ -v

# ── Linting & Formatting ─────────────────────────────────────────────────────
lint:
	ruff check dataguard/ tests/

format:
	ruff format dataguard/ tests/
	ruff check --fix dataguard/ tests/

# ── Type Checking ────────────────────────────────────────────────────────────
typecheck:
	mypy dataguard/

# ── Full CI Suite ────────────────────────────────────────────────────────────
check: lint typecheck test
	@echo ""
	@echo "  ✅  All checks passed."
	@echo ""

# ── Cleanup ──────────────────────────────────────────────────────────────────
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info"  -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov"     -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage
	@echo "  🧹  Clean complete."
