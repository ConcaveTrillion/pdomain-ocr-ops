<!-- docgraph: ignore -->
<!--
  ISSUE REPORT TEMPLATE — copy to docs/issues/YYYY-MM-DD-short-slug.md and fill in.
  This file is excluded from the docgraph index (the marker above). The COPY you
  create is a real governed node, so keep its frontmatter + Agent Index and add it
  to the canonical index in docs/issues/README.md. Link it from a context doc only
  when it changes current state or durable intent.

  Conventions (see ./README.md):
    - Filename: YYYY-MM-DD-short-slug.md
    - Kind: issue ; Level: I1 (repo-wide) or I2 (local)
    - Keep frontmatter Status: == Agent Index Status: (mismatch -> field_conflict)
    - Open -> Status: active ; Resolved/Won't fix/Duplicate -> Status: retired (via doc-retirer)
    - Keep structured Agent Index values free of inline comments.
    - Add this issue to docs/issues/README.md, the canonical issue index.
    - Remove defect-only sections when Issue type is not Bug or Regression.
-->
---
Status: active            # active while Open; retired when Resolved/Won't fix/Duplicate
Owner: <owner>
Created: <YYYY-MM-DD>
Last verified: <YYYY-MM-DD>
Kind: issue
Level: I1                 # I1 repo-wide | I2 narrow/local
---

# <One-line problem statement, not a category>

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** <YYYY-MM-DD>
- **Resolution:** Open
- **Issue type:** <Bug|Regression|Investigation|Feature|Chore|Docs>
- **Priority:** <P0|P1|P2|P3>
- **Area:** <stable component name|Cross-cutting>
- **Triage:** <Accepted|Needs evidence|Deferred>
- **Affected version:** <pkg + version / commit>
- **Parent:** <relative Markdown link|None>
- **Children:** <relative Markdown links|None>
- **Blocked by:** <relative Markdown links|None>
- **Blocks:** <relative Markdown links|None>
- **Read when:** <when a future agent should pull this up>
- **Search terms:** <comma-separated symptoms, error strings, component names>
- **Relates to:** [<governed doc>](<relative/path.md>)

## Summary

<2–4 sentences: what work is needed, why it matters, and how the need was found.>

## Outcome / acceptance criteria

- <Observable result that proves this issue is complete.>

## Evidence / motivation

<Lead with the smallest decisive evidence. Separate observation from
hypothesis. For planned work, cite the spec, user need, or current limitation.>

## Dependencies

- <Restate blocking relationships and required sequencing, or `None`.>

## Next steps

1. <The first concrete action.>

<!-- Keep the sections below for Bug and Regression issues. -->

## Environment / versions

```
<pkg + versions, OS, launch command, relevant env vars, repo under test>
```

## Evidence — reproduction & diagnosis

<Lead with the smallest decisive test. Show commands AND output. Number steps.>

### 1. <Decisive observation>
```
<command / query>
<output>
```
<What it proves.>

### 2. <Supporting observation>
...

## Root-cause hypotheses (ranked)

1. **(Most likely) <hypothesis>** — <why it fits the evidence; what would confirm it>.
2. **<alternative>** — <fit / what distinguishes it>.

<Note what evidence is still needed to disambiguate (e.g. server stderr).>

## Defects to fix

1. **<defect>** — <one line>. (Primary)
2. ...

## What is NOT broken (to scope the fix)

- <Adjacent things you ruled out, so a reader doesn't re-investigate them.>

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit/spec link here, move the README pointer to "Resolved", and route
the retirement through `doc-retirer`.
