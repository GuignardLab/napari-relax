import numpy as np
import pytest
from lineagetree import LineageTreeManager
from matplotlib.figure import Figure
from napari._qt.qt_viewer import QtViewer
from napari.components import ViewerModel
from qtpy.QtCore import QEvent, QPoint
from qtpy.QtGui import QContextMenuEvent
from qtpy.QtWidgets import QMenu

from napari_relax._util_classes import TabTemplate, TimeResDialog
from napari_relax.relax_multipledatasets.cell_size import MinimalCellSize
from napari_relax.relax_multipledatasets.cross_clustermap_canvas import (
    CrossClusterMapCanvas,
)
from napari_relax.relax_multipledatasets.cross_comparisons_handler import (
    CrossHandler,
)
from napari_relax.relax_multipledatasets.cross_config import CrossConfig
from napari_relax.relax_multipledatasets.cross_embryo_comparison import (
    CrossClustermap,
)
from napari_relax.relax_multipledatasets.manager_widget import CrossEmbryo

from .conftest import add_lt_layer, make_lineage_tree, mouse_event, points_of

MAGENTA = [1, 128 / 255, 1, 1]
CYAN = [0, 1, 1, 1]


@pytest.fixture
def lt_a():
    return make_lineage_tree("a")


@pytest.fixture
def lt_b():
    # Different node IDs: a manager refuses trees equal to one it holds.
    return make_lineage_tree("b", node_offset=100)


@pytest.fixture
def manager(lt_a, lt_b):
    manager = LineageTreeManager()
    manager.add(lt_a, name="a")
    manager.add(lt_b, name="b")
    return manager


@pytest.fixture
def dataset_layers(viewer, lt_a, lt_b):
    return add_lt_layer(viewer, lt_a, "a"), add_lt_layer(viewer, lt_b, "b")


def item_position(list_widget, row):
    return list_widget.visualItemRect(list_widget.item(row)).center()


def cross_results():
    """Comparisons between node 4 of "a" and nodes 104, 113 of "b"."""
    names = {0: ("a", 4, 1), 1: ("b", 104, 101), 2: ("b", 113, 110)}
    comps = {(0, 1): 0.0, (0, 2): 3.0, (1, 2): 3.0}
    norms = {(0, 1): (3, 3), (0, 2): (3, 3), (1, 2): (3, 3)}
    return comps, norms, names


class TestCrossEmbryo:
    @pytest.fixture
    def cross_embryo(self, qtbot, viewer):
        widget = CrossEmbryo(viewer)
        qtbot.addWidget(widget)
        return widget

    def items(self, widget):
        return [
            widget.lineagetree_list.item(i).text()
            for i in range(widget.lineagetree_list.count())
        ]

    def test_create_a_manager_from_the_layers(
        self, cross_embryo, viewer, dataset_layers, qtbot
    ):
        viewer.add_image(np.zeros((3, 3)))
        with qtbot.waitSignal(cross_embryo.send_manager_to_classes) as blocker:
            cross_embryo.create_manager.click()
        manager = blocker.args[0]
        assert list(manager.lineagetrees) == ["a", "b"]
        assert (
            manager.lineagetrees["a"]
            is dataset_layers[0].metadata["LineageTree"]
        )
        assert self.items(cross_embryo) == ["a", "b"]
        assert cross_embryo.layers["a"] is dataset_layers[0]

    def test_save_and_load_a_manager(
        self, cross_embryo, dataset_layers, tmp_path, qtbot
    ):
        cross_embryo.create_a_manager()
        path = tmp_path / "manager.ltm"
        cross_embryo.save_manager_widget.value = path
        cross_embryo.save_manager_button.click()
        assert path.exists()
        cross_embryo.manager = LineageTreeManager()
        cross_embryo.load_ltm_file.line_edit.value = str(path)
        with qtbot.waitSignal(cross_embryo.send_manager_to_classes):
            cross_embryo.load_manager.click()
        assert list(cross_embryo.manager.lineagetrees) == ["a", "b"]
        assert self.items(cross_embryo) == ["a", "b"]

    def test_add_lineage_tree_files(self, cross_embryo, tmp_path, lt_a, lt_b):
        for name, lT in (("first", lt_a), ("second", lt_b)):
            lT.write(str(tmp_path / f"{name}.lT"))
        cross_embryo.add_lT_to_manager.line_edit.value = ", ".join(
            str(tmp_path / f"{name}.lT") for name in ("first", "second")
        )
        cross_embryo.add_emb.click()
        assert self.items(cross_embryo) == ["first", "second"]

    def test_remove_embryo(self, cross_embryo, dataset_layers, qtbot):
        cross_embryo.create_a_manager()
        source = cross_embryo.lineagetree_list
        with qtbot.waitSignal(cross_embryo.send_manager_to_classes):
            cross_embryo.remove_embryo(source, item_position(source, 0))
        assert list(cross_embryo.manager.lineagetrees) == ["b"]
        assert self.items(cross_embryo) == ["b"]

    def test_change_time_resolution(
        self, cross_embryo, dataset_layers, monkeypatch
    ):
        def type_resolution(self):
            self.tr_edit.value = "2.5"
            self._ok_pressed(None)

        monkeypatch.setattr(TimeResDialog, "exec_", type_resolution)
        cross_embryo.create_a_manager()
        source = cross_embryo.lineagetree_list
        cross_embryo.change_time_resolution(source, item_position(source, 1))
        assert cross_embryo.manager.lineagetrees["b"].time_resolution == 2.5
        assert cross_embryo.manager.lineagetrees["a"].time_resolution == 5

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: closing the time resolution dialog without pressing "
        "Ok sets the time resolution to 0",
    )
    def test_cancel_time_resolution_change(self, cross_embryo, dataset_layers):
        cross_embryo.create_a_manager()
        source = cross_embryo.lineagetree_list
        cross_embryo.change_time_resolution(source, item_position(source, 0))
        assert cross_embryo.manager.lineagetrees["a"].time_resolution == 5

    def test_context_menu(self, cross_embryo, dataset_layers, modal_calls):
        cross_embryo.create_a_manager()
        source = cross_embryo.lineagetree_list
        position = item_position(source, 0)
        event = QContextMenuEvent(
            QContextMenuEvent.Mouse, position, source.mapToGlobal(position)
        )
        assert cross_embryo.eventFilter(source, event)
        (menu,) = modal_calls
        assert isinstance(menu, QMenu)
        assert [a.text() for a in menu.actions()] == [
            "Change Time Resolution",
            "Remove Embryo",
        ]
        menu.actions()[1].trigger()
        assert list(cross_embryo.manager.lineagetrees) == ["b"]

    def test_other_events_are_not_filtered(self, cross_embryo, modal_calls):
        source = cross_embryo.lineagetree_list
        event = QContextMenuEvent(
            QContextMenuEvent.Mouse, QPoint(1, 1), QPoint(1, 1)
        )
        assert not cross_embryo.eventFilter(source, event)
        assert not cross_embryo.eventFilter(source, QEvent(QEvent.Enter))
        assert not modal_calls

    @pytest.mark.xfail(
        strict=True,
        raises=(TypeError, KeyError),
        reason="BUG: add_new_layer calls layer_preparation with an unknown "
        "`path` argument and no parameters",
    )
    def test_add_selected_datasets_to_the_viewer(
        self, cross_embryo, viewer, dataset_layers
    ):
        cross_embryo.create_a_manager()
        viewer.layers.remove(dataset_layers[1])
        cross_embryo.lineagetree_list.item(1).setSelected(True)
        cross_embryo.add_new_layer()
        assert [layer.name for layer in viewer.layers] == ["a", "b"]


class TestMinimalCellSize:
    @pytest.fixture
    def models(self):
        models = ViewerModel(), ViewerModel()
        for model in models:
            model.add_points(np.zeros((2, 4)), size=1)
        return models

    @pytest.fixture
    def sizes(self, qtbot, viewer, models):
        widget = MinimalCellSize(viewer, *models)
        qtbot.addWidget(widget)
        return widget

    def test_one_viewer(self, sizes, models):
        sizes.slider_1.setValue(300)
        np.testing.assert_allclose(models[0].layers[0].size, 300)
        np.testing.assert_allclose(models[1].layers[0].size, 1)
        assert "Current size 300" in sizes.slider_1.toolTip()

    def test_both_viewers(self, sizes, models):
        sizes.toggle_all.value = True
        sizes.slider_2.setValue(400)
        np.testing.assert_allclose(models[0].layers[0].size, 400)
        np.testing.assert_allclose(models[1].layers[0].size, 400)
        assert sizes.slider_1.value() == 400

    def test_viewer_without_layer(self, qtbot, viewer):
        widget = MinimalCellSize(viewer, ViewerModel(), ViewerModel())
        qtbot.addWidget(widget)
        widget.slider_1.setValue(10)  # must not raise


@pytest.fixture
def config(qtbot, viewer, manager, dataset_layers):
    widget = CrossConfig(viewer)
    qtbot.addWidget(widget)
    widget.get_lt_manager(manager)
    return widget


def select_all(list_widget):
    for i in range(list_widget.count()):
        list_widget.item(i).setSelected(True)


class TestCrossConfig:
    def test_empty(self, qtbot, viewer):
        widget = CrossConfig(viewer)
        qtbot.addWidget(widget)
        assert widget.root_tabs.count() == 1
        assert widget.root_tabs.tabText(0) == "Empty Layout"
        assert widget.lcm == 1
        assert widget.downsampling_widget.isHidden()

    def test_datasets_are_listed(self, config, dataset_layers):
        items = [
            config.lineagetree_list.item(i).text()
            for i in range(config.lineagetree_list.count())
        ]
        assert items == ["a", "b"]
        assert config.layers["a"] is dataset_layers[0]

    def test_one_tab_per_selected_dataset(self, config):
        select_all(config.lineagetree_list)
        assert set(config.tab_dictionary) == {"a", "b"}
        assert [config.root_tabs.tabText(i) for i in range(2)] == ["a", "b"]
        assert all(
            isinstance(tab, TabTemplate)
            for tab in config.tab_dictionary.values()
        )
        config.lineagetree_list.clearSelection()
        assert config.root_tabs.tabText(0) == "Empty Layout"

    def test_lcm_of_the_time_resolutions(self, config, manager):
        manager.lineagetrees["b"].time_resolution = 2
        config.lineagetree_list.item(0).setSelected(True)
        # Time resolutions are stored multiplied by 10.
        assert config.lcm == 50
        config.lineagetree_list.item(1).setSelected(True)
        assert config.lcm == 100

    def test_tree_style(self, config):
        config.tree_style_combobox.value = "downsampled"
        assert config.comp_style == "downsampled"
        assert not config.downsampling_widget.isHidden()
        config.tree_style_combobox.value = "simple"
        assert config.downsampling_widget.isHidden()

    def test_downsampling_tooltip(self, config, manager):
        manager.lineagetrees["b"].time_resolution = 2.5
        select_all(config.lineagetree_list)
        config.downsampling_widget.setCurrentIndex(1)
        tooltip = config.downsampling_widget.toolTip()
        # lcm(50, 25) = 50: "b" is sampled twice as often as "a".
        assert "a with downsampling: 2.0" in tooltip
        assert "b with downsampling: 4.0" in tooltip

    def test_comparisons(self, config):
        select_all(config.lineagetree_list)
        for tab in config.tab_dictionary.values():
            tab.root_list.item(0).setSelected(True)
        config.times = {"a": [3], "b": [3]}
        results = list(CrossConfig.roots_selector.__wrapped__(config))
        assert len(results) == 1
        comparisons, names, norms = results[0]
        assert sorted(names[0].values()) == [
            ("a", 4, 1),
            ("a", 5, 1),
            ("b", 104, 101),
            ("b", 105, 101),
        ]
        assert len(comparisons[0]) == 6
        assert set(norms[0]) == set(comparisons[0])
        # Identical sublineages have a distance of 0.
        index = {v[1]: k for k, v in names[0].items()}
        pair = tuple(sorted((index[4], index[104])))
        assert comparisons[0][pair] == 0


@pytest.fixture
def cross_clustermap(qtbot, viewer, manager, dataset_layers):
    models = [ViewerModel(), ViewerModel()]
    widget = CrossClustermap(viewer, dataset_viewers=models)
    qtbot.addWidget(widget)
    widget.get_lt_manager(manager)
    widget.layers = {
        layer.metadata["name_for_manager"]: layer for layer in viewer.layers
    }
    return widget


class TestCrossClusterMapCanvas:
    @pytest.fixture
    def canvas(self, qtbot, manager):
        figure = Figure()
        canvas = CrossClusterMapCanvas(figure, figure.add_subplot(111))
        qtbot.addWidget(canvas)
        canvas._receive_data(*cross_results(), manager)
        return canvas

    def test_plot(self, canvas):
        assert sorted(canvas.labels_of_clustermap) == ["a_A", "b_A", "b_B"]
        np.testing.assert_allclose(canvas.plot, canvas.plot.T)
        np.testing.assert_allclose(np.diag(canvas.plot), 0)
        assert sorted(canvas.names_of_nodes) == ["a", "b", "b"]

    def test_click(self, canvas, qtbot):
        with qtbot.waitSignal(canvas.click_signal) as blocker:
            canvas._click(mouse_event(canvas, canvas.ax, 0, 1))
        layers, nodes = blocker.args[0]
        assert layers == canvas.names_of_nodes[:2]
        assert nodes == canvas.labels_node[:2]

    def test_annotation(self, canvas):
        canvas.print_text((0, 1))
        text = canvas.hover_annotation.get_text()
        assert canvas.labels_of_clustermap[0] in text
        assert "Score" in text

    def test_clear_data(self, canvas):
        canvas.clear_data()
        assert canvas.manager is None


class TestCrossClustermap:
    def test_send_data_without_results(self, cross_clustermap):
        cross_clustermap.send_data()
        assert not hasattr(cross_clustermap.canvas, "plot")

    def test_send_data(self, cross_clustermap):
        comps, norms, names = cross_results()
        cross_clustermap.comps = [comps]
        cross_clustermap.norms = [norms]
        cross_clustermap.names = [names]
        cross_clustermap.send_data()
        assert sorted(cross_clustermap.canvas.labels_of_clustermap) == [
            "a_A",
            "b_A",
            "b_B",
        ]

    def test_click_shows_the_two_sublineages(
        self, cross_clustermap, viewer, dataset_layers
    ):
        cross_clustermap._click([["a", "b"], [4, 113]])
        for model, color, nodes in zip(
            cross_clustermap.viewers,
            (MAGENTA, CYAN),
            ([4, 6, 8], [113, 114, 115]),
            strict=True,
        ):
            (layer,) = model.layers
            assert model.dims.ndisplay == 3
            np.testing.assert_allclose(
                layer.face_color[points_of(layer, nodes)], [color] * 3
            )
            others = np.ones(len(layer.data), bool)
            others[points_of(layer, nodes)] = False
            np.testing.assert_allclose(layer.face_color[others], 1)
        assert viewer.layers.selection.active is dataset_layers[1]
        assert all(ax.has_data() for ax in cross_clustermap.axes)

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: a dataset that is not in the viewer is added without "
        "its Lineage Viewer graphs, so its tree cannot be drawn",
    )
    def test_click_on_a_dataset_not_in_the_viewer(
        self, cross_clustermap, viewer, dataset_layers
    ):
        viewer.layers.remove(dataset_layers[1])
        cross_clustermap._click([["a", "b"], [4, 113]])
        assert cross_clustermap.axes[1].has_data()

    @pytest.mark.xfail(
        strict=True,
        raises=AttributeError,
        reason="BUG: save_dictionary reads self.comparisons and self.time, "
        "which are never set (results are stored in self.comps)",
    )
    def test_save_dictionary(self, cross_clustermap, tmp_path):
        comps, norms, names = cross_results()
        cross_clustermap.comps = [comps]
        cross_clustermap.norms = [norms]
        cross_clustermap.names = [names]
        cross_clustermap.save_pkl.value = tmp_path / "cross.pkl"
        cross_clustermap.save_dictionary()
        assert (tmp_path / "cross.pkl").exists()


@pytest.fixture
def make_cross_handler(qtbot, viewer):
    """Create CrossHandler widgets and delete them before napari checks
    that no QtViewer is left behind.

    Pytest keeps fixture values (and xfail tracebacks) alive until the end
    of the teardown, so the Python wrappers of the two dataset viewers are
    also removed from napari's registry once their Qt objects are deleted.
    """
    widgets = []

    def factory():
        widgets.append(CrossHandler(viewer))
        return widgets[-1]

    yield factory
    for widget in widgets:
        widget.close()
        widget.deleteLater()
    qtbot.wait(50)
    for widget in widgets:
        QtViewer._instances.discard(widget.qt_viewer1)
        QtViewer._instances.discard(widget.qt_viewer2)
    widgets.clear()


class TestCrossHandler:
    @pytest.fixture
    def handler(self, make_cross_handler, manager, dataset_layers):
        widget = make_cross_handler()
        widget.get_lt_manager(manager)
        return widget

    def test_initial_state(self, make_cross_handler, viewer):
        widget = make_cross_handler()
        assert widget.stopbutton.isChecked()
        assert widget.qt_viewer1.main_viewer is viewer
        assert widget.comparisonswidget.viewers == [
            widget.viewer_model1,
            widget.viewer_model2,
        ]

    def test_get_lt_manager(self, handler, manager, dataset_layers):
        assert handler.config.manager is manager
        assert handler.comparisonswidget.manager is manager
        assert handler.config.lineagetree_list.count() == 2
        assert handler.comparisonswidget.layers["b"] is dataset_layers[1]

    def test_update_comparisons(self, handler):
        comps, norms, names = cross_results()
        handler.update_comparisons(([comps] * 2, [names] * 2, [norms] * 2))
        assert handler.comparisonswidget.time_slider.max == 1
        assert sorted(handler.comparisonswidget.canvas.names_of_nodes) == [
            "a",
            "b",
            "b",
        ]

    def test_long_names_ask_for_confirmation(
        self, handler, manager, lt_a, modal_calls
    ):
        manager.add(make_lineage_tree(node_offset=200), name="long name")
        handler.thread_handler()
        assert modal_calls
        assert not hasattr(handler, "worker")

    def test_run_the_comparisons(self, handler, qtbot):
        select_all(handler.config.lineagetree_list)
        for tab in handler.config.tab_dictionary.values():
            tab.root_list.item(0).setSelected(True)
            tab.times_slicer.value = slice(3, 3, 1)
        handler.thread_handler()
        with qtbot.waitSignal(handler.worker.finished, timeout=20000):
            pass
        qtbot.waitUntil(lambda: handler.stopbutton.isChecked())
        assert len(handler.comparisonswidget.comps) == 1
        assert len(handler.comparisonswidget.names[0]) == 4
        assert handler.pbr is None

    @pytest.mark.xfail(
        strict=True,
        raises=AttributeError,
        reason="BUG: kill_thread uses self.worker, which does not exist "
        "before the first run",
    )
    def test_stop_before_running(self, handler):
        handler.kill_thread()
