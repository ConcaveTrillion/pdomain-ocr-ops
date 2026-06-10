"""Tests for suite shared-paths API."""

from __future__ import annotations

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
