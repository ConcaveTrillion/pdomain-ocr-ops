from fastapi import FastAPI
from fastapi.testclient import TestClient

from pdomain_ops.gpu.device_probe import DeviceInfoEntry
from pdomain_ops.suite.device_routes import mount_device_routes


def _client(monkeypatch, prefs, mode="local"):
    monkeypatch.setattr(
        "pdomain_ops.suite.device_routes.list_devices",
        lambda: [DeviceInfoEntry(id="cpu", label="CPU")],
    )
    app = FastAPI()
    mount_device_routes(app, prefs=prefs, app_id="app1", mode=mode)
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


def test_put_device_bad_scope_returns_400(monkeypatch, local_prefs):
    c = _client(monkeypatch, local_prefs)
    r = c.put("/api/suite/device", json={"scope": "invalid", "device": "cpu"})
    assert r.status_code == 400
    assert "scope" in r.json()["detail"].lower()


def test_put_device_suite_scope_persists_to_common(monkeypatch, local_prefs):
    c = _client(monkeypatch, local_prefs)
    r = c.put("/api/suite/device", json={"scope": "suite", "device": "cuda:0"})
    assert r.status_code == 200
    assert local_prefs.read().common.compute_device_default == "cuda:0"


def test_put_device_app_scope_clear_removes_app_override(monkeypatch, local_prefs):
    c = _client(monkeypatch, local_prefs)
    r = c.put("/api/suite/device", json={"scope": "app", "device": "cpu"})
    assert r.status_code == 200
    assert local_prefs.read().apps.get("app1", {}).get("compute_device") == "cpu"

    r = c.put("/api/suite/device", json={"scope": "app", "device": ""})

    assert r.status_code == 200
    assert r.json()["effective_source"] == "auto"
    assert "compute_device" not in local_prefs.read().apps.get("app1", {})


def test_put_device_suite_scope_clear_resets_suite_default(monkeypatch, local_prefs):
    c = _client(monkeypatch, local_prefs)
    r = c.put("/api/suite/device", json={"scope": "suite", "device": "cuda:0"})
    assert r.status_code == 200
    assert local_prefs.read().common.compute_device_default == "cuda:0"

    r = c.put("/api/suite/device", json={"scope": "suite", "device": ""})

    assert r.status_code == 200
    assert r.json()["effective_source"] == "auto"
    assert local_prefs.read().common.compute_device_default == ""


def test_get_device_includes_cuda_docs_url_and_unavailable_hardware(monkeypatch, local_prefs):
    app = FastAPI()
    mount_device_routes(app, prefs=local_prefs, app_id="app1", mode="local")
    monkeypatch.setattr(
        "pdomain_ops.suite.device_routes.list_devices",
        lambda: [
            DeviceInfoEntry(
                id="nvidia:0",
                label="NVIDIA RTX",
                available=False,
                kind="nvidia",
                reason="no cuda",
            ),
            DeviceInfoEntry(id="cpu", label="CPU"),
        ],
    )
    c = TestClient(app)

    r = c.get("/api/suite/device")

    assert r.status_code == 200
    body = r.json()
    assert body["cuda_docs_url"] == "/docs/runbooks/cuda-setup.md"
    nvidia = next(d for d in body["available"] if d["id"] == "nvidia:0")
    assert nvidia["available"] is False
    assert nvidia["kind"] == "nvidia"
    assert nvidia["reason"] == "no cuda"


def test_get_device_non_local_mode_returns_mode_only(monkeypatch, local_prefs):
    c = _client(monkeypatch, local_prefs, mode="hosted")
    r = c.get("/api/suite/device")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "hosted"
    assert body.get("offload_target") is None
    # Non-local mode returns no device list
    assert body.get("available", []) == []


def test_get_device_translates_auto_local_to_cuda_id(monkeypatch, local_prefs):
    monkeypatch.setattr(
        "pdomain_ops.suite.device_routes.list_devices",
        lambda: [
            DeviceInfoEntry(id="cuda:0", label="GPU 0"),
            DeviceInfoEntry(id="cpu", label="CPU"),
        ],
    )
    monkeypatch.setattr("pdomain_ops.suite.device_prefs.pick_device", lambda: "local")
    app = FastAPI()
    mount_device_routes(app, prefs=local_prefs, app_id="app1", mode="local")
    c = TestClient(app)

    body = c.get("/api/suite/device").json()

    assert body["current"] == "cuda:0"
    assert body["current"] in {d["id"] for d in body["available"]}
