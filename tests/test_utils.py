from unittest.mock import patch
from src.ai_review_hook.utils import redact, parse_file_patterns, should_review_file


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


def test_redact_github_tokens():
    """Test that GitHub tokens are redacted."""
    text = "Here is a GitHub PAT: ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    redacted_text = redact(text)
    assert "[REDACTED]" in redacted_text
    assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz" not in redacted_text


def test_redact_bearer_tokens():
    """Test that Bearer tokens are redacted."""
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    redacted_text = redact(text)
    assert "[REDACTED]" in redacted_text
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted_text


def test_redact_jwt_tokens():
    """Test that JWT tokens are redacted."""
    text = "Token: eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWV9.EkN-DOsnsuRjRO6BxXemmJDm3HbxrbRzXglbN2S4sOkopdU4IsDxTI8jO19W_A4K8ZPJijNLis4EZsHeY559a4DFOd50_OqgHs3VMObvQA0jNEOqZlFIkVW5_32vlnqgQ"
    redacted_text = redact(text)
    assert "[REDACTED]" in redacted_text
    assert "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted_text


def test_redact_slack_tokens():
    """Test that Slack tokens are redacted."""
    text = "Slack token: xoxb-123-456-789abcdefghijklmnopqr"
    redacted_text = redact(text)
    assert "[REDACTED]" in redacted_text
    assert "xoxb-123-456-789abcdefghijklmnopqr" not in redacted_text


def test_redact_database_urls():
    """Test that database URLs with credentials are redacted."""
    text = "DATABASE_URL=postgresql://user:password@localhost:5432/mydb"
    redacted_text = redact(text)
    assert "[REDACTED]" in redacted_text
    assert "user:password" not in redacted_text


def test_redact_generic_api_keys():
    """Test that generic API keys are redacted."""
    text = "API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz"
    redacted_text = redact(text)
    assert "[REDACTED]" in redacted_text
    assert "sk-1234567890abcdefghijklmnopqrstuvwxyz" not in redacted_text


def test_redact_skip_if_empty():
    """Test that redaction can be skipped for empty text."""
    # Should skip redaction and return quickly
    empty_text = ""
    result = redact(empty_text, skip_if_empty=True)
    assert result == ""

    # Should still redact when not empty
    secret_text = "API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz"
    result = redact(secret_text, skip_if_empty=True)
    assert "[REDACTED]" in result
    assert "sk-1234567890abcdefghijklmnopqrstuvwxyz" not in result


def test_file_filtering_integration():
    """Test file filtering integration with main function."""
    # Test parse_file_patterns function
    assert parse_file_patterns(["*.py,*.js", "*.go"]) == ["*.py", "*.js", "*.go"]
    assert parse_file_patterns(["*.py, *.js"]) == ["*.py", "*.js"]
    assert parse_file_patterns([]) == []

    # Test should_review_file function
    assert should_review_file("test.py", ["*.py"], [])
    assert not should_review_file("test.py", ["*.js"], [])
    assert not should_review_file("test.py", ["*.py"], ["*.py"])
    assert should_review_file("test.py", [], [])


def test_load_filetype_prompts_invalid_prompt_type(tmp_path):
    """Test that load_filetype_prompts handles non-string prompts gracefully."""
    import json
    from src.ai_review_hook.utils import load_filetype_prompts

    # Create a temporary prompts file with an invalid prompt type and a valid one
    prompts = {"*.py": 12345, "*.js": "Valid prompt"}
    prompts_file = tmp_path / "prompts.json"
    prompts_file.write_text(json.dumps(prompts))

    with patch("logging.warning") as mock_log_warning:
        loaded_prompts = load_filetype_prompts(str(prompts_file))
        # The invalid prompt should be skipped, and the valid one should be loaded
        assert loaded_prompts == {"*.js": "Valid prompt"}
        # A warning should be logged for the invalid prompt
        mock_log_warning.assert_called_once()
        assert "Skipping non-string prompt" in mock_log_warning.call_args[0][0]
