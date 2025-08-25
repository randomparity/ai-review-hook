# Contributing

Thank you for your interest in contributing!

## Development setup

To contribute to this project, first clone the repository and then install the necessary dependencies for local development:

```sh
pip install -r requirements-dev.txt
```

Next, install the pre-commit hooks to ensure your contributions adhere to the project's linting and formatting standards:

```sh
pre-commit install
```

Now, every time you commit your changes, the pre-commit hooks will automatically run, checking for any issues. If any are found, the commit will be aborted, allowing you to fix the issues before committing again.

## Running tests

This project uses pytest for tests:

```sh
pytest -q
```

## Local CLI check

After changes, you can run the CLI help to verify argument wiring:

```sh
ai-review --help
```
