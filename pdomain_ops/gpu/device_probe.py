"""Device probe helper — lists available compute targets with VRAM info."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceInfoEntry:
    """A single available compute target with optional VRAM information."""

    id: str  # "cpu" | "cuda:0" | "mps"
    label: str
    vram_total_mb: int | None = None
    vram_free_mb: int | None = None


def _probe_cuda() -> list[DeviceInfoEntry]:
    try:
        import torch
    except ImportError:
        return []
    if not torch.cuda.is_available():
        return []
    out: list[DeviceInfoEntry] = []
    for i in range(torch.cuda.device_count()):
        free, total = torch.cuda.mem_get_info(i)
        out.append(
            DeviceInfoEntry(
                id=f"cuda:{i}",
                label=torch.cuda.get_device_name(i),
                vram_total_mb=total // (1024 * 1024),
                vram_free_mb=free // (1024 * 1024),
            )
        )
    return out


def list_devices() -> list[DeviceInfoEntry]:
    """Return all available compute targets; CPU is always included last."""
    return [*_probe_cuda(), DeviceInfoEntry(id="cpu", label="CPU")]
