import asyncio

from pdomain_ops.gpu.local_stage import LocalStageDispatcher


def test_run_stage_uses_device_resolver():
    seen = {}

    async def fake_impl(page_id, device, **kw):
        seen["dev"] = device
        return {"ok": True}

    d = LocalStageDispatcher(device_resolver=lambda: "cuda:0")
    d.register_stage("s", "cuda:0", fake_impl)
    asyncio.run(d.run_stage("s", "p1"))
    assert seen["dev"] == "cuda:0"
