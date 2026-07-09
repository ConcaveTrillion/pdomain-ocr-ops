# style-review JSON contract

`scripts/style-review-detect.py` emits a single JSON document on stdout.
`scripts/style-review-apply.py` reads it from `--findings-file` or stdin.

## Schema

```json
{
  "scope": "diff" | "tree",
  "scope_detail": {
    "from_sha": "...",
    "to_sha": "..."
  } | {
    "tree_root": "/srv/bot-workspaces/style-sweep/<repo>"
  },
  "findings": [
    {
      "rule_citation": "## Rule: No comments explaining what code does",
      "file": "src/foo.py",
      "line": 42,
      "patch": "<unified diff string applicable via `git apply`>",
      "confidence": "high" | "judgment",
      "description": "Short, human-readable summary. Used in PR review comments."
    }
  ],
  "stats": {
    "total_findings": 3,
    "high": 2,
    "judgment": 1,
    "sweep_capped": false
  }
}
```

## Rules
- All paths are repo-relative.
- `patch` is a unified diff (`git diff` format), suitable for `git apply`.
- `confidence: "high"` triggers auto-apply by `apply.py`; failures of
  `make fast-check` after apply demote the finding to `judgment` (the
  patch is reverted, the comment is posted instead).
- `sweep_capped: true` indicates the cap was hit; apply.py emits a
  `sweep-capped` event into the events log.
- An empty `findings` array is valid: detect.py returns success, apply.py
  no-ops.
