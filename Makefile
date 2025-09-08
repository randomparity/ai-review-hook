# Makefile for VidClean
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help
.PHONY: help check-python setup install clean clean-venv venv-info lint format typecheck security test ci

# Required Python version from .python-version file
REQUIRED_PYTHON_VERSION := $(shell cat .python-version 2>/dev/null || echo "3.12.11")
REQUIRED_PYTHON_MAJOR := $(shell echo $(REQUIRED_PYTHON_VERSION) | cut -d. -f1,2)

COV := 79
SRC  := src
TESTS := tests
VENV := .venv
REQ_FILE ?= requirements-dev.txt

# Python & tools inside the venv
PY         := $(VENV)/bin/python
PIP        := $(VENV)/bin/pip
RUFF       := $(PY) -m ruff
MYPY       := $(PY) -m mypy
PYTEST     := $(PY) -m pytest
BLACK      := $(PY) -m black
BANDIT     := $(PY) -m bandit
PRECOMMIT  := $(PY) -m pre_commit

# Detect OS for guidance messages
UNAME_S := $(shell uname -s)

# Guard: require the venv and correct Python to be used
define REQUIRE_VENV
	@test -x "$(VENV)/bin/python" || { echo "❌ Missing venv. Run 'make setup' first."; exit 1; }
	@$(VENV)/bin/python -c "import sys, pathlib; p=pathlib.Path(sys.prefix).resolve(); 		assert '$(VENV)' in str(p), f'Not using $(VENV) (sys.prefix={p})'" || { 		echo "❌ Not using $(VENV). Use $(VENV)/bin/... or run 'make setup'."; exit 1; }
	@v="$$($(VENV)/bin/python -c 'import sys; print("%d.%d"%sys.version_info[:2])')"; 		req="$(REQUIRED_PYTHON_MAJOR)"; 		[ "$$v" = "$$req" ] || { echo "❌ Python $$v != required $$req. See 'make check-python'."; exit 1; }
endef
export REQUIRE_VENV

help: ## Show this help
	@awk 'BEGIN{FS=":.*?## "}; /^[a-zA-Z0-9_-]+:.*?## /{printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}' $(firstword $(MAKEFILE_LIST)) | sort

# Validate python toolchain on the host and print guidance
check-python: ## Validate host has a compatible Python and venv tooling
	@echo '🔎 Checking Python toolchain...'
	@if ! command -v python3 >/dev/null; then echo '❌ python3 not found'; exit 1; fi
	@HOST_PY=$$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")'); 	REQ='$(REQUIRED_PYTHON_MAJOR)'; 	if [ "$$HOST_PY" != "$$REQ" ]; then 		echo '⚠️  Host Python ('"$$HOST_PY"') != required ('"$$REQ"')'; 		echo '   Consider pyenv or uv to install the exact version.'; 	fi
	@echo '✅ Python toolchain looks OK.'

setup: ## Create venv and install dev deps
	@# Prefer uv, then pyenv, then system python for venv creation and deps
	@if command -v uv >/dev/null 2>&1; then \

		echo '🔧 Using uv to create venv and install dev dependencies'; \

		[ -d $(VENV) ] || uv venv --python '$(REQUIRED_PYTHON_VERSION)' '$(VENV)' || uv venv '$(VENV)'; \

		uv pip install -p '$(VENV)/bin/python' -U pip; \

		if [ -f pyproject.toml ]; then uv pip install -p '$(VENV)/bin/python' -e '.[dev]'; fi; \

	elif command -v pyenv >/dev/null 2>&1; then \

		echo '🔧 Using pyenv to create venv and install dev dependencies'; \

		pyenv install -s '$(REQUIRED_PYTHON_VERSION)'; \

		[ -d $(VENV) ] || PYENV_VERSION='$(REQUIRED_PYTHON_VERSION)' pyenv exec python -m venv '$(VENV)'; \

		'$(VENV)/bin/python' -m pip install -U pip; \

		if [ -f pyproject.toml ]; then '$(VENV)/bin/pip' install -e '.[dev]'; fi; \

	else \

		echo '🔧 Using system python3 to create venv and install dev dependencies'; \

		command -v python3 >/dev/null || { echo '❌ python3 not found'; exit 1; }; \

		[ -d $(VENV) ] || python3 -m venv '$(VENV)'; \

		'$(VENV)/bin/python' -m pip install -U pip; \

		if [ -f pyproject.toml ]; then '$(VENV)/bin/pip' install -e '.[dev]'; fi; \

	fi; \

	@# Optional git hooks if pre-commit is installed in the venv
	@$(PRECOMMIT) install --hook-type commit-msg --hook-type pre-push || true

install: setup ## Alias

venv-info: ## Print venv diagnostics
	@echo 'VENV: $(VENV)'
	@echo 'PY:   $(PY)'
	@$(PY) -c 'import sys,platform; print("sys.prefix=", sys.prefix); print("version=", platform.python_version())'
	@$(RUFF) --version || echo 'ruff not installed in venv'
	@$(MYPY) --version || echo 'mypy not installed in venv'
	@$(BLACK) --version || echo 'ruff not installed in venv'
	@$(PYTEST) --version || echo 'pytest not installed in venv'

lint: ## Run ruff linting
	$(REQUIRE_VENV)
	$(RUFF) check $(SRC)/ $(TESTS)/

format: ## Run black formatting
	$(REQUIRE_VENV)
	$(BLACK) $(SRC)/ $(TESTS)/

typecheck: ## Run mypy type checking
	$(REQUIRE_VENV)
	$(MYPY) --strict $(SRC)/

security: ## Run bandit security scanning
	$(REQUIRE_VENV)
	$(BANDIT) -q -r $(SRC)/

test: ## Run pytest with coverage gate
	$(REQUIRE_VENV)
	$(PYTEST) $(TESTS)/ -q --tb=short --cov=$(SRC) --cov-report=term-missing --cov-report=xml --cov-fail-under=$(COV) --junit-xml=junit.xml

ci: ## Run all CI checks (lint, format-check, typecheck, security, test)
	$(REQUIRE_VENV)
	$(RUFF) check $(SRC)/ $(TESTS)/
	$(BLACK) $(SRC)/
	$(MYPY) --strict $(SRC)/
	$(BANDIT) -q -r $(SRC)/
	$(PYTEST) $(TESTS)/ -q --tb=short --cov=$(SRC) --cov-report=term-missing --cov-report=xml --cov-fail-under=$(COV) --junit-xml=junit.xml

clean: ## Remove caches and build artifacts
	rm -rf .mypy_cache .ruff_cache .pytest_cache .coverage htmlcov dist build *.egg-info .reports

clean-venv: ## Remove the virtual environment
	rm -rf $(VENV)
