---
Status: active
Owner: CT
Created: 2026-05-22
Last verified: 2026-07-13
Kind: process
---

# pdomain-ops conventions

<!-- workspace-conventions:start -->

## Rule: Write docs clearly

**The rule.** Follow [Writing Style](docs/process/writing-style.md) for docs,
reports, issue text, PR text, and user-facing copy.

**Why.** Detailed style guidance belongs in a process doc. CONVENTIONS.md
should stay short.

## Rule: No comments explaining what code does

**The rule.** Don't add comments that restate what the code does;
well-named identifiers already explain it. Add a comment only when the WHY is
non-obvious. Examples include a hidden constraint, a subtle invariant, or a
workaround for a specific bug.

**Why.** Comments rot when code changes and become misleading. This rule also
applies to docstrings. Use one short line at most. Do not use multi-paragraph
docstrings or multi-line comment blocks.

**Common high-confidence violations** (bot auto-fix candidates)

- One-line summary comment immediately above a function that restates its name.
- `# returns the X` or `# sets the Y` before a return/assignment statement.
- Multi-line docstrings that explain every parameter with no non-obvious WHY.
- Section divider blocks: `# ---…---` / `# ===…===` multi-line banners used as
  navigation headers in test files — class names and blank lines already
  provide structure; remove the banner, keep the blank lines.
- Multi-paragraph module or class docstrings with a "Focus on:" / "Covers:"
  section — collapse to a single-line summary.

**Common judgment-call violations** (bot flags, CT decides)

- Comments that reference the PR, issue, or task that introduced the code. This
  context belongs in the commit message, not the source.
- Multi-line preamble that mixes WHY (worth keeping) with WHAT (worth removing).

## Rule: Unicode escape sequences for ruff-flagged ambiguous characters

**The rule.** Characters ruff flags under RUF001/002/003 (ambiguous Unicode —
curly quotes, en-dashes, em-dashes, multiplication signs, non-breaking spaces,
etc.) must use `\uXXXX` escape sequences in string and docstring literals. In
comments, replace them with the plain ASCII equivalent. Always include a short
inline comment that names the character, e.g.
`"""  # LEFT DOUBLE QUOTATION MARK`.

**Why.** Most editors and diff views make literal curly quotes and dashes look
like their ASCII equivalents. This similarity makes string comparisons and grep
silently fragile. Escape sequences make intent explicit and work safely across
all encodings. `# noqa: RUF00x` masks the problem instead of fixing it.

**Common high-confidence violations** (bot auto-fix candidates)

- A string literal containing `"hello – world"` written with the literal
  `–` character instead of the escape sequence.
- `# noqa: RUF001`, `# noqa: RUF002`, or `# noqa: RUF003` suppressions instead
  of escape sequences.
- `RUF002` or `RUF003` added to `[tool.ruff.lint] ignore` in `pyproject.toml`
  to paper over ambiguous characters.

**Common judgment-call violations** (bot flags, CT decides)

- Test strings that intentionally exercise curly-quote round-trip through the
  OCR pipeline and must contain the literal character. Keep the literal with an
  explicit `# noqa: RUF001  # intentional: testing curly-quote round-trip`
  comment. The comment must name the character and state the reason.

## Rule: Use `uv run` for all Python and tool invocation

**The rule.** Invoke Python, pytest, ruff, mypy/pyright, and any project-local
CLI through `uv run`. Never call bare `python`, `python3`, `pytest`, or
`pre-commit` from a Makefile target, CI step, or hook.

**Why.** Direct invocation skips the project's `.venv` and the lockfile-pinned
toolchain. The bare interpreter may see different installed package versions,
so tests can pass locally and fail in CI, or vice versa. `uv run` is uniformly
fast (<200 ms warm) and always selects the project venv.

**Common high-confidence violations** (bot auto-fix candidates)

- `python -m pytest` or `python3 script.py` in any `Makefile`, `*.sh`,
  `.github/workflows/*.yml`, or `.pre-commit-config.yaml` hook.
- `pre-commit run` (bare) instead of `uv run pre-commit run` in CI or scripts.
- `ruff check` or `pyright` (bare) in scripts that don't activate a venv first.

**Common judgment-call violations** (bot flags, CT decides)

- One-off REPL commands typed in CT's interactive shell. These commands are out
  of scope for this rule.

## Rule: Design spec files live in `docs/specs/` until the milestone ships

**The rule.** A design spec file produced by `/spec-from-issue` lives at
`docs/specs/<date>-<topic>-design.md` while the milestone's chore issues are open.
Move the file to `docs/architecture/` in a housekeeping commit when both
conditions are met: the milestone's last chore closes, and the implementation
lands.

```bash
git mv docs/specs/<date>-<topic>-design.md docs/architecture/
git commit -m "docs: promote <topic> spec to architecture/ (milestone shipped)"
```

Update any `Spec: docs/specs/...` pointers in still-open issues after the move.

**Why.** `docs/specs/` is the active working area. Implementing agents follow
`Spec:` pointers to find their instructions. `docs/architecture/` is the
permanent design record for shipped features. Mixing shipped and in-progress
specs makes it unclear which specs still govern ongoing work.

**Common high-confidence violations** (bot auto-fix candidates)

- A spec file remaining in `docs/specs/` after its milestone's last chore issue closes.

**Common judgment-call violations** (bot flags, CT decides)

- A milestone with one chore still open but all substantive work done — CT decides
  whether to move the spec early or wait for the final chore to close.

## Rule: Document every lint-rule suppression

**The rule.** Prefer fixing the underlying issue; suppress a lint rule only
when the deviation is genuinely correct (e.g. an optional dependency import
guarded by `try`/`except`). When a suppression *is* warranted, including
`# pyright: ignore[...]`, `# type: ignore[...]`, `# noqa: ...`, or a
`[tool.ruff.lint]` `ignore` / `per-file-ignores` entry, it must meet two
conditions:

1. Add a short inline rationale at the point of deviation. Explain *why* the
   suppression is safe.
2. Catalogue the suppression in the repo's
   `docs/process/lint-deviations.md`. Record the rule, tool, file locations,
   and justification.

Use basedpyright's native
`# pyright: ignore[reportRuleName]` form — mypy-style `# type: ignore[code]`
codes are not honored by basedpyright.

**Why.** A bare suppression hides whether the deviation was a deliberate,
reviewed decision or a shortcut. It also rots silently when the surrounding
code changes. The inline comment shows intent where people read the code. The
central doc keeps the whole suppression set auditable in one place so it cannot
quietly grow. This rule is the escape valve for the "Unicode escape sequences"
rule above. Use it to justify a `# noqa` that genuinely must stay.

**Common high-confidence violations** (bot auto-fix candidates)

- A `# pyright: ignore`, `# type: ignore`, or `# noqa` with no adjacent comment
  stating why the suppression is safe.
- mypy-style `# type: ignore[import-not-found]` used to suppress a basedpyright
  diagnostic — replace with `# pyright: ignore[reportMissingImports]`.
- A bare unscoped `# type: ignore` / `# noqa` with no bracketed rule code.

**Common judgment-call violations** (bot flags, CT decides)

- A suppression whose inline rationale exists but is missing from
  `docs/process/lint-deviations.md` — CT decides whether to catalogue it or
  remove the suppression.
- A long-standing suppression whose stated rationale no longer holds after a
  refactor — CT decides whether to drop the suppression.

<!-- workspace-conventions:end -->
