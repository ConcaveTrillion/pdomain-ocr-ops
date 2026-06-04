"""Tests for single-instance pidfile lock + stale reap."""

from __future__ import annotations

import os

from pdomain_ops.suite.single_instance import InstanceLock, acquire, read_live


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
