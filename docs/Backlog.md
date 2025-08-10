# Future features under consideration

- Inline MR annotations: Output in GitLab/GitHub Code Quality (CodeClimate) JSON to annotate lines; optionally add a --format {text|codeclimate|json}.
- Token accounting & budgets: Log response.usage (prompt/completion tokens); add --max-total-tokens per run.
- Result schema: Ask the model to return a small JSON block {status, findings[]} in addition to the human text; use it to make pass/fail decisions more robust than regex.
- Caching: Skip unchanged files by caching (file hash → last review outcome) in .git/ai-review-cache.json.
- Default excludes: Provide a built-in list (lockfiles, vendored deps, minified assets, images) with --no-default-excludes to override.
- Streaming: Stream model output to give live feedback for long reviews.
- Provider adapters: Pluggable backends (OpenAI, Azure, local OpenAI-compatible server) with per-provider auth/env settings.
- Policy packs: Allow loading rule presets per language/framework, merging with filetype prompts.
- Concurrency control: Adaptive worker count based on observed 429 rate; honor Retry-After if present.
- Security mode: Force --diff-only and redact logs automatically when --security-mode is enabled (for sensitive repos).
