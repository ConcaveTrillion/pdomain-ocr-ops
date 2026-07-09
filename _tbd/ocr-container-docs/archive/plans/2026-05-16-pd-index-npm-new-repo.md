---
status: complete
synced: 2026-05-17
milestone: 3
repo: ConcaveTrillion/ocr-container-meta
---

# pdomain-index-npm — new repo (static npm registry on GitHub Pages)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a brand-new repo `ConcaveTrillion/pdomain-index-npm` that serves a Verdaccio-style static npm registry from GitHub Pages, so `pd-*` TypeScript packages (starting with `@concavetrillion/pdomain-ui`) can be `npm install`ed by every downstream SPA without going through public npmjs.org. This is the npm sibling of the existing `pd-index` (pip) and mirrors its "wheels live in GitHub Releases, the index is just metadata" approach as closely as the npm registry protocol allows.

**Architecture:** A static site under `https://concavetrillion.github.io/pdomain-index-npm/` whose directory layout obeys the parts of the npm registry HTTP API that `npm install` actually exercises against a registry serving its responses pre-rendered:
- `GET /<package>` (URL-encoded scope, e.g. `/@concavetrillion%2Fpd-ui`) returns the **packument** JSON — a document with `name`, `dist-tags`, `versions{<v>: { name, version, dist: { tarball, shasum, integrity } } }`, `time`.
- `GET /<package>/-/<filename>.tgz` returns the tarball bytes themselves.
This is the same shape Verdaccio writes to disk under `storage/` when its `web` UI generates a static snapshot, and the same shape PEP 503 would look like if it were npm.
Publishing is a GitHub Action: a publisher repo (e.g. pdomain-ui's release workflow in plan #6) dispatches a `pd-npm-publish` event into pdomain-index-npm carrying the `.tgz` (or a download URL for it). The action checks out a `gh-pages` branch, drops the tarball into `@<scope>/<name>/-/<name>-<version>.tgz`, recomputes the packument JSON (merging the new version into existing `versions{}` + `dist-tags.latest`), commits, and the GitHub Pages site serves the result.
Consumers add one line to their `.npmrc`:
```
@concavetrillion:registry=https://concavetrillion.github.io/pdomain-index-npm/
```
After which `npm install @concavetrillion/pdomain-ui` resolves through the static site exactly as if it were a real registry, while every other package continues to resolve from npmjs.org. This mirrors the pip side where every `pd-*` `pyproject.toml` carries the `[[tool.uv.index]] name = "pd-index" url = "..."` block.

**Tech Stack:** Static site (no runtime), GitHub Pages, GitHub Actions (publish workflow), Node 20 + a tiny TypeScript publish script (`scripts/publish.ts`) using Node stdlib only — no Verdaccio dep, no npm packages beyond `typescript` + `@types/node` for dev. The publish script does: tarball validation (parse `package.json` from inside the `.tgz`), shasum/integrity hash computation, packument JSON merge, atomic file write. A smoke-test fixture package `@concavetrillion/test-package@0.0.1` (literally a hello-world) lives in the repo so CI can prove the round-trip end-to-end on every PR.

**Scope independence:** This plan is independent of every other Phase 1 plan **except** pdomain-ui's publish step (plan #6) depends on pdomain-index-npm being ready. It does NOT depend on plan #3 (pd-index → pdomain-index-pip rename), plan #1 (pdomain-book-tools ReviewMetadata / schemas.emit), or plan #2 (pdomain-ocr-ops). Work can begin immediately and ship in parallel with all of those.

**Out of scope (handled elsewhere):**
- Publisher-side tooling inside pdomain-ui (the npm pack + dispatch step in pdomain-ui's release workflow) — that's **plan #6** for pdomain-ui.
- Renaming the existing pip index — that's **plan #3** for pd-index → pdomain-index-pip.
- Consumer-side `.npmrc` wiring inside specific apps (labeler-spa, pgdp-prep, future trainer-spa / simple-gui) — that lands when those apps migrate to depend on `@concavetrillion/pdomain-ui`, in their respective Phase-2 migration plans.

**Working directory for all commands once the repo is cloned:** `/workspaces/ocr-container/pdomain-index-npm/`. Until the repo exists locally, the scaffold tasks run in a temp dir then push to a freshly-created GitHub repo (see Task 1).

---

## Task 1: Create the GitHub repo + initial scaffold {#create-the-github-repo-initial-scaffold}

**Files (in a new repo `ConcaveTrillion/pdomain-index-npm`):**
- Create: `README.md`
- Create: `LICENSE` (MIT, matching every other pd-* repo)
- Create: `.gitignore`
- Create: `package.json` (dev-only deps, no runtime)
- Create: `tsconfig.json`
- Create: `.editorconfig`

**Why:** Every pd-* repo follows the same bootstrap (LICENSE + README + .gitignore + dev metadata) so contributors and tooling find a uniform shape. Doing this as Task 1 prevents the metadata-invention failure mode logged in workspace memory (`feedback_no_invented_metadata`): we copy author/email/org from existing pd-* peer repos rather than guessing.

**What:**

- [ ] **Step 1: Create the empty GitHub repo**

```bash
gh repo create ConcaveTrillion/pdomain-index-npm \
  --public \
  --description "Self-hosted static npm registry (Verdaccio-style) for the pd-* family of repos. Sibling of pdomain-index-pip." \
  --homepage "https://concavetrillion.github.io/pdomain-index-npm/" \
  --disable-wiki
```

Expected: repo exists at `https://github.com/ConcaveTrillion/pdomain-index-npm`.

- [ ] **Step 2: Clone into the workspace**

```bash
cd /workspaces/ocr-container/
gh repo clone ConcaveTrillion/pdomain-index-npm
cd pdomain-index-npm
```

Verify `.git/config` `user.name = CT` and `user.email = concavetrillion@gmail.com`; copy from a peer pd-* repo if absent. **Do NOT invent these values** — per workspace memory, always copy from existing pd-* peer `.git/config`.

- [ ] **Step 3: Write the LICENSE**

Copy `LICENSE` byte-for-byte from `/workspaces/ocr-container/pd-index/LICENSE` (MIT, ConcaveTrillion copyright). Update year if needed.

- [ ] **Step 4: Write `.gitignore`**

```gitignore
# Build output
dist/
_site/
*.tgz

# Node
node_modules/
.npm/

# Editor / OS
.DS_Store
.vscode/
.idea/
*.swp

# Agent memory (per workspace convention; never tracked inside pd-* trees)
.claude/
```

- [ ] **Step 5: Write `package.json`**

```json
{
  "name": "pdomain-index-npm-tools",
  "version": "0.0.0",
  "private": true,
  "description": "Build tooling for the pdomain-index-npm static registry. The published artifacts live under gh-pages, not in this package.",
  "author": "CT <concavetrillion@gmail.com>",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/ConcaveTrillion/pdomain-index-npm.git"
  },
  "engines": {
    "node": ">=20"
  },
  "scripts": {
    "build": "tsc -p tsconfig.json",
    "publish-pkg": "node dist/publish.js",
    "rebuild-packuments": "node dist/rebuild-packuments.js",
    "smoke": "node dist/smoke.js"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "typescript": "^5.4.0"
  }
}
```

- [ ] **Step 6: Write `tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "Node16",
    "moduleResolution": "Node16",
    "outDir": "dist",
    "rootDir": "scripts",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "declaration": false,
    "sourceMap": true
  },
  "include": ["scripts/**/*.ts"]
}
```

- [ ] **Step 7: Write the initial `README.md`**

Modeled on `/workspaces/ocr-container/pd-index/README.md` but for npm:
- One-paragraph description (self-hosted Verdaccio-style index for `pd-*` npm packages, sibling of `pdomain-index-pip`).
- URL: `https://concavetrillion.github.io/pdomain-index-npm/`.
- "How consumers use it" section showing the `.npmrc` line.
- "How publishers push to it" section showing the `workflow_dispatch`/`repository_dispatch` trigger shape (filled in by Task 4).
- "Versioning conventions" — packages SHOULD follow semver; pre-1.0 packages use `0.x.y-alpha.N` for incubation; once stabilized they cut a `1.0.0` and the index serves both `dist-tags.latest` and `dist-tags.alpha` lines.
- "Why not just publish to npmjs.org" mirroring the pip README's rationale.

- [ ] **Step 8: Acceptance — first commit + push**

```bash
git add LICENSE .gitignore package.json tsconfig.json README.md .editorconfig
git commit -m "chore(repo): initial scaffold

LICENSE + README + .gitignore + dev tsconfig. Repo will host a
Verdaccio-style static npm registry for @concavetrillion/* packages,
served from GitHub Pages, paired with the existing pd-index (pip)."
git push -u origin main
```

**Acceptance:** Repo cloned, `gh repo view ConcaveTrillion/pdomain-index-npm` shows the description and homepage URL; `git log --oneline` shows the initial commit; `.git/config` has correct CT identity.

---

## Task 2: Wire GitHub Pages + the `gh-pages` content branch {#wire-github-pages-the-gh-pages-content-branch}

**Files:**
- Create: `gh-pages` orphan branch with a placeholder `index.html`
- Modify: repo settings (Pages source = `gh-pages` branch, `/` root)

**Why:** The publish workflow writes registry content (packuments + tarballs) to the `gh-pages` branch; GitHub Pages serves whatever is on that branch. We bootstrap the branch with a placeholder so Pages has something to deploy before the first real publish, and so the workflow can do a no-op fast-forward instead of a from-scratch init.

**What:**

- [ ] **Step 1: Create the orphan `gh-pages` branch**

```bash
git checkout --orphan gh-pages
git rm -rf .
cat > index.html <<'HTML'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>pdomain-index-npm</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      body { font-family: system-ui, sans-serif; max-width: 720px; margin: 3rem auto; padding: 0 1rem; color: #222; }
      code { background: #f0f0f0; padding: 2px 6px; border-radius: 4px; }
      pre  { background: #f6f6f6; padding: 1rem; border-radius: 6px; overflow-x: auto; }
    </style>
  </head>
  <body>
    <h1>pdomain-index-npm</h1>
    <p>Static npm registry for the <code>@concavetrillion/*</code> scope.</p>
    <h2>Consumer setup</h2>
    <p>Add to your project's <code>.npmrc</code>:</p>
    <pre>@concavetrillion:registry=https://concavetrillion.github.io/pdomain-index-npm/</pre>
    <p>See <a href="https://github.com/ConcaveTrillion/pdomain-index-npm">the repo</a> for publishing and conventions.</p>
  </body>
</html>
HTML
git add index.html
git commit -m "chore(pages): bootstrap gh-pages with placeholder index"
git push -u origin gh-pages
git checkout main
```

- [ ] **Step 2: Enable GitHub Pages from `gh-pages` branch**

```bash
gh api -X PUT repos/ConcaveTrillion/pdomain-index-npm/pages \
  -f source.branch=gh-pages -f source.path=/
```

Wait ~60s for Pages to provision. Then:

```bash
curl -sI https://concavetrillion.github.io/pdomain-index-npm/ | head -5
```

Expected: HTTP 200 (or 301 → trailing slash) with `server: GitHub.com`. If 404, wait another minute and retry; Pages first-provision can take 2-3 minutes.

- [ ] **Step 3: Acceptance**

Browser-load `https://concavetrillion.github.io/pdomain-index-npm/` and confirm the placeholder page renders. `curl https://concavetrillion.github.io/pdomain-index-npm/index.html` returns the HTML.

**Acceptance:** Pages is live, serving the placeholder; `gh-pages` branch exists with one commit; main branch is unaffected.

---

## Task 3: Define the on-disk registry layout + write the `rebuild-packuments` script {#define-the-on-disk-registry-layout-write-the-rebui}

**Files:**
- Create: `scripts/registry-layout.ts` — types + constants describing the static layout
- Create: `scripts/rebuild-packuments.ts` — scans `packages/` and (re)generates packument JSON files
- Create: `tests/test_rebuild_packuments.mjs` — Node `node:test` based test
- Create: `docs/REGISTRY_FORMAT.md` — short reference doc + pointers to upstream specs

**Why:** Splitting layout-knowledge into a tiny module keeps the publish script (Task 4) honest — it composes Task 3's primitives instead of reinventing them. Having a `rebuild-packuments` script means the index can be regenerated from tarball state if a packument ever drifts (the safety net the pip index gets from `regen_index.py`). The format doc spares future maintainers from reverse-engineering Verdaccio's static output.

**What the layout looks like (mirrored under `gh-pages`):**

```
/                                # GitHub Pages root → https://concavetrillion.github.io/pdomain-index-npm/
  index.html                     # placeholder from Task 2
  @concavetrillion%2fpd-ui       # URL-encoded scoped package name; packument JSON
  @concavetrillion%2fpd-ui/-/pdomain-ui-0.1.0-alpha.tgz
  @concavetrillion%2fpd-ui/-/pdomain-ui-0.1.1-alpha.tgz
  @concavetrillion%2ftest-package
  @concavetrillion%2ftest-package/-/test-package-0.0.1.tgz
```

The packument document for `@concavetrillion/pdomain-ui` is JSON with shape:

```json
{
  "name": "@concavetrillion/pdomain-ui",
  "dist-tags": { "latest": "0.1.1-alpha", "alpha": "0.1.1-alpha" },
  "versions": {
    "0.1.0-alpha": {
      "name": "@concavetrillion/pdomain-ui",
      "version": "0.1.0-alpha",
      "description": "...",
      "main": "dist/index.js",
      "dist": {
        "tarball": "https://concavetrillion.github.io/pdomain-index-npm/@concavetrillion%2fpd-ui/-/pdomain-ui-0.1.0-alpha.tgz",
        "shasum": "<sha1 hex>",
        "integrity": "sha512-<base64>"
      }
    },
    "0.1.1-alpha": { "...": "..." }
  },
  "time": {
    "created":  "2026-05-17T...Z",
    "modified": "2026-05-18T...Z",
    "0.1.0-alpha": "2026-05-17T...Z",
    "0.1.1-alpha": "2026-05-18T...Z"
  }
}
```

The `dist.tarball` URL is **absolute** so `npm install` doesn't have to know the registry's base path twice. This matches Verdaccio's default static-export behavior. The publisher can override neither — the URL is recomputed by the publish script every time.

**TDD steps:**

- [ ] **Step 1: Add `node:test` smoke harness + write the failing test**

`package.json` `scripts` entry: `"test": "node --test --test-reporter=spec dist/tests/**/*.test.js"` (TS test files compile into `dist/tests/`).

Create `tests/test_rebuild_packuments.test.ts`:

```ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, writeFile, mkdir, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { rebuildPackuments } from "../scripts/rebuild-packuments.js";

async function fixtureWithTarball(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "pdomain-index-npm-"));
  const tgzDir = join(root, "@concavetrillion%2ftest-package", "-");
  await mkdir(tgzDir, { recursive: true });
  // Minimal valid .tgz containing a package.json. The rebuild script must
  // parse the tarball, NOT trust a sidecar file — that's the point.
  // (Implementation: gzip a tar containing 'package/package.json'.)
  await writeFile(join(tgzDir, "test-package-0.0.1.tgz"),
    await buildMinimalTarball({ name: "@concavetrillion/test-package", version: "0.0.1" }));
  return root;
}

test("rebuildPackuments writes a valid packument JSON next to the tarball dir", async () => {
  const root = await fixtureWithTarball();
  await rebuildPackuments({ root, baseUrl: "https://concavetrillion.github.io/pdomain-index-npm/" });
  const packumentPath = join(root, "@concavetrillion%2ftest-package");
  const doc = JSON.parse(await readFile(packumentPath, "utf8"));
  assert.equal(doc.name, "@concavetrillion/test-package");
  assert.equal(doc["dist-tags"].latest, "0.0.1");
  assert.ok(doc.versions["0.0.1"]);
  assert.match(
    doc.versions["0.0.1"].dist.tarball,
    /^https:\/\/concavetrillion\.github\.io\/pdomain-index-npm\/@concavetrillion%2ftest-package\/-\/test-package-0\.0\.1\.tgz$/,
  );
  assert.match(doc.versions["0.0.1"].dist.integrity, /^sha512-/);
  assert.match(doc.versions["0.0.1"].dist.shasum, /^[0-9a-f]{40}$/);
});

test("rebuildPackuments merges multiple versions under one packument", async () => {
  // Same fixture pattern but with both 0.0.1 and 0.0.2 .tgzs in -/
  // Assert dist-tags.latest === '0.0.2' (semver-highest non-prerelease),
  // versions has both keys, time has 'created' = earliest, 'modified' = latest.
});

test("rebuildPackuments respects prerelease ordering for dist-tags", async () => {
  // 0.1.0-alpha.1, 0.1.0-alpha.2, 0.1.0 all present
  // Expect: dist-tags.latest === '0.1.0', dist-tags.alpha === '0.1.0-alpha.2'
});
```

`buildMinimalTarball` is a test helper that uses Node's `zlib` + a minimal tar writer (no third-party tar lib — vendor a 50-line tar-write helper in `tests/_tar.ts`). The shape is exactly what `npm pack` produces: one top-level `package/` directory containing `package.json`.

- [ ] **Step 2: Run tests to confirm they fail**

```bash
npm install
npm run build
npm test
```

Expected: import of `../scripts/rebuild-packuments.js` fails (`Cannot find module`).

- [ ] **Step 3: Implement `scripts/registry-layout.ts`**

Exports:
- `encodeScopedName(name)` → `"@concavetrillion/pdomain-ui"` → `"@concavetrillion%2fpd-ui"`
- `tarballDirFor(name)` → `<encoded>/-`
- `packumentPathFor(name)` → `<encoded>` (extensionless; npm clients request the path directly)
- `tarballUrlFor(baseUrl, name, version)` → absolute URL string

- [ ] **Step 4: Implement `scripts/rebuild-packuments.ts`**

Algorithm:
1. Walk `root/@<scope>%2f<name>/-/` directories.
2. For each `.tgz` file: read it, gunzip, parse out `package/package.json` from the tar entries (vendor minimal tar reader OR use Node's experimental built-ins if stable; otherwise add `tar` from npm as a runtime dep — note: adding a runtime dep is acceptable here, the script only runs in CI, not in any pd-* consumer).
3. Compute `shasum` (SHA-1 of the tarball bytes) and `integrity` (SHA-512 base64, prefixed `sha512-`).
4. Group by package name; semver-sort the versions; pick `latest` = highest non-prerelease (fall back to highest overall if all are prereleases); per-prerelease-tag (the part before `+` after `-`, e.g. `alpha` from `0.1.0-alpha.2`) pick latest matching version.
5. Emit packument JSON to the encoded path (no extension).
6. Preserve the existing packument's `time.created` if a previous packument exists at that path (so timeline doesn't reset on every rebuild).

Public API:
```ts
export async function rebuildPackuments(opts: {
  root: string;
  baseUrl: string;       // e.g. "https://concavetrillion.github.io/pdomain-index-npm/"
  packageName?: string;  // optional: only rebuild this one packument
}): Promise<{ rebuilt: string[] }>
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
npm run build
npm test
```

Expected: all `rebuildPackuments` tests pass.

- [ ] **Step 6: Write `docs/REGISTRY_FORMAT.md`**

Short doc (one screen) covering:
- The directory layout above.
- The packument shape with pointers to:
  - npm registry HTTP spec: https://github.com/npm/registry/blob/main/docs/REGISTRY-API.md
  - Verdaccio's static-publish output as the closest existing reference.
- The intentional simplifications: no `_attachments` (we serve tarballs as static files, not as embedded base64), no `_rev`, no PUT semantics.
- The trust model: tarballs go in, the script does the integrity / shasum work — publishers don't compute hashes themselves.

- [ ] **Step 7: Commit**

```bash
git add scripts/ tests/ docs/ package.json
git commit -m "feat(registry): static layout + rebuild-packuments script

Defines the Verdaccio-style on-disk layout the gh-pages branch will
serve, plus a script that re-derives packument JSON from the tarballs
present under each <scope>/<name>/-/ directory. Backed by node:test
fixtures that build a real minimal .tgz, run the script, and assert
the packument's name / dist-tags / dist.tarball / integrity / shasum."
```

**Acceptance:**
- `npm test` passes locally.
- `docs/REGISTRY_FORMAT.md` describes the layout in one screen of prose.
- `npm run rebuild-packuments -- --root ./fixture` (where `./fixture` contains a hand-rolled `.tgz`) produces a packument file that `curl http://localhost:8000/...` (via `python -m http.server`) successfully feeds to `npm view @concavetrillion/test-package --registry http://localhost:8000/`.

---

## Task 4: Write the `publish.ts` script that adds one tarball to the index {#write-the-publishts-script-that-adds-one-tarball-t}

**Files:**
- Create: `scripts/publish.ts`
- Create: `tests/test_publish.test.ts`

**Why:** Separating "publish a single tarball" from "rebuild all packuments" is the right factoring: real publishes only need the incremental path (download the tarball, drop it in, update one packument), while `rebuild-packuments` is the safety net. The publish script is also what the GitHub Action in Task 5 calls — keeping its surface narrow (`publish --tarball <path-or-url> --root <gh-pages-checkout>`) makes the Action trivial.

**What:**

- [ ] **Step 1: Write the failing test**

`tests/test_publish.test.ts`:

```ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { publish } from "../scripts/publish.js";
import { buildMinimalTarball } from "./_tar.js";

test("publish drops the tarball into the right encoded path", async () => {
  const root = await mkdtemp(join(tmpdir(), "pdomain-index-npm-pub-"));
  await mkdir(root, { recursive: true });
  const tarballBytes = await buildMinimalTarball({
    name: "@concavetrillion/pdomain-ui",
    version: "0.1.0-alpha",
  });
  const localTarball = join(root, "_input", "pdomain-ui-0.1.0-alpha.tgz");
  await mkdir(join(root, "_input"), { recursive: true });
  await writeFile(localTarball, tarballBytes);

  const result = await publish({
    root,
    tarballPath: localTarball,
    baseUrl: "https://concavetrillion.github.io/pdomain-index-npm/",
  });

  assert.equal(result.packageName, "@concavetrillion/pdomain-ui");
  assert.equal(result.version, "0.1.0-alpha");
  const tgzAtRest = await readFile(
    join(root, "@concavetrillion%2fpd-ui", "-", "pdomain-ui-0.1.0-alpha.tgz"),
  );
  assert.equal(tgzAtRest.byteLength, tarballBytes.byteLength);
  const packument = JSON.parse(
    await readFile(join(root, "@concavetrillion%2fpd-ui"), "utf8"),
  );
  assert.equal(packument["dist-tags"].latest, "0.1.0-alpha"); // only version, so it's latest
  assert.equal(packument["dist-tags"].alpha, "0.1.0-alpha");
});

test("publish refuses to overwrite an existing version", async () => {
  // Set up a packument with version 0.1.0 already present.
  // Call publish() with another 0.1.0 tarball.
  // Expect: throws PublishConflictError with a message naming the version.
});

test("publish accepts a URL for the tarball, downloads it, then publishes", async () => {
  // Stand up a tiny http server serving the tarball bytes.
  // Call publish({ tarballUrl: 'http://127.0.0.1:N/pkg.tgz', ... }).
  // Same assertions as the first test.
});
```

- [ ] **Step 2: Run to confirm failure**

```bash
npm run build && npm test
```

Expected: tests fail (`publish` not exported).

- [ ] **Step 3: Implement `scripts/publish.ts`**

```ts
export interface PublishOptions {
  root: string;
  tarballPath?: string;
  tarballUrl?: string;
  baseUrl: string;
}
export interface PublishResult {
  packageName: string;
  version: string;
  packumentPath: string;
  tarballRestingPath: string;
}
export class PublishConflictError extends Error {}

export async function publish(opts: PublishOptions): Promise<PublishResult> { ... }
```

Algorithm:
1. If `tarballUrl`, download to a temp file via `fetch()` (Node 20 native).
2. Parse `package/package.json` out of the tarball → `{ name, version }`.
3. Compute integrity + shasum.
4. Check existing packument; if `versions[version]` exists with a different shasum, throw `PublishConflictError`. (Idempotent re-publish of the **same** bytes is allowed — useful for retry-after-flake.)
5. Move tarball into `<root>/<encoded>/-/<name>-<version>.tgz`.
6. Call `rebuildPackuments({ root, baseUrl, packageName })` to refresh just that packument.

- [ ] **Step 4: Pass the tests**

```bash
npm run build && npm test
```

Expected: 3 publish tests + 3 rebuild tests all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/publish.ts tests/test_publish.test.ts
git commit -m "feat(publish): scripts/publish.ts — drop one .tgz into the registry

Accepts either --tarball <path> or --tarball-url <url>. Validates the
package.json inside the tarball; computes integrity + shasum; refuses
to overwrite an existing version with different bytes (idempotent
same-bytes re-publish is allowed); delegates packument refresh to
scripts/rebuild-packuments."
```

**Acceptance:** `npm test` green for both rebuild and publish scripts; refusal-to-overwrite path covered.

---

## Task 5: GitHub Action — `publish.yml` (workflow_dispatch + repository_dispatch) {#github-action-publishyml-workflowdispatch-reposito}

**Files:**
- Create: `.github/workflows/publish.yml`

**Why:** The publish step has to run inside CI (not in a publisher repo) so that pushes to `gh-pages` use the standard `GITHUB_TOKEN` of pdomain-index-npm and don't require any cross-repo write PAT. Publisher repos (pdomain-ui) dispatch a `repository_dispatch` event with the tarball URL — they don't need write access to pdomain-index-npm. The action is the only thing that mutates `gh-pages`.

**What:**

- [ ] **Step 1: Write the workflow file**

`.github/workflows/publish.yml`:

```yaml
name: Publish package to pdomain-index-npm

on:
  workflow_dispatch:
    inputs:
      tarball_url:
        description: "URL to the .tgz to publish (typically a GitHub Release asset URL)"
        required: true
        type: string
  repository_dispatch:
    types: [pd-npm-publish]

concurrency:
  # Serialize all publishes; the gh-pages branch is mutated.
  group: pdomain-index-npm-publish
  cancel-in-progress: false

permissions:
  contents: write        # to push to gh-pages
  pages: write           # to deploy
  id-token: write        # for the Pages deploy action

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout main (tooling)
        uses: actions/checkout@v4
        with:
          ref: main
          path: tooling
      - name: Checkout gh-pages (registry content)
        uses: actions/checkout@v4
        with:
          ref: gh-pages
          path: registry
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: Build tooling
        working-directory: tooling
        run: |
          npm ci
          npm run build
      - name: Resolve tarball URL
        id: url
        run: |
          if [ "${{ github.event_name }}" = "repository_dispatch" ]; then
            echo "url=${{ github.event.client_payload.tarball_url }}" >> "$GITHUB_OUTPUT"
          else
            echo "url=${{ inputs.tarball_url }}" >> "$GITHUB_OUTPUT"
          fi
      - name: Publish
        working-directory: tooling
        env:
          TARBALL_URL: ${{ steps.url.outputs.url }}
          REGISTRY_ROOT: ${{ github.workspace }}/registry
          BASE_URL: https://concavetrillion.github.io/pdomain-index-npm/
        run: |
          node dist/publish.js \
            --tarball-url "$TARBALL_URL" \
            --root        "$REGISTRY_ROOT" \
            --base-url    "$BASE_URL"
      - name: Commit + push gh-pages
        working-directory: registry
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add -A
          if git diff --staged --quiet; then
            echo "No changes to commit; tarball was already present."
            exit 0
          fi
          git commit -m "publish: ${{ steps.url.outputs.url }}"
          git push origin gh-pages
```

(Pages serves from the branch automatically — no separate deploy step needed since Pages is configured for `gh-pages` branch in Task 2.)

- [ ] **Step 2: Smoke-test the workflow with a synthetic tarball**

Manual run, from a workstation:

```bash
# Build a stub @concavetrillion/test-package-0.0.1.tgz locally
mkdir -p /tmp/test-pkg/package
cat > /tmp/test-pkg/package/package.json <<'JSON'
{ "name": "@concavetrillion/test-package", "version": "0.0.1", "description": "Smoke test for pdomain-index-npm.", "main": "index.js" }
JSON
echo "module.exports = 'pdomain-index-npm smoke ok';" > /tmp/test-pkg/package/index.js
( cd /tmp/test-pkg && tar -czf /tmp/test-package-0.0.1.tgz package/ )

# Upload the .tgz as a release asset on the pdomain-index-npm repo itself
# (for the smoke test — real publishes upload to the publishing repo).
gh release create smoke-test --repo ConcaveTrillion/pdomain-index-npm \
  --title "Smoke test fixture" --notes "Used by Task 5 smoke test only."
gh release upload smoke-test /tmp/test-package-0.0.1.tgz \
  --repo ConcaveTrillion/pdomain-index-npm

# Get the download URL
URL=$(gh release view smoke-test --repo ConcaveTrillion/pdomain-index-npm \
  --json assets --jq '.assets[0].url')

# Trigger the workflow
gh workflow run publish.yml --repo ConcaveTrillion/pdomain-index-npm \
  -f tarball_url="$URL"
```

Watch the run with `gh run watch`. Expected: green; the `gh-pages` branch gains the test-package files.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/publish.yml
git commit -m "ci(publish): GitHub Action — publish.yml

Triggered by workflow_dispatch (manual smoke) or repository_dispatch
type=pd-npm-publish (from publisher repos like pdomain-ui). Checks out main
for tooling, gh-pages for content, runs scripts/publish.ts with the
tarball URL, commits + pushes gh-pages. Concurrency group serializes
all publishes so packument writes don't race."
```

**Acceptance:** Workflow file exists, syntax-valid (CI lints YAML), and the manual smoke-test run succeeds (gh-pages branch shows the new files after the action completes).

---

## Task 6: End-to-end smoke test — install the published package from a clean directory {#end-to-end-smoke-test-install-the-published-packag}

**Files:**
- Create: `tests/smoke/run.sh`
- Create: `tests/smoke/README.md`

**Why:** The whole point of the index is that `npm install` works against it the same way `npm install` works against npmjs.org. A test that publishes a stub package and then `npm install`s it from a fresh, empty directory is the only test that actually proves the index speaks npm's wire protocol correctly. Without this, every other test is just unit-testing our own implementation.

**What:**

- [ ] **Step 1: Write the smoke script**

`tests/smoke/run.sh`:

```bash
#!/usr/bin/env bash
# End-to-end smoke test for pdomain-index-npm.
#
# Preconditions:
#   - The smoke-test fixture @concavetrillion/test-package@0.0.1 has been
#     published to the index (run Task 5's smoke-test once, manually).
#   - You have curl and npm installed.
#
# What it does:
#   1. curl the packument JSON, validate shape.
#   2. curl the tarball URL the packument points at, validate it's a real tgz.
#   3. Create a brand-new throwaway directory.
#   4. Write a minimal .npmrc pointing the @concavetrillion scope at the index.
#   5. `npm install @concavetrillion/test-package@0.0.1` from that dir.
#   6. require() the installed package; assert it logs the smoke string.
#
# Exit non-zero on any step's failure.

set -euo pipefail

REGISTRY="${REGISTRY:-https://concavetrillion.github.io/pdomain-index-npm/}"
PACKAGE="@concavetrillion/test-package"
VERSION="0.0.1"
ENC="@concavetrillion%2ftest-package"

echo "::group::Fetch + validate packument"
PACKUMENT_URL="${REGISTRY}${ENC}"
PACKUMENT=$(curl -fsSL "$PACKUMENT_URL")
echo "$PACKUMENT" | jq -e '.name == "@concavetrillion/test-package"' >/dev/null
echo "$PACKUMENT" | jq -e ".versions.\"$VERSION\".dist.tarball | startswith(\"https://\")" >/dev/null
TARBALL_URL=$(echo "$PACKUMENT" | jq -r ".versions.\"$VERSION\".dist.tarball")
echo "OK: packument shape valid; tarball URL = $TARBALL_URL"
echo "::endgroup::"

echo "::group::Fetch + validate tarball"
TGZ=$(mktemp --suffix=.tgz)
curl -fsSL "$TARBALL_URL" -o "$TGZ"
file "$TGZ" | grep -q "gzip compressed" || { echo "Tarball is not gzip!"; exit 1; }
tar -tzf "$TGZ" | grep -q "^package/package.json$" || { echo "Tarball missing package.json!"; exit 1; }
echo "OK: tarball is real npm-shape gzipped tar"
echo "::endgroup::"

echo "::group::Install via npm from a clean directory"
WORK=$(mktemp -d)
pushd "$WORK" >/dev/null
cat > .npmrc <<NPM
@concavetrillion:registry=${REGISTRY}
NPM
npm init -y >/dev/null
npm install --no-audit --no-fund "${PACKAGE}@${VERSION}"
node -e "console.log(require('${PACKAGE}'))" | grep -q "pdomain-index-npm smoke ok"
popd >/dev/null
rm -rf "$WORK"
echo "OK: clean-dir npm install resolved through pdomain-index-npm"
echo "::endgroup::"

echo "SMOKE PASSED"
```

- [ ] **Step 2: Wire the smoke into CI**

Append a new `smoke` job to `.github/workflows/publish.yml` (or a separate `smoke.yml` triggered on push to main and on schedule):

```yaml
  smoke:
    needs: publish    # in publish.yml — runs after every publish
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: Wait for Pages to update
        run: sleep 60   # Pages publish lag — empirically ~30-60s after gh-pages push
      - name: Run smoke
        run: bash tests/smoke/run.sh
```

Note the `sleep 60` is a deliberate (small, documented) sleep because GitHub Pages does NOT expose a "publish complete" webhook. Adjust upward if flaky.

- [ ] **Step 3: Document for humans**

`tests/smoke/README.md` — one screen explaining:
- What the smoke proves end-to-end.
- How to run it locally (`bash tests/smoke/run.sh`).
- What to do if it fails (Pages lag vs. real index bug vs. tarball missing).

- [ ] **Step 4: Run the smoke manually**

```bash
chmod +x tests/smoke/run.sh
./tests/smoke/run.sh
```

Expected: `SMOKE PASSED` printed; non-zero exit on any failure.

- [ ] **Step 5: Commit**

```bash
git add tests/smoke/ .github/workflows/publish.yml
git commit -m "test(smoke): end-to-end clean-dir npm install via pdomain-index-npm

Smoke script: curl packument → curl tarball → mktemp → write .npmrc →
npm install → require() the installed module. Proves the index speaks
npm wire protocol correctly. Wired into CI as a job that follows every
publish (with a 60s Pages-lag sleep)."
```

**Acceptance:** Smoke script exits 0 locally and as a CI job following the Task 5 publish.

---

## Task 7: Consumer documentation in README + `.npmrc` example {#consumer-documentation-in-readme-npmrc-example}

**Files:**
- Modify: `README.md`
- Create: `examples/consumer-.npmrc` (example file for downstream repos to copy)

**Why:** The whole point is that downstream pd-* repos (labeler-spa, pgdp-prep, future trainer-spa / simple-gui) consume `@concavetrillion/pdomain-ui` from this index. The README is the doc those repos' agents will read when they wire up consumption. Without a copy-paste-ready `.npmrc` snippet plus an explanation of the auth-free model, every consumer will reinvent the configuration.

**What:**

- [ ] **Step 1: Flesh out the README**

Replace the Task 1 README with the full content. Sections:

```markdown
# pdomain-index-npm

Self-hosted [npm registry](https://github.com/npm/registry/blob/main/docs/REGISTRY-API.md)
for the `@concavetrillion/*` scope, served as a static site from GitHub
Pages. The npm sibling of the existing [`pd-index`](https://github.com/ConcaveTrillion/pd-index)
(pip).

## URL

```
https://concavetrillion.github.io/pdomain-index-npm/
```

## How consumers use it

Add to your project's `.npmrc`:

```
@concavetrillion:registry=https://concavetrillion.github.io/pdomain-index-npm/
```

Then:

```sh
npm install @concavetrillion/pdomain-ui
```

Resolves through the static registry. Every other package continues to
resolve from npmjs.org. The registry is **read-only and unauthenticated**
— no token, no `npm login` required.

## How publishers push to it

Publisher repos trigger a `repository_dispatch` of type `pd-npm-publish`
with a `client_payload.tarball_url` pointing at the `.tgz` (typically a
GitHub Release asset URL on the publisher's own repo):

```sh
gh api repos/ConcaveTrillion/pdomain-index-npm/dispatches \
  -f event_type=pd-npm-publish \
  -f client_payload[tarball_url]="https://github.com/pdomain/pdomain-ui/releases/download/v0.1.0-alpha/pdomain-ui-0.1.0-alpha.tgz"
```

The publish workflow downloads the tarball, computes integrity + shasum,
writes it to the `gh-pages` branch, updates the package's packument, and
commits. GitHub Pages picks up the new content within ~60s.

## Versioning conventions

- Semver throughout.
- Pre-1.0 incubation: `0.X.Y-alpha[.N]`. The `alpha` dist-tag tracks the
  latest prerelease; `latest` only advances when a non-prerelease is
  published.
- Versions are immutable. Republishing the same `name@version` with
  different tarball bytes is rejected by `scripts/publish.ts`.

## Layout

See [docs/REGISTRY_FORMAT.md](docs/REGISTRY_FORMAT.md) for the on-disk
shape and the parts of the npm registry HTTP API we serve.

## Why not just publish to npmjs.org?

Same answer as the pip side. The index speaks the same wire protocol
npmjs does, so migration later is `npm publish` + dropping the `.npmrc`
line. No package-shape changes required.
```

- [ ] **Step 2: Add the example `.npmrc`**

`examples/consumer-.npmrc`:

```
# Copy this file's content into your repo's .npmrc (root or frontend/),
# OR your user-level ~/.npmrc, to pull @concavetrillion/* packages from
# the self-hosted pdomain-index-npm registry. Every other scope continues to
# resolve from npmjs.org.
@concavetrillion:registry=https://concavetrillion.github.io/pdomain-index-npm/
```

- [ ] **Step 3: Commit**

```bash
git add README.md examples/
git commit -m "docs(readme): consumer + publisher instructions; example .npmrc

README now covers: the public URL, how consumers wire .npmrc, how
publishers trigger the repository_dispatch, versioning conventions
(semver + 0.x-alpha lane), and a pointer to docs/REGISTRY_FORMAT.md
for the on-disk shape. examples/consumer-.npmrc is the copy-paste
file downstream pd-* repos drop into their frontend/."
```

**Acceptance:** README renders correctly on GitHub; copy-pasting the `.npmrc` line into a clean shell + running `npm install @concavetrillion/test-package@0.0.1` works (this is what Task 6's smoke script proves).

---

## Task 8: Workspace integration — `.gitignore` anchor + CLAUDE.md notes {#workspace-integration-gitignore-anchor-claudemd-no}

**Files (outside the new repo):**
- Modify: `/workspaces/ocr-container/.gitignore`
- Modify: `/workspaces/ocr-container/CLAUDE.md` (the workspace one)

**Why:** Every pd-* repo already gets a workspace-level `.gitignore` anchor (`/pdomain-book-tools/`, etc.) so the outer workspace doesn't accidentally track its contents. The workspace CLAUDE.md routing table doesn't currently mention any pd-index-* repos because they're agentless tooling; adding a one-line note under "Repo & release layout" prevents future agents from being surprised by the new directory.

**What:**

- [ ] **Step 1: Add the `.gitignore` anchor**

In `/workspaces/ocr-container/.gitignore`, add (alphabetized with the other `/pd-*/` anchors):

```
/pdomain-index-npm/
```

- [ ] **Step 2: Update workspace CLAUDE.md**

Open `/workspaces/ocr-container/CLAUDE.md`. Under the table of `pd-*` projects (or in a nearby paragraph about release indexes — there isn't a dedicated section yet, so adding one is fine), add a short note:

```markdown
## Release indexes (no agents; tooling-only repos)

- `pd-index` → being renamed to `pdomain-index-pip` (plan #3) — PEP 503 simple
  index for `pd-*` Python wheels.
- `pdomain-index-npm` (NEW, plan #4) — Verdaccio-style static npm registry for
  the `@concavetrillion/*` scope, hosted on GitHub Pages. First publisher
  is `pdomain-ui` (plan #6).
```

Neither index gets a dedicated subagent — both are small enough that workspace-root agent direct edits are appropriate.

- [ ] **Step 3: Commit (in the ocr-container workspace, not pdomain-index-npm)**

```bash
cd /workspaces/ocr-container/
git add .gitignore CLAUDE.md
git commit -m "chore(workspace): anchor pdomain-index-npm and note release-index repos

Adds /pdomain-index-npm/ to the workspace .gitignore so the outer repo
doesn't accidentally track its contents. CLAUDE.md gains a short
'Release indexes (no agents)' section listing both pdomain-index-pip
(post-rename) and pdomain-index-npm."
```

**Acceptance:** `git status` from `/workspaces/ocr-container/` after cloning pdomain-index-npm shows it as untracked-by-anchor (i.e., the anchor is working). Workspace CLAUDE.md mentions both indexes.

---

## Self-review checklist (for the engineer; do this before declaring done)

- [ ] Repo author/email/URL metadata copied from a peer pd-* repo, NOT invented (per `feedback_no_invented_metadata`).
- [ ] `gh-pages` branch exists and Pages is live (Task 2).
- [ ] `npm test` passes (Tasks 3 + 4 unit tests).
- [ ] Manual workflow_dispatch with the smoke-test tarball succeeds and the registry serves the result (Task 5).
- [ ] `tests/smoke/run.sh` succeeds locally against the live registry (Task 6).
- [ ] README has both consumer `.npmrc` snippet AND publisher `repository_dispatch` snippet (Task 7).
- [ ] Workspace `.gitignore` and CLAUDE.md updated (Task 8).
- [ ] No invented runtime dependencies — registry content is static; the only Node deps are dev-tooling for the publish + rebuild scripts.

## Follow-up plans (not in scope here)

1. **pdomain-ui release workflow (plan #6).** Publisher side: in pdomain-ui's `release.yml`, after `npm pack` succeeds, upload the `.tgz` to a pdomain-ui GitHub Release, then dispatch the `pd-npm-publish` event into pdomain-index-npm with the asset's `browser_download_url`. Plan #6 owns this end of the round trip.
2. **Consumer wiring per app.** Each pd-* SPA that depends on `@concavetrillion/pdomain-ui` adds the `.npmrc` line (or equivalent under `frontend/.npmrc`) when it starts consuming pdomain-ui — typically as part of the Phase 2 migration plans for labeler-spa and pgdp-prep.
3. **Optional: cron safety-net rebuild.** Mirror pd-index's cron-based regen: a scheduled workflow that runs `rebuild-packuments` against the full `gh-pages` checkout to repair any drift. Not needed at MVP since the publish path is the only writer, but a small insurance policy worth adding once we have ≥3 published packages.
4. **Optional: cross-repo dispatch PAT documentation.** `repository_dispatch` from a publisher repo into pdomain-index-npm requires a PAT with `repo` scope on the target. Document the PAT setup (where to mint it, which org secret to store it under) once the first real publisher (pdomain-ui) starts using it.
5. **Future: pd-* tag promotion convention.** Once multiple packages are published, decide whether dist-tags should include suite-version markers (`suite-2026-Q3` etc.). Out of scope until ≥2 packages exist.

## Open questions

These do NOT block starting the work — flag them when they bite during implementation, and update the plan inline.

1. **Tarball path encoding.** The plan uses `%2f` (lowercase) for the URL-encoded `/` in scoped names; some npm clients have historically been picky about case. If a downstream `npm install` 404s, try `%2F` first. Verify against current npm CLI behavior during Task 6 smoke.
2. **Packument `extensionless` file vs. `.json`.** The npm CLI requests packuments at the extensionless path (e.g. `GET /@scope%2fname`). GitHub Pages serves files exactly as named — confirm during Task 6 smoke that a file named `@concavetrillion%2fpd-ui` (no extension) is served with `Content-Type: application/json` or, failing that, `application/octet-stream` (which npm tolerates if the body parses as JSON). If MIME issues arise, the fallback is to add a custom `_headers` file (Netlify-style) — but GitHub Pages doesn't honor those. Real fallback: switch to serving everything via `.json` suffix and adjust the publish script + URL convention. Decide during Task 5/6.
3. **`shasum` algorithm.** npm registry packuments historically used SHA-1 for `shasum`; modern clients use the `integrity` SHA-512 field and fall back to `shasum` only on legacy paths. The plan computes both. If a client emits a deprecation warning about SHA-1 we can drop the `shasum` field in a follow-up — it's optional in current npm.
4. **Pages publish lag.** Task 6's smoke script `sleep 60`s after publish. Empirically Pages updates within 30s but can spike to 2 min. If smoke flakes, increase to 90s before investigating real bugs.
5. **`workflow_dispatch` `inputs.tarball_url` vs. accepting an attached file.** GitHub Actions doesn't support file uploads as `workflow_dispatch` inputs. The URL-based contract is the only viable approach — meaning publishers MUST first upload their `.tgz` to **some** HTTP-fetchable location (GitHub Release asset is the obvious choice; pdomain-ui plan #6 will use that). Document this as the only supported flow.
6. **Tar library choice.** The plan suggests vendoring a minimal tar reader to avoid a runtime dep. If that proves too painful (tar's format has edge cases), pull in the `tar` npm package as a dev/CI-only dep — it's only used by the publish script in CI, not by any pd-* consumer. Decide during Task 3 implementation.

## One-line summary

A new tooling-only repo (`pdomain-index-npm`) that pairs with the existing pip index to give `pd-*` TypeScript packages — starting with `@concavetrillion/pdomain-ui` — a self-hosted, GitHub-Pages-served, Verdaccio-style npm registry consumable via a one-line `.npmrc` directive.
