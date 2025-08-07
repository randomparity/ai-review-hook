#!/usr/bin/env python3
"""
AI Review Hook - Main script for performing AI-assisted code reviews.

This script integrates with pre-commit to provide AI-powered code reviews
using the OpenAI API with configurable models and endpoints.
"""

import argparse
import logging
import os
import re
import subprocess
import sys
from typing import Optional, Tuple

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


def redact(text: str) -> str:
    """Redact secrets from a string using predefined patterns."""
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
        """
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
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
        """Create the AI review prompt."""
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

        # Apply size limits
        if max_diff_bytes > 0 and len(diff.encode("utf-8")) > max_diff_bytes:
            return (
                False,
                f"AI-REVIEW:[FAIL] Diff size ({len(diff.encode('utf-8'))} bytes) exceeds limit ({max_diff_bytes} bytes)",
            )

        content = ""
        if not diff_only:
            content = self.get_file_content(filename)
            if (
                max_content_bytes > 0
                and len(content.encode("utf-8")) > max_content_bytes
            ):
                return (
                    False,
                    f"AI-REVIEW:[FAIL] File content size ({len(content.encode('utf-8'))} bytes) exceeds limit ({max_content_bytes} bytes)",
                )

        # Redact secrets before sending to the model
        redacted_diff = redact(diff)
        redacted_content = redact(content) if content else ""

        prompt = self.create_review_prompt(
            filename, redacted_diff, redacted_content, diff_only
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert code reviewer. Provide thorough, constructive feedback on code changes.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            review_text = response.choices[0].message.content

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
        "--output-file",
        help="File to save the complete review output.",
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

    # Initialize AI reviewer
    try:
        reviewer = AIReviewer(
            api_key=api_key,
            base_url=args.base_url,
            model=args.model,
            timeout=args.timeout,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )
    except Exception as e:
        logging.error(f"Error initializing AI reviewer: {e}")
        return 1

    # Review each file
    failed_files = []
    all_reviews = []

    for filename in args.files:
        logging.info(f"Reviewing {filename}...")

        # This is a synchronous operation. For a large number of files, consider
        # parallelizing this process using concurrent.futures or similar libraries.
        diff = reviewer.get_file_diff(filename, args.context_lines)
        passed, review = reviewer.review_file(
            filename,
            diff=diff,
            max_diff_bytes=args.max_diff_bytes,
            max_content_bytes=args.max_content_bytes,
            diff_only=args.diff_only,
        )

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
        all_reviews.append(review_log_entry)

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
