"""Tests of the demo datasets and of their download and cache helpers.

The download helpers are always pointed at a temporary directory: they
delete files, so they must never touch the real ``demo_data`` folder.
"""

import builtins
import hashlib
import json
from pathlib import Path
from urllib.error import URLError

import pytest

import napari_relax.demo_data as demo_data
from napari_relax.demo_data import (
    _datasets,
    _download_utils,
    _load_demo,
    _setup_demo_config,
)

REAL_DEMO_DIR = Path(demo_data.__file__).parent
CONTENT = b"lineage tree bytes"
CONTENT_MD5 = hashlib.md5(CONTENT).hexdigest()


@pytest.fixture
def real_demo_path(monkeypatch):
    """Serve the shipped demo file without running the download logic."""
    path = REAL_DEMO_DIR / "demo.lT"
    monkeypatch.setattr(_load_demo, "ensure_demo_data", lambda name: path)
    return path


@pytest.fixture
def demo_dir(tmp_path, monkeypatch):
    """Point the download helpers at a temporary folder and config."""
    datasets = {
        "local": {
            "filename": "local.lT",
            "url": None,
            "md5": CONTENT_MD5,
            "description": "",
            "size_mb": 0.0,
        },
        "remote": {
            "filename": "remote.lT",
            "url": "https://example.org/remote.lT",
            "md5": CONTENT_MD5,
            "description": "",
            "size_mb": 0.0,
        },
        "unhashed": {
            "filename": "unhashed.lT",
            "url": "https://example.org/unhashed.lT",
            "md5": None,
            "description": "",
            "size_mb": 0.0,
        },
    }
    monkeypatch.setattr(_download_utils, "get_demo_data_dir", lambda: tmp_path)
    monkeypatch.setattr(_download_utils, "DEMO_DATASETS", datasets)
    return tmp_path


@pytest.fixture
def downloads(monkeypatch):
    """Replace the network download with writing ``CONTENT``."""
    urls = []

    def fake_download(url, filepath):
        urls.append(url)
        Path(filepath).write_bytes(CONTENT)

    monkeypatch.setattr(
        _download_utils, "download_with_progress", fake_download
    )
    return urls


class TestLoaders:
    def test_load_demo(self, real_demo_path):
        (layer,) = demo_data.load_demo()
        data, kwargs, layer_type = layer
        assert layer_type == "points"
        assert kwargs["name"] == "Demo"
        lT = kwargs["metadata"]["LineageTree"]
        assert lT.time_resolution == 1
        assert len(data) == len(lT.nodes)

    def test_load_celegans(self, monkeypatch, tmp_path, lt):
        path = tmp_path / "celegans.lT"
        lt.write(str(path))
        requested = []
        monkeypatch.setattr(
            _load_demo,
            "ensure_demo_data",
            lambda name: requested.append(name) or path,
        )
        (layer,) = demo_data.load_celegans()
        assert requested == ["C.elegans"]
        assert layer[1]["name"] == "C.elegans"
        assert layer[1]["metadata"]["LineageTree"].time_resolution == 1

    def test_open_sample_with_napari(self, viewer, real_demo_path):
        viewer.open_sample("napari-relax", "unique_id.6")
        (layer,) = viewer.layers
        assert layer.name == "Demo"
        assert "LineageTree" in layer.metadata


class TestDatasetsConfiguration:
    def test_known_datasets(self):
        assert {"demo", "C.elegans"} <= set(demo_data.DEMO_DATASETS)
        for config in demo_data.DEMO_DATASETS.values():
            assert {"filename", "url", "md5", "description", "size_mb"} <= (
                set(config)
            )

    def test_shipped_demo_matches_its_hash(self):
        # ensure_demo_data deletes a local file with a wrong hash, and the
        # demo dataset has no URL to download it again.
        config = demo_data.DEMO_DATASETS["demo"]
        path = REAL_DEMO_DIR / config["filename"]
        assert path.exists()
        assert _download_utils.calculate_md5(path) == config["md5"]

    def test_load_and_save_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_datasets, "__file__", str(tmp_path / "x.py"))
        datasets = {"a": {"filename": "a.lT", "url": None}}
        _datasets.save_demo_datasets(datasets)
        assert _datasets.load_demo_datasets() == datasets
        assert json.loads((tmp_path / "datasets.json").read_text()) == (
            datasets
        )


class TestEnsureDemoData:
    def test_unknown_dataset(self, demo_dir):
        with pytest.raises(ValueError, match="Unknown dataset"):
            _download_utils.ensure_demo_data("missing")

    def test_valid_local_file(self, demo_dir, downloads):
        (demo_dir / "local.lT").write_bytes(CONTENT)
        assert _download_utils.ensure_demo_data("local") == (
            demo_dir / "local.lT"
        )
        assert not downloads

    def test_unhashed_local_file_is_trusted(self, demo_dir, downloads):
        (demo_dir / "unhashed.lT").write_bytes(b"anything")
        assert _download_utils.ensure_demo_data("unhashed").read_bytes() == (
            b"anything"
        )
        assert not downloads

    def test_missing_file_without_url(self, demo_dir, downloads):
        with pytest.raises(RuntimeError, match="no download URL"):
            _download_utils.ensure_demo_data("local")

    def test_corrupted_file_without_url_is_removed(self, demo_dir):
        (demo_dir / "local.lT").write_bytes(b"corrupted")
        with pytest.raises(RuntimeError, match="no download URL"):
            _download_utils.ensure_demo_data("local")
        assert not (demo_dir / "local.lT").exists()

    def test_download(self, demo_dir, downloads):
        path = _download_utils.ensure_demo_data("remote")
        assert downloads == ["https://example.org/remote.lT"]
        assert path.read_bytes() == CONTENT
        cache = _download_utils.load_cache_info()
        assert cache["remote"]["md5"] == CONTENT_MD5
        assert cache["remote"]["size_bytes"] == len(CONTENT)

    def test_corrupted_file_is_downloaded_again(self, demo_dir, downloads):
        (demo_dir / "remote.lT").write_bytes(b"corrupted")
        path = _download_utils.ensure_demo_data("remote")
        assert downloads == ["https://example.org/remote.lT"]
        assert path.read_bytes() == CONTENT

    def test_unhashed_download_caches_the_computed_hash(
        self, demo_dir, downloads
    ):
        _download_utils.ensure_demo_data("unhashed")
        cache = _download_utils.load_cache_info()
        assert cache["unhashed"]["md5"] == CONTENT_MD5

    def test_failed_download_removes_partial_file(self, demo_dir, monkeypatch):
        def failing_download(url, filepath):
            Path(filepath).write_bytes(b"partial")
            raise RuntimeError("network down")

        monkeypatch.setattr(
            _download_utils, "download_with_progress", failing_download
        )
        with pytest.raises(RuntimeError, match="network down"):
            _download_utils.ensure_demo_data("remote")
        assert not (demo_dir / "remote.lT").exists()

    def test_download_with_wrong_hash(self, demo_dir, monkeypatch):
        monkeypatch.setattr(
            _download_utils,
            "download_with_progress",
            lambda url, path: Path(path).write_bytes(b"unexpected"),
        )
        with pytest.raises(RuntimeError, match="incorrect hash"):
            _download_utils.ensure_demo_data("remote")
        assert not (demo_dir / "remote.lT").exists()


class TestDownloadWithProgress:
    def test_reports_progress(self, tmp_path, monkeypatch, capsys):
        def fake_urlretrieve(url, filepath, reporthook):
            reporthook(1, 50, 100)
            reporthook(2, 50, 100)
            Path(filepath).write_bytes(CONTENT)

        monkeypatch.setattr(_download_utils, "urlretrieve", fake_urlretrieve)
        _download_utils.download_with_progress("url", tmp_path / "f")
        assert (tmp_path / "f").read_bytes() == CONTENT
        assert "100.0%" in capsys.readouterr().out

    def test_network_error(self, tmp_path, monkeypatch):
        def fake_urlretrieve(url, filepath, reporthook):
            raise URLError("offline")

        monkeypatch.setattr(_download_utils, "urlretrieve", fake_urlretrieve)
        with pytest.raises(RuntimeError, match="Failed to download url"):
            _download_utils.download_with_progress("url", tmp_path / "f")


class TestCache:
    def test_calculate_md5(self, tmp_path):
        path = tmp_path / "f"
        path.write_bytes(CONTENT * 1000)
        assert _download_utils.calculate_md5(path) == (
            hashlib.md5(CONTENT * 1000).hexdigest()
        )

    def test_verify_file_integrity(self, tmp_path):
        path = tmp_path / "f"
        assert not _download_utils.verify_file_integrity(path, CONTENT_MD5)
        path.write_bytes(CONTENT)
        assert _download_utils.verify_file_integrity(path, CONTENT_MD5)
        assert not _download_utils.verify_file_integrity(path, "0" * 32)

    def test_cache_info_round_trip(self, demo_dir):
        assert _download_utils.load_cache_info() == {}
        _download_utils.save_cache_info({"a": {"md5": "x"}})
        assert _download_utils.load_cache_info() == {"a": {"md5": "x"}}

    def test_corrupted_cache_info(self, demo_dir):
        (demo_dir / ".download_cache.json").write_text("{not json")
        assert _download_utils.load_cache_info() == {}

    def test_get_cached_datasets(self, demo_dir):
        (demo_dir / "local.lT").write_bytes(CONTENT)
        _download_utils.save_cache_info({"local": {"md5": CONTENT_MD5}})
        cached = _download_utils.get_cached_datasets()
        assert cached["local"]["exists"]
        assert cached["local"]["size_bytes"] == len(CONTENT)
        assert cached["local"]["cache_info"] == {"md5": CONTENT_MD5}
        assert not cached["remote"]["exists"]
        assert cached["remote"]["cache_info"] == {}

    def test_clear_one_dataset(self, demo_dir):
        (demo_dir / "local.lT").write_bytes(CONTENT)
        (demo_dir / "remote.lT").write_bytes(CONTENT)
        _download_utils.save_cache_info({"local": {}, "remote": {}})
        _download_utils.clear_cache("local")
        assert not (demo_dir / "local.lT").exists()
        assert (demo_dir / "remote.lT").exists()
        assert _download_utils.load_cache_info() == {"remote": {}}

    def test_clear_unknown_dataset(self, demo_dir, capsys):
        _download_utils.clear_cache("missing")
        assert "Unknown dataset" in capsys.readouterr().out

    def test_clear_everything(self, demo_dir):
        (demo_dir / "local.lT").write_bytes(CONTENT)
        (demo_dir / "remote.lT").write_bytes(CONTENT)
        _download_utils.save_cache_info({"local": {}})
        _download_utils.clear_cache()
        assert not (demo_dir / "local.lT").exists()
        assert not (demo_dir / "remote.lT").exists()
        assert not (demo_dir / ".download_cache.json").exists()


class TestSetupDemoConfig:
    @pytest.fixture
    def config_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            _setup_demo_config, "__file__", str(tmp_path / "x.py")
        )
        monkeypatch.setattr(
            _setup_demo_config,
            "DEMO_DATASETS",
            {"known": {"filename": "known.lT", "md5": None, "size_mb": 0}},
        )
        (tmp_path / "known.lT").write_bytes(CONTENT)
        (tmp_path / "new-file_demo.lT").write_bytes(CONTENT * 2)
        return tmp_path

    @pytest.fixture
    def saved(self, monkeypatch):
        saved = []
        monkeypatch.setattr(
            _setup_demo_config, "save_demo_datasets", saved.append
        )
        monkeypatch.setattr(_setup_demo_config, "load_demo_datasets", dict)
        return saved

    @staticmethod
    def answer(monkeypatch, *answers):
        answers = iter(answers)
        monkeypatch.setattr(builtins, "input", lambda prompt="": next(answers))

    def test_scan_demo_files(self, config_dir):
        configured, unconfigured = _setup_demo_config.scan_demo_files()
        assert [p.name for p in configured] == ["known.lT"]
        assert [p.name for p in unconfigured] == ["new-file_demo.lT"]

    def test_calculate_file_info(self, config_dir):
        info = _setup_demo_config.calculate_file_info(config_dir / "known.lT")
        assert info["filename"] == "known.lT"
        assert info["md5"] == CONTENT_MD5
        assert info["size_bytes"] == len(CONTENT)

    def test_propose_configurations(self, config_dir):
        (proposal,) = _setup_demo_config.propose_configurations(
            [config_dir / "new-file_demo.lT"]
        )
        assert proposal["name"] == "new_file"
        assert proposal["config"]["filename"] == "new-file_demo.lT"
        assert proposal["config"]["url"] is None

    def test_add_datasets_interactively(self, monkeypatch, saved):
        self.answer(monkeypatch, "e", "renamed", "y")
        proposal = {"name": "new", "config": {"filename": "f.lT", "md5": "x"}}
        proposal["config"]["size_mb"] = 1
        _setup_demo_config.add_datasets_interactively([proposal])
        assert saved == [{"renamed": proposal["config"]}]

    def test_skipped_datasets_are_not_saved(self, monkeypatch, saved):
        self.answer(monkeypatch, "maybe", "n")
        proposal = {"name": "new", "config": {"filename": "f.lT", "md5": "x"}}
        proposal["config"]["size_mb"] = 1
        _setup_demo_config.add_datasets_interactively([proposal])
        assert saved == []

    def test_setup_demo_config(self, config_dir, monkeypatch, saved):
        self.answer(monkeypatch, "y", "y")
        _setup_demo_config.setup_demo_config()
        (datasets,) = saved
        assert datasets["new_file"]["filename"] == "new-file_demo.lT"

    def test_setup_demo_config_without_files(
        self, tmp_path, monkeypatch, capsys
    ):
        monkeypatch.setattr(
            _setup_demo_config, "__file__", str(tmp_path / "x.py")
        )
        _setup_demo_config.setup_demo_config()
        assert "No .lT files found" in capsys.readouterr().out
