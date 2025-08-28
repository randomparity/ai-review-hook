# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.
``

Project overview
- Python package that provides a pre-commit hook and CLI for AI-assisted code review using the OpenAI API.
- Entry point: ai_review_hook.main:main exposed as the ai-review console script.
- Key capabilities: secret redaction, diff-only mode, file filtering via glob patterns, optional filetype-specific prompts, retry/backoff, and parallel review.

Common commands
Environment setup
- Install dev deps (pytest, pre-commit, etc.):
  - pip install -r requirements-dev.txt
- Optional (recommended for local CLI testing): install the package in editable mode:
  - pip install -e .

Build, linting, tests (Makefile)
- One-time setup (creates .venv, installs dev deps):
  - make setup
- Lint:
  - make lint
- Format code:
  - make format
- Typecheck and security scan:
  - make typecheck
  - make security
- Run tests:
  - make test
- Full CI suite (what CI runs):
  - make ci
- Run all pre-commit hooks locally:
  - pre-commit run -a

Tests (single-file or single-test examples)
- Run a specific test file:
  - .venv/bin/pytest tests/test_main.py -q
- Run a single test:
  - .venv/bin/pytest tests/test_main.py::test_review_file_pass -q
- Filter by keyword expression:
  - .venv/bin/pytest -k "redact and not jwt"

CLI and hook usage (local development)
- Ensure an API key env var is set (defaults to OPENAI_API_KEY):
  - export OPENAI_API_KEY={{OPENAI_API_KEY}}
- After editable install, view CLI help:
  - ai-review --help
- Try the hook as pre-commit would execute it, using this repo as the source of the hook definition:
  - pre-commit try-repo . ai-review --all-files --verbose --hook-stage commit -- --diff-only -v
  Notes:
  - The hook id is defined in .pre-commit-hooks.yaml (ai-review).
  - Arguments after -- are passed to the hook (e.g., --model, --base-url, --filetype-prompts, etc.).
- Typical consumer configuration (from README) to add to another repo’s .pre-commit-config.yaml:
  - repos:
    - repo: https://github.com/randomparity/ai-review-hook
      rev: v1.0.0
      hooks:
        - id: ai-review

Important repo-specific behavior and conventions
- PASS/FAIL contract: The model must begin its first line with AI-REVIEW:[PASS] or AI-REVIEW:[FAIL]. The hook fails closed if markers are missing or a FAIL marker appears anywhere in the response.
- Secret redaction: Before sending any content to the AI API, the tool redacts common secrets (AWS keys, GitHub tokens, JWTs, bearer tokens, DB URLs, private keys, generic API keys). Redaction happens for both diff and file content; binary files are detected and replaced with a placeholder to avoid exfiltration.
- Diff handling: The tool pulls git diffs (staged first, falls back to unstaged) with configurable context lines. For large diffs, it extracts hunks and truncates with explicit markers.
- File filtering: Include/exclude glob patterns are supported; exclude has precedence. Patterns apply to both full paths and basenames. Helper: parse_file_patterns([...]) normalizes comma-separated inputs.
- Filetype-specific prompts: Optional JSON mapping of glob patterns to prompt templates. Matching priority: exact filename, then full-path globs, then extension globs, then basename globs (first match wins). Placeholders {filename}, {diff}, {content}, {diff_only_note} are supported. If no custom match, a comprehensive default prompt is used.
- Parallelism: When --jobs > 1, files are reviewed concurrently with ThreadPoolExecutor; results are re-ordered to match input.
- Retry/backoff: API errors considered retryable (rate limit, timeout, connection, some 5xx/422) trigger exponential backoff with jitter; capped by --max-retries and delay settings.
- Output: Optionally writes a combined review log with per-file sections when --output-file is provided. Process exit code is nonzero if any file fails review.

Structure and key files
- src/ai_review_hook/main.py: CLI, argument parsing, AIReviewer class, redaction, diff/content handling, pattern parsing, prompts selection, retry/parallel orchestration, and program exit control.
- src/ai_review_hook/__init__.py: version metadata.
- .pre-commit-hooks.yaml: defines the ai-review hook for consumers.
- .pre-commit-config.yaml: local dev hooks (ruff, ruff-format, and a local pytest hook which runs on commit).
- tests/: unit tests covering redaction, prompt selection and glob priority, truncation, retries/backoff, and parallel execution.
- pyproject.toml: project metadata; pytest and ruff configuration; console script entry point (ai-review).
- .github/workflows/ci.yml: runs pytest on pushes/PRs to main.

Key options to know (see README for full list)
- --api-key-env: environment variable name for API key (default OPENAI_API_KEY)
- --base-url: custom API base for compatible providers; requires --allow-unsafe-base-url if not an official OpenAI endpoint
- --model: model identifier (default gpt-4o-mini)
- --diff-only: send only the diff to the model (useful for sensitive repos)
- --jobs/-j: parallel reviews
- --filetype-prompts: JSON file mapping glob patterns to prompt templates
- --max-diff-bytes / --max-content-bytes: size limits with truncation markers
- --context-lines: git diff context size

CI
- GitHub Actions runs `make ci` on Python 3.12. Prefer the same Makefile targets locally before commit/push.

Notes from README
- Quick Start and usage examples for consumers are in README.md, including how to add this hook to a project, configure models/base URLs, filter files, enable parallelism, and use filetype-specific prompts with glob patterns.
- Development setup in this repo: pip install -r requirements-dev.txt and pre-commit install.
