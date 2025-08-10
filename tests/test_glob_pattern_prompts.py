#!/usr/bin/env python3
"""
Unit tests for glob pattern-based prompt selection functionality.

Tests the enhanced filetype prompts feature that supports glob patterns
for more flexible file-based prompt selection.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ai_review_hook.main import (
    load_filetype_prompts,
    select_prompt_template,
    AIReviewer,
)


class TestGlobPatternPrompts(unittest.TestCase):
    """Test glob pattern-based prompt selection."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_select_prompt_template_exact_filename_match(self):
        """Test exact filename matching takes highest priority."""
        patterns = {
            "main.py": "Special main file prompt",
            "*.py": "Generic Python prompt",
            "src/**/*.py": "Source Python prompt",
        }

        # Exact filename match should win
        result = select_prompt_template("main.py", patterns)
        self.assertEqual(result, "Special main file prompt")

        result = select_prompt_template("src/main.py", patterns)
        self.assertEqual(result, "Special main file prompt")

    def test_select_prompt_template_path_patterns(self):
        """Test full path pattern matching."""
        patterns = {
            "src/**/*.py": "Source Python prompt",
            "tests/**/*.py": "Test Python prompt",
            "*.py": "Generic Python prompt",
        }

        # Should match path patterns
        result = select_prompt_template("src/core/module.py", patterns)
        self.assertEqual(result, "Source Python prompt")

        result = select_prompt_template("tests/unit/test_module.py", patterns)
        self.assertEqual(result, "Test Python prompt")

    def test_select_prompt_template_extension_patterns(self):
        """Test file extension pattern matching."""
        patterns = {
            "*.py": "Python prompt",
            "*.js": "JavaScript prompt",
            "*.md": "Markdown prompt",
        }

        result = select_prompt_template("script.py", patterns)
        self.assertEqual(result, "Python prompt")

        result = select_prompt_template("app.js", patterns)
        self.assertEqual(result, "JavaScript prompt")

        result = select_prompt_template("README.md", patterns)
        self.assertEqual(result, "Markdown prompt")

    def test_select_prompt_template_basename_patterns(self):
        """Test basename pattern matching."""
        patterns = {
            "test_*.py": "Python test prompt",
            "*_spec.js": "JavaScript spec prompt",
            "config.*": "Configuration prompt",
        }

        result = select_prompt_template("test_module.py", patterns)
        self.assertEqual(result, "Python test prompt")

        result = select_prompt_template("src/test_module.py", patterns)
        self.assertEqual(result, "Python test prompt")

        result = select_prompt_template("module_spec.js", patterns)
        self.assertEqual(result, "JavaScript spec prompt")

        result = select_prompt_template("config.yaml", patterns)
        self.assertEqual(result, "Configuration prompt")

    def test_select_prompt_template_priority_order(self):
        """Test that pattern matching follows correct priority order."""
        patterns = {
            "test.py": "Exact match prompt",  # Priority 1
            "tests/*.py": "Test directory prompt",  # Priority 2
            "*.py": "Generic Python prompt",  # Priority 3
            "test_*.py": "Test file prompt",  # Priority 4
        }

        # Exact match should win
        result = select_prompt_template("test.py", patterns)
        self.assertEqual(result, "Exact match prompt")

        # Path pattern should win over extension pattern
        result = select_prompt_template("tests/module.py", patterns)
        self.assertEqual(result, "Test directory prompt")

        # Generic extension for files not matching specific patterns
        result = select_prompt_template("main.py", patterns)
        self.assertEqual(result, "Generic Python prompt")

    def test_select_prompt_template_specificity_order(self):
        """Test that more specific patterns (longer) are matched first."""
        patterns = {
            "*.py": "Generic Python prompt",
            "test_*.py": "Test Python prompt",
            "tests/**/*.py": "Nested test Python prompt",
        }

        # More specific pattern should win
        result = select_prompt_template("tests/unit/test_module.py", patterns)
        self.assertEqual(result, "Nested test Python prompt")

        result = select_prompt_template("test_module.py", patterns)
        self.assertEqual(result, "Test Python prompt")

        result = select_prompt_template("main.py", patterns)
        self.assertEqual(result, "Generic Python prompt")

    def test_select_prompt_template_no_match(self):
        """Test behavior when no pattern matches."""
        patterns = {"*.py": "Python prompt", "*.js": "JavaScript prompt"}

        result = select_prompt_template("README.md", patterns)
        self.assertIsNone(result)

        result = select_prompt_template("config.yaml", patterns)
        self.assertIsNone(result)

    def test_select_prompt_template_empty_patterns(self):
        """Test behavior with empty pattern dictionary."""
        result = select_prompt_template("main.py", {})
        self.assertIsNone(result)

        result = select_prompt_template("main.py", None)
        self.assertIsNone(result)

    def test_load_filetype_prompts_valid_file(self):
        """Test loading valid JSON prompt file."""
        prompts_data = {
            "*.py": "Review this Python code for PEP8 compliance and best practices.",
            "tests/**/*.py": "Review this test file for test completeness and clarity.",
            "*.md": "Review this Markdown documentation for clarity and accuracy.",
            "src/core/*.py": "Review this core module with extra attention to performance.",
        }

        # Create temporary file
        prompts_file = os.path.join(self.temp_dir, "prompts.json")
        with open(prompts_file, "w") as f:
            json.dump(prompts_data, f)

        result = load_filetype_prompts(prompts_file)
        self.assertEqual(result, prompts_data)

    def test_load_filetype_prompts_nonexistent_file(self):
        """Test loading nonexistent prompt file."""
        with patch("src.ai_review_hook.main.logging") as mock_logging:
            result = load_filetype_prompts("/nonexistent/file.json")
            self.assertEqual(result, {})
            mock_logging.warning.assert_called_once()

    def test_load_filetype_prompts_invalid_json(self):
        """Test loading invalid JSON file."""
        # Create file with invalid JSON
        prompts_file = os.path.join(self.temp_dir, "invalid.json")
        with open(prompts_file, "w") as f:
            f.write("{ invalid json }")

        with patch("src.ai_review_hook.main.logging") as mock_logging:
            result = load_filetype_prompts(prompts_file)
            self.assertEqual(result, {})
            mock_logging.error.assert_called_once()

    def test_load_filetype_prompts_non_dict_content(self):
        """Test loading JSON file with non-dictionary content."""
        prompts_file = os.path.join(self.temp_dir, "non_dict.json")
        with open(prompts_file, "w") as f:
            json.dump(["not", "a", "dict"], f)

        with patch("src.ai_review_hook.main.logging") as mock_logging:
            result = load_filetype_prompts(prompts_file)
            self.assertEqual(result, {})
            mock_logging.error.assert_called_once()

    def test_load_filetype_prompts_non_string_values(self):
        """Test loading prompts with non-string values."""
        prompts_data = {
            "*.py": "Valid Python prompt",
            "*.js": 123,  # Invalid: not a string
            "*.md": {"invalid": "dict"},  # Invalid: not a string
            "*.go": "Valid Go prompt",
        }

        prompts_file = os.path.join(self.temp_dir, "mixed_types.json")
        with open(prompts_file, "w") as f:
            json.dump(prompts_data, f)

        with patch("src.ai_review_hook.main.logging") as mock_logging:
            result = load_filetype_prompts(prompts_file)
            expected = {"*.py": "Valid Python prompt", "*.go": "Valid Go prompt"}
            self.assertEqual(result, expected)
            self.assertEqual(mock_logging.warning.call_count, 2)

    def test_load_filetype_prompts_none_path(self):
        """Test loading prompts with None path."""
        result = load_filetype_prompts(None)
        self.assertEqual(result, {})

    def test_load_filetype_prompts_empty_path(self):
        """Test loading prompts with empty path."""
        result = load_filetype_prompts("")
        self.assertEqual(result, {})


class TestAIReviewerGlobPatternIntegration(unittest.TestCase):
    """Test AIReviewer integration with glob pattern prompts."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = Mock()

    @patch("src.ai_review_hook.main.openai.OpenAI")
    def test_create_review_prompt_with_glob_patterns(self, mock_openai):
        """Test review prompt creation with glob pattern prompts."""
        glob_patterns = {
            "*.py": "AI-REVIEW:[PASS]\nPython-specific prompt for {filename}:\n{diff}\n{content}",
            "tests/**/*.py": "AI-REVIEW:[PASS]\nTest-specific prompt for {filename}:\n{diff}\n{content}",
            "src/core/*.py": "AI-REVIEW:[PASS]\nCore module prompt for {filename}:\n{diff}\n{content}",
        }

        reviewer = AIReviewer(api_key="test-key", filetype_prompts=glob_patterns)

        # Test generic Python file
        prompt = reviewer.create_review_prompt(
            "main.py", "diff content", "file content"
        )
        self.assertIn("Python-specific prompt for main.py", prompt)

        # Test test file (should match more specific pattern)
        prompt = reviewer.create_review_prompt(
            "tests/unit/test_main.py", "diff content", "file content"
        )
        self.assertIn("Test-specific prompt for tests/unit/test_main.py", prompt)

        # Test core module file
        prompt = reviewer.create_review_prompt(
            "src/core/engine.py", "diff content", "file content"
        )
        self.assertIn("Core module prompt for src/core/engine.py", prompt)

    @patch("src.ai_review_hook.main.openai.OpenAI")
    def test_create_review_prompt_fallback_to_default(self, mock_openai):
        """Test fallback to default prompt when no pattern matches."""
        glob_patterns = {
            "*.py": "Python-specific prompt",
            "*.js": "JavaScript-specific prompt",
        }

        reviewer = AIReviewer(api_key="test-key", filetype_prompts=glob_patterns)

        # Test file that doesn't match any pattern
        prompt = reviewer.create_review_prompt(
            "README.md", "diff content", "file content"
        )
        self.assertIn("Please perform a thorough code review", prompt)
        self.assertIn("AI-REVIEW:[PASS]", prompt)

    @patch("src.ai_review_hook.main.openai.OpenAI")
    def test_create_review_prompt_complex_glob_patterns(self, mock_openai):
        """Test complex glob patterns including wildcards and paths."""
        glob_patterns = {
            "Dockerfile*": "AI-REVIEW:[PASS]\nDockerfile review prompt",
            "*.dockerfile": "AI-REVIEW:[PASS]\nGeneric dockerfile prompt",
            "docker/**/*": "AI-REVIEW:[PASS]\nDocker directory prompt",
            "src/**/test_*.py": "AI-REVIEW:[PASS]\nDeep test file prompt",
            "config.*": "AI-REVIEW:[PASS]\nConfiguration file prompt",
        }

        reviewer = AIReviewer(api_key="test-key", filetype_prompts=glob_patterns)

        # Test Dockerfile
        prompt = reviewer.create_review_prompt("Dockerfile", "diff", "content")
        self.assertIn("Dockerfile review prompt", prompt)

        # Test dockerfile extension
        prompt = reviewer.create_review_prompt("app.dockerfile", "diff", "content")
        self.assertIn("Generic dockerfile prompt", prompt)

        # Test docker directory
        prompt = reviewer.create_review_prompt(
            "docker/compose/app.yaml", "diff", "content"
        )
        self.assertIn("Docker directory prompt", prompt)

        # Test deep test file
        prompt = reviewer.create_review_prompt(
            "src/module/test_feature.py", "diff", "content"
        )
        self.assertIn("Deep test file prompt", prompt)

        # Test config file
        prompt = reviewer.create_review_prompt("config.yaml", "diff", "content")
        self.assertIn("Configuration file prompt", prompt)

    @patch("src.ai_review_hook.main.openai.OpenAI")
    def test_create_review_prompt_with_placeholders(self, mock_openai):
        """Test that custom prompts properly handle format placeholders."""
        glob_patterns = {
            "*.py": "AI-REVIEW:[PASS]\nReviewing {filename}:\nDiff: {diff}\nContent: {content}\n{diff_only_note}"
        }

        reviewer = AIReviewer(api_key="test-key", filetype_prompts=glob_patterns)

        # Test normal mode
        prompt = reviewer.create_review_prompt(
            "test.py", "test diff", "test content", diff_only=False
        )
        self.assertIn("Reviewing test.py", prompt)
        self.assertIn("Diff: test diff", prompt)
        self.assertIn("Content: test content", prompt)
        self.assertNotIn("Note: Only diff is provided", prompt)

        # Test diff-only mode
        prompt = reviewer.create_review_prompt(
            "test.py", "test diff", "test content", diff_only=True
        )
        self.assertIn("Note: Only diff is provided for security", prompt)


class TestGlobPatternEdgeCases(unittest.TestCase):
    """Test edge cases for glob pattern matching."""

    def test_case_sensitivity(self):
        """Test case sensitivity in pattern matching."""
        patterns = {
            "*.PY": "Uppercase Python prompt",
            "*.py": "Lowercase Python prompt",
        }

        # fnmatch should be case-sensitive on most systems
        result = select_prompt_template("main.py", patterns)
        self.assertEqual(result, "Lowercase Python prompt")

        result = select_prompt_template("main.PY", patterns)
        self.assertEqual(result, "Uppercase Python prompt")

    def test_special_characters_in_patterns(self):
        """Test patterns with special characters."""
        patterns = {
            "*-test.py": "Dash test prompt",
            "test_*.py": "Underscore test prompt",
            "*.min.js": "Minified JS prompt",
            "[Mm]akefile": "Makefile prompt",
        }

        result = select_prompt_template("module-test.py", patterns)
        self.assertEqual(result, "Dash test prompt")

        result = select_prompt_template("test_module.py", patterns)
        self.assertEqual(result, "Underscore test prompt")

        result = select_prompt_template("app.min.js", patterns)
        self.assertEqual(result, "Minified JS prompt")

        result = select_prompt_template("Makefile", patterns)
        self.assertEqual(result, "Makefile prompt")

        result = select_prompt_template("makefile", patterns)
        self.assertEqual(result, "Makefile prompt")

    def test_overlapping_patterns(self):
        """Test behavior with overlapping patterns."""
        patterns = {
            "test*.py": "Test prefix prompt",
            "*test.py": "Test suffix prompt",
            "test_*_test.py": "Double test prompt",
        }

        # Should match the longest/most specific pattern first
        result = select_prompt_template("test_module_test.py", patterns)
        self.assertEqual(result, "Double test prompt")

        result = select_prompt_template("test_module.py", patterns)
        self.assertEqual(result, "Test prefix prompt")

        result = select_prompt_template("module_test.py", patterns)
        self.assertEqual(result, "Test suffix prompt")

    def test_deep_directory_patterns(self):
        """Test very deep directory structure patterns."""
        patterns = {
            "src/**/tests/**/*.py": "Deep test prompt",
            "src/**/*.py": "Source prompt",
            "**/**/test_*.py": "Any deep test prompt",
        }

        result = select_prompt_template(
            "src/module/submodule/tests/unit/test_feature.py", patterns
        )
        self.assertEqual(result, "Deep test prompt")

        result = select_prompt_template("src/module/feature.py", patterns)
        self.assertEqual(result, "Source prompt")

        result = select_prompt_template("any/deep/path/test_something.py", patterns)
        self.assertEqual(result, "Any deep test prompt")


if __name__ == "__main__":
    unittest.main()
