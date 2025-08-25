import json
import logging
import random
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import openai

from .utils import select_prompt_template, redact, get_file_extension

# Constants
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_MAX_TOKENS = 2000
DEFAULT_TEMPERATURE = 0.1


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
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ):
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
            except (
                subprocess.CalledProcessError,
                subprocess.TimeoutExpired,
                FileNotFoundError,
            ):
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

            # Ensure custom prompts include the required response format instruction
            if "AI-REVIEW:[" not in prompt:
                prompt = (
                    "IMPORTANT: Your first line of response must be either `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]`.\n\n"
                    + prompt
                )
            if "```json" not in prompt:
                prompt += """

Additionally, provide a JSON block containing structured findings, enclosed in markdown-style triple backticks with "json" as the language.
The JSON object should have a single key "findings" which is a list of objects, where each object has the following keys:
- "line": the line number of the issue (integer). If the issue is general or not specific to a line, use null.
- "severity": the severity of the issue, one of "info", "minor", "major", "critical", "blocker" (string).
- "message": a description of the issue (string).
- "check_name": a short, snake_case name for the check (string), e.g., "unused_variable".

If no issues are found, the "findings" list should be empty.
"""

            logging.debug(
                f"Using filetype-specific prompt for {filename} ({get_file_extension(filename)})"
            )
            return prompt

        # Fall back to default prompt
        prompt = f"""Please perform a thorough code review of the following changes.

IMPORTANT: Your response must follow this structure:
1.  A single line with either `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]`.
2.  A detailed, human-readable review.
3.  A JSON block containing structured findings, enclosed in markdown-style triple backticks with "json" as the language.

The JSON object should have a single key "findings" which is a list of objects, where each object has the following keys:
- "line": the line number of the issue (integer). If the issue is general or not specific to a line, use null.
- "severity": the severity of the issue, one of "info", "minor", "major", "critical", "blocker" (string).
- "message": a description of the issue (string).
- "check_name": a short, snake_case name for the check (string), e.g., "unused_variable".

If no issues are found, the "findings" list should be empty.

Example of the JSON block:
```json
{{
  "findings": [
    {{
      "line": 10,
      "severity": "major",
      "message": "Unused variable 'x'.",
      "check_name": "unused_variable"
    }}
  ]
}}
```

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

                # Guard against missing or empty choices
                if not response.choices or len(response.choices) == 0:
                    return (
                        "AI-REVIEW:[FAIL] Empty response from API - no choices returned"
                    )

                if (
                    not response.choices[0].message
                    or not response.choices[0].message.content
                ):
                    return "AI-REVIEW:[FAIL] Empty message content from API"

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

    @staticmethod
    def _parse_review_text(review_text: str) -> Tuple[str, Optional[List[Dict]]]:
        """
        Parses the AI review text to separate the human-readable part and the JSON findings.
        """
        json_findings = None
        human_text = review_text

        # Regex to find the JSON block
        json_match = re.search(r"```json\s*(.*?)\s*```", review_text, re.DOTALL)

        if json_match:
            # The regex now captures content between ```json and ```
            json_str = json_match.group(1).strip()
            try:
                data = json.loads(json_str)
                # Basic validation
                if isinstance(data, dict) and "findings" in data and isinstance(
                    data["findings"], list
                ):
                    json_findings = data["findings"]
                    # Remove the JSON block from the human-readable text
                    human_text = review_text.replace(json_match.group(0), "").strip()
            except json.JSONDecodeError:
                logging.warning(
                    f"Failed to parse JSON findings from AI response: {json_str}"
                )

        return human_text, json_findings

    def _determine_pass_fail(self, review_text: str) -> bool:
        """Determines pass/fail from review text."""
        # Fail-closed: FAIL takes precedence.
        # Check the first line for a definitive marker.
        match = re.match(r"^AI-REVIEW:\[(PASS|FAIL)\]", review_text.strip(), re.IGNORECASE)
        if match:
            result = match.group(1).upper()
            return result == "PASS"

        # Fallback for markers anywhere in the text, prioritizing FAIL
        if re.search(r"AI-REVIEW:\[FAIL\]", review_text, re.IGNORECASE):
            return False
        if re.search(r"AI-REVIEW:\[PASS\]", review_text, re.IGNORECASE):
            return True

        # If neither marker is found, fail the check.
        return False

    def review_file(
        self,
        filename: str,
        diff: str,
        max_diff_bytes: int = 0,
        max_content_bytes: int = 0,
        diff_only: bool = False,
    ) -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        Review a single file using AI.

        Args:
            filename: Path to the file to review
            diff: The git diff of the file
            max_diff_bytes: Maximum diff size to send (0 for no limit)
            max_content_bytes: Maximum file content size to send (0 for no limit)
            diff_only: Only send the diff to the model, not full content

        Returns:
            Tuple of (passed, review_message, findings)
        """
        if not diff.strip():
            return True, f"No changes detected in {filename}", []

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
                return (
                    False,
                    "AI-REVIEW:[FAIL] Empty or blank response from AI model",
                    None,
                )

            human_text, findings = self._parse_review_text(review_text)
            passed = self._determine_pass_fail(review_text)

            # Prepend a marker if the original response was missing one
            if not re.search(r"AI-REVIEW:\[(PASS|FAIL)\]", review_text, re.IGNORECASE):
                human_text = f"AI-REVIEW[MISSING]\n\n{human_text}"

            return passed, human_text, findings

        except openai.APIError as e:
            # Defensively format API error - fields may vary by SDK version
            status_code = getattr(e, "status_code", "unknown")
            message = getattr(e, "message", str(e))
            return (
                False,
                f"AI-REVIEW:[FAIL] OpenAI API Error: {status_code} - {message}",
                None,
            )
        except Exception as e:
            # Catch any other unexpected exceptions
            return (
                False,
                f"AI-REVIEW:[FAIL] Unexpected error during AI review: {str(e)}",
                None,
            )
