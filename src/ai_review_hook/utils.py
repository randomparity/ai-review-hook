import fnmatch
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

# Default exclude patterns for common non-reviewable files
DEFAULT_EXCLUDE_PATTERNS = [
    # Lockfiles
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "composer.lock",
    "Gemfile.lock",
    "poetry.lock",
    "Pipfile.lock",
    # Vendored dependencies
    "vendor/**",
    "node_modules/**",
    # Minified assets
    "*.min.js",
    "*.min.css",
    # Image files
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.svg",
    "*.ico",
    "*.webp",
    # Build artifacts and logs
    "dist/**",
    "build/**",
    "*.log",
    "*.tmp",
    "*.swp",
    "coverage.xml",
    # Compiled Python files
    "*.pyc",
    "__pycache__/**",
    # Data files
    "*.csv",
    "*.json",
    "*.xml",
    # Font files
    "*.woff",
    "*.woff2",
    "*.ttf",
    "*.eot",
]


# Secret detection patterns
SECRET_PATTERNS = [
    # AWS credentials
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS Access Key ID
    re.compile(
        r"(?i)aws_secret_access_key\s*=\s*[A-Za-z0-9/+=]{40}"
    ),  # AWS Secret Access Key
    # Private keys and certificates
    re.compile(
        r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP) (?:PRIVATE KEY|CERTIFICATE)-----.*?-----END (?:RSA|EC|DSA|OPENSSH|PGP) (?:PRIVATE KEY|CERTIFICATE)-----",
        re.S,
    ),  # Private Keys and Certificates
    # Authorization headers and Bearer tokens
    re.compile(
        r"(?i)authorization:\s*bearer\s+[a-z0-9\-._~+/]+=*"
    ),  # Bearer/JWT tokens in headers
    re.compile(r"(?i)bearer\s+[a-z0-9\-._~+/]{20,}={0,2}"),  # Generic Bearer tokens
    # GitHub tokens
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36,255}"),  # GitHub Personal Access Tokens
    re.compile(r"gho_[A-Za-z0-9]{36}"),  # GitHub OAuth tokens
    re.compile(r"ghs_[A-Za-z0-9]{36}"),  # GitHub server-to-server tokens
    # Generic API keys and tokens
    re.compile(
        r'(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*["\']?[A-Za-z0-9_\-.]{16,}["\']?'
    ),  # Generic API keys and tokens
    # Slack tokens
    re.compile(r"xox[baprs]-[A-Za-z0-9\-]+"),  # Slack tokens
    # OpenAI API keys
    re.compile(r"sk-[A-Za-z0-9]{20}T3BlbkFJ[A-Za-z0-9]{20}"),  # OpenAI API keys
    # JWT tokens (basic detection)
    re.compile(
        r"eyJ[A-Za-z0-9_\-]*\.eyJ[A-Za-z0-9_\-]*\.[A-Za-z0-9_\-]*"
    ),  # JWT tokens (header.payload.signature)
    # Database connection strings
    re.compile(
        r"(?i)(mongodb|mysql|postgresql|postgres)://[^\s]*:[^\s]*@[^\s]+"
    ),  # Database connection strings with credentials
    # Generic secrets in environment or config format
    re.compile(
        r'(?i)(secret|password|key|token)\s*=\s*["\'][A-Za-z0-9+/]{20,}["\']'
    ),  # Environment file style secrets
]


def should_review_file(
    filename: str, include_patterns: List[str], exclude_patterns: List[str]
) -> bool:
    """Check if a file should be reviewed based on include/exclude patterns.

    Args:
        filename: Path to the file to check
        include_patterns: List of file patterns to include (e.g., ['*.py', '*.js'])
        exclude_patterns: List of file patterns to exclude (e.g., ['*.test.py', '*.spec.js'])

    Returns:
        True if file should be reviewed, False otherwise

    Logic:
    - If include_patterns is empty, all files are included by default
    - If include_patterns is provided, file must match at least one include pattern
    - If exclude_patterns is provided and file matches any exclude pattern, it's excluded
    - Exclude patterns take precedence over include patterns
    """
    # Get the basename for pattern matching
    basename = Path(filename).name

    # Check exclude patterns first (they take precedence)
    if exclude_patterns:
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(basename, pattern):
                return False

    # If no include patterns specified, include all files (unless excluded)
    if not include_patterns:
        return True

    # Check if file matches any include pattern
    for pattern in include_patterns:
        if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(basename, pattern):
            return True

    # File doesn't match any include pattern
    return False


def parse_file_patterns(pattern_list: List[str]) -> List[str]:
    """Parse file patterns from command line arguments.

    Handles comma-separated values and individual arguments.
    Example: ['*.py,*.js', '*.go'] becomes ['*.py', '*.js', '*.go']
    """
    if not pattern_list:
        return []

    patterns = []
    for item in pattern_list:
        # Split on comma and strip whitespace
        patterns.extend([p.strip() for p in item.split(",") if p.strip()])

    return patterns


def load_filetype_prompts(prompts_file: Optional[str]) -> Dict[str, str]:
    """Load filetype-specific prompts from JSON file.

    Args:
        prompts_file: Path to JSON file containing filetype-specific prompts

    Returns:
        Dictionary mapping glob patterns to custom prompt templates
    """
    if not prompts_file:
        return {}

    try:
        if not Path(prompts_file).exists():
            logging.warning(f"Filetype prompts file not found: {prompts_file}")
            return {}

        with open(prompts_file, "r", encoding="utf-8") as f:
            prompts_data = json.load(f)

        # Validate structure
        if not isinstance(prompts_data, dict):
            logging.error(f"Invalid filetype prompts file format: {prompts_file}")
            return {}

        # Validate and store glob patterns
        validated_prompts = {}
        for pattern, prompt in prompts_data.items():
            if not isinstance(prompt, str):
                logging.warning(f"Skipping non-string prompt for pattern '{pattern}'")
                continue

            # Store patterns as-is (they can be extensions, globs, or paths)
            validated_prompts[pattern] = prompt

        logging.info(
            f"Loaded {len(validated_prompts)} glob pattern prompts from {prompts_file}"
        )
        return validated_prompts

    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Error loading filetype prompts from {prompts_file}: {e}")
        return {}


def get_file_extension(filename: str) -> str:
    """Get the normalized file extension from a filename.

    Args:
        filename: Path to the file

    Returns:
        Normalized file extension (lowercase, with leading dot)
    """
    return Path(filename).suffix.lower()


def select_prompt_template(
    filename: str, glob_pattern_prompts: Dict[str, str]
) -> Optional[str]:
    """Select the appropriate prompt template for a file using glob patterns.

    Args:
        filename: Path to the file
        glob_pattern_prompts: Dictionary mapping glob patterns to custom prompt templates

    Returns:
        Custom prompt template if found, None for default prompt

    Pattern matching priority (first match wins):
    1. Exact filename match (e.g., "main.py")
    2. Full path patterns (e.g., "src/**/*.py", "tests/*.py")
    3. File extension patterns (e.g., "*.py", "*.js")
    4. Basename patterns (e.g., "test_*.py", "*_spec.js")
    """
    if not glob_pattern_prompts:
        return None

    # Get basename for pattern matching
    basename = Path(filename).name

    # Priority 1: Exact filename match
    if filename in glob_pattern_prompts:
        return glob_pattern_prompts[filename]
    if basename in glob_pattern_prompts:
        return glob_pattern_prompts[basename]

    # Priority 2-4: Pattern matching
    # Sort patterns by specificity (longer patterns first)
    sorted_patterns = sorted(glob_pattern_prompts.keys(), key=len, reverse=True)

    for pattern in sorted_patterns:
        # Skip if already checked exact matches
        if pattern == filename or pattern == basename:
            continue

        # Try full path match first
        if fnmatch.fnmatch(filename, pattern):
            return glob_pattern_prompts[pattern]

        # Try basename match
        if fnmatch.fnmatch(basename, pattern):
            return glob_pattern_prompts[pattern]

    return None


def redact(text: str, skip_if_empty: bool = False) -> str:
    """Redact secrets from a string using predefined patterns.

    Args:
        text: The text to redact secrets from
        skip_if_empty: Skip redaction if text is empty (performance optimization)
    """
    if skip_if_empty and not text.strip():
        return text

    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text
