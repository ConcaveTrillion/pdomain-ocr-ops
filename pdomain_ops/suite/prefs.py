"""PrefsAdapter Protocol + LocalFilePrefs implementation."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any, runtime_checkable

import filelock
from typing_extensions import Protocol, override

from pdomain_ops.suite.types import CommonUIPrefs, UIPrefs

if TYPE_CHECKING:
    from collections.abc import Generator

_logger = logging.getLogger(__name__)

# Finite default lock-acquisition timeout (seconds). NEVER -1 (block forever):
# a stuck/orphaned lock holder (e.g. a killed `pytest -n auto` xdist worker or a
# leftover e2e uvicorn subprocess) must surface as a fast, typed error rather
# than wedging the caller indefinitely. Matches the 5s value the simple-gui
# TimeoutBoundedPrefs containment workaround used. Override per-instance via the
# ``lock_timeout`` constructor arg or globally via PDOMAIN_PREFS_LOCK_TIMEOUT.
DEFAULT_LOCK_TIMEOUT: float = 5.0

#: Env var (PDOMAIN_* convention, matching PDOMAIN_GPU_BACKEND / PDOMAIN_INDEX_URL)
#: that overrides the default lock timeout. The explicit ``lock_timeout=`` kwarg
#: takes precedence over this. An unparseable value falls back to the default.
LOCK_TIMEOUT_ENV_VAR = "PDOMAIN_PREFS_LOCK_TIMEOUT"


class PrefsLockTimeout(filelock.Timeout):
    """Raised when a prefs file lock cannot be acquired within the timeout.

    Subclasses ``filelock.Timeout`` (which subclasses ``TimeoutError`` /
    ``OSError``) so existing callers that already catch the upstream exception
    keep working, while new callers can catch this typed, documented error and
    map it to (for example) an HTTP 503. The message names the prefs lock file
    and the timeout so an operator can find the wedged lock holder.
    """

    def __init__(self, lock_file: str, timeout: float) -> None:
        super().__init__(lock_file)
        self.timeout = timeout

    @override
    def __str__(self) -> str:
        return (
            f"Could not acquire prefs lock on {self.lock_file!r} within "
            f"{self.timeout}s; another process may be holding it (orphaned?)."
        )


def _resolve_lock_timeout(lock_timeout: float | None) -> float:
    """Resolve the effective lock timeout.

    Precedence: explicit ``lock_timeout`` kwarg > ``PDOMAIN_PREFS_LOCK_TIMEOUT``
    env var > :data:`DEFAULT_LOCK_TIMEOUT`. An unparseable env value is ignored
    (falls back to the default) so a typo can never reintroduce a forever-block.
    """
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


@runtime_checkable
class PrefsAdapter(Protocol):
    """Protocol for suite UI preferences storage implementations."""

    def read(self) -> UIPrefs:
        """Read current prefs; return defaults if not yet persisted."""
        ...

    def write_common(self, common: CommonUIPrefs) -> None:
        """Persist the common section; preserve per-app sections."""
        ...

    def write_app(self, app_id: str, payload: dict[str, Any]) -> None:
        """Persist the per-app blob for app_id; preserve other sections."""
        ...


class LocalFilePrefs:
    """Local JSON file-based prefs adapter.

    All reads and writes serialize through a :class:`filelock.FileLock` acquired
    with a FINITE timeout (see :data:`DEFAULT_LOCK_TIMEOUT`). If the lock cannot
    be acquired in time -- e.g. an orphaned holder is wedged -- the call raises
    :class:`PrefsLockTimeout` instead of blocking forever.
    """

    def __init__(self, root: Path | None = None, *, lock_timeout: float | None = None) -> None:
        if root is None:
            from pdomain_ops.suite.paths import ui_prefs_json_path

            root = ui_prefs_json_path()
        self._path = Path(root)
        self._lock_path = self._path.with_suffix(".json.lock")
        self._lock_timeout = _resolve_lock_timeout(lock_timeout)

    @contextlib.contextmanager
    def _acquire(self) -> Generator[None]:
        """Acquire the prefs lock with a finite timeout, releasing on exit.

        Uses ``with filelock.FileLock(...)`` so the lock's ``__enter__`` honors
        the finite ``timeout`` set on the instance. Remaps the resulting
        ``filelock.Timeout`` to the typed :class:`PrefsLockTimeout`.
        """
        lock = filelock.FileLock(str(self._lock_path), timeout=self._lock_timeout)
        try:
            with lock:
                yield
        except filelock.Timeout as exc:
            raise PrefsLockTimeout(str(self._lock_path), self._lock_timeout) from exc

    def _read_raw(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return {}

    def _write_raw(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2, default=str))

    def read(self) -> UIPrefs:
        """Read prefs, returning defaults if file doesn't exist. Non-destructive.

        Raises :class:`PrefsLockTimeout` if the file lock cannot be acquired
        within the configured timeout.
        """
        with self._acquire():
            raw = self._read_raw()

        if not raw:
            return UIPrefs()

        # Warn about unknown keys in common section
        common_raw = raw.get("common", {})
        known_common_keys = {
            "theme",
            "density",
            "accent",
            "font_size_base",
            "font_scale",
            "layer_colors",
            "compute_device_default",
            "update_policy",
        }
        unknown_keys = set(common_raw.keys()) - known_common_keys
        for key in unknown_keys:
            warnings.warn(f"Unknown key in UIPrefs common section: {key!r} (ignored)", stacklevel=2)

        return UIPrefs.model_validate(raw)

    def write_common(self, common: CommonUIPrefs) -> None:
        """Update only the common section, preserving apps section.

        Raises :class:`PrefsLockTimeout` if the file lock cannot be acquired
        within the configured timeout.
        """
        with self._acquire():
            data = self._read_raw()
            data["common"] = json.loads(common.model_dump_json())
            self._write_raw(data)

    def write_app(self, app_id: str, payload: dict[str, Any]) -> None:
        """Update only the per-app section for app_id, preserving everything else.

        Raises :class:`PrefsLockTimeout` if the file lock cannot be acquired
        within the configured timeout.
        """
        with self._acquire():
            data = self._read_raw()
            if "apps" not in data:
                data["apps"] = {}
            data["apps"][app_id] = payload
            self._write_raw(data)
