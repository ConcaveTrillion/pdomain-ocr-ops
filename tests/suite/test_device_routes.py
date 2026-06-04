from fastapi import FastAPI
from fastapi.testclient import TestClient

from pdomain_ops.suite.device_routes import mount_device_routes


def _client(monkeypatch, prefs):
    monkeypatch.setattr(
        "pdomain_ops.suite.device_routes.list_devices",
        lambda: [
            type(
                "D", (), {"id": "cpu", "label": "CPU", "vram_total_mb": None, "vram_free_mb": None}
            )()
        ],
    )
    app = FastAPI()
    mount_device_routes(app, prefs=prefs, app_id="app1")
    return TestClient(app)


def test_get_device_local_mode(monkeypatch, local_prefs):
    r = _client(monkeypatch, local_prefs).get("/api/suite/device")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "local"
    assert any(d["id"] == "cpu" for d in body["available"])
    assert "current" in body
    assert "effective_source" in body


def test_put_device_persists(monkeypatch, local_prefs):
    c = _client(monkeypatch, local_prefs)
    r = c.put("/api/suite/device", json={"scope": "app", "device": "cpu"})
    assert r.status_code == 200
    assert local_prefs.read().apps.get("app1", {}).get("compute_device") == "cpu"
