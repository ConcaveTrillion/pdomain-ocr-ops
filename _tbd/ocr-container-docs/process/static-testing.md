# Static Testing

This workspace uses per-repo `Makefile` targets for local and CI verification.
There is no shared root `Makefile` or common `.mk` include, so each repo owns
its concrete recipes while following the target names and tool policy below.

## Canonical targets

Every active repo should expose the targets that match its shape:

- `lint-check`: all code repos. Read-only formatter and linter checks.
  Must not rewrite files.
- `typecheck`: typed language repos. Static type checks such as
  `basedpyright` or `tsc --noEmit`.
- `dependency-scan`: repos with dependency manifests or lockfiles. Dependency
  vulnerability scan with Trivy.
- `security-scan`: all GitHub repos. Secret scan plus dependency scan.
- `workflow-lint`: repos with `.github/workflows/`. GitHub Actions checks
  with `zizmor` and `actionlint`.
- `trivy-scan`: repos with containers, IaC, release images, or SBOM needs.
  Broad advisory filesystem, image, or config scan. Initially non-blocking
  unless a repo has a clean baseline.
- `static-check`: all code repos. Aggregate static gate: `lint-check`,
  `typecheck`, `security-scan`, and `workflow-lint` where applicable.
- `ci`: all code repos. Full gate: `static-check`, tests, and build/package
  checks.

Repos may keep legacy aliases such as `lint` or `pre-commit-check`, but new
automation should call the canonical target names.

## Workspace Defaults

Workspace-level defaults live in `scripts/workspace-defaults.json`. The file is
declarative: it records the default CI shape that new and updated repos should
follow, but each repo still owns its concrete workflow YAML and Make targets.

For Python library repos, use the `python_library.github_actions_ci` profile:

- Keep `make ci` as the local and release preflight gate.
- Split GitHub Actions CI into separate jobs so failures are easier to read:
  `pre-commit`, `lint`, `typecheck`, `test`, and `build`.
- Run `pre-commit`, `lint`, `typecheck`, and `build` on Python 3.12.
- Run `test` as a Python matrix over 3.11, 3.12, and 3.13.
- Each job should run `make setup` before its focused target so the job is
  isolated and reproducible.

The split GitHub workflow is for faster signal and clearer failure ownership.
It does not replace `make ci`; release scripts should continue to run `make ci`
before tagging.

## Installation

Each repo's `make setup` must provision the static-testing tools used by that
repo, or verify that they are available through the repo's pinned tool manager.
Do not require contributors to install scanner binaries by hand after running
`make setup`.

Prefer one of these installation paths, in order:

1. Pin tools in `mise.toml` when the tool is available through mise/asdf and
   the repo already uses mise.
2. Pin tools in the repo's package manager when there is a native dependency:
   Python dev dependencies in `pyproject.toml`, Node dev dependencies in
   `package.json`, Rust tools through the repo's Rust toolchain.
3. Use a small `scripts/install-static-tools.sh` helper for release binaries
   that are not convenient through mise or the language package manager.
   Install into a repo-local or user-local bin directory that `make setup`
   adds to the command path.

`make setup` should install or verify only the tools that apply to the repo:

- Repos with `.github/workflows/`: `zizmor` and `actionlint`.
- All GitHub repos: `gitleaks`.
- Repos with dependency manifests or lockfiles: `trivy`.
- Repos with shell scripts: `shellcheck`.
- Repos with Dockerfiles: `hadolint`.
- Rust repos: `cargo-deny` if `cargo deny check` is part of the repo gate.

The first implementation in a repo should include version-reporting in setup
or in the scan target output, for example `trivy --version` or
`zizmor --version`. This makes CI logs reproducible when a scanner finding
changes after a tool upgrade.

Example setup shape:

```text
setup
  sync project dependencies
  install pre-commit hooks
  install or verify static-testing tools used by this repo
```

If a repo cannot pin a scanner immediately, call that out in the rollout issue
and keep the target advisory until installation is reproducible.

## Tool policy

### Workflow checks

Use both workflow analyzers for repos with GitHub Actions workflows:

- `zizmor` checks GitHub Actions security posture: dangerous triggers,
  overbroad permissions, untrusted input in scripts, and related CI/CD
  supply-chain hazards.
- `actionlint` checks workflow correctness: YAML/schema mistakes, expression
  problems, invalid matrix usage, job wiring errors, and shell snippets.

These tools are complementary. Put both under `workflow-lint` and include that
target in `static-check` for repos that have `.github/workflows/`.

### Dependency and security checks

Use Trivy as the default dependency vulnerability scanner. It reads `uv.lock`
directly, which makes it a better fit for the current Python repos than
OSV-Scanner. For repos with frontend package locks, Trivy remains the
canonical dependency-scan gate; package-manager-native audit commands such as
`pnpm audit` are advisory cross-checks during rollout, not a second mandatory
blocking scanner by default:

```text
dependency-scan
  trivy fs --scanners vuln .
```

Frontend repos that use pnpm may add a non-blocking advisory target while the
Trivy baseline is being established:

```text
dependency-scan-advisory
  trivy fs --scanners vuln .
  (cd frontend && pnpm audit --prod=false)
```

Promote `pnpm audit` into a blocking repo-local target only when Trivy misses
actionable pnpm findings that the maintainer wants enforced in CI. If promoted,
document why both scanners are needed and how duplicate findings should be
triaged.

Use `gitleaks` as the dedicated secret scanner. `security-scan` should run
`gitleaks` and `dependency-scan` once the repo has graduated to blocking mode:

```text
security-scan: dependency-scan
  gitleaks detect --source . --no-git
```

Use `trivy-scan` for broader advisory coverage: dependency vulnerabilities,
misconfigurations, secrets, licenses, SBOM generation, containers, Dockerfiles,
and Kubernetes/Terraform/config files. Keep this separate from
`dependency-scan` so broad findings do not block routine CI before a repo has a
reviewed baseline:

```text
trivy-scan
  trivy fs --scanners vuln,misconfig,secret,license .
```

OSV-Scanner is optional as a cross-check if Trivy lacks coverage for a specific
ecosystem. Do not make both Trivy and OSV mandatory blockers by default; their
findings overlap, and duplicate scanners increase triage load.

The same rule applies to package-manager-native audits (`pnpm audit`,
`npm audit`, `pip-audit`, `cargo audit`, etc.): they are useful for manual
confirmation and ecosystem-specific debugging, but the workspace default is one
blocking dependency scanner plus documented exceptions where a repo proves it
needs another.

### Language and asset checks

Use the existing strict-linting decision as the language baseline:

- Python: `ruff` read-only checks plus `basedpyright`.
- TypeScript/React: ESLint plus `tsc --noEmit`; frontend-specific checks such
  as `knip`, codegen checks, theme checks, or Storybook checks remain
  repo-specific.
- Rust: `cargo fmt --check`, `cargo clippy`, and `cargo deny check`.
- Shell scripts: `shellcheck` for `*.sh` files and executable shell scripts.
- Dockerfiles: `hadolint` where Dockerfiles are part of the repo.

If a tool does not apply to a repo, omit that target rather than adding a
placeholder that always succeeds. Aggregate targets should include only the
checks that are meaningful for the repo.

## Blocking policy

New static tools start as advisory. Do not add a fresh scanner as a blocking
`make ci` dependency on the same day it is introduced to a repo unless the scan
is already clean and the maintainer explicitly accepts the gate.

Roll out each new scanner in three phases:

1. Advisory: add a Make target that runs the tool and captures findings, but
   does not fail `ci`. In GitHub Actions, use a non-blocking step or scheduled
   workflow so findings are visible without blocking unrelated work.
2. Cleanup: review the advisory output, file issues for real findings, and
   document accepted suppressions or intentional deviations in the repo's
   `docs/conventions/lint-deviations.md` or equivalent process note.
3. Blocking: after issues are resolved or explicitly accepted, remove the
   non-blocking wrapper and include the target in `static-check` and `ci`.

Keep the eventual blocking `make ci` path fast and precise:

1. Blocking in `ci`: language lint, typecheck, secret scan, Trivy dependency
   scan, workflow lint, tests, and build/package checks.
2. Advisory until baselined: Trivy broad scans, OpenSSF Scorecard, CodeQL,
   image scans, and other high-volume security tools.
3. Promote advisory checks to blocking per repo only after the first baseline
   is reviewed and documented in that repo's `docs/conventions/lint-deviations.md`
   or equivalent process note.

OpenSSF Scorecard and CodeQL are best enabled in GitHub Actions rather than
local pre-commit. Scorecard is a repository posture signal, and CodeQL is a
semantic code-scanning signal with GitHub alerting. Both are useful, but neither
should slow every local edit loop before the workspace has baselined their
findings.

## Rollout order

Integrate this with one repo at a time:

1. Survey the repo shape: workflows, lockfiles, shell scripts, Dockerfiles,
   containers, frontend packages, and existing Make targets.
2. Run the candidate tools manually and save the result summary in the issue or
   rollout notes.
3. Add scanner installation to `make setup` or the repo's pinned tool manager.
4. Add non-blocking Make targets first:
   - `dependency-scan-advisory` or `dependency-scan` with `|| true`
   - `workflow-lint-advisory` or `workflow-lint` with `|| true`
   - `trivy-scan` as advisory by default
5. Add a scheduled or manually-triggered GitHub Actions workflow for advisory
   scans if the repo benefits from periodic visibility.
6. File issues for real findings with enough detail to reproduce the command
   and identify the affected file/package/workflow.
7. Fix or document each finding. Suppress only with a reason, owner, and revisit
   condition.
8. Flip the relevant target from advisory to blocking.
9. Add the blocking target to `static-check`, then ensure `ci` calls
   `static-check` before tests and build.

For legacy or retiring repos, keep only the low-cost gates that protect the
workspace: `gitleaks`, Trivy dependency scanning if lockfiles are present, and
workflow linting if the repo publishes or deploys from GitHub Actions.

## References

- Strict linting decision: `docs/decisions/2026-05-17-strict-linting.md`
- Original strict-linting research:
  `docs/archive/research/2026-05-17-strict-linting-stack.md`
