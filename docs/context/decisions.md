---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-13
Kind: context
---

# Decisions

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** checking durable documentation and lifecycle decisions.
- **Search terms:** decisions, retired plan, archive policy, tombstone.

### 2026-07-13 — Retire completed implementation plans

- **Context:** Two inferred-active plans describe behavior that shipped in May
  and June 2026.
- **Decision:** Delete the plans after promoting their durable behavior to
  [`batched-ocr-dispatch.md`](../architecture/batched-ocr-dispatch.md) and
  [`shared-paths-and-export-manifest.md`](../architecture/shared-paths-and-export-manifest.md).
- **Rationale:** Architecture docs are current truth; completed execution
  checklists are not.
- **Evidence:** Commits `8703224`, `eee600b`, `4111e95`, `4898f33`, `d7209ab`,
  and the source and tests cited by both architecture docs.
- **Remaining work:** Remote OCR batch dispatch remains deferred in
  [`intent-map.md`](intent-map.md).

### 2026-07-13 — Retire the parallel archive tree

- **Context:** `docs/archive/` contained nine empty `.gitkeep` files and no
  documentation.
- **Decision:** Remove the archive scaffold and stop treating archive as a
  lifecycle destination.
- **Rationale:** Docgraph retirement preserves durable truth in architecture,
  decisions, and residual intent. Empty cold-storage folders add a competing
  convention without preserving knowledge.
- **Evidence:** Owner direction on 2026-07-13 and commit `a603ce9`, which created
  the otherwise-unused scaffold.
- **Remaining work:** none.

### 2026-07-13 — Exclude the salvaged holding area pending triage

- **Context:** `_tbd/` contains 210 tracked Markdown files salvaged from the old
  OCR meta-repository, and its README requires keep-or-delete review.
- **Decision:** Exclude `_tbd/**` from docgraph indexing and reverse-reference
  scans until the owner classifies that corpus.
- **Rationale:** Those files are not wired into pdomain-ops, but their unique
  historical content makes automatic deletion or lifecycle inference unsafe.
- **Evidence:** `_tbd/README.md` and the tracked-file count on 2026-07-13.
- **Remaining work:** Resolve the owner-decision item in
  [`intent-map.md`](intent-map.md).

### 2026-07-13 — Red-team salvaged documents before lifecycle action

- **Context:** The 210 tracked Markdown files under `_tbd/` may describe ideas
  that diverge from implementation or current practice. Their historical value
  does not make every document current truth.
- **Decision:** Red-team each document against implementation and current
  practice. Route materially diverged documents to supersession or retirement.
  Do not add conformance headings merely to make a document appear current.
- **Rationale:** Lifecycle status should reflect evidence. Before superseding
  or retiring a diverged source, preserve useful ideas in the correct durable
  destination: architecture for shipped truths, decisions for rationale, and
  the intent map for promising unbuilt ideas. Explicitly label what did not
  ship or no longer matches current practice; do not discard a diverged
  document wholesale.
- **Evidence:** Owner authorization on 2026-07-13.
- **Remaining work:** Review the corpus without migrating or deleting `_tbd/`
  until each document has been red-teamed.

### 2026-07-13 — Bound automation with observable human gates

- **Context:** Historical workspace automation combined schedulers, model
  calls, issue mutation, credentials, and cost tracking in one bot stack.
- **Decision:** Treat least privilege, narrow command surfaces, explicit
  eligibility and blocker checks, observable outcomes, bounded budgets, and
  human escalation as portable workspace requirements. Keep deterministic
  helpers free of hidden model calls.
- **Rationale:** Automation failures remain recoverable when authority and
  transitions are visible and mutation requires an explicit gate.
- **Evidence:** `_tbd/ocr-container-docs/archive/plans/2026-05-09-workspace-foundation.md`,
  `_tbd/ocr-container-docs/archive/specs/2026-05-14-coding-bot-design.md`,
  current `CLAUDE.md`, installed Superpowers skills, and Codex tool permissions.
  Current practice uses Codex collaboration, plugins, and worktrees instead of
  the Claude/ctask scheduler and its branch, PAT, and model-label protocol.
- **Remaining work:** Apply this rationale when designing cross-repo
  automation; it does not define pdomain-ops runtime architecture.

### 2026-07-13 — Pilot risky automation before broad rollout

- **Context:** Earlier bot rollouts used bounded repositories, bake periods,
  stress cycles, and rollback gates before expansion.
- **Decision:** Preserve pilot-first rollout, explicit acceptance criteria,
  bake time, multi-cycle verification, and rollback as portable workspace
  rationale.
- **Rationale:** A narrow pilot exposes operational and security failures before
  they become workspace-wide incidents.
- **Evidence:** `_tbd/ocr-container-docs/archive/plans/2026-05-10-pilot-pd-book-tools.md`,
  `_tbd/ocr-container-docs/archive/plans/2026-05-11-r4-pd-book-tools-b6-multi-cycle-stress.md`,
  and current `CLAUDE.md` worktree, verification, and integration rules. Current
  practice replaced rollout waves and a rolling WIP branch with per-task
  worktrees and repository-local gates.
- **Remaining work:** Use the principle for future automation changes; do not
  restore the historical bot topology.

### 2026-07-13 — Separate introduced failures from inherited debt

- **Context:** A failing gate may expose old debt or a regression introduced by
  the current change.
- **Decision:** Block changes on introduced failures. Keep inherited failures
  visible and route them to a separate, deduplicated remediation path. Clear
  mechanical failures before judgment-heavy review.
- **Rationale:** This avoids both false blame and silent acceptance of existing
  debt.
- **Evidence:** `_tbd/ocr-container-docs/archive/plans/2026-05-11-r0-lint-first-pr-unblock.md`,
  `_tbd/ocr-container-docs/archive/plans/2026-05-12-ci-failure-triage.md`, current
  Makefile gates, and the systematic-debugging and verification skills. Current
  practice uses repository-native checks instead of a custom triage bot.
- **Remaining work:** Apply this portable review rule when a baseline already
  fails; it is not permission to waive either failure class.

### 2026-07-13 — Keep issue axes and dependency chains explicit

- **Context:** The salvaged label system separated issue kind, workflow status,
  triage outcome, priority, area, and dependency relationships.
- **Decision:** Preserve those concepts as orthogonal, portable workspace
  rationale. Require human approval before issue creation and keep parent,
  child, and blocker links machine-checkable.
- **Rationale:** Collapsing type, state, and intent makes automation ambiguous
  and can reactivate retired work accidentally.
- **Evidence:** `_tbd/ocr-container-docs/architecture/label-taxonomy.md`,
  `_tbd/ocr-container-docs/specs/2026-05-10-feature-request-spec-decomposition-design.md`,
  and current repo guidance to check issue status and in-flight work. Current
  practice uses live `pdomain/*` labels and current tools, not the old
  ConcaveTrillion colors, Claude model labels, or automation tables.
- **Remaining work:** Reconcile the model with live GitHub labels before any
  new machine-readable workspace taxonomy is adopted.

### 2026-07-13 — Keep editable sibling mode explicit and reversible

- **Context:** Local development needs editable siblings, while release and
  dependency truth comes from registries.
- **Decision:** Require an explicit local-mode marker, deterministic sibling
  selection, reversible upgrades, and registry-resolved release validation.
  Dependency refreshes leave a reviewable diff and never commit or push
  silently.
- **Rationale:** Implicit worktree selection and hidden dependency commits make
  builds irreproducible and changes hard to audit.
- **Evidence:** `_tbd/ocr-container-docs/plans/2026-05-24-local-dev-standardization.md`,
  `_tbd/ocr-container-docs/archive/specs/2026-05-24-update-pd-deps-design.md`,
  current `scripts/local-dev.sh`, `scripts/local-upgrade-deps.sh`,
  `scripts/update-pdomain-deps.sh`, and Makefile targets. Current practice uses
  `pdomain` commands and `.pdomain-local-mode`, not the old `pd` names.
- **Remaining work:** Keep exact sibling matrices and marker behavior in the
  current scripts rather than duplicating them here.

### 2026-07-13 — Make unpublished sibling validation transient

- **Context:** Testing against sibling source branches can catch integration
  breaks before a package release.
- **Decision:** Keep this validation optional, require a clean tree, and restore
  manifests and lockfiles exactly. Validate Python from Git sources; keep npm
  registry-based unless a deliberate source-build path exists.
- **Rationale:** Transient validation must not rewrite the developer's lasting
  dependency state.
- **Evidence:** `_tbd/ocr-container-docs/plans/2026-06-06-git-main-validation-mode.md`,
  `_tbd/ocr-container-docs/process/ci-against-main.md`, current
  `scripts/ci-against-master.sh`, `scripts/git_master_sources.py`, and
  `scripts/release-common.sh`. Current practice uses `master` naming and
  `VALIDATE_AGAINST_MASTER`.
- **Remaining work:** None for pdomain-ops; other repositories own their
  sibling lists and source-build capabilities.

### 2026-07-13 — Require narrow, documented lint escape valves

- **Context:** Strict checks need exceptions for correct optional imports,
  runtime type imports, generated code, tests, and third-party stub gaps.
- **Decision:** Allow a suppression only when it is scoped, justified inline,
  and recorded in the central deviation catalog. Introduce new scanners as
  advisory until their baseline is clean.
- **Rationale:** An auditable escape valve preserves signal without pretending
  every diagnostic is correct.
- **Evidence:** `_tbd/ocr-container-docs/decisions/2026-05-17-strict-linting.md`,
  `_tbd/ocr-container-docs/archive/research/2026-05-17-strict-linting-stack.md`,
  current `pyproject.toml`, `CONVENTIONS.md`, and
  [`lint-deviations.md`](../process/lint-deviations.md). Current practice gates
  recommended-mode errors with `failOnWarnings = false`, not the proposed
  universal warning-failing policy.
- **Remaining work:** Keep the catalog synchronized whenever suppressions or
  config-level ignores change.

### 2026-07-13 — Build reviewable release artifacts and isolate index dispatch

- **Context:** A package build, GitHub release, and package-index refresh are
  related but distinct failure domains.
- **Decision:** Pin managed actions immutably, derive version truth from package
  metadata, verify artifacts before publishing, and notify indexes separately.
  An index-notification failure does not invalidate an artifact already
  published successfully.
- **Rationale:** Build-once artifacts and isolated dispatch make releases
  reproducible and recoverable.
- **Evidence:** `_tbd/ocr-container-docs/plans/2026-06-01-sha-pinning-enforcement.md`,
  `_tbd/ocr-container-docs/process/pdomain-release-and-index-dispatch.md`,
  current `.github/workflows/release.yml`, `scripts/release-common.sh`, and the
  `pdomain-release-published` receiver in pdomain-index-pip. Current workflows
  do not all contain the old proposed GitHub `release-ci` job; the verified
  local `ci-slow` gate and per-repo workflow are authoritative.
- **Remaining work:** Treat this as portable release rationale; each package
  owns its exact build and publish workflow.

### 2026-07-13 — Route documentation claims by evidence and lifecycle

- **Context:** Source observations, unverified commands, decisions, gaps, and
  future intent require different authority and lifecycle treatment.
- **Decision:** Require evidence for claims and adjudicate contradictions.
  Route shipped truth to architecture, rationale to decisions, and promising
  unbuilt work to intent instead of keeping completed plans as parallel truth.
- **Rationale:** Predictable placement and lifecycle state make retrieval safer
  without discarding useful knowledge.
- **Evidence:** `_tbd/ocr-container-docs/process/document-existing-repo.md`,
  `_tbd/ocr-container-docs/archive/process/doc-claim-audit.md`, current
  `DOCGRAPH.md`, `docgraph.toml`, and the context docs. Current practice uses
  docgraph metadata and checks rather than the old optional-frontmatter folder
  template and archive lifecycle.
- **Remaining work:** Apply this decision to approved `_tbd/` preservation and
  retirement work.

### 2026-07-13 — Write reader-facing prose answer first

- **Context:** Operational readers may be tired, new to the project, or reading
  in a second language.
- **Decision:** Lead with the answer, give each paragraph one idea, use
  descriptive headings and short active sentences, and preserve every fact.
- **Rationale:** Readability reduces review mistakes without trading away
  precision.
- **Evidence:** `_tbd/ocr-container-docs/plans/2026-05-28-writing-style-rollout.md`,
  `_tbd/ocr-container-docs/process/writing-style.md`, the managed readable-output
  block in `AGENTS.md`, `CONVENTIONS.md`, and current
  `docs/process/writing-style.md`. Current practice strengthens and manages the
  old standalone rule.
- **Remaining work:** None; keep managed guidance and repo-local prose aligned.

### 2026-07-13 — Separate OCR content from operational page lifecycle

- **Context:** OCR values and persisted page lifecycle have different ownership
  and dependency requirements.
- **Decision:** Keep OCR content in `Page`. Put stable identity, provenance,
  persistence metadata, blob references, and event history in `PageRecord` and
  lifecycle aggregates. Keep application extensions namespaced and JSON-safe.
- **Rationale:** The split avoids package cycles, keeps the foundation model
  portable, and lets lifecycle consumers depend on protocols rather than a
  remote-service assumption.
- **Evidence:** `_tbd/ocr-container-docs/specs/2026-05-31-page-record-ops-design.md`,
  `_tbd/ocr-container-docs/archive/plans/2026-06-01-page-record-ops-pdomain-ops.md`,
  current pdomain-book-tools `ocr/page.py` and `blob_protocol.py`, and current
  pdomain-ops `pages/`, `blob_store.py`, `page_aggregate.py`, and tests. Current
  APIs retain compatibility fields and evolved beyond the plan's exact removals.
- **Remaining work:** Promote a focused architecture record if current source
  coverage is not already sufficient in the owning repositories.

### 2026-07-13 — Share stable seams, not specialized application behavior

- **Context:** Reusable UI and ops code serves several applications with
  different workflows.
- **Decision:** Shared packages own primitives, protocols, types, and neutral
  extension points. Applications keep specialized behavior until repeated
  evidence justifies promotion. Shared UI accepts host callbacks instead of
  importing backend ops.
- **Rationale:** Evidence-based promotion avoids coupling every consumer to one
  application's workflow.
- **Evidence:** `_tbd/ocr-container-docs/specs/2026-05-16-cross-cut-design.md`,
  `_tbd/ocr-container-docs/plans/2026-06-10-trainer-spa-next-arc.md`, current
  pdomain-ui canvas/primitives exports, pdomain-ops protocols, and consumer
  source. Current practice uses `@pdomain/pdomain-ui` and `pdomain-ops`, not the
  original package names or drop-in design-system bundle.
- **Remaining work:** This is portable workspace rationale; consumer repos own
  decisions to promote additional shared behavior.

### 2026-07-13 — Require consent at local application trust boundaries

- **Context:** Local applications handle filesystem paths, uploaded archives,
  updates, desktop integration, and test data.
- **Decision:** Reject traversal and unsafe paths, separate local authority from
  uploaded data, require explicit consent for persistent mutations and
  upgrades, make launcher installation opt-in, and isolate and purge test data.
- **Rationale:** Local access is powerful; safe defaults prevent an interface
  convenience from becoming implicit filesystem or system authority.
- **Evidence:** `_tbd/ocr-container-docs/specs/2026-05-26-pd-ocr-simple-gui-reconciliation-design.md`,
  `_tbd/ocr-container-docs/specs/2026-06-04-pd-suite-desktop-shell-design.md`,
  current pdomain-ocr-simple-gui source/tests, and pdomain-ops `desktop.py` and
  desktop tests. Current platform support, auth scope, and CLI surfaces differ
  from the salvaged plans.
- **Remaining work:** Keep unsupported platforms or auth capabilities explicit
  in the owning repository's intent map.

### 2026-07-13 — Trace approved behavior through stable records and tests

- **Context:** UI intent, observable behavior, backend effects, and executable
  verification are related but distinct artifacts.
- **Decision:** Separate target definition from behavior capture. Give behavior
  records stable IDs, distinguish observable output from side effects, chain
  flows by record ID, and keep intended-but-unbuilt behavior visibly open.
  Use deterministic fake-dependency CI plus opt-in real-engine verification.
- **Rationale:** Traceable records expose mismatches without duplicating the
  same requirement across flows and tests.
- **Evidence:** `_tbd/ocr-container-docs/process/behavior-e2e-capture.md`,
  `_tbd/ocr-container-docs/superpowers/specs/2026-06-01-ui-behavior-intent-evidence-design.md`,
  and current pdomain-ocr-simple-gui behavior specs, E2E tests, and scanner
  tests. Current practice must derive ID grammar from scanner tests because old
  multi-segment examples and template IDs caused silent coverage errors.
- **Remaining work:** Treat this as portable testing rationale; publish only a
  scanner-safe template if current consumers still need one.

### 2026-07-13 — Separate image-correction regimes and evaluate dependencies

- **Context:** Coarse orientation, fine skew, perspective, textline curvature,
  page-side detection, and general restoration are different image problems.
- **Decision:** Keep these regimes explicit. Use owned classical geometry as a
  baseline, preserve CPU/GPU parity, and gate expensive neural correction by
  measured need. Treat license, maintenance, weights, runtime, and CLI
  boundaries as adoption criteria.
- **Rationale:** A single correction label hides incompatible algorithms,
  licensing risks, and performance costs.
- **Evidence:** `_tbd/ocr-container-docs/specs/2026-06-02-geometry-correction-design.md`,
  `_tbd/ocr-container-docs/research/2026-06-02-deskew-dewarp-backend-options.md`,
  `_tbd/ocr-container-docs/research/dewarp/uvdoc.md`, and current geometry and
  dewarp code/tests in pdomain-book-tools. Current practice selected a narrower
  stack than the survey and did not adopt every benchmark candidate.
- **Remaining work:** This is portable OCR rationale; benchmark rankings and
  dependency health require fresh evidence before new adoption.

### 2026-07-13 — Execute cross-repository renames as phased migrations

- **Context:** Public renames affect repositories, packages, indexes,
  consumers, local paths, automation, external identities, and release events.
- **Decision:** Sequence those surfaces with acceptance scans, smoke installs,
  redirect checks, and rollback. Exclude historical fixtures, retired repos,
  and audit records from blind replacement.
- **Rationale:** A staged migration preserves recoverability and distinguishes
  active runtime identity from historical evidence.
- **Evidence:** `_tbd/ocr-container-docs/archive/specs/2026-05-26-pd-to-pdomain-rename-design.md`,
  `_tbd/ocr-container-docs/archive/plans/2026-05-31-pdomain-prefix-finalization.md`,
  current `/workspaces/pdomain` repository names, manifests, remotes, release
  events, and `.pdomain-*` markers. Current practice completed the rename; the
  old disabled-Actions state, ConcaveTrillion URLs, and temporary dependency
  pointers are obsolete.
- **Remaining work:** Use this only as portable migration rationale; do not
  reopen the completed pdomain rename without current runtime evidence.

### 2026-07-13 — Remove the excluded corpus only after preservation gates pass

- **Context:** The red-team ledger covers 210 unique `_tbd/` Markdown paths and
  proposes 185 retirement candidates, but it does not itself authorize
  deletion.
- **Decision:** Treat eventual holding-corpus removal as one corpus-level
  tombstone action. Delete no source until verified shipped truth is preserved
  in architecture, durable rationale is preserved in decisions, promising
  unbuilt work is routed to intent, unresolved external-state questions retain
  explicit blockers in the intent map, and the ledger is checked against the
  final disposition set.
- **Rationale:** One evidence-backed corpus tombstone avoids repetitive
  per-document entries while preventing wholesale loss of useful material.
- **Evidence:** `_tbd/README.md`, all source paths recorded in
  [`2026-07-13-salvaged-docs-red-team.md`](../research/2026-07-13-salvaged-docs-red-team.md),
  and the preservation and lifecycle rules in `DOCGRAPH.md`. No `_tbd/` source
  has been deleted by this decision.
- **Remaining work:** Complete architecture and intent preservation, resolve
  uncertain rows with owners or owning repositories, verify the ledger, then
  use the docgraph retirement workflow for the approved removal.

### 2026-07-13 — Retired: salvaged holding corpus

- **Old path:** `_tbd/` (222 tracked files: 210 Markdown sources, four design
  assets, and eight empty placeholders).
- **Outcome:** The corpus was red-teamed and deleted after preservation.
- **Superseded by:**
  [`2026-07-13-salvaged-docs-red-team.md`](../research/2026-07-13-salvaged-docs-red-team.md),
  the current architecture records, this decision log, and
  [`intent-map.md`](intent-map.md).
- **Removal commit:** This corpus-retirement commit.
- **Rationale kept:** The ledger preserves every disposition; architecture
  preserves verified shipped behavior; the preceding decision themes preserve
  durable rationale; the intent map preserves promising work and explicit
  blockers for questions that require external state or another repository.
- **Remaining work:** Resolve the retained blocked and owner-decision items in
  their owning systems. Their source documents are retired because they are not
  current truth; their uncertainty remains explicit in the intent map.

### 2026-07-15 — Retired local writing-style document

- **Old path:** `docs/process/writing-style.md`.
- **Outcome:** Superseded.
- **Superseded by:** Plugin-owned `write-readably` and
  `edit-for-readability` routing in `AGENTS.md` and `CONVENTIONS.md`.
- **Removal commit:** Pending this migration commit.
- **Rationale kept:** The plugin keeps the shared readability standard. Per
  owner direction, this retirement intentionally retires the local-only roughly
  seventh-grade reading target, rare parentheses and no parenthetical em dashes,
  specific link practices, and command-detail deduplication.
- **Remaining work:** None.
