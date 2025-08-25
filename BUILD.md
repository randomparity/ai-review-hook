# Build and Development

This document covers local build and install instructions for working on ai-review-hook.

## Editable install

Install the package in editable mode so changes are picked up without reinstalling:

```sh
pip install -e .
```

If you haven't yet, install development dependencies and pre-commit hooks:

```sh
pip install -r requirements-dev.txt
pre-commit install
```

## Running the CLI locally

```sh
ai-review --help
```

To run against the repo with pre-commit:

```sh
pre-commit run ai-review --all-files -- --verbose
```

## Tests

Run the test suite with pytest:

```sh
pytest -q
```
