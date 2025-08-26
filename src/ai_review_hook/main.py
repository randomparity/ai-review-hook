#!/usr/bin/env python3
"""
AI Review Hook - Main script for performing AI-assisted code reviews.

This script integrates with pre-commit to provide AI-powered code reviews
using the OpenAI API with configurable models and endpoints.
"""

import argparse
import concurrent.futures
import logging
import os
import sys
from typing import Dict, List, Optional, Tuple, Any

from .reviewer import AIReviewer, DEFAULT_MODEL, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE
from .formatters import format_as_text, format_as_json, format_as_codeclimate
from .utils import (
    should_review_file,
    parse_file_patterns,
    load_filetype_prompts,
    redact,
    DEFAULT_EXCLUDE_PATTERNS,
)


def main() -> int:
    """Main entry point for the AI review hook."""
    parser = argparse.ArgumentParser(
        description="AI-assisted code review using OpenAI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
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
        "--format",
        choices=["text", "codeclimate", "json"],
        default="text",
        help="Output format. 'text' is human-readable, 'codeclimate' is for GitLab/GitHub integration.",
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
        "--no-default-excludes",
        action="store_true",
        help="Disable the default exclude patterns for common non-reviewable files (e.g., lockfiles, vendored dependencies, minified assets).",
    )
    parser.add_argument(
        "--filetype-prompts",
        help='Path to JSON file containing glob pattern-specific prompts. File should map glob patterns to custom prompt templates (e.g., {"*.py": "Review this Python code...", "tests/**/*.py": "Review this test file...", "src/core/*.py": "Review this core module..."}). Supports exact filenames, extensions, and glob patterns.',
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
                logging.error(
                    "Note: Azure OpenAI and other third-party endpoints require this flag."
                )
                return 1
            else:
                # Warn about non-HTTPS endpoints
                if not args.base_url.startswith("https://"):
                    logging.warning(
                        f"WARNING: Base URL '{args.base_url}' is not using HTTPS! This is insecure."
                    )
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
    user_exclude_patterns = parse_file_patterns(args.exclude_files or [])

    # Combine default and user-specified exclude patterns
    if not args.no_default_excludes:
        exclude_patterns = DEFAULT_EXCLUDE_PATTERNS + user_exclude_patterns
    else:
        exclude_patterns = user_exclude_patterns

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
    all_reviews: List[Tuple[str, bool, str, Optional[List[Dict[str, Any]]]]] = []

    def review_single_file(
        filename: str,
    ) -> Tuple[str, bool, str, str, Optional[List[Dict[str, Any]]]]:
        """Review a single file and return results."""
        diff = reviewer.get_file_diff(filename, args.context_lines)
        passed, review, findings = reviewer.review_file(
            filename,
            diff=diff,
            max_diff_bytes=args.max_diff_bytes,
            max_content_bytes=args.max_content_bytes,
            diff_only=args.diff_only,
        )
        return filename, passed, review, diff, findings

    if args.jobs == 1 or len(args.files) == 1:
        # Sequential processing (original behavior)
        for filename in args.files:
            logging.info(f"Reviewing {filename}...")
            try:
                filename, passed, review, diff, findings = review_single_file(filename)
            except Exception as exc:
                # Handle exceptions in sequential processing same as parallel
                logging.error(f"Review of {filename} generated an exception: {exc}")
                filename, passed, review, diff, findings = (
                    filename,
                    False,
                    f"AI-REVIEW:[FAIL] Exception during review: {exc}",
                    "",
                    None,
                )

            if not passed:
                failed_files.append(filename)

            review_log_entry = f"""

{"=" * 60}
File: {filename}
{"=" * 60}

"""
            if args.verbose:
                # Use redacted diff in logs to prevent secret leakage
                redacted_diff_for_log = redact(diff)
                review_log_entry += f"""Git Diff:
```
{redacted_diff_for_log}```

"""
            review_log_entry += review
            all_reviews.append((filename, passed, review_log_entry, findings))
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
                            None,
                        )
                    )

            # Sort results by original file order
            filename_to_index = {filename: i for i, filename in enumerate(args.files)}
            results.sort(key=lambda x: filename_to_index[x[0]])

            # Process results
            for filename, passed, review, diff, findings in results:
                if not passed:
                    failed_files.append(filename)

                review_log_entry = f"""

{"=" * 60}
File: {filename}
{"=" * 60}

"""
                if args.verbose:
                    # Use redacted diff in logs to prevent secret leakage
                    redacted_diff_for_log = redact(diff)
                    review_log_entry += f"""Git Diff:
```
{redacted_diff_for_log}```

"""
                review_log_entry += review
                all_reviews.append((filename, passed, review_log_entry, findings))

    # Generate output based on format
    if args.format == "text":
        output_content = format_as_text(all_reviews)
    elif args.format == "json":
        output_content = format_as_json(all_reviews)
    elif args.format == "codeclimate":
        output_content = format_as_codeclimate(all_reviews)
    else:
        # Should not happen due to argparse choices
        logging.error(f"Unknown format: {args.format}")
        return 1

    output_file = args.output_file
    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(output_content)
            logging.info(f"\nFull review log saved to {output_file}")
        except IOError as e:
            logging.error(f"\nError writing to output file: {e}")
    else:
        print(output_content)

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
