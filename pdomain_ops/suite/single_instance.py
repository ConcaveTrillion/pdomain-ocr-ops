"""Single-instance pidfile lock with stale-process reap.

Implements a lightweight JSON-based pidfile under ``suite_data_dir()/locks/``
that lets a pd-* desktop app verify it is the only running instance, or focus
an already-running instance instead of spawning a duplicate.

Design notes
------------
- The registry (``installed.toml``) has *no* pid field by design; the lockfile
  is a separate artefact in ``locks/`` so it does not pollute the registry.
- A stale pidfile (process no longer alive) is silently reaped on ``read_live``.
- ``InstanceLock`` is a thin value object — callers hold it for the duration of
  the process lifetime (no explicit release needed; the OS removes locks when the
  process exits via normal GC or crash).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from filelock import FileLock

from pdomain_ops.suite.paths import suite_data_dir

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class InstanceLock:
    """Returned by ``acquire()`` to confirm lock ownership.

    Attributes:
        app_id: The application identifier.
        pid: The pid written to the lockfile.
        port: The port written to the lockfile.
        path: The lockfile path.
    """

    app_id: str
    pid: int
    port: int
    path: Path


def _lock_path(app_id: str) -> Path:
    """Return the JSON lockfile path for *app_id*.

    Args:
        app_id: The application identifier.

    Returns:
        A path like ``<suite_data_dir>/locks/<app_id>.json``.
    """
    locks_dir = suite_data_dir() / "locks"
    locks_dir.mkdir(parents=True, exist_ok=True)
    return locks_dir / f"{app_id}.json"


def _pid_alive(pid: int) -> bool:
    """Return True if process *pid* is alive.

    Args:
        pid: The process ID to probe.

    Returns:
        ``True`` if the process exists, ``False`` if it is dead or unreachable.
    """
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def acquire(app_id: str, *, port: int, pid: int) -> InstanceLock:
    """Write a pidfile for *app_id* and return an ``InstanceLock``.

    Overwrites any existing (possibly stale) pidfile under a filelock so
    concurrent callers cannot race on the write.

    Args:
        app_id: The application identifier.
        port: The HTTP port the app is listening on.
        pid: The process ID to record (typically ``os.getpid()``).

    Returns:
        An :class:`InstanceLock` confirming ownership.
    """
    path = _lock_path(app_id)
    lock_file = path.with_suffix(".lock")
    with FileLock(str(lock_file)):
        path.write_text(json.dumps({"pid": pid, "port": port}), encoding="utf-8")
    return InstanceLock(app_id=app_id, pid=pid, port=port, path=path)


def read_live(app_id: str) -> dict[str, int] | None:
    """Return ``{pid, port}`` for *app_id* if the process is still alive.

    If the lockfile does not exist or the recorded pid is no longer alive,
    the stale lockfile is removed and ``None`` is returned.

    Args:
        app_id: The application identifier to look up.

    Returns:
        ``{"pid": <int>, "port": <int>}`` if the process is alive,
        ``None`` if the lockfile is absent or stale.
    """
    path = _lock_path(app_id)
    if not path.exists():
        return None
    try:
        data: dict[str, int] = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        path.unlink(missing_ok=True)
        return None

    pid = data.get("pid")
    if pid is None or not _pid_alive(pid):
        path.unlink(missing_ok=True)
        return None

    return data
