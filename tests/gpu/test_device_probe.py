from pdomain_ops.gpu.device_probe import DeviceInfoEntry, list_devices


def test_list_devices_always_includes_cpu():
    devices = list_devices()
    assert any(d.id == "cpu" for d in devices)
    cpu = next(d for d in devices if d.id == "cpu")
    assert cpu.label.lower().startswith("cpu")
    assert cpu.vram_total_mb is None


def test_cuda_entries_have_vram(monkeypatch):
    monkeypatch.setattr(
        "pdomain_ops.gpu.device_probe._probe_cuda",
        lambda: [
            DeviceInfoEntry(id="cuda:0", label="Fake GPU", vram_total_mb=8192, vram_free_mb=4096)
        ],
    )
    ids = [d.id for d in list_devices()]
    assert "cuda:0" in ids
    assert "cpu" in ids


def test_mps_included_when_available(monkeypatch):
    monkeypatch.setattr(
        "pdomain_ops.gpu.device_probe._probe_mps",
        lambda: [DeviceInfoEntry(id="mps", label="Apple MPS")],
    )
    ids = [d.id for d in list_devices()]
    assert "mps" in ids
    assert "cpu" in ids


def test_mps_not_included_when_unavailable(monkeypatch):
    monkeypatch.setattr(
        "pdomain_ops.gpu.device_probe._probe_mps",
        lambda: [],
    )
    ids = [d.id for d in list_devices()]
    assert "mps" not in ids
    assert "cpu" in ids
