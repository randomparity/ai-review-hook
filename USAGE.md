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

### Option 1: Local Repository Hook

Create a `.pre-commit-config.yaml` file:

```yaml
repos:
  - repo: local
    hooks:
      - id: ai-review
        name: AI Code Review
        entry: ai-review
        language: python
        files: \.(py|js|ts|java|cpp|c|h|hpp|go|rs|rb|php|scala|kotlin|swift|cs|sh|yaml|yml|json|md)$
        require_serial: true
        pass_filenames: true
        additional_dependencies: ['openai>=1.0.0', 'requests']
        args: ['--model', 'gpt-4', '--verbose']
```

### Option 2: Using Configuration File

Create `ai-review-config.json`:
```json
{
  "api_key_env": "OPENAI_API_KEY",
  "base_url": null,
  "model": "gpt-4"
}
```

Update `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: local
    hooks:
      - id: ai-review
        name: AI Code Review
        entry: ai-review
        language: python
        files: \.(py|js|ts|java|cpp|c|h|hpp|go|rs|rb|php|scala|kotlin|swift|cs|sh|yaml|yml|json|md)$
        require_serial: true
        pass_filenames: true
        additional_dependencies: ['openai>=1.0.0', 'requests']
        args: ['--config-file', 'ai-review-config.json']
```

### Install and run pre-commit:

```bash
pip install pre-commit
pre-commit install
pre-commit run ai-review --all-files
```

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
