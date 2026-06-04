"""Tests for /api/suite/update GET/POST routes."""

from __future__ import annotations

import subprocess

from fastapi import FastAPI
from fastapi.testclient import TestClient

from pdomain_ops.suite.update import EditableInstallError
from pdomain_ops.suite.update_routes import mount_update_routes


def test_get_update(monkeypatch: object) -> None:
    monkeypatch.setattr(  # type: ignore[union-attr]
        "pdomain_ops.suite.update_routes.check_latest",
        lambda **k: {
            "current": "0.9.0",
            "latest": "0.10.0",
            "update_available": True,
            "changelog_url": "x",
            "channel": "stable",
        },
    )
    app = FastAPI()
    mount_update_routes(app, dist_name="pdomain-ocr-simple-gui", index_url="https://x")
    r = TestClient(app).get("/api/suite/update")
    assert r.status_code == 200
    assert r.json()["update_available"] is True


def test_post_update_invokes_apply(monkeypatch: object) -> None:
    seen: dict[str, str] = {}
    monkeypatch.setattr(  # type: ignore[union-attr]
        "pdomain_ops.suite.update_routes.apply_upgrade",
        lambda dist, **k: seen.setdefault("dist", dist),
    )
    app = FastAPI()
    mount_update_routes(app, dist_name="pdomain-ocr-simple-gui", index_url="https://x")
    r = TestClient(app).post("/api/suite/update")
    assert r.status_code in (200, 202)
    assert seen["dist"] == "pdomain-ocr-simple-gui"


def test_post_update_returns_409_on_editable(monkeypatch: object) -> None:
    """EditableInstallError raised by apply_upgrade maps to HTTP 409."""

    def raise_editable(dist: str, **k: object) -> None:
        raise EditableInstallError(f"{dist!r} is editable")

    monkeypatch.setattr(  # type: ignore[union-attr]
        "pdomain_ops.suite.update_routes.apply_upgrade",
        raise_editable,
    )
    app = FastAPI()
    mount_update_routes(app, dist_name="pdomain-ocr-simple-gui", index_url="https://x")
    r = TestClient(app).post("/api/suite/update")
    assert r.status_code == 409
    assert "editable" in r.json()["detail"]


def test_post_update_returns_502_on_upgrade_failure(monkeypatch: object) -> None:
    """CalledProcessError from the subprocess maps to HTTP 502."""

    def raise_cpe(dist: str, **k: object) -> None:
        raise subprocess.CalledProcessError(1, ["uv", "tool", "upgrade", dist])

    monkeypatch.setattr(  # type: ignore[union-attr]
        "pdomain_ops.suite.update_routes.apply_upgrade",
        raise_cpe,
    )
    app = FastAPI()
    mount_update_routes(app, dist_name="pdomain-ocr-simple-gui", index_url="https://x")
    r = TestClient(app).post("/api/suite/update")
    assert r.status_code == 502
    assert "upgrade failed" in r.json()["detail"]
