# AI Review Hook

This project provides a pre-commit hook for AI-assisted code reviews using the OpenAI API.

# AI Review Hook

This project provides a pre-commit hook for AI-assisted code reviews using the OpenAI API.

## Quick Start

1.  **Install the hook** by adding the following to your `.pre-commit-config.yaml`:

    ```yaml
    repos:
    -   repo: https://github.com/randomparity/ai-review-hook
        rev: v1.0.0  # Replace with the desired tag or commit SHA
        hooks:
        -   id: ai-review
    ```

2.  **Set your OpenAI API key**:

    ```bash
    export OPENAI_API_KEY="your_api_key_here"
    ```

3.  **Install and run the hooks**:

    ```bash
    pip install pre-commit
    pre-commit install
    pre-commit run ai-review --all-files
    ```

For more detailed usage instructions, including pre-push setup and command-line options, please see the [Usage Guide](USAGE.md).

## Features

*   Perform automated code reviews with AI assistance
*   Configurable OpenAI model and endpoint
*   Use environment variables for API keys
*   Customizable through command-line arguments
*   Redacts secrets from code before sending to the model

## Command-Line Options

*   `--api-key-env`: Environment variable for the OpenAI API key (default: `OPENAI_API_KEY`)
*   `--base-url`: Custom API base URL for compatible APIs
*   `--model`: OpenAI model to use (default: `gpt-4o-mini`)
*   `--timeout`: API request timeout in seconds (default: 30)
*   `--max-diff-bytes`: Maximum diff size to send (default: 10000)
*   `--max-content-bytes`: Maximum file content size to send (0 for no limit)
*   `--diff-only`: Only send the diff to the model
*   `--context-lines`: Number of context lines for git diff (default: 3)
*   `--output-file`: File to save the complete review output
*   `-v`, `--verbose`: Enable verbose logging

## Development Setup

To contribute to this project, first clone the repository and then install the necessary dependencies for local development:

```sh
pip install -r requirements-dev.txt
```

Next, install the pre-commit hooks to ensure your contributions adhere to the project's linting and formatting standards:

```sh
pre-commit install
```

Now, every time you commit your changes, the pre-commit hooks will automatically run, checking for any issues. If any are found, the commit will be aborted, allowing you to fix the issues before committing again.

## License

MIT License
