import subprocess
from pathlib import Path

from pdomain_ops.gpu import device_probe
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
        list,
    )
    ids = [d.id for d in list_devices()]
    assert "mps" not in ids
    assert "cpu" in ids


def test_detect_nvidia_hardware_from_lspci_when_torch_cuda_unavailable(monkeypatch) -> None:
    """NVIDIA hardware presence is separate from CUDA runtime usability."""

    monkeypatch.setattr(device_probe, "_probe_cuda", list)
    monkeypatch.setattr(device_probe, "_probe_mps", list)
    monkeypatch.setattr(device_probe, "_nvidia_smi_names", list)
    monkeypatch.setattr(device_probe, "_proc_nvidia_names", list)
    monkeypatch.setattr(
        device_probe,
        "_lspci_nvidia_names",
        lambda: ["NVIDIA Corporation GA104 [GeForce RTX 3070]"],
    )

    devices = device_probe.list_devices()

    assert devices[0].id == "nvidia:0"
    assert devices[0].label == "NVIDIA Corporation GA104 [GeForce RTX 3070]"
    assert devices[0].available is False
    assert devices[0].kind == "nvidia"
    assert devices[0].reason == "NVIDIA GPU detected, but CUDA is not usable by PyTorch."
    assert devices[-1].id == "cpu"
    assert devices[-1].available is True


def test_detect_nvidia_hardware_deduplicates_against_cuda_devices(monkeypatch) -> None:
    """When CUDA is usable, do not show a second unavailable NVIDIA row."""

    monkeypatch.setattr(
        device_probe,
        "_probe_cuda",
        lambda: [
            device_probe.DeviceInfoEntry(
                id="cuda:0",
                label="NVIDIA GeForce RTX 3070",
                vram_total_mb=8192,
                vram_free_mb=4096,
                available=True,
                kind="cuda",
            )
        ],
    )
    monkeypatch.setattr(device_probe, "_probe_mps", list)
    monkeypatch.setattr(
        device_probe,
        "_detect_unusable_nvidia_hardware",
        lambda: ["NVIDIA GeForce RTX 3070"],
    )

    devices = device_probe.list_devices()

    assert [device.id for device in devices] == ["cuda:0", "cpu"]


def test_proc_nvidia_names_reads_information_files(tmp_path: Path, monkeypatch) -> None:
    gpu_dir = tmp_path / "gpus" / "0000:01:00.0"
    gpu_dir.mkdir(parents=True)
    (gpu_dir / "information").write_text(
        "Model: NVIDIA GeForce RTX 3070\nIRQ: 16\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(device_probe, "_PROC_NVIDIA_GPUS", tmp_path / "gpus")

    assert device_probe._proc_nvidia_names() == ["NVIDIA GeForce RTX 3070"]


def test_lspci_nvidia_names_parses_class_code_before_model(monkeypatch) -> None:
    monkeypatch.setattr(device_probe.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        device_probe.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=(
                "01:00.0 VGA compatible controller [0300]: "
                "NVIDIA Corporation GA104 [GeForce RTX 3070] [10de:2484]\n"
            ),
        ),
    )

    assert device_probe._lspci_nvidia_names() == [
        "NVIDIA Corporation GA104 [GeForce RTX 3070]",
    ]
