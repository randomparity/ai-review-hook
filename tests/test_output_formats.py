import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys


def run_main_with_args(args):
    from ai_review_hook.main import main

    old_argv = sys.argv
    try:
        sys.argv = ["ai-review"] + args
        return main()
    finally:
        sys.argv = old_argv


@patch("ai_review_hook.main.AIReviewer")
def test_jsonl_output_writes_one_record_per_file(
    mock_reviewer: MagicMock, tmp_path: Path
):
    # Arrange: mock reviewer to PASS with empty findings
    inst = mock_reviewer.return_value
    inst.get_file_diff.side_effect = (
        lambda filename, *_: "diff --git a/{0} b/{0}\n@@ -1 +1 @@\n+change".format(
            filename
        )
    )
    inst.review_file.side_effect = lambda filename, **kwargs: (
        True,
        "AI-REVIEW:[PASS]\nLooks good",
        [],
    )

    out = tmp_path / "ai-review.jsonl"

    # Act
    code = run_main_with_args(
        [
            "--format",
            "jsonl",
            "--output-file",
            str(out),
            "file1.py",
            "file2.py",
        ]
    )

    # Assert
    assert code == 0
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    recs = [json.loads(line) for line in lines]
    assert {r["filename"] for r in recs} == {"file1.py", "file2.py"}
    assert all(r["passed"] is True for r in recs)
    assert all(isinstance(r.get("findings"), list) for r in recs)


@patch("ai_review_hook.main.AIReviewer")
def test_text_log_embeds_per_file_json_when_flag_set(
    mock_reviewer: MagicMock, tmp_path: Path
):
    # Arrange
    inst = mock_reviewer.return_value
    inst.get_file_diff.return_value = "diff --git a/x b/x\n@@ -1 +1 @@\n+1"
    inst.review_file.return_value = (True, "AI-REVIEW:[PASS]\nOK", [])

    out = tmp_path / "ai-review.log"

    # Act
    code = run_main_with_args(
        [
            "--format",
            "text",
            "--embed-json-in-log",
            "--output-file",
            str(out),
            "alpha.py",
            "beta.py",
        ]
    )

    # Assert
    assert code == 0
    content = out.read_text(encoding="utf-8")
    # Two sentinel blocks present
    assert content.count("=== AI_REVIEW_JSON_START ===") == 2
    assert content.count("=== AI_REVIEW_JSON_END ===") == 2

    # Parse one embedded JSON to sanity check shape
    start = content.find("=== AI_REVIEW_JSON_START ===")
    end = content.find("=== AI_REVIEW_JSON_END ===", start)
    assert start != -1 and end != -1
    block = content[start : end + len("=== AI_REVIEW_JSON_END ===")]
    json_str = block.splitlines()[1]
    obj = json.loads(json_str)
    assert set(obj.keys()) == {"filename", "passed", "findings"}
    assert obj["filename"] in {"alpha.py", "beta.py"}
    assert obj["passed"] is True


@patch("ai_review_hook.main.AIReviewer")
def test_default_excludes_skip_common_noise(mock_reviewer: MagicMock, tmp_path: Path):
    # Arrange: default excludes should skip node_modules/**
    inst = mock_reviewer.return_value
    inst.get_file_diff.return_value = "diff"
    inst.review_file.return_value = (True, "AI-REVIEW:[PASS]\nOK", [])

    out = tmp_path / "log.txt"

    # Act
    code = run_main_with_args(
        [
            "--format",
            "text",
            "--output-file",
            str(out),
            "node_modules/dep.js",
            "good.py",
        ]
    )

    # Assert: only good.py should be reviewed/logged
    assert code == 0
    content = out.read_text(encoding="utf-8")
    assert "File: good.py" in content
    assert "node_modules/dep.js" not in content
