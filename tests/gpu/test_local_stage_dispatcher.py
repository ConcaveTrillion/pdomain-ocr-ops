from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pdomain_ops.gpu.local_stage import LocalStageDispatcher, UnknownStageError
from pdomain_ops.gpu.types import OcrBatchRequest, StageResult


@pytest.mark.asyncio
async def test_construct_with_empty_registry():
    dispatcher = LocalStageDispatcher(registry={})
    assert dispatcher is not None


@pytest.mark.asyncio
async def test_run_stage_unknown_id_raises():
    dispatcher = LocalStageDispatcher(registry={})
    with pytest.raises(UnknownStageError) as exc_info:
        await dispatcher.run_stage("missing", "page-1")
    assert "missing" in str(exc_info.value)


@pytest.mark.asyncio
async def test_run_stage_dispatches_to_registered_impl(monkeypatch):
    monkeypatch.setenv("PDOMAIN_GPU_BACKEND", "cpu")

    async def fake(page_id, device, **kwargs):
        return {"foo": "bar"}

    registry = {("ocr", "cpu"): fake}
    dispatcher = LocalStageDispatcher(registry=registry)
    result = await dispatcher.run_stage("ocr", "page-1")
    assert isinstance(result, StageResult)
    assert result.stage_id == "ocr"
    assert result.page_id == "page-1"
    assert result.device == "cpu"
    assert result.duration_ms >= 0
    assert result.metadata == {"foo": "bar"}


@pytest.mark.asyncio
async def test_run_stage_falls_through_to_cpu_when_local_missing(monkeypatch):
    monkeypatch.setenv("PDOMAIN_GPU_BACKEND", "local")

    async def cpu_impl(page_id, device, **kwargs):
        return {}

    registry = {("ocr", "cpu"): cpu_impl}
    dispatcher = LocalStageDispatcher(registry=registry)
    # Should fall through from "local" to "cpu"
    result = await dispatcher.run_stage("ocr", "page-1")
    assert result.device == "cpu"


@pytest.mark.asyncio
async def test_run_stage_propagates_kwargs(monkeypatch):
    monkeypatch.setenv("PDOMAIN_GPU_BACKEND", "cpu")
    received_kwargs = {}

    async def impl(page_id, device, **kwargs):
        received_kwargs.update(kwargs)
        return {}

    registry = {("ocr", "cpu"): impl}
    dispatcher = LocalStageDispatcher(registry=registry)
    await dispatcher.run_stage("ocr", "page-1", threshold=0.9, mode="fast")
    assert received_kwargs == {"threshold": 0.9, "mode": "fast"}


@pytest.mark.asyncio
async def test_run_stage_accepts_cuda_id():
    async def fake(page_id, device, **kwargs):
        return {}

    registry = {("ocr", "local"): fake}
    dispatcher = LocalStageDispatcher(registry=registry)
    result = await dispatcher.run_stage("ocr", "p1", device="cuda:0")
    assert result.device == "local"  # registry hit, no silent cpu fallback


@pytest.mark.asyncio
async def test_run_stage_canonicalizes_resolver_output():
    # red-team catch: the resolver path must be canonicalized too, or a stored
    # "cuda:0" pref reintroduces the exact silent-cpu-fallback bug this fixes
    async def fake(page_id, device, **kwargs):
        return {}

    registry = {("ocr", "local"): fake}
    dispatcher = LocalStageDispatcher(registry=registry, device_resolver=lambda: "cuda:0")
    result = await dispatcher.run_stage("ocr", "p1")
    assert result.device == "local"


@pytest.mark.asyncio
async def test_batch_uses_device_resolver_when_request_has_no_device(monkeypatch):
    import pdomain_book_tools.hf as _hf_mod
    import pdomain_book_tools.ocr.doctr_support as _doctr_support

    import pdomain_ops.gpu.default_stages as ds
    import pdomain_ops.gpu.doctr_batch as doctr_batch_mod

    ds._predictor_cache.clear()
    monkeypatch.setattr(
        _hf_mod, "resolve_ocr_models", lambda: (Path("/fake/det.pt"), Path("/fake/reco.pt"))
    )
    monkeypatch.setattr(
        _doctr_support,
        "get_finetuned_torch_doctr_predictor",
        lambda d, r, det_bs=2, reco_bs=128: object(),
    )

    captured = {}

    def fake_run_doctr_batch(
        images, *, predictor, device, build_smaller=None, source_identifiers=None
    ):
        captured["device"] = device
        page = MagicMock()
        page.to_dict.return_value = {}
        return [page]

    monkeypatch.setattr(doctr_batch_mod, "run_doctr_batch", fake_run_doctr_batch)

    dispatcher = LocalStageDispatcher(device_resolver=lambda: "cpu")
    req = OcrBatchRequest(images=[b"x"], source_identifiers=["s/0"], engine="doctr", language="en")
    await dispatcher.run_ocr_batch(req)

    assert captured["device"] == "cpu"
