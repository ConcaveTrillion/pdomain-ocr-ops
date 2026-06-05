"""GET/PUT /api/suite/device — local-mode-gated compute-target endpoint."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from pdomain_ops.gpu.device_probe import DeviceInfoEntry, list_devices
from pdomain_ops.suite.device_prefs import clear_device_preference, resolve_effective_device

if TYPE_CHECKING:
    from pdomain_ops.suite.prefs import PrefsAdapter


def _device_to_dict(d: DeviceInfoEntry) -> dict[str, object]:
    """Convert a DeviceInfoEntry to a JSON-safe dict."""
    return dataclasses.asdict(d)


class DeviceInfo(BaseModel):
    """Response model for GET/PUT /api/suite/device."""

    mode: str
    available: list[dict[str, object]] = []
    current: str | None = None
    effective_source: str | None = None  # "app" | "suite" | "auto"
    offload_target: str | None = None
    cuda_docs_url: str = "/docs/runbooks/cuda-setup.md"


class DevicePutBody(BaseModel):
    """Request body for PUT /api/suite/device."""

    scope: str  # "app" | "suite"
    device: str


def mount_device_routes(
    app: FastAPI,
    *,
    prefs: PrefsAdapter,
    app_id: str,
    mode: str = "local",
) -> None:
    """Mount GET/PUT /api/suite/device onto *app*."""

    @app.get("/api/suite/device", response_model=DeviceInfo)
    def get_device() -> DeviceInfo:
        """Return the current compute-target state."""
        if mode != "local":
            return DeviceInfo(mode=mode, offload_target=None)
        snap = prefs.read()
        app_override = (snap.apps.get(app_id) or {}).get("compute_device")
        if app_override:
            source = "app"
        elif snap.common.compute_device_default:
            source = "suite"
        else:
            source = "auto"
        return DeviceInfo(
            mode="local",
            available=[_device_to_dict(d) for d in list_devices()],
            current=resolve_effective_device(prefs, app_id, snapshot=snap),
            effective_source=source,
        )

    @app.put("/api/suite/device", response_model=DeviceInfo)
    def put_device(body: DevicePutBody) -> DeviceInfo:
        """Persist the compute-device preference and return the updated state."""
        if body.device == "":
            try:
                clear_device_preference(prefs, app_id, scope=body.scope)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        elif body.scope == "suite":
            snap = prefs.read()
            common = snap.common
            common.compute_device_default = body.device
            prefs.write_common(common)
        elif body.scope == "app":
            snap = prefs.read()
            section = dict(snap.apps.get(app_id) or {})
            section["compute_device"] = body.device
            prefs.write_app(app_id, section)
        else:
            raise HTTPException(status_code=400, detail="scope must be 'app' or 'suite'")
        return get_device()
