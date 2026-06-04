"""Tests for /api/suite/update GET/POST routes."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

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
