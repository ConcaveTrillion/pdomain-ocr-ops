# pdomain Config And Release Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix every configuration, release, versioning, PAT, and GitHub Actions issue captured in `docs/research/2026-06-03-pdomain-config-release-audit/`.

**Architecture:** Keep each `pdomain-*` repo independently releasable, but standardize the release contract: Python repos use local-script-driven `workflow_dispatch`, `pdomain-ui` uses tag-push npm release, all repos document index dispatch secrets, and all workflows have managed action pins. Remove avoidable helper actions where the workspace already has shell or first-party patterns.

**Tech Stack:** GitHub Actions, `gh` CLI, uv, hatch-vcs, pnpm/Corepack, Make, Python pytest, TypeScript/Vitest where present, markdown docs.

---

## Scope Check

This is a master remediation plan spanning independent repos. Execute it as separate subagent workstreams by repo or by concern:

- Actions/workflow standardization: all repos.
- Runtime version derivation: `pdomain-ocr-synth`, `pdomain-ocr-trainer-spa`, `pdomain-ocr-training`.
- Release blocker: `pdomain-ocr-trainer-spa`.
- Documentation drift: `pdomain-book-tools`, `pdomain-index-npm`, `pdomain-index-pip`, `pdomain-ocr-cli`, `pdomain-ocr-labeler-spa`, `pdomain-ocr-simple-gui`, `pdomain-prep-for-pgdp`.
- Release gates and assertions: `pdomain-ocr-simple-gui`, `pdomain-ui`, app repos with installers or Docker builds.

## File Structure

Create or modify these files:

- Create root policy doc: `/workspaces/ocr-container/docs/process/pdomain-release-and-index-dispatch.md`.
- Modify root audit docs:
  - `/workspaces/ocr-container/docs/research/2026-06-03-pdomain-config-release-audit/README.md`
  - `/workspaces/ocr-container/docs/research/2026-06-03-pdomain-config-release-audit/github-actions-comparison.md`
- Modify workflow action updater scripts in every repo that has one:
  - `/workspaces/ocr-container/pdomain-*/scripts/update_github_actions.py`
- Add action-updater tests in Python repos that lack them:
  - `/workspaces/ocr-container/pdomain-*/tests/test_update_github_actions.py`
- Add or update Node workflow tests:
  - `/workspaces/ocr-container/pdomain-index-npm/tests/test_workflows.test.ts`
  - `/workspaces/ocr-container/pdomain-ui/src` or existing test location for release metadata checks if package scripts already cover workflow checks; otherwise add `/workspaces/ocr-container/pdomain-ui/tests/workflows.test.ts`
- Modify workflows:
  - all `/workspaces/ocr-container/pdomain-*/.github/workflows/ci.yml`
  - selected `/workspaces/ocr-container/pdomain-*/.github/workflows/release.yml`
  - `/workspaces/ocr-container/pdomain-ocr-trainer-spa/.github/workflows/nightly.yml`
- Modify runtime version files:
  - `/workspaces/ocr-container/pdomain-ocr-synth/src/pdomain_ocr_synth/__init__.py`
  - `/workspaces/ocr-container/pdomain-ocr-trainer-spa/src/pdomain_ocr_trainer_spa/_version.py`
  - `/workspaces/ocr-container/pdomain-ocr-training/pdomain_ocr_training/__init__.py`
- Modify version tests:
  - `/workspaces/ocr-container/pdomain-ocr-synth/tests/test_package.py`
  - `/workspaces/ocr-container/pdomain-ocr-training/tests/test_package.py`
  - `/workspaces/ocr-container/pdomain-ocr-training/tests/test_torch_free_import.py`
  - create `/workspaces/ocr-container/pdomain-ocr-trainer-spa/tests/unit/test_version.py`
- Modify trainer release-source files:
  - `/workspaces/ocr-container/pdomain-ocr-trainer-spa/pyproject.toml`
  - `/workspaces/ocr-container/pdomain-ocr-trainer-spa/uv.lock`
  - `/workspaces/ocr-container/pdomain-ocr-trainer-spa/Dockerfile`
- Modify docs/runbooks:
  - `/workspaces/ocr-container/pdomain-ocr-cli/DEVELOPMENT.md`
  - `/workspaces/ocr-container/pdomain-ocr-labeler-spa/docs/runbooks/release.md`
  - `/workspaces/ocr-container/pdomain-ocr-labeler-spa/CHANGELOG.md`
  - `/workspaces/ocr-container/pdomain-ocr-simple-gui/CHANGELOG.md`
  - create `/workspaces/ocr-container/pdomain-ocr-simple-gui/docs/runbooks/release.md`
  - `/workspaces/ocr-container/pdomain-prep-for-pgdp/DEVELOPMENT.md`
  - `/workspaces/ocr-container/pdomain-book-tools/CHANGELOG.md` or release-note policy doc
  - `/workspaces/ocr-container/pdomain-index-pip/README.md`
  - `/workspaces/ocr-container/pdomain-index-npm/README.md`

### Shared Decisions For Execution

- Keep Python package releases dispatch-only. Do not add tag-push publish triggers to Python repos unless the user changes this decision.
- Add `push: branches: [master]` CI to every repo where CI currently runs only on PRs.
- Add `concurrency: { group: ci-${{ github.ref }}, cancel-in-progress: true }` to every non-index CI workflow that lacks it.
- Keep `astral-sh/setup-uv` as an explicit allowed third-party action.
- Replace `softprops/action-gh-release`, `pnpm/action-setup`, `jdx/mise-action`, and avoidable `actions/github-script` usage where equivalent shell/first-party steps exist.

## Task 1: Create Central Release And Index Dispatch Policy

**Files:**
- Create: `/workspaces/ocr-container/docs/process/pdomain-release-and-index-dispatch.md`
- Modify: `/workspaces/ocr-container/docs/README.md`
- Modify: each repo release doc listed in the file structure when linking policy

- [ ] **Step 1: Create the policy doc**

Create `/workspaces/ocr-container/docs/process/pdomain-release-and-index-dispatch.md` with this content:

```markdown
# pdomain Release And Index Dispatch Policy

## Release Channels

Python package repos publish wheels and sdists as GitHub Release assets. The self-hosted `pdomain-index-pip` Pages site indexes those assets. These repos do not use PyPI, `TWINE_USERNAME`, `TWINE_PASSWORD`, or PyPI trusted publishing.

The `pdomain-ui` package publishes a GitHub Release tarball. The self-hosted `pdomain-index-npm` Pages site indexes that tarball. It does not use `NPM_TOKEN` or `NODE_AUTH_TOKEN` for registry publishing.

The index repos publish tooling releases as GitHub Releases and regenerate GitHub Pages. Their repo metadata versions may stay `0.0.0`; their release version is the git tag.

## Release Triggers

Python package repos use local release scripts as the only supported publish path:

```bash
make release-patch
make release-minor
make release-major
```

Those scripts run local preflight checks, create an annotated `vX.Y.Z` tag, push `main` and the tag, then dispatch `.github/workflows/release.yml` with the tag input.

`pdomain-ui` uses tag-push release because the package version in `package.json` is committed by its release script before tagging. The release workflow must assert that `package.json` version equals the pushed tag.

## Dispatch Secret

Publisher repos notify index repos with `secrets.PDOMAIN_INDEX_DISPATCH`.

Use a fine-grained GitHub PAT with:

- Resource owner: `pdomain`
- Repository access: only the target index repo, either `pdomain-index-pip` or `pdomain-index-npm`
- Repository permissions:
  - Contents: Read-only
  - Metadata: Read-only
  - Actions: Read-only
  - Administration: No access
  - Pull requests: No access
  - Issues: No access
- Endpoint required: `POST /repos/pdomain/<index-repo>/dispatches`

If the secret is absent or the dispatch fails, release workflows must warn and continue. The index repo scheduled regen is the fallback.

## GitHub Actions Policy

All workflow `uses:` entries must be pinned to immutable commit SHAs with adjacent version comments.

Allowed third-party actions:

- `astral-sh/setup-uv`, until the workspace standardizes a first-party shell install path for uv.

Avoid these actions when a shell or first-party equivalent exists:

- `softprops/action-gh-release`; use `gh release create`.
- `pnpm/action-setup`; use `actions/setup-node` plus pinned Corepack activation.
- `jdx/mise-action`; use explicit setup steps unless the workflow documents mise-only behavior.
- `actions/github-script`; use `gh` CLI for GitHub API operations unless JavaScript execution is required.

Each repo's `scripts/update_github_actions.py` must fail if any workflow has an unmanaged `uses:` entry.
```

- [ ] **Step 2: Link policy from root docs index**

Modify `/workspaces/ocr-container/docs/README.md` under `process/` entries:

```markdown
- `process/pdomain-release-and-index-dispatch.md` - pdomain release channels,
  index dispatch PAT permissions, and GitHub Actions policy.
```

- [ ] **Step 3: Verify doc links**

Run:

```bash
python - <<'PY'
from pathlib import Path

paths = [
    Path("/workspaces/ocr-container/docs/process/pdomain-release-and-index-dispatch.md"),
    Path("/workspaces/ocr-container/docs/README.md"),
]
for path in paths:
    text = path.read_text()
    assert "pdomain-release-and-index-dispatch" in text or path.name == "pdomain-release-and-index-dispatch.md"
print("release policy docs linked")
PY
```

Expected: `release policy docs linked`

- [ ] **Step 4: Commit**

```bash
git -C /workspaces/ocr-container add docs/process/pdomain-release-and-index-dispatch.md docs/README.md
git -C /workspaces/ocr-container commit -m "docs: add pdomain release and dispatch policy"
```

## Task 2: Add Managed Action Verification To Every Action Updater

**Files:**
- Modify: `/workspaces/ocr-container/pdomain-*/scripts/update_github_actions.py`
- Add or modify: `/workspaces/ocr-container/pdomain-*/tests/test_update_github_actions.py`
- Modify: `/workspaces/ocr-container/pdomain-index-npm/tests/test_workflows.test.ts`
- Modify or add: `/workspaces/ocr-container/pdomain-ui/tests/workflows.test.ts`

- [ ] **Step 1: Write failing Python tests in one representative Python repo**

In `/workspaces/ocr-container/pdomain-ops/tests/test_update_github_actions.py`, add:

```python
from pathlib import Path

import pytest

from scripts import update_github_actions


def test_detects_unmanaged_workflow_action(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        "name: ci\njobs:\n  ci:\n    steps:\n      - uses: example/not-managed@abc123\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="example/not-managed"):
        update_github_actions.verify_managed_actions(workflows)


def test_accepts_local_workflow_call(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "release.yml").write_text(
        "jobs:\n  regen:\n    uses: ./.github/workflows/regen.yml\n",
        encoding="utf-8",
    )

    update_github_actions.verify_managed_actions(workflows)
```

- [ ] **Step 2: Run the representative test and verify it fails**

Run:

```bash
cd /workspaces/ocr-container/pdomain-ops
uv run pytest tests/test_update_github_actions.py -q
```

Expected before implementation: failure importing `verify_managed_actions` or no module if the test file did not exist before.

- [ ] **Step 3: Implement managed-action verification in the representative script**

In `/workspaces/ocr-container/pdomain-ops/scripts/update_github_actions.py`, replace `MANAGED_ACTIONS` with:

```python
MANAGED_ACTIONS = (
    "actions/attest-build-provenance",
    "actions/cache",
    "actions/checkout",
    "actions/configure-pages",
    "actions/deploy-pages",
    "actions/download-artifact",
    "actions/setup-node",
    "actions/setup-python",
    "actions/upload-artifact",
    "actions/upload-pages-artifact",
    "astral-sh/setup-uv",
)
```

Add these functions below `update_pyproject_uv_version`:

```python
USES_PATTERN = re.compile(r"(?m)^\s*uses:\s*([^@\s#]+)(?:@[^\s#]+)?")


def workflow_action_names(path: Path) -> set[str]:
    """Return non-local action names referenced by one workflow file."""
    text = path.read_text(encoding="utf-8")
    names: set[str] = set()
    for match in USES_PATTERN.finditer(text):
        name = match.group(1)
        if name.startswith("./"):
            continue
        names.add(name)
    return names


def verify_managed_actions(workflow_dir: Path = WORKFLOW_DIR) -> None:
    """Fail when workflow files reference actions outside MANAGED_ACTIONS."""
    managed = set(MANAGED_ACTIONS)
    unmanaged: dict[str, list[str]] = {}
    for path in sorted(workflow_dir.glob("*.yml")):
        for name in sorted(workflow_action_names(path) - managed):
            unmanaged.setdefault(name, []).append(str(path.relative_to(ROOT)))
    if unmanaged:
        details = ", ".join(
            f"{name} in {'/'.join(paths)}" for name, paths in sorted(unmanaged.items())
        )
        raise ValueError(f"unmanaged workflow actions: {details}")
```

Then add this as the first line inside `update_github_actions()`:

```python
    verify_managed_actions(workflow_dir)
```

- [ ] **Step 4: Run the representative test and verify it passes**

Run:

```bash
cd /workspaces/ocr-container/pdomain-ops
uv run pytest tests/test_update_github_actions.py -q
```

Expected: all tests in `tests/test_update_github_actions.py` pass.

- [ ] **Step 5: Roll the same Python updater code to every repo with `scripts/update_github_actions.py`**

Run this inspection command first:

```bash
find /workspaces/ocr-container/pdomain-* -path '*/scripts/update_github_actions.py' -type f | sort
```

Expected: list of updater scripts. For each listed script, apply the same `MANAGED_ACTIONS`, `USES_PATTERN`, `workflow_action_names()`, `verify_managed_actions()`, and `update_github_actions()` changes from Step 3.

- [ ] **Step 6: Add equivalent tests to Python repos with pytest**

For each Python repo that has `tests/`, create or update `tests/test_update_github_actions.py` with the exact two tests from Step 1, changing only the import if the repo test style already imports scripts differently. Use this command to find targets:

```bash
find /workspaces/ocr-container/pdomain-* -maxdepth 2 -type d -name tests | sort
```

Expected: target test directories print.

- [ ] **Step 7: Add Node workflow action test**

In `/workspaces/ocr-container/pdomain-index-npm/tests/test_workflows.test.ts`, add:

```ts
import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, test } from 'vitest'

const managedActions = new Set([
  'actions/checkout',
  'actions/configure-pages',
  'actions/deploy-pages',
  'actions/download-artifact',
  'actions/setup-node',
  'actions/upload-artifact',
  'actions/upload-pages-artifact',
  'astral-sh/setup-uv',
])

describe('workflow action policy', () => {
  test('every non-local workflow action is managed', () => {
    const workflowDir = join(process.cwd(), '.github', 'workflows')
    const unmanaged: string[] = []

    for (const file of readdirSync(workflowDir).filter((name) => name.endsWith('.yml'))) {
      const text = readFileSync(join(workflowDir, file), 'utf8')
      for (const match of text.matchAll(/^\s*uses:\s*([^@\s#]+)(?:@[^\s#]+)?/gm)) {
        const action = match[1]
        if (action.startsWith('./')) {
          continue
        }
        if (!managedActions.has(action)) {
          unmanaged.push(`${file}: ${action}`)
        }
      }
    }

    expect(unmanaged).toEqual([])
  })
})
```

- [ ] **Step 8: Run action policy tests in representative repos**

Run:

```bash
cd /workspaces/ocr-container/pdomain-ops && uv run pytest tests/test_update_github_actions.py -q
cd /workspaces/ocr-container/pdomain-index-npm && npm test -- --run tests/test_workflows.test.ts
```

Expected: both commands pass.

- [ ] **Step 9: Commit**

```bash
git -C /workspaces/ocr-container add pdomain-*/scripts/update_github_actions.py pdomain-*/tests/test_update_github_actions.py pdomain-index-npm/tests/test_workflows.test.ts
git -C /workspaces/ocr-container commit -m "ci: enforce managed workflow actions"
```

## Task 3: Replace Avoidable Third-Party And Helper Actions

**Files:**
- Modify: `/workspaces/ocr-container/pdomain-ui/.github/workflows/release.yml`
- Modify: `/workspaces/ocr-container/pdomain-ocr-trainer-spa/.github/workflows/nightly.yml`
- Modify: SPA workflows using `pnpm/action-setup`

- [ ] **Step 1: Replace `softprops/action-gh-release` in `pdomain-ui`**

In `/workspaces/ocr-container/pdomain-ui/.github/workflows/release.yml`, replace the `softprops/action-gh-release` step with:

```yaml
      - name: Publish GitHub Release
        env:
          GH_TOKEN: ${{ github.token }}
          RELEASE_TAG: ${{ github.ref_name }}
        run: |
          set -euo pipefail
          shopt -s nullglob
          files=(dist/*.tgz)
          if [ ${#files[@]} -ne 1 ]; then
            echo "::error::expected exactly one npm tarball under dist/"
            ls -la dist/
            exit 1
          fi
          gh release create "$RELEASE_TAG" "${files[@]}" \
            --generate-notes \
            --verify-tag
```

- [ ] **Step 2: Replace `actions/github-script` in trainer nightly**

In `/workspaces/ocr-container/pdomain-ocr-trainer-spa/.github/workflows/nightly.yml`, replace the issue-creation step with:

```yaml
      - name: File nightly failure issue
        if: failure()
        env:
          GH_TOKEN: ${{ github.token }}
          NIGHTLY_DATE: ${{ github.run_started_at }}
          RUN_URL: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
        run: |
          set -euo pipefail
          gh issue create \
            --title "[nightly] slow tests failed ${NIGHTLY_DATE%%T*}" \
            --label nightly-failure \
            --body "Nightly slow tests failed. Run: ${RUN_URL}"
```

- [ ] **Step 3: Remove `jdx/mise-action` if nightly only needs Python, Node, and uv**

In `/workspaces/ocr-container/pdomain-ocr-trainer-spa/.github/workflows/nightly.yml`, replace:

```yaml
      - uses: jdx/mise-action@1648a7812b9aeae629881980618f079932869151  # v4.0.1
```

with:

```yaml
      - uses: actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e  # v6.4.0
        with:
          node-version: "24"
      - name: Enable pnpm via corepack
        run: corepack enable && corepack prepare pnpm@11.3.0 --activate
```

- [ ] **Step 4: Replace `pnpm/action-setup` with Corepack in workflows**

For each workflow using `pnpm/action-setup`, delete the `pnpm/action-setup` step and ensure the adjacent `actions/setup-node` step is followed by:

```yaml
      - name: Enable pnpm via corepack
        run: corepack enable && corepack prepare pnpm@11.3.0 --activate
```

If a repo intentionally uses pnpm 11 without patch pinning, use:

```yaml
      - name: Enable pnpm via corepack
        run: corepack enable && corepack prepare pnpm@11 --activate
```

Do not use `pnpm@latest`.

- [ ] **Step 5: Verify removed actions**

Run:

```bash
rg -n "softprops/action-gh-release|pnpm/action-setup|jdx/mise-action|actions/github-script" /workspaces/ocr-container/pdomain-*/.github/workflows
```

Expected: no matches, unless a worker intentionally kept `jdx/mise-action` with a workflow comment explaining the mise-only behavior.

- [ ] **Step 6: Run workflow static checks**

Run in repos that expose actionlint or static checks:

```bash
cd /workspaces/ocr-container/pdomain-index-npm && make static-check
cd /workspaces/ocr-container/pdomain-index-pip && make static-check
cd /workspaces/ocr-container/pdomain-ui && make lint-check
```

Expected: commands pass. If `pdomain-ui` lacks workflow linting in `make lint-check`, rely on the grep verification plus GitHub workflow syntax review in code review.

- [ ] **Step 7: Commit**

```bash
git -C /workspaces/ocr-container add pdomain-*/.github/workflows
git -C /workspaces/ocr-container commit -m "ci: replace avoidable workflow helper actions"
```

## Task 4: Standardize CI Triggers And Concurrency

**Files:**
- Modify: `/workspaces/ocr-container/pdomain-*/.github/workflows/ci.yml`

- [ ] **Step 1: Update CI triggers**

For every repo whose `ci.yml` has only:

```yaml
on:
  pull_request:
    branches: [master]
```

replace it with:

```yaml
on:
  push:
    branches: [master]
  pull_request:
    branches: [master]
```

- [ ] **Step 2: Add concurrency where missing**

After `permissions:` or after `on:` if the workflow has no `permissions:` block, add:

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

Do not add canceling concurrency to `regen.yml` Pages deployments; queued Pages deploys must not cancel in-flight deploys.

- [ ] **Step 3: Verify every CI workflow has push and PR**

Run:

```bash
python - <<'PY'
from pathlib import Path

missing = []
for path in sorted(Path("/workspaces/ocr-container").glob("pdomain-*/.github/workflows/ci.yml")):
    text = path.read_text()
    if "push:" not in text or "pull_request:" not in text:
        missing.append(str(path))
if missing:
    raise SystemExit("\n".join(missing))
print("all ci workflows include push and pull_request")
PY
```

Expected: `all ci workflows include push and pull_request`

- [ ] **Step 4: Verify concurrency**

Run:

```bash
python - <<'PY'
from pathlib import Path

missing = []
for path in sorted(Path("/workspaces/ocr-container").glob("pdomain-*/.github/workflows/ci.yml")):
    text = path.read_text()
    if "concurrency:" not in text or "cancel-in-progress: true" not in text:
        missing.append(str(path))
if missing:
    raise SystemExit("\n".join(missing))
print("all ci workflows include canceling concurrency")
PY
```

Expected: `all ci workflows include canceling concurrency`

- [ ] **Step 5: Commit**

```bash
git -C /workspaces/ocr-container add pdomain-*/.github/workflows/ci.yml
git -C /workspaces/ocr-container commit -m "ci: run pdomain CI on push and cancel stale runs"
```

## Task 5: Fix `pdomain-ocr-trainer-spa` Release Source Blocker

**Files:**
- Modify: `/workspaces/ocr-container/pdomain-ocr-trainer-spa/pyproject.toml`
- Modify: `/workspaces/ocr-container/pdomain-ocr-trainer-spa/uv.lock`
- Modify: `/workspaces/ocr-container/pdomain-ocr-trainer-spa/Dockerfile`

- [ ] **Step 1: Remove absolute local uv source from `pyproject.toml`**

In `/workspaces/ocr-container/pdomain-ocr-trainer-spa/pyproject.toml`, remove the committed absolute source entry:

```toml
pdomain-ops = { path = "/workspaces/ocr-container/pdomain-ops", editable = true }
```

If `[tool.uv.sources]` becomes empty, remove the empty section.

- [ ] **Step 2: Regenerate lockfile against registry sources**

Run:

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv lock
```

Expected: `uv.lock` no longer records `pdomain-ops` as an editable local path.

- [ ] **Step 3: Verify no absolute workspace source remains**

Run:

```bash
rg -n 'path = "/workspaces|editable = true|pdomain-ocr-ops' /workspaces/ocr-container/pdomain-ocr-trainer-spa/pyproject.toml /workspaces/ocr-container/pdomain-ocr-trainer-spa/uv.lock /workspaces/ocr-container/pdomain-ocr-trainer-spa/Dockerfile
```

Expected before Dockerfile cleanup: only Dockerfile matches.

- [ ] **Step 4: Fix Dockerfile local dependency wording**

In `/workspaces/ocr-container/pdomain-ocr-trainer-spa/Dockerfile`, remove the local path-source copy/install assumption. Replace stale `pdomain-ocr-ops` wording with `pdomain-ops`, and install from the lockfile using registry sources:

```dockerfile
RUN uv sync --frozen --no-dev
```

If the Dockerfile currently copies a sibling repo, delete that `COPY` line and any matching path-source rewrite.

- [ ] **Step 5: Run trainer setup and CI**

Run:

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv sync --group dev
make ci
```

Expected: `make ci` passes without requiring `/workspaces/ocr-container/pdomain-ops` as an absolute source.

- [ ] **Step 6: Commit**

```bash
git -C /workspaces/ocr-container add pdomain-ocr-trainer-spa/pyproject.toml pdomain-ocr-trainer-spa/uv.lock pdomain-ocr-trainer-spa/Dockerfile
git -C /workspaces/ocr-container commit -m "fix(trainer-spa): remove local pdomain-ops release source"
```

## Task 6: Standardize Runtime Version Derivation

**Files:**
- Modify: `/workspaces/ocr-container/pdomain-ocr-synth/src/pdomain_ocr_synth/__init__.py`
- Modify: `/workspaces/ocr-container/pdomain-ocr-trainer-spa/src/pdomain_ocr_trainer_spa/_version.py`
- Modify: `/workspaces/ocr-container/pdomain-ocr-training/pdomain_ocr_training/__init__.py`
- Modify tests listed in the file structure

- [ ] **Step 1: Update `pdomain-ocr-synth` version code**

Replace `/workspaces/ocr-container/pdomain-ocr-synth/src/pdomain_ocr_synth/__init__.py` with:

```python
"""pdomain OCR synthetic data tools."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pdomain-ocr-synth")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
```

- [ ] **Step 2: Update `pdomain-ocr-synth` test**

Ensure `/workspaces/ocr-container/pdomain-ocr-synth/tests/test_package.py` contains:

```python
"""Smoke tests for the package metadata."""

from pdomain_ocr_synth import __all__, __version__


def test_version_is_defined() -> None:
    assert __version__
    assert isinstance(__version__, str)
    assert __version__ != "0.0.1"


def test_public_api_exports_version() -> None:
    assert "__version__" in __all__
```

- [ ] **Step 3: Update trainer SPA version code**

Replace `/workspaces/ocr-container/pdomain-ocr-trainer-spa/src/pdomain_ocr_trainer_spa/_version.py` with:

```python
"""Runtime package version."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pdomain-ocr-trainer-spa")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
```

- [ ] **Step 4: Add trainer SPA version test**

Create `/workspaces/ocr-container/pdomain-ocr-trainer-spa/tests/unit/test_version.py`:

```python
from pdomain_ocr_trainer_spa._version import __version__


def test_runtime_version_is_not_hard_coded_alpha() -> None:
    assert __version__
    assert isinstance(__version__, str)
    assert __version__ != "0.1.0a0"
```

- [ ] **Step 5: Update training version code**

In `/workspaces/ocr-container/pdomain-ocr-training/pdomain_ocr_training/__init__.py`, replace:

```python
__version__ = "0.2.1"
```

with:

```python
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pdomain-ocr-training")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
```

Keep existing public exports and imports around it intact.

- [ ] **Step 6: Update training tests**

Replace exact-version assertions in `/workspaces/ocr-container/pdomain-ocr-training/tests/test_package.py` and `/workspaces/ocr-container/pdomain-ocr-training/tests/test_torch_free_import.py` with:

```python
assert pdomain_ocr_training.__version__
assert isinstance(pdomain_ocr_training.__version__, str)
assert pdomain_ocr_training.__version__ != "0.2.1"
```

- [ ] **Step 7: Run version tests**

Run:

```bash
cd /workspaces/ocr-container/pdomain-ocr-synth && uv run pytest tests/test_package.py tests/test_cli.py::test_version -q
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa && uv run pytest tests/unit/test_version.py -q
cd /workspaces/ocr-container/pdomain-ocr-training && uv run pytest tests/test_package.py tests/test_torch_free_import.py -q
```

Expected: all selected tests pass.

- [ ] **Step 8: Verify hard-coded versions are gone**

Run:

```bash
rg -n '__version__ = "0\\.0\\.1"|__version__ = "0\\.1\\.0a0"|__version__ = "0\\.2\\.1"' /workspaces/ocr-container/pdomain-ocr-synth /workspaces/ocr-container/pdomain-ocr-trainer-spa /workspaces/ocr-container/pdomain-ocr-training
```

Expected: no matches.

- [ ] **Step 9: Commit**

```bash
git -C /workspaces/ocr-container add pdomain-ocr-synth/src/pdomain_ocr_synth/__init__.py pdomain-ocr-synth/tests/test_package.py pdomain-ocr-trainer-spa/src/pdomain_ocr_trainer_spa/_version.py pdomain-ocr-trainer-spa/tests/unit/test_version.py pdomain-ocr-training/pdomain_ocr_training/__init__.py pdomain-ocr-training/tests/test_package.py pdomain-ocr-training/tests/test_torch_free_import.py
git -C /workspaces/ocr-container commit -m "fix: derive runtime versions from package metadata"
```

## Task 7: Add Release Assertions And GitHub-Side Gates

**Files:**
- Modify: `/workspaces/ocr-container/pdomain-ui/.github/workflows/release.yml`
- Modify: `/workspaces/ocr-container/pdomain-ocr-simple-gui/.github/workflows/release.yml`
- Review and modify app release workflows with installer or Docker assumptions

- [ ] **Step 1: Add tag/package assertion to `pdomain-ui` release**

In `/workspaces/ocr-container/pdomain-ui/.github/workflows/release.yml`, after dependency install and before build, add:

```yaml
      - name: Assert tag matches package version
        run: |
          set -euo pipefail
          package_version=$(node -p "require('./package.json').version")
          tag_version="${GITHUB_REF_NAME#v}"
          if [ "$package_version" != "$tag_version" ]; then
            echo "::error::package.json version $package_version does not match tag $GITHUB_REF_NAME"
            exit 1
          fi
```

- [ ] **Step 2: Add release CI job to `pdomain-ocr-simple-gui`**

In `/workspaces/ocr-container/pdomain-ocr-simple-gui/.github/workflows/release.yml`, add a `release-ci` job before `publish`:

```yaml
  release-ci:
    name: release CI
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0
          ref: ${{ github.event.inputs.tag }}
          persist-credentials: false
      - uses: astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b  # v8.1.0
        with:
          version: "0.11.16"
      - uses: actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e  # v6.4.0
        with:
          node-version: "24"
      - name: Enable pnpm via corepack
        run: corepack enable && corepack prepare pnpm@11.3.0 --activate
      - name: Run release CI gate
        run: make ci-slow
```

Then set the publish job dependency:

```yaml
    needs: [release-ci]
```

- [ ] **Step 3: Add artifact count assertion to Python app release workflows**

In Python app release workflows that build only wheels, before `gh release create`, add:

```bash
shopt -s nullglob
files=(dist/*.whl)
if [ ${#files[@]} -eq 0 ]; then
  echo "::error::no wheel artifacts found under dist/"
  exit 1
fi
```

Use this for wheel-only apps: `pdomain-ocr-labeler-spa`, `pdomain-ocr-trainer-spa`, `pdomain-prep-for-pgdp`, and `pdomain-ocr-simple-gui` if its build is wheel-only after inspection.

- [ ] **Step 4: Run workflow syntax grep**

Run:

```bash
rg -n "Assert tag matches package version|release-ci|no wheel artifacts found" /workspaces/ocr-container/pdomain-ui/.github/workflows/release.yml /workspaces/ocr-container/pdomain-ocr-simple-gui/.github/workflows/release.yml /workspaces/ocr-container/pdomain-ocr-labeler-spa/.github/workflows/release.yml /workspaces/ocr-container/pdomain-ocr-trainer-spa/.github/workflows/release.yml /workspaces/ocr-container/pdomain-prep-for-pgdp/.github/workflows/release.yml
```

Expected: assertions and release CI additions print.

- [ ] **Step 5: Commit**

```bash
git -C /workspaces/ocr-container add pdomain-ui/.github/workflows/release.yml pdomain-ocr-simple-gui/.github/workflows/release.yml pdomain-ocr-labeler-spa/.github/workflows/release.yml pdomain-ocr-trainer-spa/.github/workflows/release.yml pdomain-prep-for-pgdp/.github/workflows/release.yml
git -C /workspaces/ocr-container commit -m "ci: strengthen release workflow assertions"
```

## Task 8: Fix Docker Version Defaults In App Repos

**Files:**
- Modify: `/workspaces/ocr-container/pdomain-ocr-labeler-spa/Makefile`
- Modify: `/workspaces/ocr-container/pdomain-prep-for-pgdp/Makefile`
- Modify: Dockerfiles only if build args are missing or docs are stale

- [ ] **Step 1: Set Docker version from git in labeler Makefile**

In `/workspaces/ocr-container/pdomain-ocr-labeler-spa/Makefile`, update the `docker-build` recipe so it passes `VERSION`:

```make
docker-build:
	docker build \
		--build-arg VERSION=$$(git describe --tags --always --dirty) \
		-t $(DOCKER_IMAGE):$(DOCKER_TAG) .
```

- [ ] **Step 2: Set Docker version from git in prep Makefile**

In `/workspaces/ocr-container/pdomain-prep-for-pgdp/Makefile`, update the `docker-build` recipe so it passes `VERSION`:

```make
docker-build:
	docker build \
		--build-arg VERSION=$$(git describe --tags --always --dirty) \
		-t $(DOCKER_IMAGE):$(DOCKER_TAG) .
```

- [ ] **Step 3: Verify Docker build args are wired**

Run:

```bash
rg -n -- '--build-arg VERSION=|ARG VERSION' /workspaces/ocr-container/pdomain-ocr-labeler-spa/Makefile /workspaces/ocr-container/pdomain-ocr-labeler-spa/Dockerfile /workspaces/ocr-container/pdomain-prep-for-pgdp/Makefile /workspaces/ocr-container/pdomain-prep-for-pgdp/Dockerfile
```

Expected: each repo has both `ARG VERSION` in Dockerfile and `--build-arg VERSION=` in Makefile.

- [ ] **Step 4: Commit**

```bash
git -C /workspaces/ocr-container add pdomain-ocr-labeler-spa/Makefile pdomain-prep-for-pgdp/Makefile
git -C /workspaces/ocr-container commit -m "fix: pass package version into app docker builds"
```

## Task 9: Update Stale Release Docs And Changelog Policy

**Files:**
- Modify docs listed in the file structure under docs/runbooks and changelogs

- [ ] **Step 1: Update `pdomain-ocr-cli/DEVELOPMENT.md`**

Replace stale release text with:

```markdown
## Release

Releases are driven by `make release-patch`, `make release-minor`, or `make release-major`.
The release script requires clean, up-to-date `main`, runs `make ci-slow`, creates an
annotated `vX.Y.Z` tag, pushes `main` and the tag, then dispatches
`.github/workflows/release.yml` with the tag input.

`pdomain-ops` and `pdomain-book-tools` resolve from the self-hosted pdomain pip index
for release builds. Do not commit path-based sibling sources for release.
```

- [ ] **Step 2: Update `pdomain-ocr-labeler-spa/docs/runbooks/release.md`**

Replace artifact claims with:

```markdown
The release workflow builds a wheel with `make build` and attaches `dist/*.whl` to the
GitHub Release. It does not attach an sdist unless `make build` is changed to produce one.
After release creation, the workflow dispatches `pdomain-index-pip`; if dispatch fails,
the index scheduled regen is the fallback.
```

- [ ] **Step 3: Update `pdomain-ocr-simple-gui/CHANGELOG.md`**

Replace the obsolete blocked-publish note with:

```markdown
Release publishing is active. Releases are tag-derived via `hatch-vcs`, published as
GitHub Release artifacts, and indexed by `pdomain-index-pip`.
```

- [ ] **Step 4: Create simple GUI release runbook**

Create `/workspaces/ocr-container/pdomain-ocr-simple-gui/docs/runbooks/release.md`:

```markdown
# Release Runbook

Use only the local release targets:

```bash
make release-patch
make release-minor
make release-major
```

The release script verifies clean, up-to-date `main`, runs release preflight, creates an
annotated semver tag, pushes `main` and the tag, and dispatches the release workflow.

The release workflow builds GitHub Release artifacts and dispatches `pdomain-index-pip`
with `PDOMAIN_INDEX_DISPATCH`. If dispatch is unavailable, the scheduled index regen is
the fallback.
```

- [ ] **Step 5: Update `pdomain-prep-for-pgdp/DEVELOPMENT.md`**

Replace push/tag and container-publish claims with:

```markdown
Releases are workflow-dispatch based and must be started by `make release-patch`,
`make release-minor`, or `make release-major`. Tag pushes alone are not the supported
publish path. This repo does not publish a container image from GitHub Actions.
```

- [ ] **Step 6: Update index repo README release-note policy**

In both `/workspaces/ocr-container/pdomain-index-pip/README.md` and `/workspaces/ocr-container/pdomain-index-npm/README.md`, add:

```markdown
## Tooling Releases

This repo's own releases are tag-only tooling releases. Package versions indexed by
this repo come from publisher GitHub Release assets, not this repo's metadata version.
GitHub-generated release notes are canonical for tooling releases.
```

- [ ] **Step 7: Update book-tools changelog policy**

If maintaining historical changelog entries is not being done immediately, add this at the top of `/workspaces/ocr-container/pdomain-book-tools/CHANGELOG.md`:

```markdown
> Release notes after v0.14.1 are generated by GitHub Releases unless this changelog is
> updated as part of a release checklist.
```

- [ ] **Step 8: Verify stale phrases are gone**

Run:

```bash
rg -n "blocked pending index|manual push|push/tag|container build on tag|dist/\\*\\.tar\\.gz" /workspaces/ocr-container/pdomain-ocr-cli/DEVELOPMENT.md /workspaces/ocr-container/pdomain-ocr-labeler-spa/docs/runbooks/release.md /workspaces/ocr-container/pdomain-ocr-simple-gui/CHANGELOG.md /workspaces/ocr-container/pdomain-prep-for-pgdp/DEVELOPMENT.md
```

Expected: no matches for stale release claims.

- [ ] **Step 9: Commit**

```bash
git -C /workspaces/ocr-container add pdomain-ocr-cli/DEVELOPMENT.md pdomain-ocr-labeler-spa/docs/runbooks/release.md pdomain-ocr-simple-gui/CHANGELOG.md pdomain-ocr-simple-gui/docs/runbooks/release.md pdomain-prep-for-pgdp/DEVELOPMENT.md pdomain-index-pip/README.md pdomain-index-npm/README.md pdomain-book-tools/CHANGELOG.md
git -C /workspaces/ocr-container commit -m "docs: align pdomain release documentation"
```

## Task 10: Fix Dependency Refresh Coverage

**Files:**
- Modify: `/workspaces/ocr-container/pdomain-ocr-cli/scripts/update-pdomain-deps.sh`
- Modify: `/workspaces/ocr-container/pdomain-ui/codegen.versions.json` only if dependency bump is part of the same PR
- Modify: `/workspaces/ocr-container/pdomain-ops/Makefile`

- [ ] **Step 1: Add `pdomain-ops` to CLI dependency updater**

In `/workspaces/ocr-container/pdomain-ocr-cli/scripts/update-pdomain-deps.sh`, ensure both runtime pdomain dependencies are refreshed:

```bash
packages=(
  "pdomain-book-tools"
  "pdomain-ops"
)

for package in "${packages[@]}"; do
  latest=$(curl -fsSL "https://pdomain.github.io/pdomain-index-pip/simple/${package}/" \
    | python scripts/latest_pdomain_version.py)
  uv add "${package}>=${latest}"
done
```

If the script uses a different parser helper, keep that helper and add `pdomain-ops` to the package list.

- [ ] **Step 2: Guard `pdomain-ops` dependency upgrade from local mode**

In `/workspaces/ocr-container/pdomain-ops/Makefile`, make `upgrade-deps` fail in local mode:

```make
upgrade-deps:
	@if [ -f .pdomain-local-mode ] || [ -f .pdomain-dev-local ]; then \
		echo "ERROR: leave local dependency mode before upgrade-deps"; \
		exit 1; \
	fi
	uv lock --upgrade
	uv sync --group dev
```

- [ ] **Step 3: Normalize local marker names in ops docs/scripts**

Replace `.pdomain-dev-local` references with `.pdomain-local-mode` where possible. Keep a read-compatibility check for `.pdomain-dev-local` in Makefile guards until existing worktrees are migrated.

- [ ] **Step 4: Verify updater references**

Run:

```bash
rg -n "pdomain-book-tools|pdomain-ops|pdomain-local-mode|pdomain-dev-local" /workspaces/ocr-container/pdomain-ocr-cli/scripts/update-pdomain-deps.sh /workspaces/ocr-container/pdomain-ops/Makefile
```

Expected: CLI updater references both packages; ops Makefile checks both marker names.

- [ ] **Step 5: Commit**

```bash
git -C /workspaces/ocr-container add pdomain-ocr-cli/scripts/update-pdomain-deps.sh pdomain-ops/Makefile
git -C /workspaces/ocr-container commit -m "fix: align pdomain dependency refresh guards"
```

## Task 11: Final Cross-Repo Verification

**Files:**
- Modify audit docs if findings are resolved:
  - `/workspaces/ocr-container/docs/research/2026-06-03-pdomain-config-release-audit/README.md`
  - `/workspaces/ocr-container/docs/research/2026-06-03-pdomain-config-release-audit/github-actions-comparison.md`

- [ ] **Step 1: Verify no avoidable actions remain**

Run:

```bash
rg -n "softprops/action-gh-release|pnpm/action-setup|jdx/mise-action|actions/github-script" /workspaces/ocr-container/pdomain-*/.github/workflows
```

Expected: no matches, except a documented `jdx/mise-action` exception if one was retained.

- [ ] **Step 2: Verify no absolute workspace uv source remains**

Run:

```bash
rg -n 'path = "/workspaces/ocr-container|editable = true' /workspaces/ocr-container/pdomain-*/pyproject.toml /workspaces/ocr-container/pdomain-*/uv.lock
```

Expected: no release config matches. Local-only docs may mention local paths outside `pyproject.toml` and `uv.lock`.

- [ ] **Step 3: Verify hard-coded runtime versions are gone**

Run:

```bash
rg -n '__version__ = "0\\.0\\.1"|__version__ = "0\\.1\\.0a0"|__version__ = "0\\.2\\.1"' /workspaces/ocr-container/pdomain-ocr-synth /workspaces/ocr-container/pdomain-ocr-trainer-spa /workspaces/ocr-container/pdomain-ocr-training
```

Expected: no matches.

- [ ] **Step 4: Run representative CI suites**

Run:

```bash
cd /workspaces/ocr-container/pdomain-ops && make ci
cd /workspaces/ocr-container/pdomain-ocr-training && make ci
cd /workspaces/ocr-container/pdomain-ocr-synth && make ci
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa && make ci
cd /workspaces/ocr-container/pdomain-ui && make ci
```

Expected: all selected representative suites pass. If a suite needs unavailable local GPU, registry, or browser resources, record the exact failure and run the narrower non-resource command that matches that repo's CI workflow.

- [ ] **Step 5: Update audit docs with remediation status**

In `/workspaces/ocr-container/docs/research/2026-06-03-pdomain-config-release-audit/README.md`, add:

```markdown
## Remediation Status

The implementation plan for this audit is `docs/superpowers/plans/2026-06-03-pdomain-config-release-remediation.md`.

When the plan is executed, update this section with commit SHAs and any intentionally retained exceptions.
```

In `/workspaces/ocr-container/docs/research/2026-06-03-pdomain-config-release-audit/github-actions-comparison.md`, add retained exceptions under `Keep Or Remove Decision Notes`.

- [ ] **Step 6: Commit**

```bash
git -C /workspaces/ocr-container add docs/research/2026-06-03-pdomain-config-release-audit/README.md docs/research/2026-06-03-pdomain-config-release-audit/github-actions-comparison.md
git -C /workspaces/ocr-container commit -m "docs: record pdomain remediation plan status"
```

## Self-Review

Spec coverage:

- Config/release process: Tasks 1, 4, 7, 9, 11.
- Version process: Tasks 5, 6, 8.
- GitHub PAT and index dispatch: Tasks 1 and 9.
- GitHub Actions differences and avoidable third-party/helper actions: Tasks 2, 3, 4, 11.
- Repo-specific drift from the audit: Tasks 5 through 10.

Placeholder scan:

- No placeholder markers or unspecified implementation steps are intentionally present.
- Each code-changing task includes concrete snippets and verification commands.

Type and command consistency:

- Python version helper snippets use `importlib.metadata.version`.
- GitHub Release snippets use `gh release create` consistently.
- pnpm setup snippets use `actions/setup-node` plus Corepack.
