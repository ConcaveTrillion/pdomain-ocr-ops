"""Tests for update apply (editable guard + gated upgrade + rollback record)."""

from __future__ import annotations

import pytest

from pdomain_ops.suite.update import EditableInstallError, apply_upgrade


def test_refuses_editable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    monkeypatch.setattr("pdomain_ops.suite.update.is_editable_install", lambda dist: True)
    with pytest.raises(EditableInstallError):
        apply_upgrade("pdomain-ocr-simple-gui", run=lambda *a, **k: None)


def test_runs_uv_tool_upgrade_and_records_previous(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    monkeypatch.setattr("pdomain_ops.suite.update.is_editable_install", lambda dist: False)
    monkeypatch.setattr("pdomain_ops.suite.update.installed_version", lambda dist: "0.9.0")
    monkeypatch.setattr(
        "pdomain_ops.suite.update._rollback_path", lambda dist: tmp_path / "rb.json"
    )
    calls: list[list[str]] = []
    apply_upgrade("pdomain-ocr-simple-gui", run=lambda cmd, **k: calls.append(cmd))
    assert calls
    assert calls[0][:3] == ["uv", "tool", "upgrade"]
    assert (tmp_path / "rb.json").read_text().strip()  # previous version recorded
