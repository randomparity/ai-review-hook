"""Tests for filetype-specific prompts functionality."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add the src directory to sys.path to import the local module
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_review_hook.main import (
    AIReviewer,
    get_file_extension,
    load_filetype_prompts,
    select_prompt_template,
)


class TestFiletypePrompts:
    """Test filetype-specific prompts functionality."""

    def test_get_file_extension(self):
        """Test file extension extraction."""
        assert get_file_extension("script.py") == ".py"
        assert get_file_extension("README.md") == ".md"
        assert get_file_extension("/path/to/file.js") == ".js"
        assert get_file_extension("file.TEST.go") == ".go"
        assert get_file_extension("Makefile") == ""
        assert get_file_extension("file.TXT") == ".txt"  # lowercase
        assert get_file_extension("archive.tar.gz") == ".gz"

    def test_select_prompt_template_found(self):
        """Test selecting prompt template when pattern exists."""
        prompts = {"*.py": "Python prompt", "*.js": "JavaScript prompt"}

        result = select_prompt_template("script.py", prompts)
        assert result == "Python prompt"

        result = select_prompt_template("/path/to/app.js", prompts)
        assert result == "JavaScript prompt"

    def test_select_prompt_template_not_found(self):
        """Test selecting prompt template when extension doesn't exist."""
        prompts = {".py": "Python prompt", ".js": "JavaScript prompt"}

        result = select_prompt_template("README.md", prompts)
        assert result is None

        result = select_prompt_template("Makefile", prompts)
        assert result is None

    def test_select_prompt_template_case_insensitive(self):
        """Test prompt selection with case variations."""
        # Case sensitive patterns
        prompts = {"*.py": "Python prompt"}

        result = select_prompt_template("Script.py", prompts)
        assert result == "Python prompt"

        # Case sensitive pattern matching
        result = select_prompt_template("Script.PY", prompts)
        assert result is None  # fnmatch is case-sensitive

    def test_load_filetype_prompts_valid_file(self):
        """Test loading valid filetype prompts file."""
        prompts_data = {
            "*.py": "Review this Python code for PEP8 compliance",
            "*.js": "Review this JavaScript code for modern practices",
            "*.md": "Review this documentation for clarity",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(prompts_data, f)
            temp_path = f.name

        try:
            result = load_filetype_prompts(temp_path)

            # Should keep patterns as-is (no normalization in new system)
            expected = {
                "*.py": "Review this Python code for PEP8 compliance",
                "*.js": "Review this JavaScript code for modern practices",
                "*.md": "Review this documentation for clarity",
            }
            assert result == expected
        finally:
            Path(temp_path).unlink()

    def test_load_filetype_prompts_none_path(self):
        """Test loading prompts with None path."""
        result = load_filetype_prompts(None)
        assert result == {}

    def test_load_filetype_prompts_missing_file(self):
        """Test loading prompts from non-existent file."""
        with patch("ai_review_hook.main.logging") as mock_logging:
            result = load_filetype_prompts("/nonexistent/file.json")
            assert result == {}
            mock_logging.warning.assert_called_once()

    def test_load_filetype_prompts_invalid_json(self):
        """Test loading prompts from invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            temp_path = f.name

        try:
            with patch("ai_review_hook.main.logging") as mock_logging:
                result = load_filetype_prompts(temp_path)
                assert result == {}
                mock_logging.error.assert_called_once()
        finally:
            Path(temp_path).unlink()

    def test_load_filetype_prompts_non_dict_content(self):
        """Test loading prompts from file with non-dict content."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(["not", "a", "dict"], f)
            temp_path = f.name

        try:
            with patch("ai_review_hook.main.logging") as mock_logging:
                result = load_filetype_prompts(temp_path)
                assert result == {}
                mock_logging.error.assert_called_once()
        finally:
            Path(temp_path).unlink()

    def test_load_filetype_prompts_non_string_values(self):
        """Test loading prompts with non-string values."""
        prompts_data = {
            "*.py": "Valid prompt",
            "*.js": 123,  # Invalid non-string
            "*.md": None,  # Invalid None
            "*.go": "Another valid prompt",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(prompts_data, f)
            temp_path = f.name

        try:
            with patch("ai_review_hook.main.logging") as mock_logging:
                result = load_filetype_prompts(temp_path)

                # Should skip invalid values (no normalization in new system)
                expected = {"*.py": "Valid prompt", "*.go": "Another valid prompt"}
                assert result == expected
                # Should warn about skipped values
                assert mock_logging.warning.call_count == 2
        finally:
            Path(temp_path).unlink()


class TestAIReviewerFiletypePrompts:
    """Test AIReviewer with filetype-specific prompts."""

    @pytest.fixture
    def reviewer_with_prompts(self):
        """Create AIReviewer with sample filetype prompts."""
        prompts = {
            "*.py": "IMPORTANT: Your first line must be `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]`.\n\nReview Python file: {filename}\n\nDiff:\n{diff}\n\nContent:\n{content}\n\nFocus on Python-specific issues like PEP8, imports, and type hints.",
            "*.md": "IMPORTANT: Your first line must be `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]`.\n\nReview documentation file: {filename}\n\nChanges:\n{diff}\n\n{diff_only_note}\n\nFocus on grammar, clarity, formatting, and completeness.",
            "*.js": "IMPORTANT: Your first line must be `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]`.\n\nReview JavaScript file: {filename}\n\nDiff: {diff}\nContent: {content}\n\nCheck for modern JS practices, async/await usage, and potential runtime errors.",
        }

        return AIReviewer(api_key="test-key", filetype_prompts=prompts)

    @pytest.fixture
    def reviewer_no_prompts(self):
        """Create AIReviewer without filetype prompts."""
        return AIReviewer(api_key="test-key")

    def test_create_review_prompt_with_custom_prompt(self, reviewer_with_prompts):
        """Test creating review prompt with custom filetype-specific prompt."""
        filename = "script.py"
        diff = "some diff content"
        content = "some file content"

        prompt = reviewer_with_prompts.create_review_prompt(
            filename, diff, content, False
        )

        # Should use custom Python prompt
        assert "Review Python file: script.py" in prompt
        assert "Focus on Python-specific issues like PEP8" in prompt
        assert "some diff content" in prompt
        assert "some file content" in prompt
        assert "AI-REVIEW:[PASS]" in prompt

    def test_create_review_prompt_with_custom_prompt_diff_only(
        self, reviewer_with_prompts
    ):
        """Test creating review prompt with custom prompt in diff-only mode."""
        filename = "README.md"
        diff = "documentation diff"
        content = "file content"

        prompt = reviewer_with_prompts.create_review_prompt(
            filename, diff, content, True
        )

        # Should use custom markdown prompt
        assert "Review documentation file: README.md" in prompt
        assert "Focus on grammar, clarity" in prompt
        assert "documentation diff" in prompt
        # Should not include content in diff-only mode but should show note
        assert "file content" not in prompt
        assert "Only diff is provided for security" in prompt

    def test_create_review_prompt_fallback_to_default(self, reviewer_with_prompts):
        """Test falling back to default prompt when no custom prompt exists."""
        filename = "config.yaml"  # No custom prompt for .yaml
        diff = "yaml diff content"
        content = "yaml file content"

        prompt = reviewer_with_prompts.create_review_prompt(
            filename, diff, content, False
        )

        # Should use default prompt
        assert "Please perform a thorough code review" in prompt
        assert "Code Quality & Best Practices" in prompt
        assert "yaml diff content" in prompt
        assert "yaml file content" in prompt

    def test_create_review_prompt_no_prompts_configured(self, reviewer_no_prompts):
        """Test creating prompt when no filetype prompts are configured."""
        filename = "script.py"
        diff = "python diff"
        content = "python content"

        prompt = reviewer_no_prompts.create_review_prompt(
            filename, diff, content, False
        )

        # Should use default prompt
        assert "Please perform a thorough code review" in prompt
        assert "Code Quality & Best Practices" in prompt

    @patch("ai_review_hook.main.logging")
    def test_create_review_prompt_logs_custom_usage(
        self, mock_logging, reviewer_with_prompts
    ):
        """Test that custom prompt usage is logged in debug mode."""
        filename = "test.js"
        diff = "js diff"
        content = "js content"

        reviewer_with_prompts.create_review_prompt(filename, diff, content, False)

        # Should log debug message about using custom prompt
        mock_logging.debug.assert_called_once()
        debug_call = mock_logging.debug.call_args[0][0]
        assert "filetype-specific prompt" in debug_call
        assert "test.js" in debug_call
        assert ".js" in debug_call

    def test_create_review_prompt_handles_format_placeholders(
        self, reviewer_with_prompts
    ):
        """Test that prompt template placeholders are properly replaced."""
        filename = "app.js"
        diff = "javascript changes"
        content = "javascript code"

        prompt = reviewer_with_prompts.create_review_prompt(
            filename, diff, content, False
        )

        # All placeholders should be replaced
        assert "{filename}" not in prompt
        assert "{diff}" not in prompt
        assert "{content}" not in prompt
        assert "{diff_only_note}" not in prompt

        # Values should be present
        assert "app.js" in prompt
        assert "javascript changes" in prompt
        assert "javascript code" in prompt

    def test_create_review_prompt_empty_content_handling(self, reviewer_with_prompts):
        """Test handling of empty or binary file content."""
        filename = "script.py"
        diff = "some diff"

        # Test with empty content
        prompt = reviewer_with_prompts.create_review_prompt(filename, diff, "", False)
        assert "{content}" not in prompt  # Should not have unresolved placeholder

        # Test with binary file marker
        binary_content = "[BINARY FILE - Content not shown for security]"
        prompt = reviewer_with_prompts.create_review_prompt(
            filename, diff, binary_content, False
        )
        assert "{content}" not in prompt  # Should not include binary content

    def test_filetype_prompts_integration(self):
        """Test end-to-end integration of filetype prompts."""
        # Create a temporary prompts file
        prompts_data = {
            "*.py": "IMPORTANT: Reply with `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]`.\n\nPython Review for: {filename}\nChanges: {diff}\nCode: {content}\n\nCheck Python conventions.",
            "*.md": "IMPORTANT: Reply with `AI-REVIEW:[PASS]` or `AI-REVIEW:[FAIL]`.\n\nMarkdown Review: {filename}\nDiff: {diff}\n{diff_only_note}\n\nCheck documentation quality.",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(prompts_data, f)
            temp_path = f.name

        try:
            # Load prompts and create reviewer
            loaded_prompts = load_filetype_prompts(temp_path)
            reviewer = AIReviewer(api_key="test-key", filetype_prompts=loaded_prompts)

            # Test Python file
            py_prompt = reviewer.create_review_prompt(
                "test.py", "py diff", "py code", False
            )
            assert "Python Review for: test.py" in py_prompt
            assert "Check Python conventions" in py_prompt

            # Test Markdown file in diff-only mode
            md_prompt = reviewer.create_review_prompt(
                "README.md", "md diff", "content", True
            )
            assert "Markdown Review: README.md" in md_prompt
            assert "Only diff is provided for security" in md_prompt

            # Test file without custom prompt (should use default)
            go_prompt = reviewer.create_review_prompt(
                "main.go", "go diff", "go code", False
            )
            assert "Please perform a thorough code review" in go_prompt

        finally:
            Path(temp_path).unlink()
