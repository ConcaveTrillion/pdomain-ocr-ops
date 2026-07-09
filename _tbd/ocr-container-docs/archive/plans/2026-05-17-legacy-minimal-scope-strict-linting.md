---
status: complete
synced: 2026-05-17
milestone: 1
repo: ConcaveTrillion/pd-ocr-labeler
---

# pd-ocr-labeler + pd-ocr-trainer — minimal-scope strict-linting

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans`. This plan applies to TWO legacy repos at MINIMAL scope only per decision doc §pd-ocr-labeler and §pd-ocr-trainer. Each repo gets its own agent + own commits — they share this plan template but execute independently.

**Reference:** [`docs/decisions/2026-05-17-strict-linting.md`](../decisions/2026-05-17-strict-linting.md) §pd-ocr-labeler (legacy NiceGUI) and §pd-ocr-trainer (will be rewritten). Both are slated for replacement; the full strict-linting stack lands WITH the replacement, not before.

**Applies to:**
- `/workspaces/ocr-container/pd-ocr-labeler/` (legacy NiceGUI labeler being replaced by pdomain-ocr-labeler-spa)
- `/workspaces/ocr-container/pd-ocr-trainer/` (DocTR training pipeline being rewritten into the SPA ecosystem)

**Reference canonical:** pdomain-book-tools at commit `f809701` (2026-05-17).

---

## Scope — what to apply

Apply ONLY these three things (minimal scope per decision doc):
1. `gitleaks` pre-commit hook (v8.30.1)
2. `uv-lock-check` local pre-commit hook
3. Canonical `.editorconfig`

## Scope — what to DEFER (do NOT apply)

Per decision doc §pd-ocr-labeler:
- Ruff rule expansion (keep current select as-is)
- basedpyright migration (keep whatever pyright config exists, or absence)
- `D` (docstring) rules
- `filterwarnings = ["error"]`
- gitlint
- Coverage floor changes (keep `fail_under = 0` if set; do NOT raise)

These would be wasted work for repos slated for replacement.

---

## Task 1: Add canonical `.editorconfig` {#add-canonical-editorconfig}

- [ ] `cat /workspaces/ocr-container/pdomain-book-tools/.editorconfig > .editorconfig`
- [ ] Verify first line: `# .editorconfig — workspace canonical`.
- [ ] Commit:
```
chore: add canonical .editorconfig

Workspace-canonical file per docs/decisions/2026-05-17-strict-linting.md.
Minimal-scope addition for legacy repo slated for replacement.
```

---

## Task 2: Add gitleaks + uv-lock-check pre-commit hooks {#add-gitleaks-uv-lock-check-pre-commit-hooks}

If `.pre-commit-config.yaml` exists:

- [ ] In `.pre-commit-config.yaml`, locate the existing `repos:` block.
- [ ] Insert (alphabetically — between `pre-commit-hooks` and `ruff-pre-commit` blocks if present, or at end):
```yaml
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.1
    hooks:
      - id: gitleaks
```
- [ ] Append (or extend if `local` repo exists):
```yaml
  - repo: local
    hooks:
      - id: uv-lock-check
        name: uv.lock is in sync with pyproject.toml
        entry: uv lock --check
        language: system
        stages: [pre-commit]
        pass_filenames: false
        files: ^(pyproject\.toml|uv\.lock)$
```
- [ ] Re-install: `uv run pre-commit install`.
- [ ] Smoke test: `uv run pre-commit run gitleaks --all-files` (should be clean).
- [ ] Smoke test: `uv run pre-commit run uv-lock-check --files pyproject.toml`.
- [ ] Commit:
```
chore(precommit): add gitleaks + uv-lock-check (minimal scope)

gitleaks v8.30.1 scans staged diff for secrets (<100ms typical).
uv-lock-check ensures uv.lock stays in sync with pyproject.toml.

Minimal-scope additions per docs/decisions/2026-05-17-strict-linting.md
for this legacy repo (full strict-linting stack lands with the
replacement project, not before).
```

If `.pre-commit-config.yaml` does NOT exist:

- [ ] Create it from scratch with this content (minimal — only the canonical hooks for this scope):
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-toml
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.1
    hooks:
      - id: gitleaks
  - repo: local
    hooks:
      - id: uv-lock-check
        name: uv.lock is in sync with pyproject.toml
        entry: uv lock --check
        language: system
        stages: [pre-commit]
        pass_filenames: false
        files: ^(pyproject\.toml|uv\.lock)$
```
- [ ] Add `"pre-commit>=4.2.0",` to dev deps if missing. `uv sync`.
- [ ] Install: `uv run pre-commit install`.
- [ ] Commit per above.

---

## Self-review checklist

- [ ] 2 commits land (editorconfig + pre-commit additions).
- [ ] No `--no-verify`.
- [ ] `make ci AI=1` is green (if `make ci` exists; if not, run `uv run pre-commit run --all-files`).
- [ ] NO ruff expansion, basedpyright migration, gitlint, or filterwarnings changes.
- [ ] `.editorconfig` byte-equal to pdomain-book-tools' `.editorconfig`.

## Notes for the agent

- This is intentionally MINIMAL. Resist the urge to apply other canonical patterns — the decision doc is explicit that fuller treatment lands with the replacement project.
- If you discover `.pre-commit-config.yaml` already has gitleaks or uv-lock-check at a different version, don't bump — leave it. The goal is presence-of-secret-scan, not version-canonicality for a legacy repo.
- Final report: "2 commits landed; final SHA: <X>; gitleaks + uv-lock-check + .editorconfig present; no other canonical patterns applied per decision doc minimal-scope mandate".
