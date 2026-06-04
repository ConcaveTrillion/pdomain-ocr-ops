"""Device preference resolution — per-app override -> suite default -> pick_device() auto."""

from __future__ import annotations

from pdomain_ops.gpu.device import pick_device
from pdomain_ops.suite.prefs import PrefsAdapter  # noqa: TC001
from pdomain_ops.suite.types import UIPrefs  # noqa: TC001


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
    override = app_section.get("compute_device") if isinstance(app_section, dict) else None
    if override:
        return override
    if snap.common.compute_device_default:
        return snap.common.compute_device_default
    return pick_device()
