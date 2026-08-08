---
Status: active
Owner: CT
Created: 2026-05-22
Last verified: 2026-08-08
Kind: process
---

# Lint-rule Deviations — pdomain-ops

## Agent Index

- **Kind:** process
- **Status:** active
- **Read when:** adding, removing, or reviewing a lint-rule suppression.
- **Search terms:** lint deviations, suppressions, noqa, pyright ignore.

This catalog lists every standing inline suppression, config-level override,
and narrowed type-check gate in the repository. Update the catalog whenever one
of them changes.
The governing rule is [Document every lint-rule suppression](../../CONVENTIONS.md#rule-document-every-lint-rule-suppression).

## Inline basedpyright suppressions

### `reportMissingImports`

The following imports are optional dependencies that the default development
and CI environment does not install, so basedpyright cannot resolve them:

- `pdomain_ops/desktop.py`: `webview` and `pystray` support the optional GUI and
  tray paths.
- `pdomain_ops/gpu/device.py`: `cupy` supports the optional `[gpu]` probe.
- `pdomain_ops/gpu/modal_app.py`: `modal` supports the optional `[modal]`
  deployment entry point.
- `pdomain_ops/gpu/modal_dispatcher.py`: `modal` supports remote dispatch when
  the `[modal]` extra is installed.

These imports are guarded, deferred until the feature is used, or kept in an
optional deployment module. Use the native
`# pyright: ignore[reportMissingImports]` form because basedpyright does not
honor mypy import codes.

The `torch`, `psutil`, `cv2`, and `PIL.Image` imports no longer carry this
suppression: those packages are present in the canonical `uv`-synced gate
environment, so `reportMissingImports` does not fire and the strict
`reportUnnecessaryTypeIgnoreComment` rule flags the ignore as redundant.

### Narrowed return types

- `pdomain_ops/gpu/device.py` suppresses `reportReturnType` on the `explicit`
  and `legacy` device returns. Both values pass `_VALID_DEVICES` checks before
  return, but basedpyright does not preserve the literal narrowing.

### Partially-typed first-party boundary and shared cache

- `pdomain_ops/gpu/default_stages.py` and `pdomain_ops/gpu/local_stage.py`
  suppress `reportUnknownVariableType` on the
  `get_finetuned_torch_doctr_predictor` import. The `pdomain-book-tools`
  function is only partially annotated at that boundary, so strict mode reports
  its inferred type as unknown.
- `pdomain_ops/gpu/local_stage.py` suppresses `reportPrivateUsage` on its import
  of `_predictor_cache` from `pdomain_ops/gpu/default_stages.py`. The cache is a
  deliberate GPU-package-internal share between the local and default stages.

Optional untyped modules (`webview`, `pystray`, `cupy`, and `modal`) are bound
to an `Any`-typed local at the import boundary instead of being suppressed, so
their member access is `Any` rather than unknown without scattering per-call
ignores. `pdomain_ops/gpu/modal_app.py` and
`pdomain_ops/gpu/modal_dispatcher.py` both use this binding, so neither file
carries a per-call Modal suppression.

## Inline Ruff suppressions

### Runtime type imports: `TC001` and `TC003`

These imports must remain available at runtime despite appearing usable only
as annotations:

- `pdomain_ops/gpu/types.py`: `datetime` (`TC003`) is a Pydantic field type.
- `pdomain_ops/pages/payload.py`: `UUID` (`TC003`) and `PageRecord` (`TC001`)
  are Pydantic field types.
- `pdomain_ops/pages/provenance.py`: `datetime` (`TC003`) is a Pydantic field
  type.
- `pdomain_ops/pages/records.py`: `datetime`, `Path`, and `UUID` (`TC003`) and
  `ProvenanceGraph` (`TC001`) are Pydantic field types.
- `pdomain_ops/schemas/doctr_export.py`: `datetime` and `Path` (`TC003`) are
  Pydantic field types.
- `tests/test_desktop_run_windowed.py`: `threading` (`TC003`) is used at
  runtime for `threading.Event`.
- `tests/test_lifecycle_integration.py`: `Path` and `UUID` (`TC003`) are
  constructed by fixtures at runtime.

Moving these imports under `TYPE_CHECKING` would break model construction or
the tests.

### Intentional broad exception handling: `BLE001` and `S110`

- `pdomain_ops/desktop.py` suppresses `BLE001` and `S110` because health
  polling tolerates transient request failures.
- `pdomain_ops/gpu/default_stages.py` suppresses `BLE001` so an optional stage
  failure can fall back gracefully.
- `pdomain_ops/gpu/doctr_batch.py` suppresses `BLE001` and `S110` because GPU
  cache cleanup is best-effort and does not benefit from logging.
- `pdomain_ops/suite/bootstrap.py` suppresses `BLE001` because startup
  continues when optional registry integration fails.
- `pdomain_ops/suite/shared_paths.py` suppresses `BLE001` because malformed
  persisted JSON falls back to the empty/default state.
- `pdomain_ops/suite/update.py` suppresses `BLE001` where update checks fail
  closed on registry or version errors. It suppresses `BLE001` with `S110`
  where metadata errors cause the install to be treated as non-editable.

### Trusted process execution: `S603` and `S606`

- `pdomain_ops/gpu/device_probe.py` suppresses `S603` for argument vectors that
  start with resolved, trusted `nvidia-smi` and `lspci` executables.
- `scripts/update_github_actions.py` suppresses `S603` for an argument vector
  that starts with the resolved, trusted `gh` executable.
- `pdomain_ops/desktop.py` suppresses `S606` because restart must replace the
  current process with `os.execv`.

### Framework class mappings: `RUF012`

- `pdomain_ops/page_aggregate.py` defines `snapshotting_intervals` as an
  intentional framework class mapping.
- `tests/test_page_aggregate.py` and `tests/test_extension_mutation.py`
  override that framework class mapping for tests.

### Intentional output and test binding: `T201` and `S104`

- `pdomain_ops/schemas/emit.py` suppresses `T201` because JSON on stdout is
  the schema CLI's output.
- `pdomain_ops/suite/bootstrap.py` suppresses `T201` because the startup URL is
  intentional CLI output.
- `tests/suite/test_bootstrap.py` suppresses `S104` because the test verifies
  explicit all-interface binding to `0.0.0.0`.

## Config-level Ruff deviations

The comments beside these settings in `pyproject.toml` are the point-of-use
rationales. This section is the central catalog.

### Project-wide `[tool.ruff.lint] ignore`

| Rule | Reason |
|---|---|
| `E501` | Long docstrings, error messages, and URLs make 100-character wrapping noisy. |
| `D203`, `D212` | They conflict with the selected `D211` and `D213` styles. |
| `D100`, `D104`, `D107` | Module, package, and `__init__` docstrings are being added incrementally. |
| `D105` | Magic methods such as `__repr__` and `__eq__` are self-documenting. |
| `D205` | Enforcing summary separation across the existing docstring backlog is too noisy for one change. |
| `PLR0913` | Pipeline functions legitimately need many parameters; a config-object refactor is not warranted. |
| `PLR2004` | Threshold, port, and timeout comparisons commonly use literal values. |
| `PLR0912`, `PLR0911`, `PLR0915` | Pipeline functions legitimately have high branch, return, and statement counts. |
| `TRY003` | This library commonly uses specific f-string exception messages. |
| `COM812` | The rule conflicts with Ruff formatter style. |
| `PLC0415` | Deferred imports break cycles and avoid eagerly loading optional heavy modules. |
| `ANN401` | JSON deserializers and generic dispatch helpers legitimately accept or return `Any`. |
| `B008` | FastAPI `Depends()` and Pydantic `field()` legitimately use calls in defaults. |

### `[tool.ruff.lint.per-file-ignores]`

| File glob | Rules | Reason |
|---|---|---|
| `tests/**/*.py` | `S101, S105, S106, S311, T201, ANN, D, PLR2004, PT011, S108, PLR0133, PLW2901, PERF401, BLE001, PLW1510, SIM117, S603, S607` | Test idioms include assertions, fixture credentials and randomness, helper output, relaxed annotations and docstrings, temporary paths, broad stress-test catches, explicit subprocess return-code assertions, and trusted subprocess tools resolved through `PATH`. |
| `scripts/*.py` | `T201, D, S607` | Tracked maintenance scripts use stdout and invoke system tools such as `uv` and `git` through `PATH`; they do not require docstrings. |
| `**/__init__.py` | `D104, F401, TC` | Package initializers expose runtime imports as public API; moving them under `TYPE_CHECKING` or removing them as unused would break re-exports. |
| `**/_*.py` | `D` | Private modules do not require docstrings. |
| `pdomain_ops/gpu/device.py` | `BLE001, S110` | Optional dependency probes must tolerate every import or runtime failure and fall through silently. |
| `pdomain_ops/gpu/local_jobs.py` | `BLE001, S603, RUF006` | The runner uses `subprocess.Popen`, supervises an intentional fire-and-forget task, and catches all supervisor failures. |
| `pdomain_ops/suite/prefs.py` | `BLE001` | JSON parse failures produce an empty/default preference state. |
| `pdomain_ops/suite/registry.py` | `BLE001, TRY300, S112` | TOML parse failures produce an empty registry; the read-or-default structure and stale-entry `continue` are intentional. |
| `pdomain_ops/suite/sibling_spawn.py` | `BLE001, S603, S110` | The launcher uses `subprocess.Popen`; health polling catches and ignores transient failures. |

## Config-level basedpyright deviations

### Strict mode on the package; no warning failures

`pyproject.toml` sets `typeCheckingMode = "strict"` and explicitly sets
`failOnWarnings = false`. The 2026-07-15 decision made strict the
workspace-canonical mode for the shipped package, overriding the earlier
2026-05-17 choice of recommended. It also enables `reportImplicitOverride` and
`reportUnnecessaryTypeIgnoreComment`. CI and release gates enforce errors with
`--level error`; warnings remain visible without blocking the gate.

Tests and scripts stay at recommended-equivalent strictness. basedpyright does
not honor a per-execution-environment `typeCheckingMode`, so the `tests` and
`scripts` execution environments in `pyproject.toml` instead set the
strict-only inference rules (`reportUnknownParameterType`,
`reportMissingParameterType`, `reportUnknownMemberType`, and the rest of that
family) to `none`. Un-annotated test fixtures and `monkeypatch` code would
otherwise flood strict with inferred-`Any` errors. Real type errors
(`reportArgumentType`, `reportCallIssue`, and similar) stay enforced everywhere.

### Unused-function detection is off

`pyproject.toml` sets `reportUnusedFunction = false`. This suite-plumbing
library mounts its FastAPI route handlers as nested functions inside `register_*`
helpers (ten or more across `suite/`). Strict flags each decorator-registered
handler as "not accessed", but the decorator registration is the real use, so
the rule is a systematic false positive here. The disable is package-wide rather
than per-handler because per-site ignores would recur on every new route and
drift out of sync. The trade-off: it also silences any genuine module-level dead
function. No such function is known in the package today; the last one,
`pdomain_ops/desktop.py::_noop_app`, was
[removed on 2026-08-07](../issues/2026-08-07-desktop-noop-app-dead-code.md).
File any new case as a governed issue rather than leaving it silently hidden.

### No basedpyright baseline

`pdomain_ops` type-checks clean under strict mode with no baseline file. The
repository previously carried `.basedpyright/baseline.json` to hold diagnostics
that predated strict mode: 263 entries at first, pruned to 33, then fixed and
[the file deleted on 2026-08-08](../issues/2026-08-07-basedpyright-strict-baseline.md).
Do not reintroduce a baseline. Fix the diagnostic, or add a narrow suppression
and catalog it above.

### Import-cycle diagnostics are disabled

`pyproject.toml` sets `reportImportCycles = "none"`. Structural cycles are
resolved with `TYPE_CHECKING` guards. Tests expose genuine runtime import-order
failures as `ImportError`.

### Automated type checking covers the shipped package

The `Makefile` `typecheck` target and the local basedpyright pre-commit hook in
`.pre-commit-config.yaml` both run
`uv run basedpyright pdomain_ops --level error`. They gate only the shipped
package, not `tests/` or `scripts/`.

`pyproject.toml` still includes `pdomain_ops`, `tests`, and `scripts` for editor
checking. Its `tests` and `scripts` execution-environment tables downgrade the
strict-only inference rules to `none` (see "Strict mode on the package" above),
so editor checking of test and script code matches the recommended-equivalent
gate rather than full strict.

The `Makefile` `pre-commit-check` target sets `SKIP=basedpyright` because
`make ci` runs the dedicated `typecheck` target immediately afterward. This
avoids running the same package check twice. Running `pre-commit-check` alone
therefore does not run basedpyright.

## Resolved suppressions

No mypy-style `# type: ignore[...]` suppressions remain in any tracked Python
file. Earlier artifacts appeared in
`pdomain_ops/suite/register_self.py`, `pdomain_ops/gpu/modal_app.py`,
`tests/suite/test_register_self.py`, and `tests/gpu/test_modal_dispatcher.py`.
They either suppressed no basedpyright diagnostic or were replaced by fixes to
the underlying type issue.
