---
Status: active
Owner: CT
Created: 2026-08-07
Last verified: 2026-08-07
Kind: issue
Level: I1
---

# 33 pre-existing strict diagnostics sit in the basedpyright baseline

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-08-07
- **Resolution:** Open
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

The basedpyright baseline hides 33 strict diagnostics that predate the switch
to strict mode, so the type gate reports only new regressions, not the
existing backlog. Enabling strict on `pdomain_ops` on 2026-07-15 pruned the
baseline from 263 entries to these 33. Until they are fixed, no one can tell
from a green gate whether a file is actually clean. This issue records the
work that the intent map deferred.

## Outcome / acceptance criteria

- `.basedpyright/baseline.json` is deleted or empty.
- `uv run basedpyright pdomain_ops --level error` passes with no baseline file.
- Every fix resolves the underlying type, rather than adding a suppression. Any
  unavoidable suppression is narrow and is added to the
  [lint-rule deviation catalog](../process/lint-deviations.md).

## Evidence / motivation

The baseline holds 33 diagnostics across 9 files, counted from
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

Three files carry 20 of the 33, so the work splits cleanly. The GPU dispatch
files and the suite files can be cleared independently.

Three of these files already carry documented suppressions for a related reason.
`gpu/modal_dispatcher.py` and `gpu/modal_app.py` work around incomplete Modal
type information, and `suite/types.py` works around Pydantic fields that start
as `None`. Expect some baseline entries in those files to need the same kind of
boundary fix rather than a direct type correction.

## Dependencies

- None. Each file can be cleared on its own.

## Next steps

1. Clear `gpu/modal_dispatcher.py`, `gpu/events.py`, and `suite/types.py`, which
   together hold 20 of the 33 entries.
2. Clear the remaining six files.
3. Delete `.basedpyright/baseline.json` and confirm
   `uv run basedpyright pdomain_ops --level error` passes without it.
4. Update the baseline section of the
   [lint-rule deviation catalog](../process/lint-deviations.md), and remove the
   deferred entry from the [intent map](../context/intent-map.md).

## Resolution

_Open._ When fixed: set frontmatter and Agent Index `Status: retired`, add the
resolving commit link here, move the README pointer to "Resolved", and route the
retirement through `doc-retirer`.
