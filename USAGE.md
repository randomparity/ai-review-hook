# AI Review Hook - Usage Guide

## Quick Start

1. **Set up your OpenAI API key:**
   ```bash
   export OPENAI_API_KEY="your_api_key_here"
   ```

2. **Install the package:**
   ```bash
   pip install .
   ```

3. **Test the command directly:**
   ```bash
   ai-review test_sample.py --verbose
   ```

## Pre-commit Integration

To integrate the AI review hook with pre-commit, you'll add a new repository to your `.pre-commit-config.yaml` file.

### Option 1: GitHub Repository

This is the recommended approach. Create a `.pre-commit-config.yaml` file in your project's root directory with the following content:

```yaml
repos:
-   repo: https://github.com/dave/ai-code-review
    rev: v1.0.0  # Replace with the desired tag or commit SHA
    hooks:
    -   id: ai-review
        name: AI Code Review
        args: ['--model', 'gpt-4', '--verbose']
```

### Option 2: Using a Configuration File

For more complex configurations, you can use a separate configuration file.

1.  Create `ai-review-config.json`:

    ```json
    {
      "api_key_env": "OPENAI_API_KEY",
      "base_url": null,
      "model": "gpt-4"
    }
    ```

2.  Update your `.pre-commit-config.yaml` to reference the configuration file:

    ```yaml
    repos:
    -   repo: https://github.com/randomparity/ai-code-review
        rev: v1.0.0 # Replace with the desired git tag or commit SHA
        hooks:
        -   id: ai-review
            name: AI Code Review
            args: ['--config-file', 'ai-review-config.json']
    ```

### Install and Run

Once your `.pre-commit-config.yaml` is set up, install the hooks and run them:

```bash
pip install pre-commit
pre-commit install
pre-commit run ai-review --all-files
```

## Pre-push Integration

For checks that might be too time-consuming to run on every commit, you can configure the AI review to run as a `pre-push` hook. This will run the review process only when you try to push your changes to the remote repository.

To configure the AI review as a `pre-push` hook, add the following to your `.pre-commit-config.yaml`:

```yaml
repos:
-   repo: https://github.com/dave/ai-code-review
    rev: v1.0.0 # Replace with the desired git tag or commit SHA
    hooks:
    -   id: ai-review-push
        name: AI Code Review (pre-push)
        stages: [pre-push]
        args: ['--model', 'gpt-4', '--verbose']
```

### Installation

To install the pre-push hook, run:

```bash
pre-commit install --hook-type pre-push
```

Now, `pre-commit` will run the `ai-review` hook before you push your code.

### When to use pre-commit vs. pre-push

*   **pre-commit**: Runs on every `git commit`. Use for fast checks like linters and formatters. The AI review can be used here for quick feedback, perhaps with a faster model.
*   **pre-push**: Runs on every `git push`. Use for slower, more comprehensive checks like running a full test suite or a more thorough AI review with a powerful model (e.g., GPT-4). This is a good place to put the AI review hook if you find it slows down your commits too much.

## Command Line Options

### Basic Usage
```bash
ai-review file1.py file2.js --verbose
```

### Custom Model
```bash
ai-review file.py --model gpt-4
```

### Custom API Endpoint (e.g., Azure OpenAI)
```bash
ai-review file.py --base-url https://your-endpoint.openai.azure.com/
```

### Custom API Key Environment Variable
```bash
export MY_API_KEY="your_key"
ai-review file.py --api-key-env MY_API_KEY
```

### Using Configuration File
```bash
ai-review file.py --config-file custom-config.json
```

### Custom Git Diff Context
```bash
# Use more context lines for better AI analysis (default is 3)
ai-review file.py --context-lines 10

# Use minimal context for focused reviews
ai-review file.py --context-lines 1
```

## Configuration File Format

```json
{
  "api_key_env": "OPENAI_API_KEY",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-4",
  "context_lines": 5,
  "comment": "context_lines controls how much surrounding code context is included in git diff"
}
```

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (default)
- `CUSTOM_API_KEY`: Custom API key (if using --api-key-env)

## AI Review Response Format

The AI will respond with one of:
- `AI-REVIEW:[PASS]` - Code is ready to commit
- `AI-REVIEW:[FAIL]` - Issues found that should be addressed

## Examples

### Testing with Sample File
```bash
# Stage a file with some issues
git add test_sample.py

# Run AI review
ai-review test_sample.py --verbose

# Expected output will show AI-REVIEW:[FAIL] with detailed feedback
```

### Integration with Git Workflow
```bash
# Make changes to your code
git add your_file.py

# Pre-commit will automatically run AI review
git commit -m "Your commit message"

# If AI review fails, fix issues and try again
```

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   ```
   Error: API key not found in environment variable 'OPENAI_API_KEY'
   ```
   Solution: Set your API key environment variable

2. **No Changes Detected**
   ```
   No changes detected in filename
   ```
   Solution: Make sure file is staged with `git add`

3. **OpenAI API Error**
   ```
   AI-REVIEW:[FAIL] Error during AI review: ...
   ```
   Solution: Check API key, internet connection, and OpenAI service status

### Debug Mode
Run with `--verbose` to see detailed output:
```bash
ai-review file.py --verbose
```

## Supported File Types

The hook is configured to review these file types:
- Python (.py)
- JavaScript (.js)
- TypeScript (.ts)
- Java (.java)
- C/C++ (.cpp, .c, .h, .hpp)
- Go (.go)
- Rust (.rs)
- Ruby (.rb)
- PHP (.php)
- Scala (.scala)
- Kotlin (.kotlin)
- Swift (.swift)
- C# (.cs)
- Shell scripts (.sh)
- YAML (.yaml, .yml)
- JSON (.json)
- Markdown (.md)
