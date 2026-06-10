"""Tests for suite shared-paths API."""

from __future__ import annotations

import threading

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


def test_publish_relative_path_raises(tmp_path, monkeypatch):
    from pathlib import Path

    monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path))
    with pytest.raises(ValueError, match="absolute"):
        publish_shared_path("key", Path("relative/path"), app="x")


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
        pytest.fail(f"call did not return within {watchdog_s}s -- lock is blocking indefinitely")
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
        assert isinstance(exc, SharedPathsLockTimeout), (
            f"expected SharedPathsLockTimeout, got {exc!r}"
        )
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
        assert isinstance(exc, SharedPathsLockTimeout), (
            f"expected SharedPathsLockTimeout, got {exc!r}"
        )
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


def test_resolve_corrupt_json_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path))
    (tmp_path / "shared-paths.json").write_text("not valid json", encoding="utf-8")
    assert resolve_shared_path("any-key") is None


def test_resolve_non_dict_json_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path))
    (tmp_path / "shared-paths.json").write_text("[1, 2, 3]", encoding="utf-8")
    assert resolve_shared_path("any-key") is None
