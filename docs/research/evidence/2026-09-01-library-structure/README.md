<!-- docgraph: ignore -->

# Evidence for the 2026-09-01 library structure survey

Raw findings behind
`docs/plans/2026-09-01-extract-book-contracts-and-retire-pd-repos.md`. Six
independent surveys of all eighteen workspace repositories, none of which saw
the others' work. Kept verbatim as agent output.

| File | Covers |
| --- | --- |
| `01-book-tools-structure.md` | Module map, dependency graph, extraction seams and their sizes |
| `02-consumer-usage.md` | What each repo imports, version pinning, the path-loading workaround |
| `03-labeler-side.md` | Labeler repos, contracts, the bbox tightener, headless review |
| `04-training-side.md` | Training repos, the torch-free boundary pattern, glyph features |
| `05-data-prep-side.md` | Data repos, the two PGDP readers, duplicated alignment glue |
| `06-duplication.md` | Every concept implemented more than once, ranked by pain |
