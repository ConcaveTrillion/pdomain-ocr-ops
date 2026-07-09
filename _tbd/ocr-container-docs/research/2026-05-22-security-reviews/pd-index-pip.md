# pdomain-index-pip Deep Review and Security Scan

Date: 2026-05-22

Repo: `ConcaveTrillion/pdomain-index-pip`

## Verification

- `python3 -m py_compile scripts/regen_index.py` passed.
- `scripts/regen_index.py` dry-run generated a temporary simple index with 22 distribution assets.
- `bandit -r scripts -f json` reported three low-severity subprocess findings: B404, B607, and B603.

## Findings

### 1. Medium security/docs: consumer docs create dependency-confusion risk

Evidence:
- `README.md:17-21` recommends `--extra-index-url`.
- `README.md:27-30` configures uv with `explicit = false`.

Impact:
Installers can resolve matching package names from PyPI if someone publishes the same `pd-*` names there, especially with higher versions. That defeats the intended release-index trust boundary.

Suggested fix:
Document uv as an explicit index and map `pd-*` packages to it with `tool.uv.sources`. For pip, avoid `--extra-index-url` where possible or require constraints/hash pins for the private package names.

Issue filed: https://github.com/ConcaveTrillion/pdomain-index-pip/issues/16

### 2. Medium code/ci: asset fetch failures silently deploy an incomplete index

Evidence:
- `scripts/regen_index.py:96-98` catches any `CalledProcessError` from `gh release view`, prints a warning, and skips that tag.

Impact:
Transient GitHub API, auth, or rate-limit failures can remove a release's files from the generated Pages artifact. Installs can fail until a later successful rebuild.

Suggested fix:
Re-raise by default. Only skip narrowly identified deleted/not-found releases, and consider retry/backoff for transient failures.

Issue filed: https://github.com/ConcaveTrillion/pdomain-index-pip/issues/17

### 3. Medium docs: published index URL appears stale after repo rename

Evidence:
- `.github/workflows/regen.yml:70-76` refers to `pdomain-index-pip`.
- `README.md:11-12`, `README.md:17-21`, and `README.md:27-30` still document `https://concavetrillion.github.io/pd-index/simple/`.

Impact:
Users can copy a dead or stale index URL, causing failed installs or continued dependency on the old Pages path.

Suggested fix:
Update docs to the canonical Pages URL for `pdomain-index-pip`, or explicitly document any custom Pages path or redirect if the old path is intentional.

Issue filed: https://github.com/ConcaveTrillion/pdomain-index-pip/issues/18

### 4. Low security/code: simple index omits available distribution hash fragments

Evidence:
- `scripts/regen_index.py:125-136` renders plain asset URLs and filenames only.
- GitHub release asset metadata includes a digest field such as `sha256:<hex>`.

Impact:
Clients fetch over TLS, but the simple index does not expose PEP 503 hash fragments, so consumers cannot use index metadata for end-to-end artifact integrity checks.

Suggested fix:
Use each GitHub release asset's digest when present and append `#sha256=<hex>` to the anchor href. Add tests covering hash rendering and fallback behavior when a digest is absent.

Issue filed: https://github.com/ConcaveTrillion/pdomain-index-pip/issues/19

### 5. Low tests: no committed tests for the generator or workflow assumptions

Evidence:
- The repo has `.github/workflows/regen.yml`, docs, and `scripts/regen_index.py`, but no committed `tests/` directory or test workflow.

Impact:
Normalization, HTML escaping, asset filtering, duplicate handling, failure behavior, URL rendering, and future hash rendering can regress without detection.

Suggested fix:
Add focused unit tests with mocked `gh_json` responses plus a CI check that runs them.

Issue filed: https://github.com/ConcaveTrillion/pdomain-index-pip/issues/20

### 6. Low security/tooling: subprocess invocation relies on PATH resolution

Evidence:
- `bandit` reported B404 at `scripts/regen_index.py:17`, B607 and B603 at `scripts/regen_index.py:47-49`.
- `gh_json()` invokes `subprocess.run(["gh", *args], capture_output=True, text=True, check=True)`.

Impact:
The call does not use a shell and the arguments are static/internal, so command injection risk is low. The remaining risk is PATH hijacking in a compromised local or CI environment.

Suggested fix:
Resolve `gh` with `shutil.which("gh")`, fail if it is missing, and pass the resolved absolute path to `subprocess.run`. Keep `shell=False`.

Issue filed: https://github.com/ConcaveTrillion/pdomain-index-pip/issues/21
