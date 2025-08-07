from unittest.mock import MagicMock, patch
from src.ai_review_hook.main import redact, AIReviewer
import concurrent.futures


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
        passed, review = reviewer.review_file("test.py", diff="- some changes")
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
        passed, review = reviewer.review_file("test.py", diff="- some changes")
        assert passed is False
        assert "AI-REVIEW:[FAIL]" in review


@patch("src.ai_review_hook.main.openai.OpenAI")
def test_review_file_empty_response(mock_openai):
    """Test that the review fails when the AI returns empty content."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = ""
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    reviewer = AIReviewer(api_key="test_key")
    with patch.object(reviewer, "get_file_diff", return_value="- some changes"):
        passed, review = reviewer.review_file("test.py", diff="- some changes")
        assert passed is False
        assert "Empty or blank response from AI model" in review


@patch("src.ai_review_hook.main.openai.OpenAI")
def test_review_file_blank_response(mock_openai):
    """Test that the review fails when the AI returns blank/whitespace content."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "   \n\t  "
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    reviewer = AIReviewer(api_key="test_key")
    with patch.object(reviewer, "get_file_diff", return_value="- some changes"):
        passed, review = reviewer.review_file("test.py", diff="- some changes")
        assert passed is False
        assert "Empty or blank response from AI model" in review


@patch("src.ai_review_hook.main.openai.OpenAI")
def test_review_file_api_error(mock_openai):
    """Test that API errors are handled gracefully."""
    import openai

    # Create a mock API error with attributes
    class MockAPIError(openai.APIError):
        def __init__(self, message):
            super().__init__(message=message, request=None, body=None)
            self.status_code = 429
            self.message = message

    api_error = MockAPIError("Rate limit exceeded")
    mock_openai.return_value.chat.completions.create.side_effect = api_error

    reviewer = AIReviewer(api_key="test_key")
    with patch.object(reviewer, "get_file_diff", return_value="- some changes"):
        passed, review = reviewer.review_file("test.py", diff="- some changes")
        assert passed is False
        assert "OpenAI API Error" in review
        assert "429" in review


@patch("src.ai_review_hook.main.openai.OpenAI")
def test_review_file_generic_error(mock_openai):
    """Test that generic errors are handled gracefully."""
    # Test generic exception handling
    mock_openai.return_value.chat.completions.create.side_effect = ValueError(
        "Something went wrong"
    )

    reviewer = AIReviewer(api_key="test_key")
    with patch.object(reviewer, "get_file_diff", return_value="- some changes"):
        passed, review = reviewer.review_file("test.py", diff="- some changes")
        assert passed is False
        assert "Unexpected error during AI review" in review
        assert "Something went wrong" in review


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


@patch("src.ai_review_hook.main.openai.OpenAI")
def test_binary_file_detection(mock_openai):
    """Test that binary files are detected and handled securely."""
    reviewer = AIReviewer(api_key="test_key")

    # Mock is_binary_file to return True
    with patch.object(reviewer, "is_binary_file", return_value=True):
        content = reviewer.get_file_content("test.bin")
        assert "[BINARY FILE - Content not shown for security]" in content
        assert content.startswith("[BINARY FILE")


@patch("src.ai_review_hook.main.openai.OpenAI")
def test_diff_only_mode(mock_openai):
    """Test that diff-only mode works correctly."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "AI-REVIEW:[PASS]\nLooks good!"
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    reviewer = AIReviewer(api_key="test_key")

    # Mock the create_review_prompt method to capture arguments
    with patch.object(
        reviewer, "create_review_prompt", return_value="test prompt"
    ) as mock_prompt:
        passed, review = reviewer.review_file(
            "test.py", diff="- some changes", diff_only=True
        )

        # Verify that diff_only=True was passed to create_review_prompt
        mock_prompt.assert_called_once()
        args, kwargs = mock_prompt.call_args
        # The call should include diff_only=True as the 4th argument
        assert len(args) >= 4 and args[3] is True

        assert passed is True
        assert "AI-REVIEW:[PASS]" in review


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


@patch("src.ai_review_hook.main.openai.OpenAI")
def test_truncate_text_with_marker(mock_openai):
    """Test text truncation with clear markers."""
    reviewer = AIReviewer(api_key="test_key")

    # Test normal truncation
    long_text = "A" * 1000
    truncated = reviewer.truncate_text_with_marker(long_text, 100, "test")
    assert "[TRUNCATED - test was 1000 bytes" in truncated
    assert len(truncated.encode("utf-8")) <= 100

    # Test no truncation needed
    short_text = "A" * 50
    result = reviewer.truncate_text_with_marker(short_text, 100, "test")
    assert result == short_text
    assert "TRUNCATED" not in result

    # Test text too large for any meaningful truncation
    tiny_limit = reviewer.truncate_text_with_marker(long_text, 10, "test")
    assert "[TRUNCATED - test too large (1000 bytes)]" == tiny_limit


@patch("src.ai_review_hook.main.openai.OpenAI")
def test_extract_changed_hunks(mock_openai):
    """Test extraction of changed hunks from diff."""
    reviewer = AIReviewer(api_key="test_key")

    # Test diff with multiple hunks
    diff_content = """diff --git a/test.py b/test.py
index 1234567..abcdefg 100644
--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 def function1():
+    print("new line")
     pass

@@ -10,2 +11,3 @@
 def function2():
+    print("another new line")
     pass
"""

    result = reviewer.extract_changed_hunks(diff_content)
    assert "@@ -1,3 +1,4 @@" in result
    assert "@@ -10,2 +11,3 @@" in result
    assert 'print("new line")' in result
    assert 'print("another new line")' in result

    # Test empty diff
    empty_result = reviewer.extract_changed_hunks("")
    assert empty_result == ""

    # Test diff with many hunks (should truncate)
    many_hunks = "\n".join(
        [f"@@ -{i},1 +{i},2 @@\n line {i}\n+ new line {i}" for i in range(15)]
    )
    truncated_result = reviewer.extract_changed_hunks(many_hunks, max_hunks=5)
    assert "[TRUNCATED - showing first 5 hunks of diff]" in truncated_result


@patch("src.ai_review_hook.main.openai.OpenAI")
def test_parallel_processing_simulation(mock_openai):
    """Test that parallel processing components work correctly."""
    # Mock successful AI response
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "AI-REVIEW:[PASS]\nLooks good!"
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    reviewer = AIReviewer(api_key="test_key")

    # Test the review_single_file function concept
    def review_single_file(filename: str):
        diff = "- some changes"
        passed, review = reviewer.review_file(filename, diff=diff)
        return filename, passed, review, diff

    # Simulate parallel processing with ThreadPoolExecutor
    files = ["file1.py", "file2.py", "file3.py"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(review_single_file, f): f for f in files}
        results = []

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)

        # Should have results for all files
        assert len(results) == 3
        filenames = [r[0] for r in results]
        assert set(filenames) == set(files)

        # All should pass
        for _, passed, review, _ in results:
            assert passed is True
            assert "AI-REVIEW:[PASS]" in review


@patch("src.ai_review_hook.main.openai.OpenAI")
def test_intelligent_truncation_integration(mock_openai):
    """Test that size limits with truncation work in review_file."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "AI-REVIEW:[PASS]\nOK"
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    reviewer = AIReviewer(api_key="test_key")

    # Create a large diff
    large_diff = "diff --git a/test.py b/test.py\n" + "A" * 2000

    with patch.object(reviewer, "get_file_content", return_value="small content"):
        # Should truncate diff but not fail
        passed, review = reviewer.review_file(
            "test.py", diff=large_diff, max_diff_bytes=500, max_content_bytes=1000
        )

        assert passed is True
        assert "AI-REVIEW:[PASS]" in review

        # Verify truncation was applied by checking the call to OpenAI
        assert mock_openai.return_value.chat.completions.create.called
        call_args = mock_openai.return_value.chat.completions.create.call_args
        prompt_content = call_args[1]["messages"][1]["content"]
        # Should contain truncation marker
        assert (
            "TRUNCATED" in prompt_content or len(prompt_content.encode("utf-8")) < 2500
        )
