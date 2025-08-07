from unittest.mock import MagicMock, patch
from src.ai_review_hook.main import redact, AIReviewer


def test_redact_aws_access_key():
    """Test that AWS access keys are redacted."""
    text = "This is a test with an AWS key: AKIAIOSFODNN7EXAMPLE"
    redacted_text = redact(text)
    assert "[REDACTED]" in redacted_text
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted_text


def test_redact_aws_secret_key():
    """Test that AWS secret keys are redacted."""
    text = "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    redacted_text = redact(text)
    assert "[REDACTED]" in redacted_text
    assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in redacted_text


def test_redact_private_key():
    """Test that private keys are redacted."""
    text = "-----BEGIN RSA PRIVATE KEY-----\nMIICXAIBAAKBgQC...\n-----END RSA PRIVATE KEY-----"
    redacted_text = redact(text)
    assert "[REDACTED]" in redacted_text
    assert "BEGIN RSA PRIVATE KEY" not in redacted_text


@patch("src.ai_review_hook.main.openai.OpenAI")
def test_review_file_pass(mock_openai):
    """Test that the review passes when the AI returns a PASS marker."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "AI-REVIEW:[PASS]\nLGTM!"
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    reviewer = AIReviewer(api_key="test_key")
    with patch.object(reviewer, "get_file_diff", return_value="- some changes"):
        passed, review = reviewer.review_file("test.py")
        assert passed is True
        assert "AI-REVIEW:[PASS]" in review


@patch("src.ai_review_hook.main.openai.OpenAI")
def test_review_file_fail(mock_openai):
    """Test that the review fails when the AI returns a FAIL marker."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "AI-REVIEW:[FAIL]\nThis is not good."
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    reviewer = AIReviewer(api_key="test_key")
    with patch.object(reviewer, "get_file_diff", return_value="- some changes"):
        passed, review = reviewer.review_file("test.py")
        assert passed is False
        assert "AI-REVIEW:[FAIL]" in review
