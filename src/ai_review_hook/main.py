#!/usr/bin/env python3
"""
AI Review Hook - Main script for performing AI-assisted code reviews.

This script integrates with pre-commit to provide AI-powered code reviews
using the OpenAI API with configurable models and endpoints.
"""

import argparse
import concurrent.futures
import json
import logging
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

# Constants
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_MAX_TOKENS = 2000
DEFAULT_TEMPERATURE = 0.1

# Secret detection patterns
SECRET_PATTERNS = [
    # AWS credentials
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS Access Key ID
    re.compile(
        r"(?i)aws_secret_access_key\s*=\s*[A-Za-z0-9/+=]{40}"
    ),  # AWS Secret Access Key
    # Private keys and certificates
    re.compile(
        r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP) (?:PRIVATE KEY|CERTIFICATE)-----.*?-----END (?:RSA|EC|DSA|OPENSSH|PGP) (?:PRIVATE KEY|CERTIFICATE)-----",
        re.S,
    ),  # Private Keys and Certificates
    # Authorization headers and Bearer tokens
    re.compile(
        r"(?i)authorization:\s*bearer\s+[a-z0-9\-._~+/]+=*"
    ),  # Bearer/JWT tokens in headers
    re.compile(r"(?i)bearer\s+[a-z0-9\-._~+/]{20,}={0,2}"),  # Generic Bearer tokens
    # GitHub tokens
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36,255}"),  # GitHub Personal Access Tokens
    re.compile(r"gho_[A-Za-z0-9]{36}"),  # GitHub OAuth tokens
    re.compile(r"ghs_[A-Za-z0-9]{36}"),  # GitHub server-to-server tokens
    # Generic API keys and tokens
    re.compile(
        r'(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*["\']?[A-Za-z0-9_\-.]{16,}["\']?'
    ),  # Generic API keys and tokens
    # Slack tokens
    re.compile(r"xox[baprs]-[A-Za-z0-9\-]+"),  # Slack tokens
    # OpenAI API keys
    re.compile(r"sk-[A-Za-z0-9]{20}T3BlbkFJ[A-Za-z0-9]{20}"),  # OpenAI API keys
    # JWT tokens (basic detection)
    re.compile(
        r"eyJ[A-Za-z0-9_\-]*\.eyJ[A-Za-z0-9_\-]*\.[A-Za-z0-9_\-]*"
    ),  # JWT tokens (header.payload.signature)
    # Database connection strings
    re.compile(
        r"(?i)(mongodb|mysql|postgresql|postgres)://[^\s]*:[^\s]*@[^\s]+"
    ),  # Database connection strings with credentials
    # Generic secrets in environment or config format
    re.compile(
        r'(?i)(secret|password|key|token)\s*=\s*["\'][A-Za-z0-9+/]{20,}["\']'
    ),  # Environment file style secrets
]


def should_review_file(
    filename: str, include_patterns: List[str], exclude_patterns: List[str]
) -> bool:
    """Check if a file should be reviewed based on include/exclude patterns.

    Args:
        filename: Path to the file to check
        include_patterns: List of file patterns to include (e.g., ['*.py', '*.js'])
        exclude_patterns: List of file patterns to exclude (e.g., ['*.test.py', '*.spec.js'])

    Returns:
        True if file should be reviewed, False otherwise

    Logic:
    - If include_patterns is empty, all files are included by default
    - If include_patterns is provided, file must match at least one include pattern
    - If exclude_patterns is provided and file matches any exclude pattern, it's excluded
    - Exclude patterns take precedence over include patterns
    """
    import fnmatch
    import os

    # Get the basename for pattern matching
    basename = os.path.basename(filename)

    # Check exclude patterns first (they take precedence)
    if exclude_patterns:
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(basename, pattern):
                return False

    # If no include patterns specified, include all files (unless excluded)
    if not include_patterns:
        return True

    # Check if file matches any include pattern
    for pattern in include_patterns:
        if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(basename, pattern):
            return True

    # File doesn't match any include pattern
    return False


def parse_file_patterns(pattern_list: List[str]) -> List[str]:
    """Parse file patterns from command line arguments.

    Handles comma-separated values and individual arguments.
    Example: ['*.py,*.js', '*.go'] becomes ['*.py', '*.js', '*.go']
    """
    if not pattern_list:
        return []

    patterns = []
    for item in pattern_list:
        # Split on comma and strip whitespace
        patterns.extend([p.strip() for p in item.split(",") if p.strip()])

    return patterns


def load_filetype_prompts(prompts_file: Optional[str]) -> Dict[str, str]:
    """Load filetype-specific prompts from JSON file.

    Args:
        prompts_file: Path to JSON file containing filetype-specific prompts

    Returns:
        Dictionary mapping file extensions to custom prompt templates
    """
    if not prompts_file:
        return {}

    try:
        if not Path(prompts_file).exists():
            logging.warning(f"Filetype prompts file not found: {prompts_file}")
            return {}

        with open(prompts_file, "r", encoding="utf-8") as f:
            prompts_data = json.load(f)

        # Validate structure
        if not isinstance(prompts_data, dict):
            logging.error(f"Invalid filetype prompts file format: {prompts_file}")
            return {}

        # Normalize extensions (ensure they start with .)
        normalized_prompts = {}
        for ext, prompt in prompts_data.items():
            if not isinstance(prompt, str):
                logging.warning(f"Skipping non-string prompt for extension '{ext}'")
                continue

            # Normalize extension
            if not ext.startswith("."):
                ext = f".{ext}"
            normalized_prompts[ext.lower()] = prompt

        logging.info(
            f"Loaded {len(normalized_prompts)} filetype-specific prompts from {prompts_file}"
        )
        return normalized_prompts

    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Error loading filetype prompts from {prompts_file}: {e}")
        return {}


def get_file_extension(filename: str) -> str:
    """Get the normalized file extension from a filename.

    Args:
        filename: Path to the file

    Returns:
        Normalized file extension (lowercase, with leading dot)
    """
    return Path(filename).suffix.lower()


def select_prompt_template(
    filename: str, filetype_prompts: Dict[str, str]
) -> Optional[str]:
    """Select the appropriate prompt template for a file.

    Args:
        filename: Path to the file
        filetype_prompts: Dictionary of filetype-specific prompts

    Returns:
        Custom prompt template if found, None for default prompt
    """
    extension = get_file_extension(filename)
    return filetype_prompts.get(extension)
def redact(text: str, skip_if_empty: bool = False) -> str:
    """Redact secrets from a string using predefined patterns.

    Args:
        text: The text to redact secrets from
        skip_if_empty: Skip redaction if text is empty (performance optimization)
    """
    if skip_if_empty and not text.strip():
        return text

    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


try:
    import openai
except ImportError:
    logging.error(
        "Error: openai package not found. Please install with: pip install openai"
    )
    sys.exit(1)


class AIReviewer:
    """Handles AI-powered code review using OpenAI API."""

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        timeout: int = 30,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        max_retries: int = 3,
        initial_retry_delay: float = 1.0,
        max_retry_delay: float = 60.0,
        retry_jitter: float = 0.1,
        filetype_prompts: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the AI reviewer.

        Args:
            api_key: OpenAI API key
            base_url: Custom API base URL (optional)
            model: Model to use for review
            timeout: Timeout for API requests in seconds
            max_tokens: Maximum tokens in AI response
            temperature: AI response temperature (0.0-2.0)
            max_retries: Maximum number of retries for failed API calls
            initial_retry_delay: Initial delay between retries in seconds
            max_retry_delay: Maximum delay between retries in seconds
            retry_jitter: Jitter factor for retry delays (0.0-1.0)
            filetype_prompts: Dictionary mapping file extensions to custom prompts
        """
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.max_retry_delay = max_retry_delay
        self.retry_jitter = retry_jitter
        self.filetype_prompts = filetype_prompts or {}
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    def get_file_diff(self, filename: str, context_lines: int = 3) -> str:
        """Get the git diff for a specific file with configurable context.

        Args:
            filename: Path to the file
            context_lines: Number of context lines to include around changes
        """
        try:
            # Get staged changes for the file with custom context
            result = subprocess.run(
                [
                    "git",
                    "diff",
                    "--cached",
                    f"--unified={context_lines}",
                    "--",
                    filename,
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            return result.stdout
        except subprocess.CalledProcessError:
            # Fallback to unstaged changes if no staged changes
            try:
                result = subprocess.run(
                    ["git", "diff", f"--unified={context_lines}", "--", filename],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30,
                )
                return result.stdout
            except subprocess.CalledProcessError:
                return ""

    def is_binary_file(self, filename: str) -> bool:
        """Check if a file is likely binary using heuristics."""
        try:
            with open(filename, "rb") as f:
                # Read first 8192 bytes to check for binary content
                chunk = f.read(8192)
                if not chunk:
                    return False
                # Check for null bytes (common in binary files)
                if b"\x00" in chunk:
                    return True
                # Check for high ratio of non-text bytes
                text_chars = sum(1 for b in chunk if 32 <= b <= 126 or b in [9, 10, 13])
                return (text_chars / len(chunk)) < 0.75
        except (IOError, OSError):
            # If we can't read the file, assume it might be binary
            return True

    def get_file_content(self, filename: str) -> str:
        """Read the current content of a file, skipping binary files for security."""
        # Check if file is binary first
        if self.is_binary_file(filename):
            return "[BINARY FILE - Content not shown for security]"

        try:
            with open(filename, "r", encoding="utf-8") as f:
                return f.read()
        except (IOError, UnicodeDecodeError) as e:
            return f"[UNREADABLE FILE - {e}]"

    def create_review_prompt(
        self, filename: str, diff: str, content: str, diff_only: bool = False
    ) -> str:
        """Create the AI review prompt, using filetype-specific prompts if available."""
        # Check for filetype-specific prompt template
        custom_prompt = select_prompt_template(filename, self.filetype_prompts)

        if custom_prompt:
            # Use the custom prompt template, replacing placeholders
            prompt = custom_prompt.format(
                filename=filename,
                diff=diff,
                content=content
                if not diff_only and content and not content.startswith("[")
                else "",
                diff_only_note="Note: Only diff is provided for security (--diff-only mode)."
                if diff_only
                else "",
            )
            logging.debug(
                f"Using filetype-specific prompt for {filename} ({get_file_extension(filename)})"
            )
            return prompt

        # Fall back to default prompt
        prompt = f"""Please perform a thorough code review of the following changes.

IMPORTANT: Your first line of response must be either `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]`.

File: {filename}

Git Diff:
```
{diff}
```
"""

        # Only include file content if not in diff-only mode and content is meaningful
        if not diff_only and content and not content.startswith("["):
            prompt += f"""
Current File Content:
```
{content}
```
"""
        elif diff_only:
            prompt += """
Note: Only diff is provided for security (--diff-only mode).
"""

        prompt += """
Review the code for the following:
1.  **Code Quality & Best Practices**: Adherence to coding standards, clarity, and maintainability.
2.  **Potential Bugs & Logical Errors**: Flaws that could lead to incorrect behavior.
3.  **Security Vulnerabilities**: Weaknesses that could be exploited.
4.  **Performance Issues**: Inefficiencies in code that could impact speed or resource usage.
5.  **Code Style & Readability**: Consistency with project style and overall readability.
6.  **Documentation & Comments**: Clarity and usefulness of documentation and comments.
7.  **Test Coverage**: Adequacy of tests for the changes.

Provide specific, actionable feedback with line numbers where possible. If no significant issues are found, briefly explain why the code is approved.
"""
        return prompt

    def truncate_text_with_marker(
        self, text: str, max_bytes: int, marker: str = "diff"
    ) -> str:
        """Truncate text to max_bytes with clear truncation marker."""
        if max_bytes <= 0:
            return text

        text_bytes = text.encode("utf-8")
        if len(text_bytes) <= max_bytes:
            return text

        # Reserve space for truncation marker
        marker_text = f"\n\n[TRUNCATED - {marker} was {len(text_bytes)} bytes, showing first {max_bytes} bytes]\n"
        marker_bytes = len(marker_text.encode("utf-8"))

        if max_bytes <= marker_bytes:
            return f"[TRUNCATED - {marker} too large ({len(text_bytes)} bytes)]"

        # Truncate to max_bytes - marker size, then decode safely
        truncated_bytes = text_bytes[: max_bytes - marker_bytes]

        # Avoid cutting in the middle of a UTF-8 character
        while truncated_bytes:
            try:
                truncated_text = truncated_bytes.decode("utf-8")
                break
            except UnicodeDecodeError:
                truncated_bytes = truncated_bytes[:-1]
        else:
            truncated_text = "[UNABLE TO DECODE TRUNCATED TEXT]"

        return truncated_text + marker_text

    def extract_changed_hunks(self, diff: str, max_hunks: int = 10) -> str:
        """Extract only changed hunks from diff, limiting to max_hunks for performance."""
        if not diff.strip():
            return diff

        lines = diff.split("\n")
        hunks = []
        current_hunk = []
        hunk_count = 0

        for line in lines:
            if line.startswith("@@") and current_hunk:
                # Start of new hunk, save current one
                if hunk_count < max_hunks:
                    hunks.append("\n".join(current_hunk))
                    hunk_count += 1
                current_hunk = [line]
            elif line.startswith("@@"):
                # Start of first hunk
                current_hunk = [line]
            elif current_hunk and (
                line.startswith("+") or line.startswith("-") or line.startswith(" ")
            ):
                # Part of current hunk
                current_hunk.append(line)
            elif (
                line.startswith("diff ")
                or line.startswith("index ")
                or line.startswith("---")
                or line.startswith("+++")
            ):
                # Diff header, always include
                if not current_hunk:
                    hunks.append(line)

        # Add the last hunk if it exists and we haven't hit the limit
        if current_hunk and hunk_count < max_hunks:
            hunks.append("\n".join(current_hunk))
            hunk_count += 1

        result = "\n".join(hunks)

        # Add truncation notice if we hit the limit
        if hunk_count >= max_hunks and len(lines) > sum(
            len(hunk.split("\n")) for hunk in hunks
        ):
            result += f"\n\n[TRUNCATED - showing first {max_hunks} hunks of diff]\n"

        return result

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is retryable (rate limits, transient network issues)."""
        if isinstance(error, openai.RateLimitError):
            return True
        if isinstance(error, openai.APITimeoutError):
            return True
        if isinstance(error, openai.APIConnectionError):
            return True
        if isinstance(error, openai.InternalServerError):
            return True
        if isinstance(error, openai.UnprocessableEntityError):
            # Sometimes temporary due to model overload
            return True

        # Check for specific HTTP status codes that might be retryable
        if hasattr(error, "status_code"):
            retryable_codes = {429, 502, 503, 504, 520, 521, 522, 523, 524}
            return error.status_code in retryable_codes

        return False

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt with exponential backoff and jitter."""
        # Exponential backoff: delay = initial_delay * (2 ^ attempt)
        base_delay = self.initial_retry_delay * (2**attempt)

        # Cap at max delay
        base_delay = min(base_delay, self.max_retry_delay)

        # Add jitter to prevent thundering herd
        jitter = base_delay * self.retry_jitter * random.random()

        return base_delay + jitter

    def _make_api_call_with_retry(self, messages: list, filename: str) -> str:
        """Make an API call with retry logic for rate limits and transient errors."""
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                logging.debug(f"API call attempt {attempt + 1} for {filename}")

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )

                return response.choices[0].message.content

            except Exception as e:
                last_error = e

                # Check if this is the last attempt
                if attempt >= self.max_retries:
                    break

                # Check if error is retryable
                if not self._is_retryable_error(e):
                    logging.debug(f"Non-retryable error for {filename}: {e}")
                    break

                # Calculate delay and wait
                delay = self._calculate_retry_delay(attempt)

                # Log retry attempt with appropriate level based on error type
                if isinstance(e, openai.RateLimitError):
                    logging.info(
                        f"Rate limit hit for {filename}, retrying in {delay:.2f}s (attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                else:
                    logging.warning(
                        f"Transient error for {filename}: {e}. Retrying in {delay:.2f}s (attempt {attempt + 1}/{self.max_retries + 1})"
                    )

                time.sleep(delay)

        # If we get here, all retries failed
        raise last_error

    def review_file(
        self,
        filename: str,
        diff: str,
        max_diff_bytes: int = 0,
        max_content_bytes: int = 0,
        diff_only: bool = False,
    ) -> Tuple[bool, str]:
        """
        Review a single file using AI.

        Args:
            filename: Path to the file to review
            diff: The git diff of the file
            max_diff_bytes: Maximum diff size to send (0 for no limit)
            max_content_bytes: Maximum file content size to send (0 for no limit)
            diff_only: Only send the diff to the model, not full content

        Returns:
            Tuple of (passed, review_message)
        """
        if not diff.strip():
            return True, f"No changes detected in {filename}"

        # Apply size limits with intelligent truncation
        original_diff_size = len(diff.encode("utf-8"))
        if max_diff_bytes > 0 and original_diff_size > max_diff_bytes:
            # Try extracting only changed hunks first
            diff = self.extract_changed_hunks(diff)

            # If still too large, truncate with clear marker
            if len(diff.encode("utf-8")) > max_diff_bytes:
                diff = self.truncate_text_with_marker(diff, max_diff_bytes, "diff")
                logging.info(
                    f"Truncated diff for {filename}: {original_diff_size} -> {len(diff.encode('utf-8'))} bytes"
                )

        content = ""
        if not diff_only:
            content = self.get_file_content(filename)
            original_content_size = len(content.encode("utf-8"))

            if max_content_bytes > 0 and original_content_size > max_content_bytes:
                content = self.truncate_text_with_marker(
                    content, max_content_bytes, "file content"
                )
                logging.info(
                    f"Truncated content for {filename}: {original_content_size} -> {len(content.encode('utf-8'))} bytes"
                )

        # Optimized redaction: skip if content is empty (diff-only mode)
        redacted_diff = redact(diff)
        redacted_content = redact(content, skip_if_empty=True)

        prompt = self.create_review_prompt(
            filename, redacted_diff, redacted_content, diff_only
        )

        try:
            # Use retry mechanism for API calls
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert code reviewer. Provide thorough, constructive feedback on code changes.",
                },
                {"role": "user", "content": prompt},
            ]

            review_text = self._make_api_call_with_retry(messages, filename)

            # Guard against empty review_text
            if not review_text or not review_text.strip():
                return False, "AI-REVIEW:[FAIL] Empty or blank response from AI model"

            # Fail-closed: FAIL takes precedence. Check the first line for a definitive marker.
            match = re.match(
                r"^AI-REVIEW:\\[(PASS|FAIL)\\]", review_text.strip(), re.IGNORECASE
            )
            if match:
                result = match.group(1).upper()
                if result == "FAIL":
                    return False, review_text
                elif result == "PASS":
                    return True, review_text

            # Fallback for markers anywhere in the text, prioritizing FAIL
            if re.search("AI-REVIEW:\\[FAIL\\]", review_text, re.IGNORECASE):
                return False, review_text
            if re.search("AI-REVIEW:\\[PASS\\]", review_text, re.IGNORECASE):
                return True, review_text

            # If neither marker is found, fail the check.
            return False, f"AI-REVIEW[MISSING]\n\n{review_text}"

        except openai.APIError as e:
            # Defensively format API error - fields may vary by SDK version
            status_code = getattr(e, "status_code", "unknown")
            message = getattr(e, "message", str(e))
            return (
                False,
                f"AI-REVIEW:[FAIL] OpenAI API Error: {status_code} - {message}",
            )
        except Exception as e:
            # Catch any other unexpected exceptions
            return (
                False,
                f"AI-REVIEW:[FAIL] Unexpected error during AI review: {str(e)}",
            )


def main() -> int:
    """Main entry point for the AI review hook."""
    parser = argparse.ArgumentParser(description="AI-assisted code review using OpenAI")
    parser.add_argument("files", nargs="*", help="Files to review")
    parser.add_argument(
        "--api-key-env",
        default="OPENAI_API_KEY",
        help="Environment variable containing the OpenAI API key (default: OPENAI_API_KEY)",
    )
    parser.add_argument(
        "--base-url",
        help="Custom API base URL (e.g., for Azure OpenAI or other compatible APIs)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--timeout", type=int, default=30, help="API request timeout in seconds"
    )
    parser.add_argument(
        "--max-diff-bytes", type=int, default=10000, help="Maximum diff size to send"
    )
    parser.add_argument(
        "--max-content-bytes",
        type=int,
        default=0,
        help="Maximum file content size to send (0 for no limit)",
    )
    parser.add_argument(
        "--diff-only", action="store_true", help="Only send the diff to the model"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--context-lines",
        type=int,
        default=3,
        help="Number of context lines to include in git diff (default: 3)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help=f"Maximum tokens in AI response (default: {DEFAULT_MAX_TOKENS})",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help=f"AI response temperature 0.0-2.0 (default: {DEFAULT_TEMPERATURE})",
    )
    parser.add_argument(
        "--allow-unsafe-base-url",
        action="store_true",
        help="Allow using custom base URLs other than official OpenAI endpoints",
    )
    parser.add_argument(
        "--jobs",
        "-j",
        type=int,
        default=1,
        help="Number of parallel jobs for reviewing multiple files (default: 1)",
    )
    parser.add_argument(
        "--output-file",
        help="File to save the complete review output.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retries for failed API calls (default: 3)",
    )
    parser.add_argument(
        "--initial-retry-delay",
        type=float,
        default=1.0,
        help="Initial delay between retries in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--max-retry-delay",
        type=float,
        default=60.0,
        help="Maximum delay between retries in seconds (default: 60.0)",
    )
    parser.add_argument(
        "--retry-jitter",
        type=float,
        default=0.1,
        help="Jitter factor for retry delays 0.0-1.0 (default: 0.1)",
    )
    parser.add_argument(
        "--include-files",
        action="append",
        help="File patterns to include for review (e.g., '*.py' or '*.py,*.js'). Can be specified multiple times. If not specified, all files are included by default.",
    )
    parser.add_argument(
        "--exclude-files",
        action="append",
        help="File patterns to exclude from review (e.g., '*.test.py' or '*.test.*,*.spec.*'). Can be specified multiple times. Exclude patterns take precedence over include patterns.",
    )
    parser.add_argument(
        "--filetype-prompts",
        help='Path to JSON file containing filetype-specific prompts. File should map extensions to custom prompt templates (e.g., {".py": "Review this Python code...", ".md": "Review this documentation..."})',
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    # Validate base URL for security
    if args.base_url:
        if not args.base_url.startswith("https://api.openai.com"):
            if not args.allow_unsafe_base_url:
                logging.error(
                    f"Custom base URL '{args.base_url}' is not allowed for security reasons."
                )
                logging.error(
                    "If you trust this endpoint, use --allow-unsafe-base-url flag."
                )
                return 1
            else:
                logging.warning(
                    f"Using custom base URL: {args.base_url}. Code will be sent to this endpoint."
                )
    api_key = os.getenv(args.api_key_env)
    if not api_key:
        logging.error(f"API key not found in environment variable '{args.api_key_env}'")
        logging.error(
            f"Please set the environment variable: export {args.api_key_env}=your_api_key"
        )
        return 1

    if not args.files:
        logging.info("No files to review")
        return 0

    # Parse file filtering patterns
    include_patterns = parse_file_patterns(args.include_files or [])
    exclude_patterns = parse_file_patterns(args.exclude_files or [])

    # Filter files based on include/exclude patterns
    original_file_count = len(args.files)
    filtered_files = []
    skipped_files = []

    for filename in args.files:
        if should_review_file(filename, include_patterns, exclude_patterns):
            filtered_files.append(filename)
        else:
            skipped_files.append(filename)

    # Log filtering results
    if include_patterns or exclude_patterns:
        logging.info(
            f"File filtering: {len(filtered_files)}/{original_file_count} files selected for review"
        )
        if include_patterns:
            logging.info(f"Include patterns: {', '.join(include_patterns)}")
        if exclude_patterns:
            logging.info(f"Exclude patterns: {', '.join(exclude_patterns)}")
        if skipped_files and args.verbose:
            logging.info(f"Skipped files: {', '.join(skipped_files)}")

    # Update the files list to only include filtered files
    args.files = filtered_files

    if not args.files:
        logging.info("No files match the filtering criteria")
        return 0

    # Load filetype-specific prompts if provided
    filetype_prompts = load_filetype_prompts(args.filetype_prompts)
    # Initialize AI reviewer
    try:
        reviewer = AIReviewer(
            api_key=api_key,
            base_url=args.base_url,
            model=args.model,
            timeout=args.timeout,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            max_retries=args.max_retries,
            initial_retry_delay=args.initial_retry_delay,
            max_retry_delay=args.max_retry_delay,
            retry_jitter=args.retry_jitter,
            filetype_prompts=filetype_prompts,
        )
    except Exception as e:
        logging.error(f"Error initializing AI reviewer: {e}")
        return 1

    # Review files (with optional parallel processing)
    failed_files = []
    all_reviews = []

    def review_single_file(filename: str) -> Tuple[str, bool, str, str]:
        """Review a single file and return results."""
        diff = reviewer.get_file_diff(filename, args.context_lines)
        passed, review = reviewer.review_file(
            filename,
            diff=diff,
            max_diff_bytes=args.max_diff_bytes,
            max_content_bytes=args.max_content_bytes,
            diff_only=args.diff_only,
        )
        return filename, passed, review, diff

    if args.jobs == 1 or len(args.files) == 1:
        # Sequential processing (original behavior)
        for filename in args.files:
            logging.info(f"Reviewing {filename}...")
            filename, passed, review, diff = review_single_file(filename)

            if not passed:
                failed_files.append(filename)

            review_log_entry = f"""

{"=" * 60}
File: {filename}
{"=" * 60}

"""
            if args.verbose:
                review_log_entry += f"""Git Diff:
```
{diff}```

"""
            review_log_entry += review
            all_reviews.append((filename, review_log_entry))
    else:
        # Parallel processing
        logging.info(
            f"Reviewing {len(args.files)} files with {args.jobs} parallel jobs..."
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
            # Submit all jobs
            future_to_filename = {
                executor.submit(review_single_file, filename): filename
                for filename in args.files
            }

            # Collect results as they complete
            results = []
            for future in concurrent.futures.as_completed(future_to_filename):
                filename = future_to_filename[future]
                try:
                    result = future.result()
                    results.append(result)
                    logging.info(f"Completed review of {result[0]}")
                except Exception as exc:
                    logging.error(f"Review of {filename} generated an exception: {exc}")
                    # Treat exceptions as failures
                    results.append(
                        (
                            filename,
                            False,
                            f"AI-REVIEW:[FAIL] Exception during review: {exc}",
                            "",
                        )
                    )

            # Sort results by original file order
            filename_to_index = {filename: i for i, filename in enumerate(args.files)}
            results.sort(key=lambda x: filename_to_index[x[0]])

            # Process results
            for filename, passed, review, diff in results:
                if not passed:
                    failed_files.append(filename)

                review_log_entry = f"""

{"=" * 60}
File: {filename}
{"=" * 60}

"""
                if args.verbose:
                    review_log_entry += f"""Git Diff:
```
{diff}```

"""
                review_log_entry += review
                all_reviews.append((filename, review_log_entry))

    # Convert to list of review entries (maintain compatibility)
    all_reviews = [entry for _, entry in all_reviews]

    # Save review to file if requested
    output_file = args.output_file
    if output_file:
        try:
            # Join with newlines for a readable file format
            output_content = "\n".join(all_reviews)
            with open(output_file, "w", encoding="utf-8") as f:
                # Strip leading newline from the first entry for a clean file start
                f.write(output_content.lstrip("\n"))
            logging.info(f"\nFull review log saved to {output_file}")
        except IOError as e:
            logging.error(f"\nError writing to output file: {e}")
            output_file = None  # Clear on failure

    # Summary
    if failed_files:
        logging.warning(f"\n{'=' * 60}")
        logging.warning(f"AI REVIEW FAILED for {len(failed_files)} file(s):")
        for filename in failed_files:
            logging.warning(f"  - {filename}")
        if output_file:
            logging.warning(f"Review details saved to: {output_file}")
        logging.warning(f"{'=' * 60}")
        return 1
    else:
        logging.info(f"\n{'=' * 60}")
        logging.info(f"AI REVIEW PASSED for all {len(args.files)} file(s)")
        if output_file:
            logging.info(f"Review details saved to: {output_file}")
        logging.info(f"{'=' * 60}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
