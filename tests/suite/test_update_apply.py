"""Tests for update apply (editable guard + gated upgrade + rollback record)."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest

from pdomain_ops.suite.update import EditableInstallError, apply_upgrade

if TYPE_CHECKING:
    import pathlib


def test_refuses_editable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pdomain_ops.suite.update.is_editable_install", lambda dist: True)
    with pytest.raises(EditableInstallError):
        apply_upgrade("pdomain-ocr-simple-gui", run=lambda *a, **k: None)


def test_runs_uv_tool_upgrade_and_records_previous(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
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
    assert json.loads((tmp_path / "rb.json").read_text()) == {
        "dist_name": "pdomain-ocr-simple-gui",
        "previous_version": "0.9.0",
    }


def test_apply_upgrade_propagates_called_process_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """apply_upgrade with check=True propagates CalledProcessError on failure."""
    monkeypatch.setattr("pdomain_ops.suite.update.is_editable_install", lambda dist: False)
    monkeypatch.setattr("pdomain_ops.suite.update.installed_version", lambda dist: "0.9.0")
    monkeypatch.setattr(
        "pdomain_ops.suite.update._rollback_path", lambda dist: tmp_path / "rb.json"
    )

    def failing_run(cmd: list[str], **kwargs: object) -> None:
        raise subprocess.CalledProcessError(1, cmd)

    with pytest.raises(subprocess.CalledProcessError):
        apply_upgrade("pdomain-ocr-simple-gui", run=failing_run)
