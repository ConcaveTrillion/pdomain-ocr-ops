from pdomain_ops.suite.device_prefs import resolve_effective_device


class _Prefs:
    def __init__(self, common_default=None, app_overrides=None):
        self._common = common_default
        self._apps = app_overrides or {}

    def read(self):
        from pdomain_ops.suite.types import CommonUIPrefs, UIPrefs

        return UIPrefs(common=CommonUIPrefs(compute_device_default=self._common), apps=self._apps)


def test_app_override_wins():
    p = _Prefs(common_default="cpu", app_overrides={"app1": {"compute_device": "cuda:0"}})
    assert resolve_effective_device(p, "app1") == "cuda:0"


def test_falls_back_to_suite_default():
    p = _Prefs(common_default="cpu", app_overrides={})
    assert resolve_effective_device(p, "app1") == "cpu"


def test_falls_back_to_auto(monkeypatch):
    monkeypatch.setattr("pdomain_ops.suite.device_prefs.pick_device", lambda: "cpu")
    p = _Prefs(common_default=None, app_overrides={})
    assert resolve_effective_device(p, "app1") == "cpu"
