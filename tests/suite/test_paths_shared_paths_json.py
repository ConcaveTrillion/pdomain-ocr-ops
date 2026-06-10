from pdomain_ops.suite.paths import shared_paths_json_path


def test_shared_paths_json_path_under_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path))
    result = shared_paths_json_path()
    assert result == tmp_path / "shared-paths.json"
