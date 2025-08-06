# AI Review Hook

This project provides a pre-commit hook for AI-assisted code reviews using the OpenAI API.

## Features

- Perform automated code reviews with AI assistance
- Configurable OpenAI model and endpoint
- Use environment variables for API keys
- Customizable through command-line arguments and configuration files

## Installation

```sh
pip install .
```

## Configuration

A sample configuration file `ai-review-config.json` is provided. You can customize the model, API key environment variable, and base URL.

## Usage

Add the following to your `.pre-commit-config.yaml`:

```yaml
-   repo: local
    hooks:
    -   id: ai-review
```

Run the pre-commit hook manually:

```sh
pre-commit run ai-review --all-files
```

## Command Line Options

- `--api-key-env`: Specify environment variable for API key (default: `OPENAI_API_KEY`)
- `--base-url`: Set a custom API base URL
- `--model`: Choose OpenAI model (default: `gpt-3.5-turbo`)
- `--config-file`: Specify path to a JSON configuration file
- `--context-lines`: Number of context lines in git diff (default: 3)
- `--verbose, -v`: Enable verbose output

## License

MIT License
