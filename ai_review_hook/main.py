#!/usr/bin/env python3
"""
AI Review Hook - Main script for performing AI-assisted code reviews.

This script integrates with pre-commit to provide AI-powered code reviews
using the OpenAI API with configurable models and endpoints.
"""

import argparse
import os
import sys
import subprocess
import re
import logging
from typing import Tuple

try:
    import openai
except ImportError:
    logging.error("Error: openai package not found. Please install with: pip install openai")
    sys.exit(1)


class AIReviewer:
    """Handles AI-powered code review using OpenAI API."""
    
def __init__(self, api_key: str, base_url: str = None, model: str = "gpt-4o-mini", timeout: int = 30):
        """
        Initialize the AI reviewer.
        
        Args:
            api_key: OpenAI API key
            base_url: Custom API base URL (optional)
            model: Model to use for review
            timeout: Timeout for API requests in seconds
        """
        self.model = model
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )
    
    def get_file_diff(self, filename: str, context_lines: int = 3) -> str:
        """Get the git diff for a specific file with configurable context.
        
        Args:
            filename: Path to the file
            context_lines: Number of context lines to include around changes
        """
        try:
            # Get staged changes for the file with custom context
            result = subprocess.run(
                ["git", "diff", "--cached", f"--unified={context_lines}", "--", filename],
                capture_output=True,
                text=True,
                check=True,
                timeout=30
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
                    timeout=30
                )
                return result.stdout
            except subprocess.CalledProcessError:
                return ""
    
    def get_file_content(self, filename: str) -> str:
        """Read the current content of a file."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return f.read()
        except (IOError, UnicodeDecodeError) as e:
            return f"Error reading file: {e}"
    
    def create_review_prompt(self, filename: str, diff: str, content: str) -> str:
        """Create the AI review prompt."""
        return f"""Please perform a thorough code review of the following changes.

IMPORTANT: Your first line of response must be either `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]`.

File: {filename}

Git Diff:
```
{diff}
```

Current File Content:
```
{content}
```

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
    
    def review_file(self, filename: str, context_lines: int = 3) -> Tuple[bool, str]:
        """
        Review a single file using AI.
        
        Args:
            filename: Path to the file to review
            context_lines: Number of context lines to include in git diff
        
        Returns:
            Tuple of (passed, review_message)
        """
        diff = self.get_file_diff(filename, context_lines)
        if not diff.strip():
            return True, f"No changes detected in {filename}"
        
        content = self.get_file_content(filename)
        prompt = self.create_review_prompt(filename, diff, content)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert code reviewer. Provide thorough, constructive feedback on code changes."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            review_text = response.choices[0].message.content

            # Fail-closed: FAIL takes precedence. Check the first line for a definitive marker.
            match = re.match(r'^AI-REVIEW:\\[(PASS|FAIL)\\]', review_text.strip(), re.IGNORECASE)
            if match:
                result = match.group(1).upper()
                if result == 'FAIL':
                    return False, review_text
                elif result == 'PASS':
                    return True, review_text

            # Fallback for markers anywhere in the text, prioritizing FAIL
            if re.search("AI-REVIEW:\\[FAIL\\]", review_text, re.IGNORECASE):
                return False, review_text
            if re.search("AI-REVIEW:\\[PASS\\]", review_text, re.IGNORECASE):
                return True, review_text

            # If neither marker is found, fail the check.
            return False, f"AI-REVIEW[MISSING]\n\n{review_text}"

        except openai.APIError as e:
            return False, f"AI-REVIEW:[FAIL] OpenAI API Error: {e.status_code} - {e.message}"


def main() -> int:
    """Main entry point for the AI review hook."""
    parser = argparse.ArgumentParser(description="AI-assisted code review using OpenAI")
    parser.add_argument(
        "files",
        nargs="*",
        help="Files to review"
    )
    parser.add_argument(
        "--api-key-env",
        default="OPENAI_API_KEY",
        help="Environment variable containing the OpenAI API key (default: OPENAI_API_KEY)"
    )
    parser.add_argument(
        "--base-url",
        help="Custom API base URL (e.g., for Azure OpenAI or other compatible APIs)"
    )
    parser.add_argument(
        "--model",
        default="gpt-3.5-turbo",
        help="OpenAI model to use (default: gpt-4o-mini)"
    )
    parser.add_argument(
        "--timeout", type=int,
        default=30,
        help="API request timeout in seconds"
    )
    parser.add_argument(
        "--max-diff-bytes", type=int,
        default=10000,
        help="Maximum diff size to send"
    )
    parser.add_argument(
        "--max-content-bytes", type=int,
        default=0,
        help="Maximum file content size to send (0 for no limit)"
    )
    parser.add_argument(
        "--diff-only",
        action="store_true",
        help="Only send the diff to the model")
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--context-lines",
        type=int,
        default=3,
        help="Number of context lines to include in git diff (default: 3)"
    )
    parser.add_argument(
        "--output-file",
        help="File to save the complete review output.",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format='%(levelname)s: %(message)s')

    if args.base_url and not args.base_url.startswith("https://api.openai.com"):
        logging.warning(f"Using a custom base URL: {args.base_url}. Ensure it is trusted.")
    if not api_key:
        logging.error(f"API key not found in environment variable '{args.api_key_env}'")
        logging.error(f"Please set the environment variable: export {args.api_key_env}=your_api_key")
        return 1

    if not args.files:
        logging.info("No files to review")
        return 0

    # Initialize AI reviewer
    try:
        reviewer = AIReviewer(api_key=api_key, base_url=args.base_url, model=args.model, timeout=args.timeout)
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
        passed, review = reviewer.review_file(filename, args.context_lines)
        all_reviews.append(f"\n{'='*60}\nFile: {filename}\\n{'='*60}\\n{review}")

        if not passed:
            failed_files.append(filename)

    for review in all_reviews:
        print(review)

    # Save review to file if requested
    output_file = args.output_file
    if output_file:
        try:
            # Join with newlines for a readable file format
            output_content = "\n".join(all_reviews)
            with open(output_file, "w", encoding="utf-8") as f:
                # Strip leading newline from the first entry for a clean file start
                f.write(output_content.lstrip('\n'))
            logging.info(f"\nFull review log saved to {output_file}")
        except IOError as e:
            logging.error(f"\nError writing to output file: {e}")
            output_file = None  # Clear on failure

    # Summary
    if failed_files:
        logging.warning(f"\n{'='*60}")
        logging.warning(f"AI REVIEW FAILED for {len(failed_files)} file(s):")
        for filename in failed_files:
            logging.warning(f"  - {filename}")
        if output_file:
            logging.warning(f"Review details saved to: {output_file}")
        logging.warning(f"{'='*60}")
        return 1
    else:
        logging.info(f"\n{'='*60}")
        logging.info(f"AI REVIEW PASSED for all {len(args.files)} file(s)")
        if output_file:
            logging.info(f"Review details saved to: {output_file}")
        logging.info(f"{'='*60}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
