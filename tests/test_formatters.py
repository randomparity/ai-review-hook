import json
from src.ai_review_hook.formatters import (
    format_as_text,
    format_as_json,
    format_as_codeclimate,
)


def test_format_as_text():
    """Test text formatting."""
    mock_reviews = [
        (
            "file1.py",
            False,
            "AI-REVIEW:[FAIL]\\nReview for file1",
            [
                {
                    "line": 1,
                    "message": "finding 1",
                    "severity": "major",
                    "check_name": "check1",
                }
            ],
        ),
        (
            "file2.py",
            True,
            "AI-REVIEW:[PASS]\\nReview for file2",
            [],
        ),
    ]
    output = format_as_text(mock_reviews)
    assert "Review for file1" in output
    assert "Review for file2" in output


def test_format_as_json():
    """Test JSON formatting."""
    mock_reviews = [
        (
            "file1.py",
            False,
            "AI-REVIEW:[FAIL]\\nReview for file1",
            [
                {
                    "line": 1,
                    "message": "finding 1",
                    "severity": "major",
                    "check_name": "check1",
                }
            ],
        ),
        (
            "file2.py",
            True,
            "AI-REVIEW:[PASS]\\nReview for file2",
            [],
        ),
    ]
    output = format_as_json(mock_reviews)
    data = json.loads(output)
    assert len(data) == 2
    assert data[0]["filename"] == "file1.py"
    assert data[0]["passed"] is False
    assert len(data[0]["findings"]) == 1
    assert data[1]["filename"] == "file2.py"
    assert data[1]["passed"] is True
    assert len(data[1]["findings"]) == 0


def test_format_as_codeclimate():
    """Test CodeClimate formatting."""
    mock_reviews = [
        (
            "file1.py",
            False,
            "AI-REVIEW:[FAIL]\\nReview for file1",
            [
                {
                    "line": 1,
                    "message": "finding 1",
                    "severity": "major",
                    "check_name": "check1",
                }
            ],
        ),
        (
            "file2.py",
            True,
            "AI-REVIEW:[PASS]\\nReview for file2",
            [],
        ),
        (
            "file3.py",
            False,
            "AI-REVIEW:[FAIL]\\nReview for file3",
            [
                {
                    "line": None,
                    "message": "general finding",
                    "severity": "minor",
                    "check_name": "check2",
                }
            ],
        ),
    ]
    output = format_as_codeclimate(mock_reviews)
    data = json.loads(output)
    assert len(data) == 1
    assert data[0]["description"] == "finding 1"
    assert data[0]["location"]["path"] == "file1.py"
    assert data[0]["location"]["lines"]["begin"] == 1
    assert "fingerprint" in data[0]
