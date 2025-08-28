import json
import hashlib
from typing import Dict, List, Optional, Tuple, Any


def format_as_text(
    all_reviews: List[Tuple[str, bool, str, Optional[List[Dict[str, Any]]]]],
) -> str:
    """Formats the review results as a single human-readable text block."""
    all_review_texts = [review_text for _, _, review_text, _ in all_reviews]
    return "\n".join(all_review_texts).lstrip("\n")


def format_as_json(
    all_reviews: List[Tuple[str, bool, str, Optional[List[Dict[str, Any]]]]],
) -> str:
    """Formats the review results as a JSON string."""
    results = []
    for filename, passed, _, findings in all_reviews:
        results.append(
            {
                "filename": filename,
                "passed": passed,
                "findings": findings if findings else [],
            }
        )
    return json.dumps(results, indent=2)


def format_as_codeclimate(
    all_reviews: List[Tuple[str, bool, str, Optional[List[Dict[str, Any]]]]],
) -> str:
    """Formats the review results as a CodeClimate JSON report."""
    codeclimate_issues = []
    for filename, _, _, findings in all_reviews:
        if not findings:
            continue
        for finding in findings:
            if finding.get("line") is None:  # Skip general comments for codeclimate
                continue

            # Generate a fingerprint
            fingerprint_content = f"{filename}-{finding.get('line')}-{finding.get('check_name')}-{finding.get('message')}"
            fingerprint = hashlib.sha256(
                fingerprint_content.encode("utf-8")
            ).hexdigest()

            issue = {
                "description": finding.get("message"),
                "check_name": finding.get("check_name", "ai-review"),
                "fingerprint": fingerprint,
                "severity": finding.get("severity", "minor"),
                "location": {
                    "path": filename,
                    "lines": {
                        "begin": finding.get("line"),
                    },
                },
            }
            codeclimate_issues.append(issue)

    return json.dumps(codeclimate_issues, indent=2)


def format_as_jsonl(
    all_reviews: List[Tuple[str, bool, str, Optional[List[Dict[str, Any]]]]],
) -> str:
    """Formats the review results as JSON Lines (one object per file)."""
    lines = []
    for filename, passed, _, findings in all_reviews:
        record = {
            "filename": filename,
            "passed": passed,
            "findings": findings if findings else [],
        }
        lines.append(json.dumps(record, ensure_ascii=False))
    return "\n".join(lines)
