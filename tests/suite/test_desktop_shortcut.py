"""Tests for Linux desktop shortcut install/remove."""

from __future__ import annotations

import sys

import pytest

from pdomain_ops.suite.desktop import install_shortcut, remove_shortcut
from pdomain_ops.suite.types import InstalledApp


def _app() -> InstalledApp:
    return InstalledApp(
        app_id="ocr",
        package="p",
        version="1",
        binary="/usr/bin/ocr",
        default_port=8004,
        icon="ocr",
        display_name="OCR",
    )


@pytest.mark.skipif(sys.platform != "linux", reason="linux shortcut")
def test_install_writes_desktop_file(monkeypatch, tmp_path):
    monkeypatch.setattr("pdomain_ops.suite.desktop._applications_dir", lambda: tmp_path)
    app = _app()
    install_shortcut(app)
    f = tmp_path / "pdomain-ocr.desktop"
    text = f.read_text()
    assert "Exec=/usr/bin/ocr --desktop" in text
    assert "Name=OCR" in text
    remove_shortcut("ocr")
    assert not f.exists()


@pytest.mark.skipif(sys.platform == "linux", reason="non-linux raises NotImplementedError")
def test_install_raises_on_non_linux():
    with pytest.raises(NotImplementedError):
        install_shortcut(_app())
