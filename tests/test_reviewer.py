from unittest.mock import MagicMock, patch
from src.ai_review_hook.reviewer import AIReviewer
import concurrent.futures


@patch("src.ai_review_hook.reviewer.openai.OpenAI")
def test_review_file_pass(mock_openai):
    """Test that the review passes when the AI returns a PASS marker."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "AI-REVIEW:[PASS]\nLGTM!"
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    reviewer = AIReviewer(api_key="test_key")
    with patch.object(reviewer, "get_file_diff", return_value="- some changes"):
        passed, review, findings = reviewer.review_file("test.py", diff="- some changes")
        assert passed is True
        assert "AI-REVIEW:[PASS]" in review
        assert findings is None


@patch("src.ai_review_hook.reviewer.openai.OpenAI")
def test_review_file_fail(mock_openai):
    """Test that the review fails when the AI returns a FAIL marker."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "AI-REVIEW:[FAIL]\nThis is not good."
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    reviewer = AIReviewer(api_key="test_key")
    with patch.object(reviewer, "get_file_diff", return_value="- some changes"):
        passed, review, findings = reviewer.review_file("test.py", diff="- some changes")
        assert passed is False
        assert "AI-REVIEW:[FAIL]" in review
        assert findings is None


@patch("src.ai_review_hook.reviewer.openai.OpenAI")
def test_review_file_empty_response(mock_openai):
    """Test that the review fails when the AI returns empty content."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = ""
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    reviewer = AIReviewer(api_key="test_key")
    with patch.object(reviewer, "get_file_diff", return_value="- some changes"):
        passed, review, findings = reviewer.review_file("test.py", diff="- some changes")
        assert passed is False
        assert "Empty message content from API" in review
        assert findings is None


@patch("src.ai_review_hook.reviewer.openai.OpenAI")
def test_review_file_blank_response(mock_openai):
    """Test that the review fails when the AI returns blank/whitespace content."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "   \n\t  "
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    reviewer = AIReviewer(api_key="test_key")
    with patch.object(reviewer, "get_file_diff", return_value="- some changes"):
        passed, review, findings = reviewer.review_file("test.py", diff="- some changes")
        assert passed is False
        assert "Empty or blank response from AI model" in review
        assert findings is None


@patch("src.ai_review_hook.reviewer.openai.OpenAI")
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
        passed, review, findings = reviewer.review_file("test.py", diff="- some changes")
        assert passed is False
        assert "OpenAI API Error" in review
        assert "429" in review
        assert findings is None


@patch("src.ai_review_hook.reviewer.openai.OpenAI")
def test_review_file_generic_error(mock_openai):
    """Test that generic errors are handled gracefully."""
    # Test generic exception handling
    mock_openai.return_value.chat.completions.create.side_effect = ValueError(
        "Something went wrong"
    )

    reviewer = AIReviewer(api_key="test_key")
    with patch.object(reviewer, "get_file_diff", return_value="- some changes"):
        passed, review, findings = reviewer.review_file("test.py", diff="- some changes")
        assert passed is False
        assert "Unexpected error during AI review" in review
        assert "Something went wrong" in review
        assert findings is None


@patch("src.ai_review_hook.reviewer.openai.OpenAI")
def test_binary_file_detection(mock_openai):
    """Test that binary files are detected and handled securely."""
    reviewer = AIReviewer(api_key="test_key")

    # Mock is_binary_file to return True
    with patch.object(reviewer, "is_binary_file", return_value=True):
        content = reviewer.get_file_content("test.bin")
        assert "[BINARY FILE - Content not shown for security]" in content
        assert content.startswith("[BINARY FILE")


@patch("src.ai_review_hook.reviewer.openai.OpenAI")
def test_diff_only_mode(mock_openai):
    """Test that diff-only mode works correctly."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "AI-REVIEW:[PASS]\nLooks good!"
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    reviewer = AIReviewer(api_key="test_key")

    # Mock the create_review_prompt method to capture arguments
    with patch.object(
        reviewer, "create_review_prompt", return_value="test prompt"
    ) as mock_prompt:
        passed, review, findings = reviewer.review_file(
            "test.py", diff="- some changes", diff_only=True
        )

        # Verify that diff_only=True was passed to create_review_prompt
        mock_prompt.assert_called_once()
        args, kwargs = mock_prompt.call_args
        # The call should include diff_only=True as the 4th argument
        assert len(args) >= 4 and args[3] is True

        assert passed is True
        assert "AI-REVIEW:[PASS]" in review


@patch("src.ai_review_hook.reviewer.openai.OpenAI")
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


@patch("src.ai_review_hook.reviewer.openai.OpenAI")
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


@patch("src.ai_review_hook.reviewer.openai.OpenAI")
def test_parallel_processing_simulation(mock_openai):
    """Test that parallel processing components work correctly."""
    # Mock successful AI response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "AI-REVIEW:[PASS]\nLooks good!"
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    reviewer = AIReviewer(api_key="test_key")

    # Test the review_single_file function concept
    def review_single_file(filename: str):
        diff = "- some changes"
        passed, review, findings = reviewer.review_file(filename, diff=diff)
        return filename, passed, review, diff, findings

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
        for _, passed, review, _, _ in results:
            assert passed is True
            assert "AI-REVIEW:[PASS]" in review


@patch("src.ai_review_hook.reviewer.openai.OpenAI")
def test_intelligent_truncation_integration(mock_openai):
    """Test that size limits with truncation work in review_file."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "AI-REVIEW:[PASS]\nOK"
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    reviewer = AIReviewer(api_key="test_key")

    # Create a large diff
    large_diff = "diff --git a/test.py b/test.py\n" + "A" * 2000

    with patch.object(reviewer, "get_file_content", return_value="small content"):
        # Should truncate diff but not fail
        passed, review, findings = reviewer.review_file(
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


@patch("src.ai_review_hook.reviewer.openai.OpenAI")
def test_is_retryable_error(mock_openai):
    """Test that retryable errors are correctly identified."""
    import openai

    reviewer = AIReviewer(api_key="test_key")

    # Create mock errors with proper structure
    def create_mock_api_error(error_class, message="Error", status_code=None):
        error = MagicMock(spec=error_class)
        if status_code:
            error.status_code = status_code
        return error

    # Test retryable errors
    assert reviewer._is_retryable_error(
        create_mock_api_error(openai.RateLimitError, "Rate limited", 429)
    )
    assert reviewer._is_retryable_error(
        create_mock_api_error(openai.APITimeoutError, "Timeout")
    )
    assert reviewer._is_retryable_error(
        create_mock_api_error(openai.APIConnectionError, "Connection error")
    )
    assert reviewer._is_retryable_error(
        create_mock_api_error(openai.InternalServerError, "Server error", 500)
    )
    assert reviewer._is_retryable_error(
        create_mock_api_error(openai.UnprocessableEntityError, "Overloaded", 422)
    )

    # Test non-retryable errors
    assert not reviewer._is_retryable_error(
        create_mock_api_error(openai.AuthenticationError, "Invalid key", 401)
    )
    assert not reviewer._is_retryable_error(ValueError("Bad value"))

    # Test status code checking
    class MockErrorWithStatus(Exception):
        def __init__(self, status_code):
            self.status_code = status_code

    # Retryable status codes
    assert reviewer._is_retryable_error(MockErrorWithStatus(429))
    assert reviewer._is_retryable_error(MockErrorWithStatus(502))
    assert reviewer._is_retryable_error(MockErrorWithStatus(503))
    assert reviewer._is_retryable_error(MockErrorWithStatus(504))

    # Non-retryable status codes
    assert not reviewer._is_retryable_error(MockErrorWithStatus(400))
    assert not reviewer._is_retryable_error(MockErrorWithStatus(401))
    assert not reviewer._is_retryable_error(MockErrorWithStatus(403))


@patch("src.ai_review_hook.reviewer.openai.OpenAI")
def test_calculate_retry_delay(mock_openai):
    """Test that retry delays are calculated correctly with exponential backoff and jitter."""
    reviewer = AIReviewer(
        api_key="test_key",
        initial_retry_delay=1.0,
        max_retry_delay=10.0,
        retry_jitter=0.1,
    )

    # Test exponential backoff
    delay_0 = reviewer._calculate_retry_delay(0)
    delay_1 = reviewer._calculate_retry_delay(1)
    delay_2 = reviewer._calculate_retry_delay(2)

    # Should grow exponentially (with jitter)
    assert 0.9 <= delay_0 <= 1.1  # ~1.0 with jitter
    assert 1.8 <= delay_1 <= 2.2  # ~2.0 with jitter
    assert 3.6 <= delay_2 <= 4.4  # ~4.0 with jitter

    # Test max delay cap
    delay_large = reviewer._calculate_retry_delay(
        10
    )  # Should be capped at max_retry_delay
    assert delay_large <= reviewer.max_retry_delay * 1.1  # Allow for jitter


@patch("src.ai_review_hook.reviewer.time.sleep")
@patch("src.ai_review_hook.reviewer.openai.OpenAI")
def test_retry_on_rate_limit(mock_openai, mock_sleep):
    """Test that rate limit errors trigger retries."""
    import openai

    # Configure reviewer with fast retries for testing
    reviewer = AIReviewer(
        api_key="test_key", max_retries=2, initial_retry_delay=0.1, retry_jitter=0.0
    )

    # Mock rate limit error on first two calls, success on third
    mock_client = mock_openai.return_value
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "AI-REVIEW:[PASS]\nSuccess after retry!"

    # Create test exception classes that inherit from the real ones
    class TestRateLimitError(openai.RateLimitError):
        def __init__(self, message="Rate limited"):
            self.status_code = 429
            self.message = message
            # Don't call super().__init__ to avoid constructor issues

    rate_limit_error = TestRateLimitError()

    mock_client.chat.completions.create.side_effect = [
        rate_limit_error,
        rate_limit_error,
        mock_response,
    ]

    messages = [{"role": "user", "content": "test"}]
    result = reviewer._make_api_call_with_retry(messages, "test.py")

    # Should succeed after retries
    assert result == "AI-REVIEW:[PASS]\nSuccess after retry!"

    # Should have made 3 API calls
    assert mock_client.chat.completions.create.call_count == 3

    # Should have slept twice (between attempts)
    assert mock_sleep.call_count == 2


@patch("src.ai_review_hook.reviewer.time.sleep")
@patch("src.ai_review_hook.reviewer.openai.OpenAI")
def test_retry_exhaustion(mock_openai, mock_sleep):
    """Test that retries are exhausted and final error is raised."""
    import openai

    reviewer = AIReviewer(
        api_key="test_key", max_retries=2, initial_retry_delay=0.1, retry_jitter=0.0
    )

    # Create test exception class
    class TestRateLimitError(openai.RateLimitError):
        def __init__(self, message="Rate limited"):
            self.status_code = 429
            self.message = message

    # Mock rate limit error on all calls
    mock_client = mock_openai.return_value
    rate_limit_error = TestRateLimitError()
    mock_client.chat.completions.create.side_effect = rate_limit_error

    messages = [{"role": "user", "content": "test"}]

    # Should raise the final error after exhausting retries
    try:
        reviewer._make_api_call_with_retry(messages, "test.py")
        assert False, "Should have raised an exception"
    except openai.RateLimitError:
        pass  # Expected

    # Should have made max_retries + 1 calls
    assert mock_client.chat.completions.create.call_count == 3

    # Should have slept max_retries times
    assert mock_sleep.call_count == 2


@patch("src.ai_review_hook.reviewer.openai.OpenAI")
def test_non_retryable_error_no_retry(mock_openai):
    """Test that non-retryable errors don't trigger retries."""
    import openai

    reviewer = AIReviewer(api_key="test_key", max_retries=2)

    # Create test exception class
    class TestAuthenticationError(openai.AuthenticationError):
        def __init__(self, message="Invalid API key"):
            self.status_code = 401
            self.message = message

    # Mock non-retryable error
    mock_client = mock_openai.return_value
    auth_error = TestAuthenticationError()
    mock_client.chat.completions.create.side_effect = auth_error

    messages = [{"role": "user", "content": "test"}]

    # Should raise immediately without retrying
    try:
        reviewer._make_api_call_with_retry(messages, "test.py")
        assert False, "Should have raised an exception"
    except openai.AuthenticationError:
        pass  # Expected

    # Should have made only 1 call (no retries)
    assert mock_client.chat.completions.create.call_count == 1


@patch("src.ai_review_hook.reviewer.time.sleep")
@patch("src.ai_review_hook.reviewer.openai.OpenAI")
def test_retry_with_different_error_types(mock_openai, mock_sleep):
    """Test retry behavior with different types of retryable errors."""
    import openai

    reviewer = AIReviewer(
        api_key="test_key", max_retries=3, initial_retry_delay=0.1, retry_jitter=0.0
    )

    # Mock different retryable errors, then success
    mock_client = mock_openai.return_value
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "AI-REVIEW:[PASS]\nSuccess!"

    # Create test exception classes
    class TestRateLimitError(openai.RateLimitError):
        def __init__(self):
            self.status_code = 429

    class TestAPITimeoutError(openai.APITimeoutError):
        def __init__(self):
            pass

    class TestAPIConnectionError(openai.APIConnectionError):
        def __init__(self):
            pass

    # Create errors properly
    error1 = TestRateLimitError()
    error2 = TestAPITimeoutError()
    error3 = TestAPIConnectionError()

    mock_client.chat.completions.create.side_effect = [
        error1,
        error2,
        error3,
        mock_response,
    ]

    messages = [{"role": "user", "content": "test"}]
    result = reviewer._make_api_call_with_retry(messages, "test.py")

    # Should succeed after multiple different errors
    assert result == "AI-REVIEW:[PASS]\nSuccess!"
    assert mock_client.chat.completions.create.call_count == 4
    assert mock_sleep.call_count == 3


@patch("src.ai_review_hook.reviewer.openai.OpenAI")
def test_review_file_with_retry_integration(mock_openai):
    """Test that review_file properly integrates with retry mechanism."""
    import openai

    reviewer = AIReviewer(
        api_key="test_key", max_retries=1, initial_retry_delay=0.01, retry_jitter=0.0
    )

    # Mock rate limit error on first call, success on second
    mock_client = mock_openai.return_value
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[
        0
    ].message.content = "AI-REVIEW:[PASS]\nLooks good after retry!"

    # Create test exception class
    class TestRateLimitError(openai.RateLimitError):
        def __init__(self):
            self.status_code = 429

    rate_limit_error = TestRateLimitError()
    mock_client.chat.completions.create.side_effect = [rate_limit_error, mock_response]

    with patch("src.ai_review_hook.reviewer.time.sleep"):
        passed, review, findings = reviewer.review_file("test.py", diff="- some changes")

    # Should succeed after retry
    assert passed is True
    assert "AI-REVIEW:[PASS]" in review
    assert "Looks good after retry!" in review

    # Should have made 2 API calls
    assert mock_client.chat.completions.create.call_count == 2


@patch("src.ai_review_hook.reviewer.openai.OpenAI")
def test_retry_configuration_parameters(mock_openai):
    """Test that retry configuration parameters are properly set."""
    reviewer = AIReviewer(
        api_key="test_key",
        max_retries=5,
        initial_retry_delay=2.0,
        max_retry_delay=120.0,
        retry_jitter=0.2,
    )

    assert reviewer.max_retries == 5
    assert reviewer.initial_retry_delay == 2.0
    assert reviewer.max_retry_delay == 120.0
    assert reviewer.retry_jitter == 0.2

    # Test delay calculation with custom parameters
    delay = reviewer._calculate_retry_delay(1)
    # Should be around 4.0 (2.0 * 2^1) with up to 20% jitter
    assert 3.2 <= delay <= 4.8


def test_parse_review_text_with_findings():
    """Test parsing of review text with JSON findings."""
    review_text = """AI-REVIEW:[FAIL]
This is a review.

```json
{
  "findings": [
    {
      "line": 10,
      "message": "This is a test finding."
    }
  ]
}
```
"""
    human_text, findings = AIReviewer._parse_review_text(review_text)
    assert "This is a review." in human_text
    assert "```json" not in human_text
    assert findings is not None
    assert len(findings) == 1
    assert findings[0]["line"] == 10
    assert findings[0]["message"] == "This is a test finding."


def test_parse_review_text_no_findings():
    """Test parsing of review text without JSON findings."""
    review_text = "AI-REVIEW:[PASS]\\nThis is a review without findings."
    human_text, findings = AIReviewer._parse_review_text(review_text)
    assert "This is a review without findings." in human_text
    assert findings is None


def test_parse_review_text_malformed_json():
    """Test parsing of review text with malformed JSON."""
    review_text = """AI-REVIEW:[FAIL]
This is a review.

```json
{
  "findings": [
    {
      "line": 10,
      "message": "This is a test finding."
    }
  ],
}
```
"""
    human_text, findings = AIReviewer._parse_review_text(review_text)
    # Should return original text and no findings
    assert "```json" in human_text
    assert findings is None


def test_determine_pass_fail():
    """Test the pass/fail determination logic."""
    reviewer = AIReviewer(api_key="test")
    assert reviewer._determine_pass_fail("AI-REVIEW:[PASS]\\nLGTM") is True
    assert reviewer._determine_pass_fail("AI-REVIEW:[FAIL]\\nNot good") is False
    assert reviewer._determine_pass_fail("Some other text\\nAI-REVIEW:[FAIL]") is False
    assert reviewer._determine_pass_fail("No marker here") is False


def test_create_review_prompt_with_custom_prompt():
    """Test that create_review_prompt uses the custom prompt template."""
    prompts = {"*.py": "Review this Python file: {filename}"}
    reviewer = AIReviewer(api_key="test_key", filetype_prompts=prompts)

    prompt = reviewer.create_review_prompt("test.py", "some content", "some diff", False)

    assert "Review this Python file: test.py" in prompt
    # The default prompt content should not be present
    assert "You are an AI code reviewer" not in prompt


def test_create_review_prompt_diff_only():
    """Test that create_review_prompt omits file content in diff-only mode."""
    reviewer = AIReviewer(api_key="test_key")

    prompt = reviewer.create_review_prompt("test.py", "some diff", "some content", True)

    assert "Git Diff:\n```\nsome diff\n```" in prompt
    assert "Current File Content:" not in prompt
    assert "Note: Only diff is provided for security (--diff-only mode)." in prompt


def test_create_review_prompt_no_diff():
    """Test that create_review_prompt handles an empty diff."""
    reviewer = AIReviewer(api_key="test_key")

    prompt = reviewer.create_review_prompt("test.py", "", "some content", False)

    assert "Git Diff:\n```\n\n```" in prompt
    assert "Current File Content:\n```\nsome content\n```" in prompt


def test_get_file_content_unreadable():
    """Test that get_file_content handles unreadable files."""
    reviewer = AIReviewer(api_key="test_key")
    # First, patch is_binary_file to return False so we can test the open() block
    with patch.object(reviewer, "is_binary_file", return_value=False):
        with patch("builtins.open", side_effect=IOError("Permission denied")):
            content = reviewer.get_file_content("unreadable.txt")
            assert "[UNREADABLE FILE - Permission denied]" in content


def test_get_file_diff_git_error():
    """Test that get_file_diff handles git errors."""
    import subprocess
    reviewer = AIReviewer(api_key="test_key")
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")):
        diff = reviewer.get_file_diff("test.py")
        assert diff == ""
