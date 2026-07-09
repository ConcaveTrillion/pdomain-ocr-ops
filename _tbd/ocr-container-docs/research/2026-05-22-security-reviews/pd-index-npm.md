# pdomain-index-npm Deep Review and Security Scan

Date: 2026-05-22

Repo: `ConcaveTrillion/pdomain-index-npm`

## Verification

- `npm run build` passed.
- `npm test` passed: 8 tests.
- `npm audit --audit-level=low --json` reported 0 vulnerabilities.
- Subagent review also ran TypeScript no-emit checks and confirmed a clean working tree.

## Findings

### 1. High security: tarball-controlled package names can escape registry paths

Evidence:
- `scripts/publish.ts:151` reads `name` from the submitted tarball's `package.json`.
- `scripts/publish.ts:165` joins that package name into the packument path.
- `scripts/publish.ts:205-209` joins that package name into the tarball write path.
- `scripts/registry-layout.ts:35-47` returns raw package names as path fragments.

Impact:
A malicious or malformed tarball can choose a package name containing path traversal or unexpected path syntax and cause the publish workflow to write outside the intended `@scope/name` layout. Because the workflow commits `git add -A` from the registry checkout, this can overwrite generated site files before publishing.

Suggested fix:
Validate package names and versions before any filesystem use. Restrict package names to the intended scope, for example `@concavetrillion/<valid npm package name>`, validate semver, and resolve all write targets with a registry-root prefix check. Add regression tests for traversal names and invalid versions.

Issue filed: https://github.com/ConcaveTrillion/pdomain-index-npm/issues/10

### 2. Medium correctness: prerelease semver ordering is lexicographic

Evidence:
- `scripts/rebuild-packuments.ts:116-126` compares prerelease strings directly.
- `scripts/rebuild-packuments.ts:305-326` uses that ordering to select `latest` and prerelease dist-tags.
- `tests/test_rebuild_packuments.test.ts:80-95` covers `alpha.1` versus `alpha.2`, but not numeric width cases such as `alpha.10` versus `alpha.2`.

Impact:
Publishing `alpha.10` after `alpha.2` can leave the `alpha` dist-tag pointing at the older prerelease, so consumers install stale builds.

Suggested fix:
Use a real semver comparator or implement SemVer prerelease identifier comparison: numeric identifiers compare numerically, numeric identifiers have lower precedence than non-numeric identifiers, and dot-separated identifiers compare one segment at a time. Add tests for `alpha.2` versus `alpha.10` and mixed prerelease identifiers.

Issue filed: https://github.com/ConcaveTrillion/pdomain-index-npm/issues/11

### 3. Low tests/maintainability: `npm run smoke` points at a missing built file

Evidence:
- `package.json:20` defines `"smoke": "node dist/smoke.js"`.
- There is no `scripts/smoke.ts`; the actual smoke test is `tests/smoke/run.sh`.
- The subagent reproduced `npm run smoke --silent` failing with a missing `dist/smoke.js` module.

Impact:
Maintainers running the advertised smoke command get a false failure unrelated to registry behavior.

Suggested fix:
Change the package script to `bash tests/smoke/run.sh`, or add a real TypeScript smoke entrypoint that compiles to `dist/smoke.js`.

Issue filed: https://github.com/ConcaveTrillion/pdomain-index-npm/issues/12
