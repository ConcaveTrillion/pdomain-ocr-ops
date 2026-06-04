"""Tests for single-instance pidfile lock + stale reap."""

from __future__ import annotations

import os

from pdomain_ops.suite.single_instance import InstanceLock, _pid_alive, acquire, read_live


def test_acquire_then_read(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "pdomain_ops.suite.single_instance._lock_path",
        lambda app_id: tmp_path / f"{app_id}.json",
    )
    current_pid = os.getpid()
    lock = acquire("ocr", port=8004, pid=current_pid)
    assert isinstance(lock, InstanceLock)
    live = read_live("ocr")
    assert live is not None
    assert live["port"] == 8004
    assert live["pid"] == current_pid


def test_stale_reaped(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "pdomain_ops.suite.single_instance._lock_path",
        lambda app_id: tmp_path / f"{app_id}.json",
    )
    monkeypatch.setattr("pdomain_ops.suite.single_instance._pid_alive", lambda pid: False)
    acquire("ocr", port=8004, pid=999999)
    assert read_live("ocr") is None  # dead pid → reaped


def test_pid_alive_permission_error_means_alive(monkeypatch):
    """PermissionError from os.kill means process EXISTS but we can't signal it.

    _pid_alive must return True (alive) in this case so the pidfile is NOT
    reaped as stale.
    """

    def _raise_permission(pid: int, sig: int) -> None:
        raise PermissionError("operation not permitted")

    monkeypatch.setattr(os, "kill", _raise_permission)
    assert _pid_alive(12345) is True


def test_pid_alive_process_lookup_error_means_dead(monkeypatch):
    """ProcessLookupError from os.kill means process does NOT exist."""

    def _raise_lookup(pid: int, sig: int) -> None:
        raise ProcessLookupError("no such process")

    monkeypatch.setattr(os, "kill", _raise_lookup)
    assert _pid_alive(12345) is False


def test_permission_error_pidfile_not_reaped(monkeypatch, tmp_path):
    """When os.kill raises PermissionError, the pidfile must NOT be removed.

    This ensures a process owned by a different user is not treated as stale.
    """
    monkeypatch.setattr(
        "pdomain_ops.suite.single_instance._lock_path",
        lambda app_id: tmp_path / f"{app_id}.json",
    )

    def _raise_permission(pid: int, sig: int) -> None:
        raise PermissionError("operation not permitted")

    monkeypatch.setattr(os, "kill", _raise_permission)

    # Write a pidfile for a "different-user" process.
    acquire("ocr", port=8004, pid=99999)
    # read_live must return the live record, not None.
    live = read_live("ocr")
    assert live is not None, "process with PermissionError should be treated as alive"
    assert live["pid"] == 99999


def test_second_acquire_overwrites_first(monkeypatch, tmp_path):
    """A second acquire() for the same app_id succeeds and overwrites the prior pidfile."""
    monkeypatch.setattr(
        "pdomain_ops.suite.single_instance._lock_path",
        lambda app_id: tmp_path / f"{app_id}.json",
    )
    current_pid = os.getpid()

    lock1 = acquire("ocr", port=8001, pid=current_pid)
    assert lock1.port == 8001

    # Second acquire with a different port — should overwrite.
    lock2 = acquire("ocr", port=8002, pid=current_pid)
    assert lock2.port == 8002

    live = read_live("ocr")
    assert live is not None
    assert live["port"] == 8002  # new value wins
