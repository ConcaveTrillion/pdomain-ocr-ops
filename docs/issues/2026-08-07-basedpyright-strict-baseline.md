---
Status: retired
Owner: CT
Created: 2026-08-07
Last verified: 2026-08-08
Kind: issue
Level: I1
---

# 33 pre-existing strict diagnostics sit in the basedpyright baseline

## Agent Index

- **Kind:** issue
- **Status:** retired
- **Level:** I1
- **Last verified:** 2026-08-08
- **Resolution:** Resolved
- **Issue type:** Chore
- **Priority:** P2
- **Area:** Cross-cutting
- **Triage:** Accepted
- **Affected version:** pdomain-ops at commit d73c331
- **Parent:** None
- **Children:** None
- **Blocked by:** None
- **Blocks:** None
- **Read when:** touching a file listed below, or deciding whether the strict
  type gate can drop its baseline.
- **Search terms:** basedpyright, baseline.json, strict mode, type diagnostics,
  reportUnknownMemberType, strict backlog.
- **Relates to:** [lint-rule deviations](../process/lint-deviations.md)

## Summary

The basedpyright baseline hid 33 strict diagnostics that predated the switch to
strict mode, so the type gate reported only new regressions, not the existing
backlog. Enabling strict on `pdomain_ops` on 2026-07-15 pruned the baseline from
263 entries to these 33. While they remained, no one could tell from a green gate
whether a file was actually clean. All 33 are now fixed and the baseline file is
deleted.

## Outcome / acceptance criteria

- `.basedpyright/baseline.json` is deleted or empty. **Met.**
- `uv run basedpyright pdomain_ops --level error` passes with no baseline file.
  **Met.**
- Every fix resolves the underlying type, rather than adding a suppression. Any
  unavoidable suppression is narrow and is added to the
  [lint-rule deviation catalog](../process/lint-deviations.md). **Met** — the
  change removed six suppressions and added none.

## Evidence / motivation

The baseline held 33 diagnostics across 9 files, counted from
`.basedpyright/baseline.json` on 2026-08-07:

```text
 8  pdomain_ops/gpu/modal_dispatcher.py
 6  pdomain_ops/gpu/events.py
 6  pdomain_ops/suite/types.py
 3  pdomain_ops/gpu/default_stages.py
 3  pdomain_ops/gpu/shared_container_dispatcher.py
 2  pdomain_ops/gpu/modal_app.py
 2  pdomain_ops/suite/auth.py
 2  pdomain_ops/suite/registry.py
 1  pdomain_ops/schemas/emit.py
```

Three files carried 20 of the 33. Removing the baseline surfaced 29 of the
entries as errors at `--level error`; the rest were lower-severity diagnostics
that the same fixes cleared.

The entries fell into five groups, and each group had a root-cause fix rather
than a per-site suppression:

- Seven `reportImplicitOverride` findings on methods implementing the
  `GPUBackend` protocol and Pydantic's `model_post_init`.
- Nine findings in `suite/types.py` from three fields declared non-optional but
  defaulted to `None` and filled in by `model_post_init`.
- Six findings in `gpu/events.py` from `json.loads` returning `Any`.
- Seven findings across `gpu/modal_app.py` and `gpu/modal_dispatcher.py` because
  Modal ships no type stubs.
- Four remaining findings: a private import from `pdomain-book-tools`, an
  unannotated list, and an unannotated `TypeAdapter`.

## Dependencies

- None. Each file was cleared on its own.

## Next steps

1. None. The work is complete.

## Resolution

_Resolved._ All 33 entries are fixed, `.basedpyright/baseline.json` is deleted,
and `uv run basedpyright pdomain_ops --level error` reports no errors, warnings,
or notes without it. The full suite passes.

The fixes were structural, not suppressions. Six methods gained `@override`.
`suite/types.py` now uses Pydantic `Field(default_factory=...)` for
`registered_at`, `layer_colors`, and `common`, which deleted all three
`model_post_init` hooks along with their dead `is None` comparisons.
`gpu/events.py` narrows decoded JSON through a `TypeGuard` helper.
`gpu/modal_app.py` and `gpu/modal_dispatcher.py` bind Modal to an `Any` local at
the import boundary, matching the pattern the repository already uses for
`webview` and `pystray`. `gpu/default_stages.py` calls
`importlib.import_module("pytesseract")` inside a `try` instead of importing
another package's private flag. Import by name rather than a `find_spec` probe,
so an installed-but-broken `pytesseract` still fails before OCR starts, which is
what the private flag did.

Net effect on suppressions: six removed, none added. Gone are three
`reportAssignmentType` ignores in `suite/types.py`, one
`reportAttributeAccessIssue` ignore in `gpu/modal_dispatcher.py`, the
`reportUnknownMemberType` and `reportUntypedFunctionDecorator` ignores in
`gpu/modal_app.py`, and two `TRY004` ruff directives in `gpu/events.py`. The
[lint-rule deviation catalog](../process/lint-deviations.md) records the current
state.

One test changed with the code.
`tests/gpu/test_default_stages.py::test_tesseract_stage_raises_when_unavailable`
patched the upstream private flag, so it now patches `importlib.import_module`
instead. The behavior it asserts is unchanged: an absent `pytesseract` raises
`ImportError`.
