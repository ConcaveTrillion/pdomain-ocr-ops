---
Status: retired
Owner: CT
Created: 2026-08-07
Last verified: 2026-08-07
Kind: issue
Level: I2
---

# desktop._noop_app was dead code kept by a stale docstring

## Agent Index

- **Kind:** issue
- **Status:** retired
- **Level:** I2
- **Last verified:** 2026-08-07
- **Resolution:** Resolved
- **Issue type:** Chore
- **Priority:** P3
- **Area:** desktop
- **Triage:** Accepted
- **Affected version:** pdomain-ops at commit 7cc25cf
- **Parent:** None
- **Children:** None
- **Blocked by:** None
- **Blocks:** None
- **Read when:** asking why `reportUnusedFunction` is disabled package-wide, or
  auditing what that disable hides.
- **Search terms:** _noop_app, desktop.py, dead code, reportUnusedFunction, ASGI
  placeholder.
- **Relates to:** [lint-rule deviations](../process/lint-deviations.md)

## Summary

`pdomain_ops/desktop.py` carried an ASGI placeholder named `_noop_app` that
nothing called. Its docstring claimed it was kept for test usage, which was no
longer true. The package-wide `reportUnusedFunction = false` setting, which
FastAPI route handlers require, kept the strict type gate from reporting it. The
function is now removed.

## Outcome / acceptance criteria

- `_noop_app` is gone from `pdomain_ops/desktop.py`. **Met.**
- No documentation still describes it as live or untriaged code. **Met.**
- The type, lint, and desktop test gates pass after removal. **Met.**

## Evidence / motivation

A repository-wide search on 2026-08-07 found the definition and no call site:

```text
pdomain_ops/desktop.py:586      async def _noop_app(...)
pyproject.toml:229              comment naming it as an untriaged example
docs/context/intent-map.md:58   deferred triage entry
docs/process/lint-deviations.md:221  named as the hidden dead function
```

Every mention outside the definition described the function as untriaged. No
test imported it, no entry point referenced it by string, and its body was a
docstring alone.

## Dependencies

- None.

## Next steps

1. None. The work is complete.

## Resolution

_Resolved._ Commit `d73c331` removed the function and its banner comment. The
gate passed afterward: `ruff check`, `ruff format --check`, and
`basedpyright pdomain_ops --level error` reported no errors, and 58 desktop
tests passed.

The follow-up documentation edits landed in the same change set. The
[lint-rule deviation catalog](../process/lint-deviations.md) and the
`reportUnusedFunction` comment in `pyproject.toml` no longer cite this function
as a live example. The deferred entry also left the
[intent map](../context/intent-map.md).
