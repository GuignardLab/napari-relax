"""Tests of the two dock widgets and of the signals connecting their tabs."""

from types import SimpleNamespace

import numpy as np
import pytest
from qtpy.QtWidgets import QComboBox, QStackedWidget

from napari_relax import (
    CrossEmbryoComparisonWidget,
    LineageTreeAnalysisWidget,
    lineage_tree_analysis,
    relax_multipledatasets,
)
from napari_relax.lineage_tree_analysis.cells_size import CellSize

from .conftest import TIME, add_lt_layer, make_lineage_tree


@pytest.fixture
def analysis_widget(qtbot, viewer, lt_layer):
    viewer.layers.selection.active = lt_layer
    widget = LineageTreeAnalysisWidget(viewer)
    qtbot.addWidget(widget)
    return widget


class TestLineageTreeAnalysisWidget:
    def test_empty_viewer(self, qtbot, viewer):
        widget = LineageTreeAnalysisWidget(viewer)
        qtbot.addWidget(widget)
        assert list(widget.widget_dictionary) == [
            w.name for w in lineage_tree_analysis.__all_widgets__
        ]
        assert widget.findChild(CellSize) is not None

    def test_combobox_switches_the_widgets(self, analysis_widget):
        combobox = analysis_widget.findChild(QComboBox)
        stack = analysis_widget.findChild(QStackedWidget)
        assert [combobox.itemText(i) for i in range(combobox.count())] == [
            "Explore and Relabel",
            "Distance Calculation",
            "Attribute Based Recoloring",
        ]
        for index in range(combobox.count()):
            combobox.setCurrentIndex(index)
            assert stack.currentIndex() == index
            assert (
                stack.currentWidget()
                is analysis_widget.widget_dictionary[combobox.itemText(index)]
            )

    def test_label_change_updates_the_distance_calculation(
        self, analysis_widget, lt
    ):
        explore = analysis_widget.widget_dictionary["Explore and Relabel"]
        distances = analysis_widget.widget_dictionary["Distance Calculation"]
        root = explore.roots[0]
        explore.w_lineedit.setText("renamed")
        explore.w_lineedit.returnPressed.emit()
        items = [
            distances.config.list_widget.item(i).text()
            for i in range(distances.config.list_widget.count())
        ]
        assert f"renamed - {root} starts from 0 timepoint" in items
        assert distances.clustermap.labels[root] == "renamed"

    def test_recoloring_updates_the_lineage_viewer(
        self, analysis_widget, lt_layer, lt
    ):
        explore = analysis_widget.widget_dictionary["Explore and Relabel"]
        recoloring = analysis_widget.widget_dictionary[
            "Attribute Based Recoloring"
        ]
        quantitative = recoloring.coloring_widget.quant
        lt.volume = {n: 0.5 + n for n in TIME}
        quantitative.layer_change()
        quantitative.selected_attribute.setCurrentText("volume")
        quantitative.generate_colors()
        current = explore.canvas.points_layer_metadata["current_face_colors"]
        np.testing.assert_allclose(current, lt_layer.face_color)
        root = explore.canvas.root
        index = lt_layer.metadata["lT2napari"][root]
        assert explore.canvas.coloring[root] == pytest.approx(
            lt_layer.face_color[index].tolist()
        )

    def test_switching_datasets(self, analysis_widget, viewer):
        other = add_lt_layer(viewer, make_lineage_tree(time_offset=4), "late")
        viewer.layers.selection.active = other
        explore = analysis_widget.widget_dictionary["Explore and Relabel"]
        distances = analysis_widget.widget_dictionary["Distance Calculation"]
        assert explore.lT is other.metadata["LineageTree"]
        assert distances.config.lT is other.metadata["LineageTree"]
        assert distances.config.time_slicer.start.value == 4

    def test_font_is_scaled_to_the_screen(self, qtbot, viewer):
        from qtpy.QtWidgets import QApplication, QWidget

        widget = LineageTreeAnalysisWidget(viewer)
        qtbot.addWidget(widget)
        scale = QApplication.primaryScreen().logicalDotsPerInch() / 96
        assert widget.font().pointSizeF() == pytest.approx(
            QWidget().font().pointSizeF() * scale
        )


class TestCrossEmbryoComparisonWidget:
    @pytest.fixture
    def cross_widget(self, qtbot, viewer):
        from napari._qt.qt_viewer import QtViewer

        widget = CrossEmbryoComparisonWidget(viewer)
        yield widget
        handler = widget.widget_dictionary["Cross Distance Calculation"]
        widget.close()
        widget.deleteLater()
        qtbot.wait(50)
        # See make_cross_handler in test_multiple_datasets.
        QtViewer._instances.discard(handler.qt_viewer1)
        QtViewer._instances.discard(handler.qt_viewer2)

    def test_widgets(self, cross_widget):
        assert list(cross_widget.widget_dictionary) == [
            w.name for w in relax_multipledatasets.__all_widgets__
        ]

    def test_manager_is_sent_to_the_comparisons(
        self, cross_widget, viewer, lt
    ):
        add_lt_layer(viewer, lt, "a")
        add_lt_layer(viewer, make_lineage_tree(node_offset=100), "b")
        manager_widget = cross_widget.widget_dictionary["Manager Manipulation"]
        handler = cross_widget.widget_dictionary["Cross Distance Calculation"]
        manager_widget.create_a_manager()
        assert handler.manager is manager_widget.manager
        assert handler.config.lineagetree_list.count() == 2
        assert handler.comparisonswidget.manager is manager_widget.manager


def test_open_the_dock_widget_with_napari(viewer, lt_layer):
    viewer.layers.selection.active = lt_layer
    _, widget = viewer.window.add_plugin_dock_widget(
        "napari-relax", "Lineage tree analysis"
    )
    assert isinstance(widget, LineageTreeAnalysisWidget)
    explore = widget.widget_dictionary["Explore and Relabel"]
    assert explore.lT is lt_layer.metadata["LineageTree"]


@pytest.mark.xfail(
    strict=True,
    raises=RuntimeError,
    reason="BUG: ProgenySelection appends point_click to the viewer's "
    "mouse drag callbacks and never removes it, so a Shift + right "
    "click after the plugin is closed reaches the destroyed widget",
)
def test_mouse_click_after_the_plugins_are_closed(qtbot, viewer, lt_layer):
    """Open both plugins, close them, then click in the viewer."""
    from napari._qt.qt_viewer import QtViewer
    from napari.utils.interactions import mouse_press_callbacks

    viewer.layers.selection.active = lt_layer
    docks = [
        viewer.window.add_plugin_dock_widget("napari-relax", name)
        for name in ("Lineage tree analysis", "Cross Lineagetree comparison")
    ]
    handler = docks[1][1].widget_dictionary["Cross Distance Calculation"]
    dataset_viewers = (handler.qt_viewer1, handler.qt_viewer2)

    # Removing the dock keeps the widget alive, so wait for its death.
    for dock, widget in docks:
        viewer.window.remove_dock_widget(dock)
        with qtbot.waitSignal(widget.destroyed, timeout=5000):
            widget.deleteLater()
    for dataset_viewer in dataset_viewers:
        QtViewer._instances.discard(dataset_viewer)

    event = SimpleNamespace(
        type="mouse_press",
        modifiers=["Shift"],
        button=2,
        position=np.zeros(4),
        view_direction=np.array([0, 1, 0, 0]),
        dims_displayed=[1, 2, 3],
        is_dragging=False,
        handled=False,
    )
    mouse_press_callbacks(viewer, event)
    assert not [
        callback
        for callback in viewer.mouse_drag_callbacks
        if "point_click" in callback.__name__
    ]
