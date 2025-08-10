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

    Or a real-world example:

    ```yaml
    - repo: https://github.com/randomparity/ai-review-hook
      rev: v0.1.1
      hooks:
        - id: ai-review
          name: AI Code Review
          additional_dependencies: ['openai>=1.0.0', 'requests']
          args:
            - "--model"
            - "qwen/qwen3-coder"
            - "--verbose"
            - "--context-lines"
            - "5"
            - "--output-file"
            - "ai-review.log"
            - "--allow-unsafe-base-url"
            - "--base-url"
            - "https://openrouter.ai/api/v1"
            - "--api-key-env"
            - "OPENROUTER_API_KEY"
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


## Features

*   Perform automated code reviews with AI assistance
*   Configurable OpenAI model and endpoint
*   Use environment variables for API keys
*   Customizable through command-line arguments
*   **Enhanced Security**:
    *   Comprehensive secret redaction (AWS, GitHub, Slack, JWT, API keys, database URLs, etc.)
    *   Binary file detection and exclusion
    *   Secure base URL validation
    *   Diff-only mode for sensitive repositories
*   **High Performance**:
    *   Parallel processing for multiple files with `--jobs` option
    *   Intelligent content truncation with clear markers
    *   Optimized diff processing (hunk extraction)
    *   Smart redaction with performance optimizations

## Command-Line Options

*   `--api-key-env`: Environment variable for the OpenAI API key (default: `OPENAI_API_KEY`)
*   `--base-url`: Custom API base URL for compatible APIs
*   `--model`: OpenAI model to use (default: `gpt-4o-mini`)
*   `--timeout`: API request timeout in seconds (default: 30)
*   `--max-diff-bytes`: Maximum diff size to send in bytes (default: 10000)
*   `--max-content-bytes`: Maximum file content size to send in bytes (0 for no limit, default: 0)
*   `--diff-only`: Only send the diff to the model, not the full file content
*   `--max-tokens`: Maximum tokens in AI response (default: 2000)
*   `--temperature`: AI response temperature 0.0-2.0 (default: 0.1)
*   `--context-lines`: Number of context lines for git diff (default: 3)
*   `--jobs`, `-j`: Number of parallel jobs for reviewing multiple files (default: 1)
*   `--allow-unsafe-base-url`: Allow custom base URLs other than official OpenAI endpoints
*   `--output-file`: File to save the complete review output
*   `--include-files`: File patterns to include for review (e.g., '*.py' or '*.py,*.js'). Can be specified multiple times. If not specified, all files are included by default.
*   `--exclude-files`: File patterns to exclude from review (e.g., '*.test.py' or '*.test.*,*.spec.*'). Can be specified multiple times. Exclude patterns take precedence over include patterns.
*   `--filetype-prompts`: Path to JSON file containing filetype-specific prompts. File should map extensions to custom prompt templates (e.g., `{".py": "Review this Python code...", ".md": "Review this documentation..."}`)
*   `-v`, `--verbose`: Enable verbose logging

## Security Features

The AI Review Hook includes comprehensive security measures to protect sensitive information:

### Secret Detection & Redaction
Automatically detects and redacts various types of secrets before sending to the AI model:

*   **AWS Credentials**: Access keys, secret keys
*   **GitHub Tokens**: Personal access tokens, OAuth tokens, server-to-server tokens
*   **API Keys**: Generic API keys, tokens, and secrets
*   **JWT Tokens**: JSON Web Tokens
*   **Bearer Tokens**: Authorization headers and bearer tokens
*   **Slack Tokens**: Slack API tokens
*   **OpenAI Keys**: OpenAI API keys
*   **Database URLs**: Connection strings with credentials
*   **Private Keys**: RSA, EC, DSA, OpenSSH, PGP keys and certificates

### Binary File Protection
*   Automatically detects binary files using heuristics
*   Excludes binary content from being sent to the AI model
*   Shows "[BINARY FILE - Content not shown for security]" placeholder

### Secure Endpoint Validation
*   By default, only allows official OpenAI API endpoints
*   Custom endpoints require explicit `--allow-unsafe-base-url` flag
*   Clear warnings when using non-official endpoints

### Diff-Only Mode
*   Use `--diff-only` flag to send only git diff, not full file content
*   Reduces data exposure for sensitive repositories
*   Maintains review quality while enhancing security

## Performance Features

The AI Review Hook includes several performance optimizations for efficient code review:

### Parallel Processing
*   Use `--jobs N` (or `-j N`) to review multiple files simultaneously
*   Automatically scales based on available CPU cores
*   Maintains deterministic output order
*   Fallback to sequential processing for single files or when `--jobs 1`

### Intelligent Content Management
*   **Smart Truncation**: Large diffs/files are truncated with clear markers showing original size
*   **Hunk Extraction**: Extracts only changed code hunks before truncation
*   **UTF-8 Safe**: Truncation respects character boundaries to avoid encoding issues
*   **Clear Indicators**: Shows `[TRUNCATED - diff was X bytes, showing first Y bytes]` messages

### Optimized Processing
*   **Lazy Redaction**: Skips secret detection on empty content (diff-only mode)
*   **Binary Skip**: Fast binary file detection prevents unnecessary processing
*   **Efficient Memory**: Streams large files without loading entire content into memory

## File Type Filtering

The AI Review Hook supports filtering files by type to optimize review focus and reduce API costs:

### Include/Exclude Patterns
*   **Include Patterns**: Use `--include-files` to specify which file types to review
*   **Exclude Patterns**: Use `--exclude-files` to specify which file types to skip
*   **Pattern Syntax**: Supports standard glob patterns (`*.py`, `src/*.js`, `**/*.test.*`)
*   **Multiple Patterns**: Can specify multiple patterns using comma separation or multiple flags
*   **Precedence**: Exclude patterns take precedence over include patterns

### Usage Examples

**File Type Filtering:**
```bash
# Review only Python files
pre-commit run ai-review --all-files -- --include-files "*.py"

# Review Python and JavaScript files, but exclude tests
pre-commit run ai-review --all-files -- --include-files "*.py,*.js" --exclude-files "*.test.*,*.spec.*"

# Review files from specific directories only
pre-commit run ai-review --all-files -- --include-files "src/*.py,lib/*.py"

# Exclude common non-reviewable files
pre-commit run ai-review --all-files -- --exclude-files "*.min.*,*.generated.*,vendor/**"

# Multiple include/exclude patterns
pre-commit run ai-review --all-files -- \
  --include-files "*.py" \
  --include-files "*.js,*.ts" \
  --exclude-files "*.test.py" \
  --exclude-files "*.spec.js,*.min.js"
```

**Common Filter Patterns:**
```bash
# Python projects: exclude tests and build files
--include-files "*.py" --exclude-files "test_*,*_test.py,build/**,dist/**"

# Web projects: include source files, exclude build artifacts
--include-files "*.js,*.ts,*.jsx,*.tsx,*.css,*.scss" --exclude-files "*.min.*,dist/**,node_modules/**"

# Multi-language projects: focus on core languages
--include-files "*.py,*.js,*.go,*.rs,*.java" --exclude-files "vendor/**,third_party/**,*.test.*"
```

**Configuration in .pre-commit-config.yaml:**
```yaml
- repo: https://github.com/randomparity/ai-review-hook
  rev: v1.0.0
  hooks:
    - id: ai-review
      name: AI Code Review - Python Only
      args:
        - "--include-files"
        - "*.py"
        - "--exclude-files"
        - "test_*,*_test.py"
        - "--verbose"
```

**Parallel Processing:**
```bash
# Review 4 files simultaneously
pre-commit run ai-review --files file1.py file2.py file3.py file4.py -- --jobs 4

# Use all available CPU cores
pre-commit run ai-review --all-files -- --jobs $(nproc)
```

**Content Size Management:**
```bash
# Limit diff to 5KB, content to 20KB
pre-commit run ai-review --all-files -- --max-diff-bytes 5000 --max-content-bytes 20000

# Diff-only mode for large repositories
pre-commit run ai-review --all-files -- --diff-only
```

## Filetype-Specific Prompts

The AI Review Hook supports customized review prompts based on file types, enabling more targeted and relevant feedback for different programming languages and file formats.

### Why Use Filetype-Specific Prompts?

Different file types require different review focus:

*   **Python files** should emphasize PEP 8 compliance, type hints, and import organization
*   **Documentation files** need grammar, clarity, and formatting checks rather than security reviews
*   **JavaScript files** should focus on modern syntax, async/await patterns, and browser compatibility
*   **SQL files** require attention to injection vulnerabilities and query optimization
*   **Configuration files** need validation of syntax and security considerations

### Configuration

Create a JSON configuration file mapping file extensions to custom prompt templates:

```json
{
  ".py": "Review this Python file: {filename}\n\nDiff: {diff}\n\nFocus on PEP 8, type hints, and imports.",
  ".md": "Review this documentation: {filename}\n\nChanges: {diff}\n\nCheck grammar and clarity.",
  ".js": "Review this JavaScript: {filename}\n\nDiff: {diff}\n\nCheck modern syntax and security."
}
```

Then use the `--filetype-prompts` option:

```bash
pre-commit run ai-review --all-files -- --filetype-prompts my-prompts.json
```

### Template Placeholders

Your custom prompts can use these placeholders:

*   `{filename}` - The name of the file being reviewed
*   `{diff}` - The git diff content for the file
*   `{content}` - The current file content (empty in `--diff-only` mode)
*   `{diff_only_note}` - Shows a note when in diff-only mode, empty otherwise

### Example Configuration

The repository includes a comprehensive example at `examples/filetype-prompts.json` with specialized prompts for:

*   **Python** (`.py`) - PEP 8, type hints, imports, docstrings, error handling
*   **Markdown** (`.md`) - Grammar, formatting, clarity, accessibility
*   **JavaScript** (`.js`) - Modern syntax, security, performance, browser compatibility
*   **Go** (`.go`) - Go idioms, concurrency, error handling, testing
*   **SQL** (`.sql`) - Injection prevention, query optimization, data integrity
*   **YAML** (`.yaml`) - Configuration validation, security, maintainability

### Usage Examples

**Basic Usage:**
```bash
# Use custom prompts for all file types
pre-commit run ai-review --all-files -- --filetype-prompts examples/filetype-prompts.json

# Combine with file filtering for specific languages
pre-commit run ai-review --all-files -- \
  --include-files "*.py,*.js,*.md" \
  --filetype-prompts examples/filetype-prompts.json
```

**Pre-commit Configuration:**
```yaml
- repo: https://github.com/randomparity/ai-review-hook
  rev: v1.0.0
  hooks:
    - id: ai-review
      name: AI Code Review with Custom Prompts
      args:
        - "--filetype-prompts"
        - "prompts/review-prompts.json"
        - "--include-files"
        - "*.py,*.js,*.md,*.sql"
        - "--verbose"
```

**Creating Your Own Prompts:**
```json
{
  ".py": "IMPORTANT: Start with `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]`.\n\nPython Code Review: {filename}\n\nChanges:\n{diff}\n\nContent:\n{content}\n\n{diff_only_note}\n\nFocus Areas:\n- PEP 8 compliance\n- Type annotations\n- Import organization\n- Security issues\n- Performance concerns\n\nProvide specific feedback with line numbers.",

  ".md": "IMPORTANT: Start with `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]`.\n\nDocumentation Review: {filename}\n\nChanges:\n{diff}\n\n{diff_only_note}\n\nFocus Areas:\n- Grammar and spelling\n- Clarity and readability\n- Markdown formatting\n- Link validation\n- Content completeness\n\nNote: Security is less relevant for docs.",

  ".ts": "IMPORTANT: Start with `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]`.\n\nTypeScript Review: {filename}\n\nChanges:\n{diff}\n\nContent:\n{content}\n\n{diff_only_note}\n\nFocus Areas:\n- Type safety and annotations\n- Modern ES6+ features\n- Error handling\n- Security (XSS, validation)\n- Performance optimization\n\nProvide specific feedback with line numbers."
}
```

### Key Features

*   **Automatic Fallback**: Files without custom prompts use the default comprehensive prompt
*   **Extension Normalization**: Extensions are case-insensitive and normalized (e.g., `.PY` → `.py`)
*   **Template Validation**: Invalid JSON or malformed prompts are logged and ignored
*   **Performance**: Prompt selection is optimized and doesn't impact review speed
*   **Debugging**: Use `--verbose` to see which files use custom prompts

### Best Practices

1.  **Always include the required response format**: Start prompts with the `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]` instruction
2.  **Use all placeholders appropriately**: Include `{diff_only_note}` to handle diff-only mode gracefully
3.  **Be specific about language concerns**: Focus on language-specific best practices and common issues
4.  **Provide clear focus areas**: List 5-7 specific areas for the AI to examine
5.  **Request line numbers**: Ask for specific feedback with line references
6.  **Consider your workflow**: Create prompts that match your team's coding standards and review priorities

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
