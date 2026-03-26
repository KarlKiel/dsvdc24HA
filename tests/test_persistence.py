import os
import pytest
from pathlib import Path
from pyDSvDCAPIv2.persistence import PropertyStore


@pytest.fixture
def store(tmp_path):
    return PropertyStore(str(tmp_path / "state.yaml"))


def test_save_and_load_roundtrip(store):
    data = {"vdc": {"vdc_id": "abc123", "name": "Test"}, "devices": []}
    store.save(data)
    loaded = store.load()
    assert loaded == data


def test_load_returns_empty_dict_when_no_file(store):
    result = store.load()
    assert result == {}


def test_save_creates_backup(store, tmp_path):
    data1 = {"vdc": {"vdc_id": "first"}, "devices": []}
    data2 = {"vdc": {"vdc_id": "second"}, "devices": []}
    store.save(data1)
    store.save(data2)
    bak = Path(str(tmp_path / "state.yaml.bak"))
    assert bak.exists()
    import yaml
    with open(bak) as f:
        backed = yaml.safe_load(f)
    assert backed["vdc"]["vdc_id"] == "first"


def test_load_falls_back_to_backup(store, tmp_path):
    data = {"vdc": {"vdc_id": "backup-data"}, "devices": []}
    store.save(data)
    # corrupt primary
    Path(str(tmp_path / "state.yaml")).write_text("not: valid: yaml: [[[")
    loaded = store.load()
    assert loaded["vdc"]["vdc_id"] == "backup-data"


def test_no_tmp_file_left_after_save(store, tmp_path):
    store.save({"vdc": {}, "devices": []})
    assert not Path(str(tmp_path / "state.yaml.tmp")).exists()


def test_flush_saves_immediately(store):
    store.stage({"vdc": {"vdc_id": "staged"}, "devices": []})
    store.flush()
    loaded = store.load()
    assert loaded["vdc"]["vdc_id"] == "staged"
