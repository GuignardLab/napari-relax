import numpy as np
import pytest
from lineagetree import LineageTree
from napari.layers import Tracks

from napari_relax.lineage_tree_analysis.cells_size import CellSize

from .conftest import TIME, add_lt_layer, make_lineage_tree

# Size bounds of the conftest LineageTree (see test_utils).
MIN_SIZE, OPTIMAL_SIZE, MAX_SIZE = 0.05, 5.0, 25.0


@pytest.fixture
def cell_size(qtbot, viewer):
    widget = CellSize(viewer)
    qtbot.addWidget(widget)
    return widget


def size_for(slider_value):
    return MIN_SIZE + (MAX_SIZE - MIN_SIZE) * slider_value / 100


def test_empty_viewer(cell_size):
    assert cell_size.slider.minimum() == 1
    assert cell_size.slider.maximum() == 100
    assert "Current size None" in cell_size.slider.toolTip()


def test_is_lt_layer(cell_size, viewer, lt_layer):
    assert cell_size.is_lt_layer(lt_layer)
    assert not cell_size.is_lt_layer(viewer.add_points(np.zeros((1, 4))))
    assert not cell_size.is_lt_layer(viewer.add_image(np.zeros((3, 3))))


def test_new_lineage_layer_is_selected(cell_size, viewer, lt):
    viewer.add_image(np.zeros((3, 3)))
    layer = add_lt_layer(viewer, lt)
    assert viewer.layers.selection.active is layer
    # The slider follows the size of the new layer.
    assert cell_size.slider.value() == int(
        100 * (OPTIMAL_SIZE - MIN_SIZE) / (MAX_SIZE - MIN_SIZE)
    )


def test_size_bounds_are_computed_for_new_layers(cell_size, viewer, lt):
    data, kwargs = np.zeros((len(TIME), 4)), {"metadata": {"LineageTree": lt}}
    layer = viewer.add_points(data, **kwargs)
    assert layer.metadata["size_display_bounds"] == pytest.approx(
        (MIN_SIZE, OPTIMAL_SIZE, MAX_SIZE)
    )


def test_existing_layers_get_size_bounds(qtbot, viewer, lt):
    layer = viewer.add_points(
        np.zeros((len(TIME), 4)), metadata={"LineageTree": lt}
    )
    widget = CellSize(viewer)
    qtbot.addWidget(widget)
    assert "size_display_bounds" in layer.metadata


def test_slider_changes_the_active_layer(cell_size, viewer, lt):
    layer = add_lt_layer(viewer, lt)
    other = add_lt_layer(viewer, make_lineage_tree(), "other")
    viewer.layers.selection.active = layer
    cell_size.slider.setValue(50)
    np.testing.assert_allclose(layer.size, size_for(50))
    np.testing.assert_allclose(other.size, OPTIMAL_SIZE)
    assert f"Current size {size_for(50)}" in cell_size.slider.toolTip()


def test_slider_changes_all_layers(cell_size, viewer, lt):
    layer = add_lt_layer(viewer, lt)
    other = add_lt_layer(viewer, make_lineage_tree(), "other")
    plain = viewer.add_points(np.zeros((2, 4)), size=3)
    viewer.layers.selection.active = layer
    cell_size.toggle_all.value = True
    cell_size.slider.setValue(80)
    np.testing.assert_allclose(layer.size, size_for(80))
    np.testing.assert_allclose(other.size, size_for(80))
    np.testing.assert_allclose(plain.size, 3)


def test_reset_slider(cell_size, viewer, lt_layer):
    viewer.layers.selection.active = lt_layer
    cell_size.slider.setValue(90)
    cell_size.reset_slider()
    np.testing.assert_allclose(lt_layer.size, OPTIMAL_SIZE)
    assert cell_size.slider.value() == int(
        100 * (OPTIMAL_SIZE - MIN_SIZE) / (MAX_SIZE - MIN_SIZE)
    )


def test_reset_slider_computes_missing_bounds(cell_size, viewer, lt_layer):
    viewer.layers.selection.active = lt_layer
    del lt_layer.metadata["size_display_bounds"]
    lt_layer.size = 1
    cell_size.reset_slider()
    np.testing.assert_allclose(lt_layer.size, OPTIMAL_SIZE)
    assert lt_layer.metadata["size_display_bounds"] == pytest.approx(
        (MIN_SIZE, OPTIMAL_SIZE, MAX_SIZE)
    )


def test_selecting_a_layer_moves_the_slider(cell_size, viewer, lt):
    layer = add_lt_layer(viewer, lt)
    other = add_lt_layer(viewer, make_lineage_tree(), "other")
    other.size = size_for(70)
    viewer.layers.selection.active = layer
    viewer.layers.selection.active = other
    assert cell_size.slider.value() in (69, 70)


def test_add_tracks(cell_size, viewer, lt_layer):
    viewer.layers.selection.active = lt_layer
    cell_size.add_tracks(None)
    tracks = viewer.layers[-1]
    assert isinstance(tracks, Tracks)
    assert tracks.name == "embryo Tracks"
    assert tracks.metadata["link"] is lt_layer
    assert tracks.blending == "translucent"
    assert len(tracks.data) == len(TIME)
    assert set(tracks.properties) >= {"Lineage", "Selection"}


def test_add_tracks_without_lineage_layer(cell_size, viewer):
    cell_size.add_tracks(None)
    assert len(viewer.layers) == 0


def test_see_one_and_all_layers(cell_size, viewer, lt_layer):
    image = viewer.add_image(np.zeros((3, 3)))
    viewer.layers.selection.active = lt_layer
    cell_size.see_one_layer()
    assert lt_layer.visible
    assert not image.visible
    cell_size.see_all_layers()
    assert image.visible


def test_visibility_toggle_follows_the_selection(cell_size, viewer, lt):
    layer = add_lt_layer(viewer, lt)
    other = add_lt_layer(viewer, make_lineage_tree(), "other")
    cell_size.vis_button.value = True
    viewer.layers.selection.active = layer
    assert layer.visible
    assert not other.visible
    viewer.layers.selection.active = other
    assert other.visible
    assert not layer.visible


def test_write_embryo(cell_size, viewer, lt_layer, tmp_path):
    viewer.layers.selection.active = lt_layer
    path = tmp_path / "saved.lT"
    cell_size.save_widget.value = path
    cell_size.save_button.click()
    assert LineageTree.load(str(path)) == lt_layer.metadata["LineageTree"]


def test_write_embryo_without_layer(cell_size, tmp_path):
    cell_size.save_widget.value = tmp_path / "saved.lT"
    cell_size.write_embryo()
    assert not (tmp_path / "saved.lT").exists()
