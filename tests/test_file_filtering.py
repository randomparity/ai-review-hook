#!/usr/bin/env python3
"""
Unit tests for file type filtering functionality in AI Review Hook.
"""

import pytest
from src.ai_review_hook.utils import (
    should_review_file,
    parse_file_patterns,
    DEFAULT_EXCLUDE_PATTERNS,
)


class TestFileFiltering:
    """Test cases for file filtering functionality."""

    def test_should_review_file_no_patterns(self):
        """Test that all files are included when no patterns are specified."""
        # No patterns means include everything
        assert should_review_file("test.py", [], [])
        assert should_review_file("app.js", [], [])
        assert should_review_file("style.css", [], [])
        assert should_review_file("README.md", [], [])

    def test_should_review_file_include_patterns_only(self):
        """Test file inclusion with include patterns only."""
        include_patterns = ["*.py", "*.js"]

        # Should include matching files
        assert should_review_file("test.py", include_patterns, [])
        assert should_review_file("app.js", include_patterns, [])
        assert should_review_file("src/module.py", include_patterns, [])
        assert should_review_file("scripts/build.js", include_patterns, [])

        # Should exclude non-matching files
        assert not should_review_file("style.css", include_patterns, [])
        assert not should_review_file("README.md", include_patterns, [])
        assert not should_review_file("config.json", include_patterns, [])

    def test_should_review_file_exclude_patterns_only(self):
        """Test file exclusion with exclude patterns only."""
        exclude_patterns = ["*.test.py", "*.spec.js", "*.min.*"]

        # Should exclude matching files
        assert not should_review_file("test_utils.test.py", [], exclude_patterns)
        assert not should_review_file("component.spec.js", [], exclude_patterns)
        assert not should_review_file("app.min.js", [], exclude_patterns)
        assert not should_review_file("styles.min.css", [], exclude_patterns)

        # Should include non-matching files
        assert should_review_file("utils.py", [], exclude_patterns)
        assert should_review_file("component.js", [], exclude_patterns)
        assert should_review_file("app.js", [], exclude_patterns)

    def test_should_review_file_exclude_takes_precedence(self):
        """Test that exclude patterns take precedence over include patterns."""
        include_patterns = ["*.py", "*.js"]
        exclude_patterns = ["*.test.py", "*.spec.js"]

        # Regular files should be included
        assert should_review_file("utils.py", include_patterns, exclude_patterns)
        assert should_review_file("component.js", include_patterns, exclude_patterns)

        # Test files should be excluded despite matching include pattern
        assert not should_review_file(
            "utils.test.py", include_patterns, exclude_patterns
        )
        assert not should_review_file(
            "component.spec.js", include_patterns, exclude_patterns
        )

        # Files not matching include pattern should be excluded
        assert not should_review_file("README.md", include_patterns, exclude_patterns)

    def test_should_review_file_basename_matching(self):
        """Test that pattern matching works on both full path and basename."""
        include_patterns = ["*.py"]
        exclude_patterns = ["test_*"]

        # Full path matching
        assert should_review_file("src/utils.py", include_patterns, [])
        assert should_review_file("tests/unit/test_main.py", include_patterns, [])

        # Basename matching for exclude
        assert not should_review_file("src/test_utils.py", [], exclude_patterns)
        assert not should_review_file("tests/unit/test_main.py", [], exclude_patterns)

        # Combined: include by extension, exclude by basename
        assert should_review_file("src/utils.py", include_patterns, exclude_patterns)
        assert not should_review_file(
            "src/test_utils.py", include_patterns, exclude_patterns
        )

    def test_should_review_file_complex_patterns(self):
        """Test complex file patterns."""
        include_patterns = ["src/*.py", "*.js", "docs/*.md"]
        exclude_patterns = ["**/test_*", "*.min.*", "**/.*"]

        # Should include
        assert should_review_file("src/main.py", include_patterns, exclude_patterns)
        assert should_review_file("app.js", include_patterns, exclude_patterns)
        assert should_review_file("docs/README.md", include_patterns, exclude_patterns)

        # Should exclude by test pattern
        assert not should_review_file(
            "src/test_main.py", include_patterns, exclude_patterns
        )
        assert not should_review_file(
            "tests/test_utils.py", include_patterns, exclude_patterns
        )

        # Should exclude by min pattern
        assert not should_review_file("app.min.js", include_patterns, exclude_patterns)

        # Should exclude hidden files
        assert not should_review_file(".gitignore", include_patterns, exclude_patterns)
        assert not should_review_file(
            "src/.hidden.py", include_patterns, exclude_patterns
        )

        # Should exclude non-matching include patterns
        assert not should_review_file("config.json", include_patterns, exclude_patterns)


class TestParseFilePatterns:
    """Test cases for parsing file patterns from command line arguments."""

    def test_parse_file_patterns_empty(self):
        """Test parsing empty pattern lists."""
        assert parse_file_patterns([]) == []
        assert parse_file_patterns(None) == []

    def test_parse_file_patterns_single_patterns(self):
        """Test parsing single patterns."""
        assert parse_file_patterns(["*.py"]) == ["*.py"]
        assert parse_file_patterns(["*.js", "*.ts"]) == ["*.js", "*.ts"]

    def test_parse_file_patterns_comma_separated(self):
        """Test parsing comma-separated patterns."""
        assert parse_file_patterns(["*.py,*.js"]) == ["*.py", "*.js"]
        assert parse_file_patterns(["*.py, *.js, *.ts"]) == ["*.py", "*.js", "*.ts"]

    def test_parse_file_patterns_mixed_format(self):
        """Test parsing mixed format with individual and comma-separated patterns."""
        patterns = ["*.py,*.js", "*.go", "*.rs,*.cpp,*.c"]
        expected = ["*.py", "*.js", "*.go", "*.rs", "*.cpp", "*.c"]
        assert parse_file_patterns(patterns) == expected

    def test_parse_file_patterns_whitespace_handling(self):
        """Test that whitespace is properly handled."""
        patterns = ["*.py , *.js", " *.go ", "*.rs,  *.cpp  ,*.c  "]
        expected = ["*.py", "*.js", "*.go", "*.rs", "*.cpp", "*.c"]
        assert parse_file_patterns(patterns) == expected

    def test_parse_file_patterns_empty_strings_ignored(self):
        """Test that empty strings and whitespace-only strings are ignored."""
        patterns = ["*.py,", ",*.js", "*.go, ,*.rs", ""]
        expected = ["*.py", "*.js", "*.go", "*.rs"]
        assert parse_file_patterns(patterns) == expected


class TestFileFilteringIntegration:
    """Integration tests for file filtering with realistic scenarios."""

    def test_python_project_filtering(self):
        """Test filtering for a Python project."""
        # Typical Python project files
        files = [
            "src/main.py",
            "src/utils.py",
            "tests/test_main.py",
            "tests/test_utils.py",
            "setup.py",
            "README.md",
            "requirements.txt",
            ".gitignore",
            "pyproject.toml",
        ]

        # Only Python files, exclude tests
        include_patterns = ["*.py"]
        exclude_patterns = ["test_*.py", "**/test_*.py"]

        expected_included = ["src/main.py", "src/utils.py", "setup.py"]

        actual_included = [
            f
            for f in files
            if should_review_file(f, include_patterns, exclude_patterns)
        ]

        assert set(actual_included) == set(expected_included)

    def test_web_project_filtering(self):
        """Test filtering for a web development project."""
        files = [
            "src/components/Header.js",
            "src/components/Footer.js",
            "src/utils/api.js",
            "src/styles/main.css",
            "tests/Header.spec.js",
            "tests/Footer.test.js",
            "public/index.html",
            "dist/app.min.js",
            "dist/styles.min.css",
            "package.json",
            "README.md",
            ".env",
        ]

        # Include JS and CSS, exclude tests and minified files
        include_patterns = ["*.js", "*.css"]
        exclude_patterns = ["*.test.js", "*.spec.js", "*.min.*", ".*"]

        expected_included = [
            "src/components/Header.js",
            "src/components/Footer.js",
            "src/utils/api.js",
            "src/styles/main.css",
        ]

        actual_included = [
            f
            for f in files
            if should_review_file(f, include_patterns, exclude_patterns)
        ]

        assert set(actual_included) == set(expected_included)

    def test_multi_language_project_filtering(self):
        """Test filtering for a multi-language project."""
        files = [
            "backend/main.py",
            "backend/utils.py",
            "frontend/app.js",
            "frontend/component.tsx",
            "mobile/MainActivity.java",
            "mobile/Utils.kt",
            "scripts/deploy.sh",
            "docs/README.md",
            "tests/test_backend.py",
            "tests/frontend.test.js",
            ".github/workflows/ci.yml",
        ]

        # Include only Python and JavaScript/TypeScript files
        include_patterns = ["*.py", "*.js", "*.ts", "*.tsx"]
        exclude_patterns = ["test_*.py", "*.test.js", ".github/**"]

        expected_included = [
            "backend/main.py",
            "backend/utils.py",
            "frontend/app.js",
            "frontend/component.tsx",
        ]

        actual_included = [
            f
            for f in files
            if should_review_file(f, include_patterns, exclude_patterns)
        ]

        assert set(actual_included) == set(expected_included)

    def test_specific_directory_filtering(self):
        """Test filtering files from specific directories."""
        files = [
            "src/main.py",
            "lib/external.py",
            "vendor/third_party.py",
            "tests/test_main.py",
            "docs/example.py",
            "scripts/build.py",
        ]

        # Include Python files from src and lib only
        include_patterns = ["src/*.py", "lib/*.py"]
        exclude_patterns = []

        expected_included = ["src/main.py", "lib/external.py"]

        actual_included = [
            f
            for f in files
            if should_review_file(f, include_patterns, exclude_patterns)
        ]

        assert set(actual_included) == set(expected_included)


class TestDefaultExcludes:
    """Test cases for default file exclusion functionality."""

    def test_default_excludes_are_applied(self):
        """Test that default exclude patterns are applied correctly."""
        # These files should be excluded by default
        assert not should_review_file("package-lock.json", [], DEFAULT_EXCLUDE_PATTERNS)
        assert not should_review_file("vendor/lib/foo.js", [], DEFAULT_EXCLUDE_PATTERNS)
        assert not should_review_file(
            "assets/app.min.css", [], DEFAULT_EXCLUDE_PATTERNS
        )
        assert not should_review_file("logo.png", [], DEFAULT_EXCLUDE_PATTERNS)
        assert not should_review_file("dist/bundle.js", [], DEFAULT_EXCLUDE_PATTERNS)
        assert not should_review_file("main.pyc", [], DEFAULT_EXCLUDE_PATTERNS)
        assert not should_review_file(
            "__pycache__/settings.pyc", [], DEFAULT_EXCLUDE_PATTERNS
        )

        # A regular file should still be included
        assert should_review_file("src/main.py", [], DEFAULT_EXCLUDE_PATTERNS)

    def test_no_default_excludes_flag_works(self):
        """Test that --no-default-excludes flag disables default excludes."""
        # With an empty exclude list, these files should now be included
        assert should_review_file("package-lock.json", [], [])
        assert should_review_file("vendor/lib/foo.js", [], [])
        assert should_review_file("assets/app.min.css", [], [])

    def test_user_excludes_are_combined_with_defaults(self):
        """Test that user-specified excludes are added to the default list."""
        user_excludes = ["*.log", "config.json"]
        combined_excludes = DEFAULT_EXCLUDE_PATTERNS + user_excludes

        # Default excluded file
        assert not should_review_file("yarn.lock", [], combined_excludes)
        # User excluded files
        assert not should_review_file("error.log", [], combined_excludes)
        assert not should_review_file("config.json", [], combined_excludes)
        # Regular file
        assert should_review_file("src/main.py", [], combined_excludes)

    def test_user_excludes_work_with_no_default_excludes(self):
        """Test that user excludes still work when default excludes are disabled."""
        user_excludes = ["*.log", "config.json"]

        # User excluded files
        assert not should_review_file("error.log", [], user_excludes)
        assert not should_review_file("config.json", [], user_excludes)
        # A file that would have been excluded by default should now be included
        assert should_review_file("yarn.lock", [], user_excludes)
        # Regular file
        assert should_review_file("src/main.py", [], user_excludes)

    def test_include_patterns_still_work_with_default_excludes(self):
        """Test that include patterns are still respected with default excludes."""
        include_patterns = ["*.js"]
        # `app.min.js` matches the include pattern, but should be excluded by default
        assert not should_review_file(
            "app.min.js", include_patterns, DEFAULT_EXCLUDE_PATTERNS
        )
        # `main.js` should be included
        assert should_review_file("main.js", include_patterns, DEFAULT_EXCLUDE_PATTERNS)
        # `main.py` does not match include pattern
        assert not should_review_file(
            "main.py", include_patterns, DEFAULT_EXCLUDE_PATTERNS
        )


if __name__ == "__main__":
    pytest.main([__file__])
