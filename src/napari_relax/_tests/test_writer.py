import numpy as np
import pytest
from lineagetree import LineageTree

from napari_relax import _writer
from napari_relax._writer import write_single_image

from .conftest import TIME


@pytest.fixture
def errors(monkeypatch):
    messages = []
    monkeypatch.setattr(_writer, "show_error", messages.append)
    return messages


def test_write_from_metadata(tmp_path, lt, errors):
    path = str(tmp_path / "saved.lT")
    assert write_single_image(path, None, {"metadata": {"LineageTree": lt}})
    assert LineageTree.load(path) == lt
    assert not errors


@pytest.mark.parametrize("extension", [".lt", ".LT", ".lT"])
def test_lineage_tree_extensions_are_kept(tmp_path, lt, extension):
    path = str(tmp_path / f"saved{extension}")
    assert write_single_image(
        path, None, {"metadata": {"LineageTree": lt}}
    ) == [path]
    assert (tmp_path / f"saved{extension}").exists()


def test_other_extensions_are_replaced(tmp_path, lt):
    path = str(tmp_path / "saved.csv")
    written = write_single_image(path, None, {"metadata": {"LineageTree": lt}})
    assert written == [str(tmp_path / "saved.lT")]
    assert LineageTree.load(written[0]) == lt
    assert not (tmp_path / "saved.csv").exists()


def test_write_from_linked_layer(tmp_path, lt_layer, errors):
    path = str(tmp_path / "linked.lT")
    write_single_image(path, None, {"metadata": {"link": lt_layer}})
    assert set(LineageTree.load(path).nodes) == set(TIME)
    assert not errors


def test_no_lineage_tree_shows_an_error(tmp_path, errors):
    path = str(tmp_path / "nothing.lT")
    assert write_single_image(path, None, {"metadata": {}}) == [path]
    assert len(errors) == 1
    assert not (tmp_path / "nothing.lT").exists()


def test_link_without_lineage_tree_shows_an_error(tmp_path, viewer, errors):
    other = viewer.add_points(np.zeros((1, 3)))
    path = str(tmp_path / "nothing.lT")
    write_single_image(path, None, {"metadata": {"link": other}})
    assert len(errors) == 1


def test_save_with_napari(tmp_path, viewer, lt_layer):
    path = str(tmp_path / "from_napari.lT")
    viewer.layers.selection.active = lt_layer
    viewer.layers.save(path, selected=True, plugin="napari-relax")
    assert LineageTree.load(path) == lt_layer.metadata["LineageTree"]
