"""Suite shared-paths API: publish and resolve well-known data paths."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, override

import filelock

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

    timeout: float

    def __init__(self, lock_file: str, timeout: float) -> None:
        super().__init__(lock_file)
        self.timeout = timeout

    @override
    def __str__(self) -> str:
        return (
            f"Could not acquire shared-paths lock on {self.lock_file!r} within "
            f"{self.timeout}s; another process may be holding it (orphaned?)."
        )


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


def _read_raw(json_path: Path) -> dict[str, Any]:
    """Read shared-paths.json, returning an empty structure on any error."""
    if not json_path.exists():
        return {"paths": {}}
    try:
        raw: Any = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — JSON parse failure treated as empty/default (resilience)
        return {"paths": {}}
    else:
        if isinstance(raw, dict):
            return raw  # type: ignore[return-value]
        return {"paths": {}}


def _atomic_write(json_path: Path, data: dict[str, Any]) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=json_path.parent, prefix=".shared-paths-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp_name, json_path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
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
        path: The filesystem path to publish. Must be absolute.
        app: The publishing app id (informational, stored alongside the path).
        lock_timeout: Seconds to wait for the file lock. Falls back to
            ``PDOMAIN_SHARED_PATHS_LOCK_TIMEOUT`` env var, then
            :data:`DEFAULT_LOCK_TIMEOUT`.

    Raises:
        ValueError: If *path* is not absolute.
        SharedPathsLockTimeout: If the lock cannot be acquired in time.
    """
    if not path.is_absolute():
        raise ValueError(f"publish_shared_path: path must be absolute, got {path!r}")
    timeout = _resolve_timeout(lock_timeout)
    json_path = _shared_paths_json()
    lock_file = str(json_path.with_suffix(".json.lock"))
    lock = filelock.FileLock(lock_file, timeout=timeout)
    try:
        with lock:
            data = _read_raw(json_path)
            paths: dict[str, Any] = data.get("paths") or {}
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

    paths: dict[str, Any] = data.get("paths") or {}
    entry = paths.get(key)
    if entry is None or not isinstance(entry, dict):
        return None
    raw_path: str | None = entry.get("path")
    if not raw_path:
        return None
    return Path(raw_path)
