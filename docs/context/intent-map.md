---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-08-08
Kind: context
---

# Intent map

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** deciding what work remains active, deferred, rejected, or blocked.
- **Search terms:** intent, deferred work, rejected direction, owner decision.

Current work stays limited to isolated ebook sessions and evidence-backed
page-model adoption. All other items are completed, deferred, rejected,
blocked, or need an owner decision.

## Active bets

- **Maintain isolated ebook sessions — active.** Keep standalone ebook work
  isolated from parent repository instructions. Also isolate it from shared
  working-directory state. Owner: the se-llm-skills or ebook-tool maintainer,
  not pdomain-ops. Route: verify and maintain the procedure in that owning
  repository. Evidence: the red-team ledger found no contradiction in the
  isolation goal. Source mapped:
  `_tbd/ocr-container-docs/process/se-ebook-isolated-sessions.md`.
- **Complete evidence-backed page-model adoption — active.** Identify only
  consumer gaps that remain in PageRecord, PagePayload, provenance, extensions,
  and persistence. Owner: each consuming pdomain repository. Route: first check
  that repository's code and tests. Record a gap in its intent map only after
  that check. Current pdomain-ops evidence lives in
  [page lifecycle and storage](../architecture/page-lifecycle-and-storage.md).
  Source mapped:
  `_tbd/ocr-container-docs/archive/specs/2026-06-01-page-split-downstream-rollout.md`.

The [lint-deviation catalog](../process/lint-deviations.md) remains a standing
maintenance obligation under `CONVENTIONS.md`; it is not a migration bet.

## Completed work

- **Clear the basedpyright strict backlog — done.** All 33 baseline diagnostics
  are fixed and the baseline file is deleted. Evidence: commit `f09d2b7` and the
  [lint-deviation catalog](../process/lint-deviations.md). Owner: CT.
- **Remove `desktop._noop_app` — done.** The dead ASGI placeholder is gone.
  Evidence: commit `d73c331`. Owner: CT.
- **Salvaged holding-area migration — done.** All 210 Markdown sources were
  red-teamed. Useful content was promoted to architecture, decisions, and this
  intent map. All 222 tracked holding-area files were retired. Evidence: the
  [red-team ledger](../research/2026-07-13-salvaged-docs-red-team.md) and the
  corpus tombstone in [decisions](decisions.md). Owner: CT. Final disposition:
  retired after preservation. Source mapped: `_tbd/README.md`.

## Deferred work

- **Rebuild behavior capture and templates — deferred.** Derive a
  cross-interface method and scanner-safe templates from current tests. Owner:
  the repository that runs the pilot. Route: start with one Web implementation.
  Verify TUI and CLI lessons in their owning repositories. Sources mapped:
  `_tbd/ocr-container-docs/process/behavior-e2e-capture.md`,
  `_tbd/ocr-container-docs/process/behavior-e2e-gotchas.md`,
  `_tbd/ocr-container-docs/templates/behavior-flows.md`, and
  `_tbd/ocr-container-docs/templates/behavior-unit-spec.md`.
- **Pilot docgraph-native documentation and UI inventories — deferred.** Keep
  the inventory-first idea, but use current docgraph metadata and a reduced UI
  contract. Owner: the first repository that requests a pilot. Route: prove one
  inventory and one UI contract. Only then propose a workspace standard.
  Sources mapped: `_tbd/ocr-container-docs/process/document-existing-repo.md`,
  `_tbd/ocr-container-docs/process/ui-definition.md`,
  `_tbd/ocr-container-docs/templates/repo-documentation-inventory.md`, and
  `_tbd/ocr-container-docs/templates/ui-unit-definition.md`.
- **Refresh notifications and operational visibility — deferred.** Evaluate a
  low-risk notification loop, cross-tool configuration sync, and
  provider-neutral cost visibility. Owner: workspace tooling, not pdomain-ops.
  Route: start with a needs assessment against current Codex and Claude tools.
  Do not revive the old ctask data model. Sources mapped:
  `_tbd/ocr-container-docs/research/2026-05-21-workspace-agent-tooling-audit.md`
  and
  `_tbd/ocr-container-docs/archive/plans/2026-05-17-cost-dashboard-redesign.md`.
- **Benchmark OCR, HTR, and dewarp alternatives — deferred.** Compare
  PP-OCRv5 ONNX, HTR engines, historical datasets, and selected dewarp options
  with the shipped DocTR, Tesseract, textline-disparity, and UVDoc baseline.
  Owner: pdomain-book-tools and the OCR training repositories. Route: before
  adoption, require dataset-license review and reproducible metrics. Evidence:
  current dispatch is documented in
  [batched OCR dispatch](../architecture/batched-ocr-dispatch.md). Sources
  mapped:
  `_tbd/ocr-container-docs/research/2026-06-02-ocr-engine-landscape-and-training-datasets.md`
  and `_tbd/ocr-container-docs/research/dewarp/docunet-benchmark.md`.
- **Publish a current project update — deferred.** Replace the unfinished
  pd-* announcement with verified names, install paths, measured quality, and
  current hosted-inference intent. Owner: CT or the project communications
  owner. Route: draft from current repositories and reproducible measurements.
  Source mapped: `_tbd/ocr-container-docs/archive/research/update-post.md`.
- **Finish optional platform and remote adapters on demand — deferred.** Keep
  Windows and macOS packaging, RemotePageStore, managed persistence, Modal,
  shared-container dispatch, and hosted deployment deferred until a consumer
  commits to them. Owner: pdomain-ops owns its protocol seams. Packaging or
  hosted owners own their implementations. Evidence: local scope and explicit
  unsupported seams are documented in
  [batched OCR dispatch](../architecture/batched-ocr-dispatch.md) and
  [page lifecycle and storage](../architecture/page-lifecycle-and-storage.md).
- **Validate product-specific roadmap residue — deferred.** Check current code
  and governed issue reports for open-in-labeler links, PageRecord replacement
  of manifest bridges, simple-GUI managed deployment, missing shared UI
  components, and platform or real-engine coverage. Owner: the affected product
  repository. Route: copy only confirmed gaps into that repository's intent map.
- **Reassess semantic and scheduled review assistance — deferred.** Consider
  semantic review or scheduled cross-repo convention audits only if installed
  plugins leave a measured gap. Owner: workspace tooling. Route: measure the
  unmet need before writing a replacement design.

## Rejected directions

- **Parallel archive tree — rejected.** Retired docs are reduced into durable
  architecture, decisions, and residual intent instead of moved under
  `docs/archive/`.
- **Persistent coding-bot and ship-issue system — rejected.** Do not revive the
  custom daemon, rolling WIP branch, state and cost databases, or unattended
  PAT-driven runner. Current practice uses worktrees, plugins, session-scoped
  agents, and human integration. Owner: workspace automation. Route: retain
  only its threat-model and human-gate rationale. Require a new design if a
  concrete need returns.
- **GitHub issue synchronization — rejected.** Do not mirror or synchronize
  governed issue reports into GitHub Issues. Repository-local issue documents
  are the only work-tracking authority. A future read-only export requires a
  new owner-approved design and must not create a second status source.
- **Full historical UI schema as a workspace standard — rejected.** Do not
  require the complete state-matrix, interaction-ID, behavior-ID, and Claude
  Design schema without a successful current pilot. Owner: shared UI process.
  Route: the reduced pilot above is the only retained intent. Draft sources
  mapped: `_tbd/ocr-container-docs/process/ui-definition.md` and
  `_tbd/ocr-container-docs/templates/ui-unit-definition.md`.

## Blocked (waiting on)

- **Cross-repo release, SHA, and static-security policy — blocked.** Active
  repositories implement many gates, but their release workflows differ. The
  historical universal release-ci claim is false. Owner: workspace release
  maintainers. Blocker: first inventory every active and legacy repo. An owner
  must then decide on required uniformity. Sources mapped:
  `_tbd/ocr-container-docs/plans/2026-06-01-sha-pinning-enforcement.md`,
  `_tbd/ocr-container-docs/process/python-release-standard.md`,
  `_tbd/ocr-container-docs/process/static-testing.md`, and
  `_tbd/ocr-container-docs/archive/plans/2026-05-17-legacy-minimal-scope-strict-linting.md`.
- **External phone-access infrastructure — blocked.** Repository evidence
  cannot confirm current Tailscale, SSH, Termux, tmux, ACL, or credential state.
  Owner: CT. Blocker: inspect the live host, tailnet, and phone. Route: if the
  infrastructure is active, write a current secret-safe runbook. Otherwise,
  retire the old material. Sources mapped:
  `_tbd/ocr-container-docs/archive/plans/2026-05-14-phone-terminal-access.md`
  and
  `_tbd/ocr-container-docs/archive/specs/2026-05-14-phone-terminal-access-design.md`.
- **Unavailable legacy and external repositories — blocked.** The current
  workspace cannot verify remaining work in se-llm-skills or pd-png-optimizer.
  Owner: each repository owner. Blocker: source access and an owner-confirmed
  lifecycle. Sources mapped:
  `_tbd/ocr-container-docs/archive/plans/2026-05-17-se-llm-skills-strict-linting.md`
  and
  `_tbd/ocr-container-docs/archive/plans/2026-05-17-pd-png-optimizer-strict-linting.md`.

## Needs owner decision

- **Legacy bot workspace support.** Decide whether `/srv/bot-workspaces`, bot
  slots, and related devcontainer permissions still serve current automation.
  Owner: CT and devcontainer maintainers. Evidence: some Makefiles retain the
  filesystem support. The claude-bot, ctask, and ship-issue protocol is stale.
  Source mapped: `_tbd/ocr-container-docs/process/bot-workspaces.md`.
- **Codex persistence runbook.** Decide whether Codex state still needs an
  owner-maintained backup and restore procedure. Owner: CT and devcontainer
  maintainers. Evidence: `/home/vscode/.codex` remains relevant, but the old
  volume, workspace, and scripts are obsolete. Source mapped:
  `_tbd/ocr-container-docs/runbooks/codex-devcontainer-persistence.md`.

## Open issues

- [`docs/issues/README.md`](../issues/README.md) is the canonical issue index.
  It records no open reports.

## Legacy-unverified sweep

<!-- needs-owner-review resolved as active: docs/process/lint-deviations.md; the catalog is reconciled against current source. -->
