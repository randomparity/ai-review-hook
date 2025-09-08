from unittest.mock import MagicMock, patch
from src.ai_review_hook.main import main, should_review_file


def test_command_line_file_filtering():
    """Test that command line arguments for file filtering are parsed correctly."""
    import sys

    # Test argument parsing
    test_args = [
        "ai-review",
        "--include-files",
        "*.py",
        "--include-files",
        "*.js,*.ts",
        "--exclude-files",
        "*.test.py",
        "--exclude-files",
        "*.spec.*,*.min.*",
        "--verbose",
        "file1.py",
        "file2.js",
        "file3.test.py",
        "file4.min.js",
    ]

    with patch.object(sys, "argv", test_args):
        with patch("os.getenv", return_value="fake-api-key"):
            with patch("src.ai_review_hook.main.AIReviewer") as mock_reviewer_class:
                # Mock the reviewer instance
                mock_reviewer = MagicMock()
                mock_reviewer.get_file_diff.return_value = "- sample diff"
                mock_reviewer.review_file.return_value = (
                    True,
                    "AI-REVIEW:[PASS] Good code",
                    None,
                )
                mock_reviewer_class.return_value = mock_reviewer

                # Mock logging to capture filter messages
                with patch("logging.info") as mock_log:
                    result = main()

                    # Should succeed (exit code 0)
                    assert result == 0

                    # Verify filtering was applied - check log calls
                    log_calls = [call[0][0] for call in mock_log.call_args_list]
                    filter_logs = [log for log in log_calls if "File filtering:" in log]
                    assert len(filter_logs) > 0

                    # Should have reviewed file1.py and file2.js, skipped test and min files
                    review_calls = mock_reviewer.review_file.call_args_list
                    # Should be called exactly twice (for file1.py and file2.js)
                    assert len(review_calls) == 2


def test_file_filtering_no_matches():
    """Test behavior when no files match filtering criteria."""
    import sys

    test_args = [
        "ai-review",
        "--include-files",
        "*.py",
        "--verbose",
        "file1.js",
        "file2.css",  # No .py files
    ]

    with patch.object(sys, "argv", test_args):
        with patch("os.getenv", return_value="fake-api-key"):
            with patch("logging.info") as mock_log:
                result = main()

                # Should exit with code 0 (no files to review is not an error)
                assert result == 0

                # Should log that no files match criteria
                log_calls = [call[0][0] for call in mock_log.call_args_list]
                no_match_logs = [log for log in log_calls if "No files match" in log]
                assert len(no_match_logs) > 0


def test_file_filtering_edge_cases():
    """Test edge cases for file filtering."""
    # Test with empty filename
    assert should_review_file("", [], [])

    # Test with None patterns
    assert should_review_file("test.py", [], [])

    # Test with complex path patterns
    assert should_review_file("src/deep/nested/file.py", ["**/*.py"], [])
    assert should_review_file("src/deep/nested/file.py", ["src/**/*.py"], [])
    assert not should_review_file("other/deep/nested/file.py", ["src/**/*.py"], [])

    # Test with overlapping patterns
    include = ["*.py", "src/*.py"]
    exclude = ["test_*.py", "**/test_*"]
    assert should_review_file("src/main.py", include, exclude)
    assert not should_review_file("src/test_main.py", include, exclude)


@patch("src.ai_review_hook.main.format_as_json")
@patch("src.ai_review_hook.main.AIReviewer")
def test_main_format_json(mock_reviewer_class, mock_formatter):
    """Test that main calls the json formatter."""
    import sys

    # Mock AIReviewer
    mock_reviewer = MagicMock()
    mock_reviewer.get_file_diff.return_value = "- diff"
    mock_reviewer.review_file.return_value = (True, "AI-REVIEW:[PASS]", [])
    mock_reviewer_class.return_value = mock_reviewer

    # Mock the formatter to check if it's called
    mock_formatter.return_value = "[]"

    test_args = ["ai-review", "--format", "json", "file1.py"]
    with patch.object(sys, "argv", test_args):
        with patch("os.getenv", return_value="fake-api-key"):
            with patch("builtins.print") as mock_print:
                main()
                mock_formatter.assert_called_once()
                mock_print.assert_called_with("[]")


@patch("src.ai_review_hook.main.format_as_codeclimate")
@patch("src.ai_review_hook.main.AIReviewer")
def test_main_format_codeclimate(mock_reviewer_class, mock_formatter):
    """Test that main calls the codeclimate formatter."""
    import sys

    # Mock AIReviewer
    mock_reviewer = MagicMock()
    mock_reviewer.get_file_diff.return_value = "- diff"
    mock_reviewer.review_file.return_value = (True, "AI-REVIEW:[PASS]", [])
    mock_reviewer_class.return_value = mock_reviewer

    # Mock the formatter to check if it's called
    mock_formatter.return_value = "[]"

    test_args = ["ai-review", "--format", "codeclimate", "file1.py"]
    with patch.object(sys, "argv", test_args):
        with patch("os.getenv", return_value="fake-api-key"):
            with patch("builtins.print") as mock_print:
                main()
                mock_formatter.assert_called_once()
                mock_print.assert_called_with("[]")


@patch("src.ai_review_hook.main.format_as_text")
@patch("src.ai_review_hook.main.AIReviewer")
def test_main_format_text(mock_reviewer_class, mock_formatter):
    """Test that main calls the text formatter."""
    import sys

    # Mock AIReviewer
    mock_reviewer = MagicMock()
    mock_reviewer.get_file_diff.return_value = "- diff"
    mock_reviewer.review_file.return_value = (True, "AI-REVIEW:[PASS]", [])
    mock_reviewer_class.return_value = mock_reviewer

    # Mock the formatter to check if it's called
    mock_formatter.return_value = "text output"

    test_args = ["ai-review", "--format", "text", "file1.py"]
    with patch.object(sys, "argv", test_args):
        with patch("os.getenv", return_value="fake-api-key"):
            with patch("builtins.print") as mock_print:
                main()
                mock_formatter.assert_called_once()
                mock_print.assert_called_with("text output")


@patch("logging.error")
def test_main_no_api_key(mock_log_error):
    """Test that main exits gracefully if no API key is found."""
    import sys

    test_args = ["ai-review", "file1.py"]
    with patch.object(sys, "argv", test_args):
        with patch("os.getenv", return_value=None):  # No API key
            result = main()
            # Should exit with error code 1
            assert result == 1
            # Should log an error message
            assert mock_log_error.call_count == 2
            mock_log_error.assert_any_call(
                "API key not found in environment variable 'OPENAI_API_KEY'"
            )


@patch("src.ai_review_hook.main.AIReviewer")
@patch("logging.warning")
def test_main_invalid_filetype_prompts_path(mock_log_warning, mock_reviewer_class):
    """Test that main warns but continues if the filetype-prompts file is not found."""
    import sys

    # Mock AIReviewer
    mock_reviewer = MagicMock()
    mock_reviewer.get_file_diff.return_value = "- diff"
    mock_reviewer.review_file.return_value = (True, "AI-REVIEW:[PASS]", [])
    mock_reviewer_class.return_value = mock_reviewer

    test_args = [
        "ai-review",
        "--filetype-prompts",
        "non_existent_path.json",
        "file1.py",
    ]
    with patch.object(sys, "argv", test_args):
        with patch("os.getenv", return_value="fake-api-key"):
            result = main()
            # Should exit with code 0 as it's a non-fatal warning
            assert result == 0
            # Should log a warning message
            mock_log_warning.assert_called_once()
            assert "Filetype prompts file not found" in mock_log_warning.call_args[0][0]


@patch("src.ai_review_hook.main.AIReviewer")
@patch("logging.error")
def test_main_unreadable_file(mock_log_error, mock_reviewer_class):
    """Test that main handles unreadable files gracefully and returns an error code."""
    import sys

    # Mock AIReviewer to raise an error for one file
    mock_reviewer = MagicMock()

    def mock_review_file(filename, *args, **kwargs):
        if filename == "unreadable.py":
            raise IOError("Permission denied")
        return (True, "AI-REVIEW:[PASS]", [])

    mock_reviewer.review_file.side_effect = mock_review_file
    mock_reviewer_class.return_value = mock_reviewer

    test_args = ["ai-review", "unreadable.py", "readable.py"]
    with patch.object(sys, "argv", test_args):
        with patch("os.getenv", return_value="fake-api-key"):
            result = main()

            # Should fail because one of the files had an error
            assert result == 1
            # Should have logged an error for the unreadable file
            mock_log_error.assert_called_once()
            assert (
                "Review of unreadable.py generated an exception: Permission denied"
                in mock_log_error.call_args[0][0]
            )
            # Should have attempted to review both files
            assert mock_reviewer.review_file.call_count == 2


@patch("src.ai_review_hook.main.AIReviewer")
def test_main_with_filetype_prompts(mock_reviewer_class, tmp_path):
    """Test that main correctly loads and uses filetype-specific prompts."""
    import sys
    import json

    # Create a temporary prompts file
    prompts = {"*.py": "Custom Python prompt"}
    prompts_file = tmp_path / "prompts.json"
    prompts_file.write_text(json.dumps(prompts))

    # Mock AIReviewer
    mock_reviewer = MagicMock()
    mock_reviewer_class.return_value = mock_reviewer

    test_args = [
        "ai-review",
        "--filetype-prompts",
        str(prompts_file),
        "file1.py",
    ]
    with patch.object(sys, "argv", test_args):
        with patch("os.getenv", return_value="fake-api-key"):
            main()
            # The AIReviewer should be initialized with the custom prompts
            mock_reviewer_class.assert_called_once()
            _, kwargs = mock_reviewer_class.call_args
            assert kwargs["filetype_prompts"] == prompts


@patch("src.ai_review_hook.main.AIReviewer")
def test_main_no_default_excludes(mock_reviewer_class):
    """Test that --no-default-excludes flag works correctly."""
    import sys

    # Mock AIReviewer
    mock_reviewer = MagicMock()
    mock_reviewer.review_file.return_value = (True, "AI-REVIEW:[PASS]", [])
    mock_reviewer_class.return_value = mock_reviewer

    # A file that would normally be excluded
    normally_excluded_file = "package-lock.json"

    test_args = [
        "ai-review",
        "--no-default-excludes",
        normally_excluded_file,
    ]
    with patch.object(sys, "argv", test_args):
        with patch("os.getenv", return_value="fake-api-key"):
            main()
            # The normally excluded file should have been reviewed
            mock_reviewer.review_file.assert_called_once()
            assert mock_reviewer.review_file.call_args[0][0] == normally_excluded_file


@patch("src.ai_review_hook.main.AIReviewer")
def test_main_with_failing_review(mock_reviewer_class):
    """Test that main returns a non-zero exit code if a review fails."""
    import sys

    # Mock AIReviewer to return a failed review
    mock_reviewer = MagicMock()
    mock_reviewer.review_file.return_value = (False, "AI-REVIEW:[FAIL]", [])
    mock_reviewer_class.return_value = mock_reviewer

    test_args = ["ai-review", "file1.py"]
    with patch.object(sys, "argv", test_args):
        with patch("os.getenv", return_value="fake-api-key"):
            result = main()
            # Should return 1 because the review failed
            assert result == 1


@patch("src.ai_review_hook.main.AIReviewer")
def test_main_end_to_end_scenario(mock_reviewer_class, tmp_path):
    """Test a more complete end-to-end scenario."""
    import sys
    import json

    # --- Setup ---
    # 1. Create a temporary prompts file
    prompts = {"*.py": "Custom Python prompt"}
    prompts_file = tmp_path / "prompts.json"
    prompts_file.write_text(json.dumps(prompts))

    # 2. Mock AIReviewer
    mock_reviewer = MagicMock()

    def mock_review_file(filename, *args, **kwargs):
        if filename == "failing.py":
            return (False, "AI-REVIEW:[FAIL]", [])
        return (True, "AI-REVIEW:[PASS]", [])

    mock_reviewer.review_file.side_effect = mock_review_file
    mock_reviewer_class.return_value = mock_reviewer

    # --- Execution ---
    test_args = [
        "ai-review",
        "--filetype-prompts",
        str(prompts_file),
        "passing.py",
        "failing.py",
    ]
    with patch.object(sys, "argv", test_args):
        with patch("os.getenv", return_value="fake-api-key"):
            with patch("logging.warning") as mock_log_warning:
                result = main()

                # --- Assertions ---
                # 1. Should return 1 because one review failed
                assert result == 1

                # 2. AIReviewer should have been initialized with prompts
                mock_reviewer_class.assert_called_once()
                _, kwargs = mock_reviewer_class.call_args
                assert kwargs["filetype_prompts"] == prompts

                # 3. review_file should have been called for both files
                assert mock_reviewer.review_file.call_count == 2

                # 4. Final summary should be logged as a warning
                log_calls = " ".join(
                    [call[0][0] for call in mock_log_warning.call_args_list]
                )
                assert "AI REVIEW FAILED" in log_calls
