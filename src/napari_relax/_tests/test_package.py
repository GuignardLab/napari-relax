"""Package level checks: exports, napari manifest and data files."""

import importlib
from importlib.resources import files

import pytest
from npe2 import PluginManifest

import napari_relax
from napari_relax import lineage_tree_analysis, relax_multipledatasets


@pytest.fixture(scope="module")
def manifest():
    return PluginManifest.from_distribution("napari-relax")


def import_python_name(python_name):
    module, _, attribute = python_name.partition(":")
    return getattr(importlib.import_module(module), attribute)


def test_version():
    assert isinstance(napari_relax.__version__, str)
    assert napari_relax.__version__


def test_public_api():
    for name in napari_relax.__all__:
        assert hasattr(napari_relax, name)


@pytest.mark.parametrize(
    "module",
    [
        "napari_relax.lineage_tree_analysis",
        "napari_relax.relax_multipledatasets",
        "napari_relax.demo_data",
        "napari_relax._util_classes.custom_colorboxes",
    ],
)
def test_all_names_exist(module):
    module = importlib.import_module(module)
    missing = [name for name in module.__all__ if not hasattr(module, name)]
    assert not missing


@pytest.mark.xfail(
    strict=True,
    reason="BUG: _util_classes.__all__ lists SingleTreeProgeny, which is "
    "not imported there, so a star import fails",
)
def test_util_classes_all_names_exist():
    module = importlib.import_module("napari_relax._util_classes")
    missing = [name for name in module.__all__ if not hasattr(module, name)]
    assert not missing


def test_manifest_is_valid(manifest):
    assert manifest.name == "napari-relax"
    assert manifest.display_name == "ReLAX"


def test_manifest_commands_are_importable(manifest):
    for command in manifest.contributions.commands:
        assert callable(import_python_name(command.python_name))


def test_manifest_reader(manifest):
    (reader,) = manifest.contributions.readers
    assert reader.command == "napari-relax.get_reader"
    assert {"*.lT", "*.lt", "*.LT"} <= set(reader.filename_patterns)
    assert not reader.accepts_directories


def test_manifest_writer(manifest):
    (writer,) = manifest.contributions.writers
    assert list(writer.layer_types) == ["points"]
    assert set(writer.filename_extensions) == {".lt", ".lT", ".LT"}


def test_manifest_widgets(manifest):
    widgets = {w.display_name: w for w in manifest.contributions.widgets}
    assert set(widgets) == {
        "Lineage tree analysis",
        "Cross Lineagetree comparison",
    }


def test_manifest_progeny_canvas_settings(manifest):
    configuration = manifest.contributions.configurations["progeny_canvas"]
    assert set(configuration.properties) == {
        "node_size",
        "edge_size",
        "font_size",
    }


def test_progeny_canvas_settings_defaults():
    from napari.settings import get_plugin_settings

    settings = get_plugin_settings("napari-relax").progeny_canvas
    assert settings.node_size == 1
    assert settings.edge_size == 1
    assert settings.font_size == 8


@pytest.mark.parametrize(
    "module", [lineage_tree_analysis, relax_multipledatasets]
)
def test_widget_names_are_unique(module):
    # The names are the keys of ReLAXWidget.widget_dictionary.
    names = [widget.name for widget in module.__all_widgets__]
    assert len(names) == len(set(names))


@pytest.mark.parametrize(
    "resource",
    [
        "napari.yaml",
        "demo_data/datasets.json",
        "demo_data/demo.lT",
        "lineage_tree_analysis/comparison_widget/clustermap.html",
        "lineage_tree_analysis/comparison_widget/config.html",
        "lineage_tree_analysis/comparison_widget/edit_distances.html",
        "lineage_tree_analysis/lineage_viewer_widget/gear-bold.svg",
        "lineage_tree_analysis/lineage_viewer_widget/progeny_selection.html",
        "lineage_tree_analysis/recoloring_with_attributes_widget/"
        "clone_recolor.html",
        "lineage_tree_analysis/recoloring_with_attributes_widget/"
        "node_recolor.html",
        "relax_multipledatasets/cross_comparison.html",
        "relax_multipledatasets/cross_config.html",
        "relax_multipledatasets/manager.html",
    ],
)
def test_data_files_exist(resource):
    assert (files("napari_relax") / resource).is_file()


def test_roma_colormap():
    from napari_relax.lineage_tree_analysis.roma import roma_map

    assert roma_map.name == "Roma"
    assert roma_map.colors.shape == (256, 4)
