---
Status: active
Owner: CT
Created: 2026-07-15
Last verified: 2026-07-15
Kind: process
---

# Writing style — pdomain-ops

## Agent Index

- **Kind:** process
- **Status:** active
- **Read when:** writing replies, docs, reports, or issue and PR text for this repo.
- **Search terms:** writing style, readability, tone, prose rules, reading level.

This is the writing style for replies, docs, reports, issue and PR text, and user-facing copy in
this repo. Follow it everywhere. It sits alongside the plugin-owned `write-readably` and
`edit-for-readability` routing in [`../../CONVENTIONS.md`](../../CONVENTIONS.md); this document
keeps the repo-local additions the plugin standard does not carry.

## Goal

Write text that is easy to scan without sounding clipped. Make it clear for readers who are tired,
new to the project, or reading in a second language. Aim for about a 7th grade English level.

## Rules

- Use short, clear sentences. Put one idea in each sentence.
- Vary sentence length so the text feels natural; don't make every sentence the same.
- Combine closely related ideas when splitting them would sound stiff.
- Prefer common words. Use active voice when it is natural. Avoid long chains of clauses.
- Short paragraphs, but keep closely related sentences together.
- Don't repeat the same idea in nearby sentences.
- Use lists when they make steps or choices easier to scan.
- Keep technical terms when they are the correct names (systemd, `OnCalendar`, symlink, exit code).
  Explain a term the first time it may be unclear.
- Use parentheses rarely. Fine for a first-time acronym write-out like `CI (continuous integration)`.
- Do not use parenthetical em dashes.

## Also (from things I've told you directly)

- **Lead with the answer.** First line: what happened or what you found. Detail after.
- **No jargon or coined terms for effect.** Don't say "footgun", "blast radius", "adversarially
  verify", "the paradox dissolves". Describe what actually happens. (Prefer common words.)
- **Don't invent labels or codenames and make me remember them.** Name the thing in place.
- **Arrows (→) and emojis are fine when they're genuinely shorter or clearer** — not as a
  substitute for an explanation.
- **Take a position. Don't hedge then un-hedge.** If I ask which, pick one and say why.
- **Match length to the task.** A small question gets a couple of sentences, not headers and tables.

## Links and detail

- If another doc explains a topic, link to it instead of repeating the detail.
- Link helpful references on first use; prefer official docs for standard tools.
- Use local source links with line anchors for project behavior.
- Avoid deep links into external source code unless the reader needs them.

## Before publishing

Read it once as if the reader is tired or new. Fix any sentence that needs a second read. Split long
paragraphs. Remove filler.
