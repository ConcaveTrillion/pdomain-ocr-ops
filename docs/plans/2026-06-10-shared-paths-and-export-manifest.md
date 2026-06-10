# Shared-Paths API and DocTR Export Manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

```yaml
repo: pdomain/pdomain-ops
plan_type: per-repo
status: not-started
synced: never
```

**Goal:** Add two small additive modules to pdomain-ops — a suite shared-paths API that lets one suite app publish a well-known data path for siblings to discover, and a shared DocTR export manifest schema with atomic IO helpers — so labeler-spa and trainer-spa can share export data without out-of-band configuration.

**Architecture:** Feature 1 stores shared paths in a JSON file (`shared-paths.json`) under `suite_data_dir()`, protected by a bounded `filelock.FileLock` reusing the same `_resolve_lock_timeout` / `PrefsLockTimeout` pattern from `prefs.py`. Feature 2 lives in `pdomain_ops/schemas/doctr_export.py` as a new Pydantic module, following the emit.py model pattern; `read_manifest` / `write_manifest` use `tmp + os.replace` atomic writes, mirroring the TOML registry write discipline. Both features are pure additions with no changes to existing modules.

**Tech Stack:** Python 3.11+, Pydantic v2, `filelock>=3.13`, `platformdirs>=4.2`, stdlib `json`, stdlib `os.replace`, `uv run pytest -n auto`.

**Downstream consumers:** labeler-spa (Track C) and trainer-spa (Track D) develop against these APIs via `make local-dev` mode until pdomain-ops cuts its next minor release (CT-gated).

---

## File Map

| File | Status | Responsibility |
|---|---|---|
| `pdomain_ops/suite/shared_paths.py` | **Create** | `publish_shared_path`, `resolve_shared_path`, `SharedPathsLockTimeout` |
| `pdomain_ops/suite/paths.py` | **Modify** | Add `shared_paths_json_path()` helper |
| `pdomain_ops/suite/__init__.py` | **Modify** | Re-export new public surface |
| `pdomain_ops/schemas/doctr_export.py` | **Create** | `DoctrExportManifest` models, `read_manifest`, `write_manifest` |
| `pdomain_ops/schemas/emit.py` | **Modify** | Add `DoctrExportManifest` and task-stats models to `PUBLIC_MODELS` |
| `tests/suite/test_shared_paths.py` | **Create** | All shared-paths tests (happy path, missing file, concurrent publish, timeout) |
| `tests/suite/test_paths_shared_paths_json.py` | **Create** | Path helper test |
| `tests/test_schemas_doctr_export.py` | **Create** | All manifest model / IO tests |
| `tests/test_schemas_emit.py` | **Modify** | Add assertions for new manifest models in emit output |
| `tests/test_public_surface.py` | **Modify** | Add import assertions for new public surface |

---

## Task 1: `shared_paths_json_path()` path helper

**Files:**

- Modify: `pdomain_ops/suite/paths.py`
- Create: `tests/suite/test_paths_shared_paths_json.py`

- [ ] **Step 1: Write the failing test**

  Create `tests/suite/test_paths_shared_paths_json.py`:

  ```python
  from pdomain_ops.suite.paths import shared_paths_json_path


  def test_shared_paths_json_path_under_data_dir(tmp_path, monkeypatch):
      monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path))
      result = shared_paths_json_path()
      assert result == tmp_path / "shared-paths.json"
  ```

- [ ] **Step 2: Run test to verify it fails**

  ```bash
  cd /workspaces/ocr-container/pdomain-ops
  uv run pytest tests/suite/test_paths_shared_paths_json.py -v
  ```

  Expected: `FAILED` — `ImportError: cannot import name 'shared_paths_json_path'`

- [ ] **Step 3: Add `shared_paths_json_path` to `paths.py`**

  In `pdomain_ops/suite/paths.py`, append after `jobs_db_path`:

  ```python
  def shared_paths_json_path() -> Path:
      """Return the path to shared-paths.json."""
      return suite_data_dir() / "shared-paths.json"
  ```

- [ ] **Step 4: Run test to verify it passes**

  ```bash
  uv run pytest tests/suite/test_paths_shared_paths_json.py -v
  ```

  Expected: `1 passed`

- [ ] **Step 5: Commit**

  ```bash
  git add pdomain_ops/suite/paths.py tests/suite/test_paths_shared_paths_json.py
  git commit -m "feat(suite): add shared_paths_json_path() helper"
  ```

---

## Task 2: `SharedPathsLockTimeout` + `_resolve_lock_timeout` reuse

**Files:**

- Create: `pdomain_ops/suite/shared_paths.py`
- Create: `tests/suite/test_shared_paths.py` (initial skeleton, expanded in later tasks)

- [ ] **Step 1: Write the failing import test**

  Create `tests/suite/test_shared_paths.py`:

  ```python
  """Tests for suite shared-paths API."""

  from __future__ import annotations

  import threading
  from pathlib import Path

  import filelock
  import pytest

  from pdomain_ops.suite.shared_paths import (
      SharedPathsLockTimeout,
      publish_shared_path,
      resolve_shared_path,
  )

  _WATCHDOG_S = 10.0


  def test_shared_paths_lock_timeout_is_filelock_timeout_subclass():
      assert issubclass(SharedPathsLockTimeout, filelock.Timeout)
  ```

- [ ] **Step 2: Run test to verify it fails**

  ```bash
  uv run pytest tests/suite/test_shared_paths.py::test_shared_paths_lock_timeout_is_filelock_timeout_subclass -v
  ```

  Expected: `FAILED` — `ImportError: cannot import name 'SharedPathsLockTimeout'`

- [ ] **Step 3: Create `shared_paths.py` with lock infrastructure**

  Create `pdomain_ops/suite/shared_paths.py`:

  ```python
  """Suite shared-paths API: publish and resolve well-known data paths."""

  from __future__ import annotations

  import json
  import logging
  import os
  import tempfile
  from pathlib import Path
  from typing import TYPE_CHECKING

  import filelock

  from pdomain_ops.suite.prefs import _resolve_lock_timeout

  if TYPE_CHECKING:
      pass

  _logger = logging.getLogger(__name__)

  #: Finite default lock timeout — matches prefs.DEFAULT_LOCK_TIMEOUT.
  DEFAULT_LOCK_TIMEOUT: float = 5.0

  #: Env var for overriding the default timeout, consistent with PDOMAIN_PREFS_LOCK_TIMEOUT.
  LOCK_TIMEOUT_ENV_VAR = "PDOMAIN_SHARED_PATHS_LOCK_TIMEOUT"


  class SharedPathsLockTimeout(filelock.Timeout):
      """Raised when the shared-paths file lock cannot be acquired within the timeout.

      Subclasses ``filelock.Timeout`` for the same reason as ``PrefsLockTimeout``:
      existing callers catching the upstream exception keep working, while new callers
      can catch this typed error and map it to an HTTP 503.
      """

      def __init__(self, lock_file: str, timeout: float) -> None:
          super().__init__(lock_file)
          self.timeout = timeout

      def __str__(self) -> str:
          return (
              f"Could not acquire shared-paths lock on {self.lock_file!r} within "
              f"{self.timeout}s; another process may be holding it (orphaned?)."
          )
  ```

- [ ] **Step 4: Run test to verify it passes**

  ```bash
  uv run pytest tests/suite/test_shared_paths.py::test_shared_paths_lock_timeout_is_filelock_timeout_subclass -v
  ```

  Expected: `1 passed`

- [ ] **Step 5: Commit**

  ```bash
  git add pdomain_ops/suite/shared_paths.py tests/suite/test_shared_paths.py
  git commit -m "feat(suite): shared_paths module skeleton + SharedPathsLockTimeout"
  ```

---

## Task 3: `publish_shared_path` — write a key/path entry atomically

**Files:**

- Modify: `pdomain_ops/suite/shared_paths.py`
- Modify: `tests/suite/test_shared_paths.py`

The storage format for `shared-paths.json` is:

```json
{
  "paths": {
    "doctr-export-root": {
      "path": "/home/user/.local/share/labeler-spa/exports",
      "app": "pdomain-ocr-labeler-spa"
    }
  }
}
```

Each entry stores both the resolved path string and the publishing app id. A second `publish_shared_path` call for the same key from the same or a different app overwrites the entry (last-writer wins under the lock).

- [ ] **Step 1: Write the failing tests**

  Append to `tests/suite/test_shared_paths.py`:

  ```python
  def test_publish_then_resolve_returns_path(tmp_path, monkeypatch):
      monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path))
      publish_shared_path("doctr-export-root", tmp_path / "exports", app="labeler")
      result = resolve_shared_path("doctr-export-root")
      assert result == tmp_path / "exports"


  def test_resolve_missing_key_returns_none(tmp_path, monkeypatch):
      monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path))
      result = resolve_shared_path("nonexistent-key")
      assert result is None


  def test_resolve_missing_file_returns_none(tmp_path, monkeypatch):
      monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path))
      # No shared-paths.json written at all
      result = resolve_shared_path("doctr-export-root")
      assert result is None


  def test_publish_overwrites_existing_key(tmp_path, monkeypatch):
      monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path))
      first = tmp_path / "v1"
      second = tmp_path / "v2"
      publish_shared_path("doctr-export-root", first, app="labeler")
      publish_shared_path("doctr-export-root", second, app="labeler")
      assert resolve_shared_path("doctr-export-root") == second


  def test_resolve_returns_path_even_if_target_does_not_exist(tmp_path, monkeypatch):
      """resolve returns the recorded path even when the directory is gone — caller decides."""
      monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path))
      stale = tmp_path / "gone"
      publish_shared_path("doctr-export-root", stale, app="labeler")
      # stale was never created — resolve must still return it
      assert resolve_shared_path("doctr-export-root") == stale


  def test_publish_multiple_keys_coexist(tmp_path, monkeypatch):
      monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path))
      publish_shared_path("key-a", tmp_path / "a", app="app-a")
      publish_shared_path("key-b", tmp_path / "b", app="app-b")
      assert resolve_shared_path("key-a") == tmp_path / "a"
      assert resolve_shared_path("key-b") == tmp_path / "b"
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  uv run pytest tests/suite/test_shared_paths.py -v -k "publish or resolve"
  ```

  Expected: all 6 new tests `FAILED` — `AttributeError: module has no attribute 'publish_shared_path'` (or similar).

- [ ] **Step 3: Implement `publish_shared_path` and `resolve_shared_path`**

  Replace the body of `pdomain_ops/suite/shared_paths.py` (keep the header and `SharedPathsLockTimeout` class, append these functions):

  ```python
  def _shared_paths_json() -> Path:
      from pdomain_ops.suite.paths import shared_paths_json_path

      return shared_paths_json_path()


  def _resolve_timeout(lock_timeout: float | None) -> float:
      """Resolve effective lock timeout using the same precedence as prefs."""
      if lock_timeout is not None:
          return lock_timeout
      env_val = os.environ.get(LOCK_TIMEOUT_ENV_VAR)
      if env_val is not None:
          try:
              return float(env_val)
          except ValueError:
              _logger.warning(
                  "%s=%r is not a valid float; using default %ss",
                  LOCK_TIMEOUT_ENV_VAR,
                  env_val,
                  DEFAULT_LOCK_TIMEOUT,
              )
      return DEFAULT_LOCK_TIMEOUT


  def _read_raw(json_path: Path) -> dict[str, object]:
      if not json_path.exists():
          return {"paths": {}}
      try:
          return json.loads(json_path.read_text(encoding="utf-8"))
      except Exception:
          return {"paths": {}}


  def _atomic_write(json_path: Path, data: dict[str, object]) -> None:
      json_path.parent.mkdir(parents=True, exist_ok=True)
      fd, tmp_name = tempfile.mkstemp(dir=json_path.parent, prefix=".shared-paths-", suffix=".tmp")
      try:
          with os.fdopen(fd, "w", encoding="utf-8") as f:
              json.dump(data, f, indent=2, default=str)
          os.replace(tmp_name, json_path)
      except Exception:
          try:
              os.unlink(tmp_name)
          except OSError:
              pass
          raise


  def publish_shared_path(
      key: str,
      path: Path,
      *,
      app: str,
      lock_timeout: float | None = None,
  ) -> None:
      """Record *path* under *key* in the suite shared-paths registry.

      Last writer wins when two apps publish the same key concurrently —
      the write is atomic (tmp + os.replace) and serialised through a
      finite-timeout FileLock so corrupt interleaved writes are impossible.

      Args:
          key: Arbitrary string identifier (e.g. ``"doctr-export-root"``).
          path: The filesystem path to publish.
          app: The publishing app id (informational, stored alongside the path).
          lock_timeout: Seconds to wait for the file lock. Falls back to
              ``PDOMAIN_SHARED_PATHS_LOCK_TIMEOUT`` env var, then
              :data:`DEFAULT_LOCK_TIMEOUT`.

      Raises:
          SharedPathsLockTimeout: If the lock cannot be acquired in time.
      """
      timeout = _resolve_timeout(lock_timeout)
      json_path = _shared_paths_json()
      lock_file = str(json_path.with_suffix(".json.lock"))
      lock = filelock.FileLock(lock_file, timeout=timeout)
      try:
          with lock:
              data = _read_raw(json_path)
              paths: dict[str, object] = data.get("paths", {})  # type: ignore[assignment]
              paths[key] = {"path": str(path), "app": app}
              data["paths"] = paths
              _atomic_write(json_path, data)
      except filelock.Timeout as exc:
          raise SharedPathsLockTimeout(lock_file, timeout) from exc


  def resolve_shared_path(
      key: str,
      *,
      lock_timeout: float | None = None,
  ) -> Path | None:
      """Return the path published under *key*, or ``None`` if not found.

      The returned path may not exist on disk — the caller is responsible for
      verifying existence if needed. A missing or corrupt registry file returns
      ``None`` silently.

      Args:
          key: The key to look up.
          lock_timeout: Seconds to wait for the file lock.

      Raises:
          SharedPathsLockTimeout: If the lock cannot be acquired in time.
      """
      timeout = _resolve_timeout(lock_timeout)
      json_path = _shared_paths_json()
      lock_file = str(json_path.with_suffix(".json.lock"))
      lock = filelock.FileLock(lock_file, timeout=timeout)
      try:
          with lock:
              data = _read_raw(json_path)
      except filelock.Timeout as exc:
          raise SharedPathsLockTimeout(lock_file, timeout) from exc

      entry = data.get("paths", {}).get(key)  # type: ignore[union-attr]
      if entry is None:
          return None
      raw_path = entry.get("path") if isinstance(entry, dict) else None  # type: ignore[union-attr]
      if not raw_path:
          return None
      return Path(raw_path)
  ```

  The full file after this step:

  ```python
  """Suite shared-paths API: publish and resolve well-known data paths."""

  from __future__ import annotations

  import json
  import logging
  import os
  import tempfile
  from pathlib import Path
  from typing import TYPE_CHECKING

  import filelock

  if TYPE_CHECKING:
      pass

  _logger = logging.getLogger(__name__)

  DEFAULT_LOCK_TIMEOUT: float = 5.0
  LOCK_TIMEOUT_ENV_VAR = "PDOMAIN_SHARED_PATHS_LOCK_TIMEOUT"


  class SharedPathsLockTimeout(filelock.Timeout):
      """Raised when the shared-paths file lock cannot be acquired within the timeout."""

      def __init__(self, lock_file: str, timeout: float) -> None:
          super().__init__(lock_file)
          self.timeout = timeout

      def __str__(self) -> str:
          return (
              f"Could not acquire shared-paths lock on {self.lock_file!r} within "
              f"{self.timeout}s; another process may be holding it (orphaned?)."
          )


  def _shared_paths_json() -> Path:
      from pdomain_ops.suite.paths import shared_paths_json_path

      return shared_paths_json_path()


  def _resolve_timeout(lock_timeout: float | None) -> float:
      if lock_timeout is not None:
          return lock_timeout
      env_val = os.environ.get(LOCK_TIMEOUT_ENV_VAR)
      if env_val is not None:
          try:
              return float(env_val)
          except ValueError:
              _logger.warning(
                  "%s=%r is not a valid float; using default %ss",
                  LOCK_TIMEOUT_ENV_VAR,
                  env_val,
                  DEFAULT_LOCK_TIMEOUT,
              )
      return DEFAULT_LOCK_TIMEOUT


  def _read_raw(json_path: Path) -> dict[str, object]:
      if not json_path.exists():
          return {"paths": {}}
      try:
          return json.loads(json_path.read_text(encoding="utf-8"))
      except Exception:
          return {"paths": {}}


  def _atomic_write(json_path: Path, data: dict[str, object]) -> None:
      json_path.parent.mkdir(parents=True, exist_ok=True)
      fd, tmp_name = tempfile.mkstemp(dir=json_path.parent, prefix=".shared-paths-", suffix=".tmp")
      try:
          with os.fdopen(fd, "w", encoding="utf-8") as f:
              json.dump(data, f, indent=2, default=str)
          os.replace(tmp_name, json_path)
      except Exception:
          try:
              os.unlink(tmp_name)
          except OSError:
              pass
          raise


  def publish_shared_path(
      key: str,
      path: Path,
      *,
      app: str,
      lock_timeout: float | None = None,
  ) -> None:
      """Record *path* under *key* in the suite shared-paths registry.

      Last writer wins when two apps publish the same key concurrently.
      Write is atomic (tmp + os.replace) and serialised through a
      finite-timeout FileLock.

      Raises:
          SharedPathsLockTimeout: If the lock cannot be acquired in time.
      """
      timeout = _resolve_timeout(lock_timeout)
      json_path = _shared_paths_json()
      lock_file = str(json_path.with_suffix(".json.lock"))
      lock = filelock.FileLock(lock_file, timeout=timeout)
      try:
          with lock:
              data = _read_raw(json_path)
              paths: dict[str, object] = data.get("paths", {})  # type: ignore[assignment]
              paths[key] = {"path": str(path), "app": app}
              data["paths"] = paths
              _atomic_write(json_path, data)
      except filelock.Timeout as exc:
          raise SharedPathsLockTimeout(lock_file, timeout) from exc


  def resolve_shared_path(
      key: str,
      *,
      lock_timeout: float | None = None,
  ) -> Path | None:
      """Return the path published under *key*, or ``None`` if not found.

      The returned path may not exist on disk — caller decides.

      Raises:
          SharedPathsLockTimeout: If the lock cannot be acquired in time.
      """
      timeout = _resolve_timeout(lock_timeout)
      json_path = _shared_paths_json()
      lock_file = str(json_path.with_suffix(".json.lock"))
      lock = filelock.FileLock(lock_file, timeout=timeout)
      try:
          with lock:
              data = _read_raw(json_path)
      except filelock.Timeout as exc:
          raise SharedPathsLockTimeout(lock_file, timeout) from exc

      entry = data.get("paths", {}).get(key)  # type: ignore[union-attr]
      if entry is None:
          return None
      raw_path = entry.get("path") if isinstance(entry, dict) else None  # type: ignore[union-attr]
      if not raw_path:
          return None
      return Path(raw_path)
  ```

- [ ] **Step 4: Run tests to verify they pass**

  ```bash
  uv run pytest tests/suite/test_shared_paths.py -v
  ```

  Expected: `7 passed` (1 from Task 2 + 6 new ones)

- [ ] **Step 5: Commit**

  ```bash
  git add pdomain_ops/suite/shared_paths.py tests/suite/test_shared_paths.py
  git commit -m "feat(suite): publish_shared_path and resolve_shared_path"
  ```

---

## Task 4: Lock-timeout and concurrency tests for shared-paths

**Files:**

- Modify: `tests/suite/test_shared_paths.py`

- [ ] **Step 1: Append lock-timeout tests**

  Append to `tests/suite/test_shared_paths.py`:

  ```python
  def _hold_lock(lock_path: str, held: threading.Event, release: threading.Event) -> None:
      with filelock.FileLock(lock_path):
          held.set()
          release.wait(timeout=_WATCHDOG_S)


  def _run_bounded(fn, *, watchdog_s: float = _WATCHDOG_S):
      box: dict[str, object] = {}

      def target() -> None:
          try:
              box["result"] = fn()
          except BaseException as exc:
              box["exc"] = exc

      worker = threading.Thread(target=target, daemon=True)
      worker.start()
      worker.join(timeout=watchdog_s)
      if worker.is_alive():
          pytest.fail(
              f"call did not return within {watchdog_s}s -- lock is blocking indefinitely"
          )
      return box.get("result"), box.get("exc")


  def test_publish_raises_lock_timeout_when_lock_held(tmp_path, monkeypatch):
      monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path))
      json_path = tmp_path / "shared-paths.json"
      lock_path = str(json_path.with_suffix(".json.lock"))

      held = threading.Event()
      release = threading.Event()
      h = threading.Thread(target=_hold_lock, args=(lock_path, held, release), daemon=True)
      h.start()
      assert held.wait(timeout=_WATCHDOG_S)

      try:
          _result, exc = _run_bounded(
              lambda: publish_shared_path(
                  "doctr-export-root", tmp_path / "exports", app="labeler", lock_timeout=0.3
              )
          )
          assert isinstance(exc, SharedPathsLockTimeout), f"expected SharedPathsLockTimeout, got {exc!r}"
          assert issubclass(type(exc), filelock.Timeout)
      finally:
          release.set()
          h.join(timeout=_WATCHDOG_S)


  def test_resolve_raises_lock_timeout_when_lock_held(tmp_path, monkeypatch):
      monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path))
      json_path = tmp_path / "shared-paths.json"
      lock_path = str(json_path.with_suffix(".json.lock"))

      held = threading.Event()
      release = threading.Event()
      h = threading.Thread(target=_hold_lock, args=(lock_path, held, release), daemon=True)
      h.start()
      assert held.wait(timeout=_WATCHDOG_S)

      try:
          _result, exc = _run_bounded(
              lambda: resolve_shared_path("doctr-export-root", lock_timeout=0.3)
          )
          assert isinstance(exc, SharedPathsLockTimeout), f"expected SharedPathsLockTimeout, got {exc!r}"
      finally:
          release.set()
          h.join(timeout=_WATCHDOG_S)


  def test_default_lock_timeout_is_finite():
      from pdomain_ops.suite.shared_paths import DEFAULT_LOCK_TIMEOUT

      assert DEFAULT_LOCK_TIMEOUT > 0
      assert DEFAULT_LOCK_TIMEOUT != -1


  def test_lock_timeout_env_var_override(tmp_path, monkeypatch):
      monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path))
      monkeypatch.setenv("PDOMAIN_SHARED_PATHS_LOCK_TIMEOUT", "2.5")
      from pdomain_ops.suite.shared_paths import _resolve_timeout

      assert _resolve_timeout(None) == 2.5


  def test_explicit_lock_timeout_beats_env_var(monkeypatch):
      monkeypatch.setenv("PDOMAIN_SHARED_PATHS_LOCK_TIMEOUT", "2.5")
      from pdomain_ops.suite.shared_paths import _resolve_timeout

      assert _resolve_timeout(3.0) == 3.0


  def test_invalid_env_var_falls_back_to_default(monkeypatch):
      monkeypatch.setenv("PDOMAIN_SHARED_PATHS_LOCK_TIMEOUT", "not-a-number")
      from pdomain_ops.suite.shared_paths import DEFAULT_LOCK_TIMEOUT, _resolve_timeout

      assert _resolve_timeout(None) == DEFAULT_LOCK_TIMEOUT
  ```

- [ ] **Step 2: Run tests to verify they pass**

  ```bash
  uv run pytest tests/suite/test_shared_paths.py -v
  ```

  Expected: `14 passed`

- [ ] **Step 3: Commit**

  ```bash
  git add tests/suite/test_shared_paths.py
  git commit -m "test(suite): lock-timeout + concurrency coverage for shared_paths"
  ```

---

## Task 5: Re-export `shared_paths` surface from `pdomain_ops.suite`

**Files:**

- Modify: `pdomain_ops/suite/__init__.py`
- Modify: `tests/test_public_surface.py`

- [ ] **Step 1: Write the failing surface test**

  Append to `tests/test_public_surface.py`:

  ```python
  def test_shared_paths_surface_importable() -> None:
      from pdomain_ops.suite.shared_paths import (
          SharedPathsLockTimeout,
          publish_shared_path,
          resolve_shared_path,
      )

      assert callable(publish_shared_path)
      assert callable(resolve_shared_path)
      assert issubclass(SharedPathsLockTimeout, Exception)
  ```

- [ ] **Step 2: Run to confirm it passes (it already imports from the module directly)**

  ```bash
  uv run pytest tests/test_public_surface.py::test_shared_paths_surface_importable -v
  ```

  Expected: `1 passed` — the direct-module import works; this test validates discoverability.

- [ ] **Step 3: Add re-exports to `pdomain_ops/suite/__init__.py`**

  In `pdomain_ops/suite/__init__.py`, add to the imports block and `__all__`:

  ```python
  from pdomain_ops.suite.shared_paths import (
      SharedPathsLockTimeout,
      publish_shared_path,
      resolve_shared_path,
  )
  ```

  And add to `__all__`:

  ```python
  "SharedPathsLockTimeout",
  "publish_shared_path",
  "resolve_shared_path",
  ```

  Full updated `__init__.py`:

  ```python
  """Suite plumbing: registry, prefs, launcher, auth, storage, routes."""

  from pdomain_ops.suite.bootstrap import bootstrap_spa
  from pdomain_ops.suite.ports import find_available_port
  from pdomain_ops.suite.prefs import (
      DEFAULT_LOCK_TIMEOUT,
      LocalFilePrefs,
      PrefsAdapter,
      PrefsLockTimeout,
  )
  from pdomain_ops.suite.register_self import register_self
  from pdomain_ops.suite.shared_paths import (
      SharedPathsLockTimeout,
      publish_shared_path,
      resolve_shared_path,
  )
  from pdomain_ops.suite.types import (
      CommonUIPrefs,
      InstalledApp,
      LayerColors,
      SuiteAdapters,
      SuiteApp,
      UIPrefs,
  )

  __all__ = [
      "DEFAULT_LOCK_TIMEOUT",
      "CommonUIPrefs",
      "InstalledApp",
      "LayerColors",
      "LocalFilePrefs",
      "PrefsAdapter",
      "PrefsLockTimeout",
      "SharedPathsLockTimeout",
      "SuiteAdapters",
      "SuiteApp",
      "UIPrefs",
      "bootstrap_spa",
      "find_available_port",
      "publish_shared_path",
      "register_self",
      "resolve_shared_path",
  ]
  ```

- [ ] **Step 4: Run full suite test to verify nothing broken**

  ```bash
  uv run pytest tests/test_public_surface.py tests/suite/test_shared_paths.py tests/suite/test_paths_shared_paths_json.py -v
  ```

  Expected: all pass

- [ ] **Step 5: Commit**

  ```bash
  git add pdomain_ops/suite/__init__.py tests/test_public_surface.py
  git commit -m "feat(suite): re-export shared_paths surface from pdomain_ops.suite"
  ```

---

## Task 6: `DoctrExportManifest` Pydantic models

**Files:**

- Create: `pdomain_ops/schemas/doctr_export.py`
- Create: `tests/test_schemas_doctr_export.py` (initial, expanded in Task 7)

The JSON contract (`<export_root>/manifest.json`) key `"schema"` is a Python reserved-ish name and collides with Pydantic's `.model_json_schema()`. Use a Python-safe field name `schema_id` with `alias="schema"` and `model_config = ConfigDict(populate_by_name=True)`.

Forward-compat policy: reading a manifest with `version > 1` logs a warning and returns the object anyway (best-effort field mapping). The caller decides whether to reject it. This prevents a hard crash when pdomain-ops ships version 2 of the manifest format while trainer-spa is still on v1.

- [ ] **Step 1: Write the failing model tests**

  Create `tests/test_schemas_doctr_export.py`:

  ```python
  """Tests for DoctrExportManifest Pydantic models."""

  from __future__ import annotations

  import json
  from datetime import datetime, timezone

  import pytest

  from pdomain_ops.schemas.doctr_export import (
      DoctrExportManifest,
      DoctrExportProject,
      DoctrExportTaskStats,
  )


  def _minimal_manifest_dict() -> dict:
      return {
          "schema": "pdomain.doctr-export-manifest",
          "version": 1,
          "generated_at": "2026-06-10T12:00:00+00:00",
          "app": "pdomain-ocr-labeler-spa",
          "projects": {},
      }


  def test_task_stats_roundtrip():
      s = DoctrExportTaskStats(item_count=42)
      assert s.item_count == 42


  def test_project_roundtrip():
      p = DoctrExportProject(
          exported_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
          page_count=12,
          tasks={"recognition": DoctrExportTaskStats(item_count=340)},
      )
      assert p.page_count == 12
      assert p.tasks["recognition"].item_count == 340


  def test_manifest_from_json_dict():
      data = _minimal_manifest_dict()
      m = DoctrExportManifest.model_validate(data)
      assert m.schema_id == "pdomain.doctr-export-manifest"
      assert m.version == 1
      assert m.app == "pdomain-ocr-labeler-spa"
      assert m.projects == {}


  def test_manifest_round_trips_via_json():
      data = _minimal_manifest_dict()
      data["projects"]["proj-1"] = {
          "exported_at": "2026-06-10T10:00:00+00:00",
          "page_count": 5,
          "tasks": {
              "recognition": {"item_count": 100},
              "detection": {"item_count": 5},
          },
      }
      m = DoctrExportManifest.model_validate(data)
      dumped = json.loads(m.model_dump_json(by_alias=True))
      assert dumped["schema"] == "pdomain.doctr-export-manifest"
      assert dumped["projects"]["proj-1"]["tasks"]["recognition"]["item_count"] == 100


  def test_unknown_task_keys_roundtrip():
      """Tasks dict is keyed by arbitrary string — unknown keys must survive."""
      data = _minimal_manifest_dict()
      data["projects"]["p"] = {
          "exported_at": "2026-06-10T10:00:00+00:00",
          "page_count": 1,
          "tasks": {
              "future-task-type": {"item_count": 7},
          },
      }
      m = DoctrExportManifest.model_validate(data)
      assert m.projects["p"].tasks["future-task-type"].item_count == 7


  def test_version_gt_1_does_not_crash():
      """Forward-compat: version > 1 must not raise — caller decides to reject."""
      data = _minimal_manifest_dict()
      data["version"] = 99
      m = DoctrExportManifest.model_validate(data)
      assert m.version == 99
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  uv run pytest tests/test_schemas_doctr_export.py -v
  ```

  Expected: all 6 `FAILED` — `ImportError: No module named 'pdomain_ops.schemas.doctr_export'`

- [ ] **Step 3: Create `pdomain_ops/schemas/doctr_export.py`**

  ```python
  """DocTR export manifest schema and IO helpers.

  The manifest file lives at ``<export_root>/manifest.json`` and records
  which projects have been exported, when, and with what task item counts.

  Forward-compat: ``version > 1`` is accepted with a log warning rather than
  raising — the caller decides whether to reject an unexpected version.
  """

  from __future__ import annotations

  import json
  import logging
  import os
  import tempfile
  from datetime import datetime
  from pathlib import Path
  from typing import TYPE_CHECKING

  from pydantic import BaseModel, ConfigDict, Field

  if TYPE_CHECKING:
      pass

  _logger = logging.getLogger(__name__)

  _MANIFEST_FILENAME = "manifest.json"
  _CURRENT_VERSION = 1


  class DoctrExportTaskStats(BaseModel):
      """Per-task item count for one export."""

      model_config = ConfigDict(extra="ignore")

      item_count: int


  class DoctrExportProject(BaseModel):
      """Export record for one project."""

      model_config = ConfigDict(extra="ignore")

      exported_at: datetime
      page_count: int
      tasks: dict[str, DoctrExportTaskStats]


  class DoctrExportManifest(BaseModel):
      """Top-level DocTR export manifest.

      The JSON key ``"schema"`` maps to the Python field ``schema_id``
      to avoid collision with Pydantic's own ``.model_json_schema()`` method.
      """

      model_config = ConfigDict(populate_by_name=True, extra="ignore")

      schema_id: str = Field(
          default="pdomain.doctr-export-manifest",
          alias="schema",
      )
      version: int = _CURRENT_VERSION
      generated_at: datetime
      app: str
      projects: dict[str, DoctrExportProject] = {}
  ```

- [ ] **Step 4: Run tests to verify they pass**

  ```bash
  uv run pytest tests/test_schemas_doctr_export.py -v
  ```

  Expected: `6 passed`

- [ ] **Step 5: Commit**

  ```bash
  git add pdomain_ops/schemas/doctr_export.py tests/test_schemas_doctr_export.py
  git commit -m "feat(schemas): DoctrExportManifest Pydantic models"
  ```

---

## Task 7: `read_manifest` and `write_manifest` IO helpers

**Files:**

- Modify: `pdomain_ops/schemas/doctr_export.py`
- Modify: `tests/test_schemas_doctr_export.py`

- [ ] **Step 1: Append failing IO tests**

  Append to `tests/test_schemas_doctr_export.py`:

  ```python
  from pdomain_ops.schemas.doctr_export import read_manifest, write_manifest


  def _sample_manifest() -> DoctrExportManifest:
      return DoctrExportManifest(
          generated_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
          app="pdomain-ocr-labeler-spa",
          projects={
              "proj-abc": DoctrExportProject(
                  exported_at=datetime(2026, 6, 10, 11, 0, tzinfo=timezone.utc),
                  page_count=3,
                  tasks={
                      "recognition": DoctrExportTaskStats(item_count=90),
                      "detection": DoctrExportTaskStats(item_count=3),
                  },
              )
          },
      )


  def test_write_then_read_manifest_roundtrip(tmp_path):
      m = _sample_manifest()
      write_manifest(tmp_path, m)
      result = read_manifest(tmp_path)
      assert result is not None
      assert result.app == "pdomain-ocr-labeler-spa"
      assert result.projects["proj-abc"].page_count == 3
      assert result.projects["proj-abc"].tasks["recognition"].item_count == 90


  def test_read_manifest_missing_file_returns_none(tmp_path):
      result = read_manifest(tmp_path)
      assert result is None


  def test_read_manifest_corrupt_file_raises(tmp_path):
      manifest_path = tmp_path / "manifest.json"
      manifest_path.write_text("not valid json", encoding="utf-8")
      with pytest.raises(ValueError, match="corrupt"):
          read_manifest(tmp_path)


  def test_write_manifest_creates_parent_dir(tmp_path):
      export_root = tmp_path / "deep" / "nested" / "dir"
      write_manifest(export_root, _sample_manifest())
      assert (export_root / "manifest.json").exists()


  def test_write_manifest_is_atomic(tmp_path):
      """write_manifest must not leave a partial file visible to readers."""
      m = _sample_manifest()
      write_manifest(tmp_path, m)
      # A second write should fully replace the first atomically
      m2 = _sample_manifest()
      m2 = m2.model_copy(update={"app": "pdomain-ocr-trainer-spa"})
      write_manifest(tmp_path, m2)
      result = read_manifest(tmp_path)
      assert result is not None
      assert result.app == "pdomain-ocr-trainer-spa"


  def test_written_json_has_schema_key_not_schema_id(tmp_path):
      """The on-disk key must be 'schema', not 'schema_id'."""
      write_manifest(tmp_path, _sample_manifest())
      raw = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
      assert "schema" in raw
      assert "schema_id" not in raw


  def test_read_manifest_version_gt_1_returns_object(tmp_path):
      """Forward-compat: version > 1 must parse successfully, not crash."""
      data = _minimal_manifest_dict()
      data["version"] = 42
      (tmp_path / "manifest.json").write_text(json.dumps(data), encoding="utf-8")
      result = read_manifest(tmp_path)
      assert result is not None
      assert result.version == 42
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  uv run pytest tests/test_schemas_doctr_export.py -v -k "read_manifest or write_manifest or roundtrip or atomic or schema_key or version_gt"
  ```

  Expected: all 7 new tests `FAILED` — `ImportError: cannot import name 'read_manifest'`

- [ ] **Step 3: Implement `read_manifest` and `write_manifest` in `doctr_export.py`**

  Append to `pdomain_ops/schemas/doctr_export.py`:

  ```python
  def read_manifest(export_root: Path) -> DoctrExportManifest | None:
      """Read the manifest from ``<export_root>/manifest.json``.

      Returns ``None`` if the file does not exist.
      Raises ``ValueError`` with "corrupt" in the message if the file exists
      but cannot be parsed or fails model validation.

      Version > 1 is accepted with a log warning — caller decides to reject.
      """
      path = export_root / _MANIFEST_FILENAME
      if not path.exists():
          return None
      try:
          data = json.loads(path.read_text(encoding="utf-8"))
      except Exception as exc:
          raise ValueError(f"corrupt manifest at {path}: {exc}") from exc
      try:
          manifest = DoctrExportManifest.model_validate(data)
      except Exception as exc:
          raise ValueError(f"corrupt manifest at {path}: {exc}") from exc
      if manifest.version > _CURRENT_VERSION:
          _logger.warning(
              "manifest at %s has version %d > current %d; parsing best-effort",
              path,
              manifest.version,
              _CURRENT_VERSION,
          )
      return manifest


  def write_manifest(export_root: Path, manifest: DoctrExportManifest) -> None:
      """Write *manifest* to ``<export_root>/manifest.json`` atomically.

      Uses a temporary file in the same directory + ``os.replace`` so
      readers never see a partial write. Creates ``export_root`` if it
      does not exist.
      """
      export_root.mkdir(parents=True, exist_ok=True)
      dest = export_root / _MANIFEST_FILENAME
      fd, tmp_name = tempfile.mkstemp(dir=export_root, prefix=".manifest-", suffix=".tmp")
      try:
          with os.fdopen(fd, "w", encoding="utf-8") as f:
              f.write(manifest.model_dump_json(by_alias=True, indent=2))
          os.replace(tmp_name, dest)
      except Exception:
          try:
              os.unlink(tmp_name)
          except OSError:
              pass
          raise
  ```

- [ ] **Step 4: Run all doctr_export tests**

  ```bash
  uv run pytest tests/test_schemas_doctr_export.py -v
  ```

  Expected: `13 passed`

- [ ] **Step 5: Commit**

  ```bash
  git add pdomain_ops/schemas/doctr_export.py tests/test_schemas_doctr_export.py
  git commit -m "feat(schemas): read_manifest + write_manifest IO helpers"
  ```

---

## Task 8: Wire `DoctrExportManifest` into `schemas/emit.py` and `test_schemas_emit.py`

**Files:**

- Modify: `pdomain_ops/schemas/emit.py`
- Modify: `tests/test_schemas_emit.py`

`DoctrExportManifest` is a public Pydantic model consumed by pdomain-ui's TypeScript codegen. It must appear in `PUBLIC_MODELS` so `pdomain-ops-schemas` includes it. `DoctrExportTaskStats` and `DoctrExportProject` are composed types; emit them separately so pdomain-ui generates individual TS interfaces.

- [ ] **Step 1: Write the failing emit test**

  Append to `tests/test_schemas_emit.py`:

  ```python
  def test_emit_includes_doctr_export_models():
      data = _emit()
      assert "DoctrExportManifest" in data
      assert "DoctrExportProject" in data
      assert "DoctrExportTaskStats" in data
      schema = data["DoctrExportManifest"]
      props = schema.get("properties", {})
      assert "schema" in props  # alias, not schema_id
      assert "version" in props
      assert "projects" in props
  ```

- [ ] **Step 2: Run test to verify it fails**

  ```bash
  uv run pytest tests/test_schemas_emit.py::test_emit_includes_doctr_export_models -v
  ```

  Expected: `FAILED` — `AssertionError: 'DoctrExportManifest' not in data`

- [ ] **Step 3: Update `emit.py`**

  In `pdomain_ops/schemas/emit.py`, add to the import block:

  ```python
  from pdomain_ops.schemas.doctr_export import (
      DoctrExportManifest,
      DoctrExportProject,
      DoctrExportTaskStats,
  )
  ```

  And append to `PUBLIC_MODELS`:

  ```python
  PUBLIC_MODELS = (
      SuiteApp,
      InstalledApp,
      LayerColors,
      CommonUIPrefs,
      UIPrefs,
      LaunchResultOpened,
      LaunchResultRequiresHostConfig,
      StageResult,
      JobStatus,
      JobEvent,
      JobSpec,
      DeviceInfo,
      UpdateInfo,
      DoctrExportTaskStats,
      DoctrExportProject,
      DoctrExportManifest,
  )
  ```

- [ ] **Step 4: Run emit tests**

  ```bash
  uv run pytest tests/test_schemas_emit.py -v
  ```

  Expected: all pass (including all prior emit tests)

- [ ] **Step 5: Commit**

  ```bash
  git add pdomain_ops/schemas/emit.py tests/test_schemas_emit.py
  git commit -m "feat(schemas): add DoctrExportManifest to schemas emit"
  ```

---

## Task 9: Final CI verification + version bump note

**Files:** none (verification only)

- [ ] **Step 1: Run full test suite**

  ```bash
  cd /workspaces/ocr-container/pdomain-ops
  uv run pytest -n auto -v 2>&1 | tail -5
  ```

  Expected: all existing tests plus the new ones pass; `0 failed`.

- [ ] **Step 2: Run lint and type check**

  ```bash
  uv run ruff check pdomain_ops/suite/shared_paths.py pdomain_ops/suite/paths.py pdomain_ops/suite/__init__.py pdomain_ops/schemas/doctr_export.py pdomain_ops/schemas/emit.py
  uv run ruff format --check pdomain_ops/suite/shared_paths.py pdomain_ops/schemas/doctr_export.py
  uv run basedpyright pdomain_ops/suite/shared_paths.py pdomain_ops/schemas/doctr_export.py
  ```

  Expected: no errors. Fix any issues, restage, and recommit before proceeding.

- [ ] **Step 3: Run `make ci` (full pre-commit + test + build pipeline)**

  ```bash
  make ci
  ```

  Expected: green. If `pre-commit install` fails due to `core.hooksPath` in a worktree, run `uv run pre-commit run --all-files` directly instead.

- [ ] **Step 4: Version bump note (do NOT release yet)**

  These two features are additive (new module + new path helper). The next release is a **minor bump** (v0.10.0 → v0.11.0) per semver since they add public API.

  Consumers developing against this work in local-dev mode:

  ```bash
  # In labeler-spa or trainer-spa:
  make local-dev   # switches to local-editable pdomain-ops from workspace sibling
  make local-check # confirm pdomain-ops resolves from ../pdomain-ops
  ```

  Release is CT-gated. Do not run `make release-minor` without explicit authorization.

- [ ] **Step 5: Final commit if any CI-fix changes were needed**

  ```bash
  git add -p   # stage only lint/type fixes
  git commit -m "chore(lint): address ruff/pyright findings in shared-paths + doctr-export"
  ```

---

## Self-review

**Spec coverage:**

| Requirement | Task |
|---|---|
| `publish_shared_path(key, path, *, app)` exact signature | Tasks 3, 5 |
| `resolve_shared_path(key) -> Path \| None` exact signature | Tasks 3, 5 |
| Missing file → `None` | Task 3 |
| Stale path (target gone) → return recorded path, caller decides | Task 3 |
| Concurrent publish → atomic + serialised | Tasks 3, 4 |
| Bounded FileLock (PrefsLockTimeout pattern) | Tasks 2, 4 |
| `doctr-export-root` key first use documented | Task 3 (in docstring + storage spec) |
| `DoctrExportTaskStats`, `DoctrExportProject`, `DoctrExportManifest` | Task 6 |
| `"schema"` key alias (Python-safe field name) | Task 6 |
| Unknown task keys round-trip | Task 6 |
| `read_manifest` → `None` on missing, raise on corrupt | Task 7 |
| `write_manifest` → tmp + `os.replace` atomic | Task 7 |
| `version > 1` → log + return, no crash | Tasks 6, 7 |
| `emit.py` wired + test | Task 8 |
| `suite/__init__.py` re-exports + public surface test | Task 5 |
| `paths.py` helper + test | Task 1 |
| Version bump note (next minor, CT-gated release) | Task 9 |
| Downstream local-dev mode instructions | Task 9 |

**Placeholder scan:** No TBD/TODO/placeholder entries present.

**Type consistency:** All tasks use `DoctrExportManifest`, `DoctrExportProject`, `DoctrExportTaskStats`, `SharedPathsLockTimeout`, `publish_shared_path`, `resolve_shared_path` consistently throughout.

**FastAPI+SPA check:** Not applicable — pdomain-ops is a library, not an SPA server. No browser verification milestone needed.
