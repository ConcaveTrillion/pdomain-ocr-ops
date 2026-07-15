"""Device preference resolution — per-app override -> suite default -> pick_device() auto."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pdomain_ops.gpu.device import pick_device

if TYPE_CHECKING:
    from pdomain_ops.suite.prefs import PrefsAdapter
    from pdomain_ops.suite.types import UIPrefs


def resolve_effective_device(
    prefs: PrefsAdapter,
    app_id: str,
    *,
    snapshot: UIPrefs | None = None,
) -> str:
    """Return the effective compute device for *app_id*.

    Resolution order:
    1. Per-app ``compute_device`` pref (``apps.<app_id>.compute_device``).
    2. Suite-wide default (``common.compute_device_default``).
    3. Auto-detection via ``pick_device()``.

    If *snapshot* is provided it is used directly; otherwise ``prefs.read()``
    is called.  Pass an already-read snapshot to avoid a redundant read.
    """
    snap = snapshot if snapshot is not None else prefs.read()
    app_section = snap.apps.get(app_id, {})
    override = app_section.get("compute_device")
    if override:
        return override
    if snap.common.compute_device_default:
        return snap.common.compute_device_default
    return pick_device()


def clear_device_preference(prefs: PrefsAdapter, app_id: str, *, scope: str) -> None:
    """Clear a persisted compute-device preference for *scope*."""
    if scope == "suite":
        snap = prefs.read()
        common = snap.common
        common.compute_device_default = ""
        prefs.write_common(common)
    elif scope == "app":
        snap = prefs.read()
        section = dict(snap.apps.get(app_id) or {})
        section.pop("compute_device", None)
        prefs.write_app(app_id, section)
    else:
        raise ValueError("scope must be 'app' or 'suite'")
