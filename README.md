# AI Review Hook

This project grew out of my frustration with existing AI coding frameworks. I would follow the general guidance to add best practices requirements to CLAUDE.md, WARP.md, or other framework specific system prompts, but the AI tends to forget about them over time and moves towards the quickest method to push code on its way out the door.

After a few atttemtps to ***vibe code*** my way to success I quickly recognized the need to setup adequate guard rails to keep an AI headed in the right direction.  Git hooks work as an excellent gate and [pre-commit](https://github.com/pre-commit/pre-commit) was a flexible way to add custom controls.

The result is [AI Hook Review](https://github.com/randomparity/ai-review-hook), a python application that uses `pre-commit` to setup `pre-commit`/`pre-push` git hooks and add the missing ***vibe coding*** guard rails.

## Quick Start

1.  **Install the hook** by adding the following to your `.pre-commit-config.yaml`:

    ```yaml
    repos:
    -   repo: https://github.com/randomparity/ai-review-hook
        rev: v0.2.0  # Replace with the desired tag or commit SHA
        hooks:
        -   id: ai-review
    ```

    Or a real-world example:

    ```yaml
    - repo: https://github.com/randomparity/ai-review-hook
      rev: v0.2.3
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

    Alternatively, store your API key in a file and pass it with --api-key-file:

    ```bash
    mkdir -p ~/.config/ai-review-hook
    # Write your key (do not commit this file)
    printf "%s" "{{OPENAI_API_KEY}}" > ~/.config/ai-review-hook/api_key
    chmod 600 ~/.config/ai-review-hook/api_key

    # Example run using the file
    pre-commit run ai-review --all-files -- --api-key-file ~/.config/ai-review-hook/api_key
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
*   `--api-key-file`: Path to a file containing the API key. If provided, it takes precedence over `--api-key-env`.
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
*   `--format`: Output format: `text` (default), `json`, or `codeclimate`. `codeclimate` produces Code Climate-compatible JSON for GitLab/GitHub code-quality reports; `json` is machine-readable.
*   `--include-files`: File patterns to include for review (e.g., '*.py' or '*.py,*.js'). Can be specified multiple times. If not specified, all files are included by default.
*   `--exclude-files`: File patterns to exclude from review (e.g., '*.test.py' or '*.test.*,*.spec.*'). Can be specified multiple times. Exclude patterns take precedence over include patterns.
*   `--no-default-excludes`: Disable the default exclude patterns for common non-reviewable files (e.g., lockfiles, vendored dependencies, minified assets).
*   `--filetype-prompts`: Path to JSON file containing filetype-specific prompts. File should map glob patterns to custom prompt templates (e.g., `{"*.py": "Review this Python code...", "*.md": "Review this documentation...", "test_*.py": "Review this test file...", "src/**/*.js": "Review this JavaScript source..."}`)
*   `-v`, `--verbose`: Enable verbose logging


### Output Formats

- text (default): human-readable review summary suitable for local runs.
- json: machine-readable array for scripting or tooling.
- codeclimate: Code Climate-compatible JSON for GitHub/GitLab code-quality reports.

Examples:

```bash
# Save JSON output to a file
pre-commit run ai-review --all-files -- --format json --output-file ai-review.json

# Generate a Code Climate report for CI
pre-commit run ai-review --all-files -- --format codeclimate --output-file gl-code-quality-report.json

# Example .pre-commit-config.yaml
```yaml
- repo: https://github.com/randomparity/ai-review-hook
  rev: v0.2.3
  hooks:
    - id: ai-review
      name: AI Code Review (Code Quality)
      args:
        - "--format"
        - "codeclimate"
        - "--output-file"
        - "gl-code-quality-report.json"
```


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

### Default Excludes
By default, `ai-review-hook` excludes a list of common files that are generally not useful to review. This helps reduce noise and API costs.

The following patterns are excluded by default:
- **Lockfiles**: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `composer.lock`, `Gemfile.lock`, `poetry.lock`, `Pipfile.lock`
- **Vendored Dependencies**: `vendor/**`, `node_modules/**`
- **Minified Assets**: `*.min.js`, `*.min.css`
- **Image Files**: `*.png`, `*.jpg`, `*.jpeg`, `*.gif`, `*.svg`, `*.ico`, `*.webp`
- **Build Artifacts & Logs**: `dist/**`, `build/**`, `*.log`, `*.tmp`, `*.swp`, `coverage.xml`
- **Compiled Python**: `*.pyc`, `__pycache__/**`
- **Data & Font Files**: `*.csv`, `*.json`, `*.xml`, `*.woff`, `*.woff2`, `*.ttf`, `*.eot`

To disable this behavior and review all files (respecting only the `--include-files` and `--exclude-files` arguments), use the `--no-default-excludes` flag.

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
  rev: v0.2.3
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

## Filetype-Specific Prompts with Glob Patterns

The AI Review Hook supports customized review prompts based on flexible glob patterns, enabling precise file targeting and more relevant feedback for different programming languages, file locations, and naming conventions.

### Why Use Filetype-Specific Prompts?

Different types of files require different review focus:

*   **Python files** should emphasize PEP 8 compliance, type hints, and import organization
*   **Test files** need focus on test coverage, assertions, and maintainability
*   **Documentation files** need grammar, clarity, and formatting checks rather than security reviews
*   **JavaScript files** should focus on modern syntax, async/await patterns, and browser compatibility
*   **Configuration files** need validation of syntax and security considerations
*   **Source vs. test files** can have completely different review criteria

### Glob Pattern Support

The system uses flexible glob patterns instead of simple file extensions, allowing for sophisticated file targeting:

**Pattern Types:**
1. **Exact filename matching**: `"README.md"`, `"Dockerfile"`, `"package.json"`
2. **Full path glob patterns**: `"src/**/*.py"`, `"tests/unit/*.go"`, `"docs/**/*.md"`
3. **File extension patterns**: `"*.py"`, `"*.js"`, `"*.md"`
4. **Basename patterns**: `"test_*.py"`, `"*_config.yaml"`, `"*.test.js"`

### Configuration

Create a JSON configuration file mapping glob patterns to custom prompt templates:

```json
{
  "*.py": "Review this Python file: {filename}\n\nDiff: {diff}\n\nFocus on PEP 8, type hints, and imports.",
  "test_*.py": "Review this Python test file: {filename}\n\nDiff: {diff}\n\nFocus on test quality, coverage, and assertions.",
  "src/**/*.js": "Review this JavaScript source: {filename}\n\nDiff: {diff}\n\nFocus on modern syntax, security, and performance.",
  "*.md": "Review this documentation: {filename}\n\nChanges: {diff}\n\nCheck grammar and clarity.",
  "Dockerfile": "Review this Docker configuration: {filename}\n\nDiff: {diff}\n\nFocus on security and best practices."
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

### Pattern Matching Priority

When multiple patterns could match a file, the system uses the following priority order for maximum specificity:

1. **Exact filename match** (full path or basename): `"README.md"`, `"Dockerfile"`
2. **Full path glob patterns**: `"src/**/*.py"`, `"tests/unit/*.go"`
3. **File extension patterns**: `"*.py"`, `"*.js"`, `"*.md"`
4. **Basename patterns**: `"test_*.py"`, `"*_config.yaml"`

### Example Configuration

The repository includes a comprehensive example at `examples/filetype-prompts.json` with specialized prompts for:

*   **Python** (`*.py`) - PEP 8, type hints, imports, docstrings, error handling
*   **Python Tests** (`test_*.py`, `*_test.py`) - Test quality, coverage, assertions
*   **Markdown** (`*.md`) - Grammar, formatting, clarity, accessibility
*   **JavaScript** (`*.js`) - Modern syntax, security, performance, browser compatibility
*   **Source JavaScript** (`src/**/*.js`) - Stricter review for source files
*   **Go** (`*.go`) - Go idioms, concurrency, error handling, testing
*   **SQL** (`*.sql`) - Injection prevention, query optimization, data integrity
*   **Configuration** (`*.yaml`, `*_config.*`) - Configuration validation, security
*   **Docker** (`Dockerfile*`) - Container security and best practices

### Usage Examples

**Basic Usage:**
```bash
# Use custom prompts with glob patterns
pre-commit run ai-review --all-files -- --filetype-prompts examples/filetype-prompts.json

# Combine with file filtering for specific languages
pre-commit run ai-review --all-files -- \
  --include-files "*.py,*.js,*.md" \
  --filetype-prompts examples/filetype-prompts.json

# Review with patterns targeting specific directories
pre-commit run ai-review --all-files -- \
  --include-files "src/**/*.py,tests/**/*.py" \
  --filetype-prompts my-prompts.json
```

**Pre-commit Configuration:**
```yaml
- repo: https://github.com/randomparity/ai-review-hook
  rev: v0.2.3
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

**Creating Your Own Prompts with Glob Patterns:**
```json
{
  "*.py": "IMPORTANT: Start with `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]`.\n\nPython Code Review: {filename}\n\nChanges:\n{diff}\n\nContent:\n{content}\n\n{diff_only_note}\n\nFocus Areas:\n- PEP 8 compliance\n- Type annotations\n- Import organization\n- Security issues\n- Performance concerns\n\nProvide specific feedback with line numbers.",

  "test_*.py": "IMPORTANT: Start with `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]`.\n\nPython Test Review: {filename}\n\nChanges:\n{diff}\n\nContent:\n{content}\n\n{diff_only_note}\n\nFocus Areas:\n- Test coverage and completeness\n- Assertion quality and clarity\n- Test organization and naming\n- Mock usage and test isolation\n- Performance of test suite\n\nProvide specific feedback with line numbers.",

  "src/**/*.js": "IMPORTANT: Start with `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]`.\n\nJavaScript Source Review: {filename}\n\nChanges:\n{diff}\n\nContent:\n{content}\n\n{diff_only_note}\n\nFocus Areas:\n- Modern ES6+ features\n- Security (XSS, validation)\n- Performance optimization\n- Error handling\n- Code maintainability\n\nProvide specific feedback with line numbers.",

  "*.md": "IMPORTANT: Start with `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]`.\n\nDocumentation Review: {filename}\n\nChanges:\n{diff}\n\n{diff_only_note}\n\nFocus Areas:\n- Grammar and spelling\n- Clarity and readability\n- Markdown formatting\n- Link validation\n- Content completeness\n\nNote: Security is less relevant for docs.",

  "Dockerfile*": "IMPORTANT: Start with `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]`.\n\nDocker Configuration Review: {filename}\n\nChanges:\n{diff}\n\nContent:\n{content}\n\n{diff_only_note}\n\nFocus Areas:\n- Security best practices\n- Image size optimization\n- Layer caching efficiency\n- Multi-stage build usage\n- Vulnerability scanning\n\nProvide specific feedback with line numbers."
}
```

### Key Features

*   **Flexible Pattern Matching**: Supports exact filenames, path patterns, extensions, and basename patterns
*   **Priority-Based Selection**: Intelligent matching with specificity-based priority ordering
*   **Automatic Fallback**: Files without matching patterns use the default comprehensive prompt
*   **Case-Sensitive Matching**: Pattern matching respects case for precise control
*   **Template Validation**: Invalid JSON or malformed prompts are logged and ignored
*   **Performance Optimized**: Efficient pattern matching that doesn't impact review speed
*   **Comprehensive Debugging**: Use `--verbose` to see which files use custom prompts and which patterns match

### Best Practices

1.  **Always include the required response format**: Start prompts with the `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]` instruction
2.  **Use all placeholders appropriately**: Include `{diff_only_note}` to handle diff-only mode gracefully
3.  **Leverage pattern specificity**: Use specific patterns like `test_*.py` for test files and `src/**/*.js` for source files
4.  **Order patterns by specificity**: More specific patterns (exact filenames, path patterns) take precedence over general patterns
5.  **Be specific about language concerns**: Focus on language-specific best practices and common issues
6.  **Provide clear focus areas**: List 5-7 specific areas for the AI to examine
7.  **Request line numbers**: Ask for specific feedback with line references
8.  **Consider your project structure**: Create patterns that match your team's directory organization and naming conventions
9.  **Test your patterns**: Use `--verbose` to verify which files match which patterns during development


> For development and build instructions, see BUILD.md and CONTRIBUTING.md.

## Development

To set up a local development environment, you'll need Python 3.9+ and `make`. The `Makefile` provides several convenient targets for common development tasks.

1.  **Set up the virtual environment and install dependencies:**

    ```bash
    make setup
    ```

    This command will create a virtual environment in `.venv/` and install all the necessary dependencies. It will try to use `uv` or `pyenv` if they are installed, falling back to the system's `python3`. It will try to use the Python version specified in a local `.python-version` file, or a default version if the file is not present.

2.  **Activate the virtual environment:**

    On macOS and Linux:
    ```bash
    source .venv/bin/activate
    ```

    On Windows:
    ```bash
    .venv\Scripts\activate
    ```

3.  **Run the tests:**

    To run the tests with the default Python version:
    ```bash
    make test
    ```

    To run the tests against all supported Python versions (from 3.9 to 3.13), you'll need to have those Python versions installed on your system (e.g., via `pyenv`). Then, run:
    ```bash
    make test-all-versions
    ```
    This uses `tox` to run the full test suite in isolated environments for each Python version.

4.  **Run linters and formatters:**

    ```bash
    make lint
    make format
    make typecheck
    ```

5.  **Run all CI checks:**

    ```bash
    make ci
    ```

## License

MIT License
