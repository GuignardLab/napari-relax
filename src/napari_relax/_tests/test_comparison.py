import pickle
from types import SimpleNamespace

import numpy as np
import pytest
from lineagetree import LineageTree
from matplotlib import colormaps
from matplotlib.figure import Figure

from napari_relax.lineage_tree_analysis.comparison_widget import (
    config as config_module,
)
from napari_relax.lineage_tree_analysis.comparison_widget.clustermap import (
    Clustermap,
)
from napari_relax.lineage_tree_analysis.comparison_widget.clustermap_canvas import (  # noqa: E501
    ClusterMapCanvas,
)
from napari_relax.lineage_tree_analysis.comparison_widget.comparisons_handler import (  # noqa: E501
    ComparisonsHandler,
)
from napari_relax.lineage_tree_analysis.comparison_widget.config import (
    ConfigurationPanel,
)

from .conftest import add_lt_layer, make_lineage_tree, mouse_event, points_of

MAGENTA = [1, 128 / 255, 1, 1]
CYAN = [0, 1, 1, 1]


def run_worker(panel):
    """Run the comparison generator synchronously and return its yields."""
    return list(ConfigurationPanel.thread_worker.__wrapped__(panel))


def fake_results(lt):
    """Comparisons between the sublineages of nodes 4, 5 and 13."""
    names = {0: (4, 1, 1), 1: (5, 1, 1), 2: (13, 10, 10)}
    comps = {(0, 1): 0.0, (0, 2): 3.0, (1, 2): 6.0}
    norms = {(0, 1): (3, 3), (0, 2): (3, 3), (1, 2): (3, 3)}
    return comps, norms, names


@pytest.fixture
def panel(qtbot, viewer, lt_layer):
    viewer.layers.selection.active = lt_layer
    widget = ConfigurationPanel(viewer)
    qtbot.addWidget(widget)
    return widget


class TestConfigurationPanel:
    def test_empty_viewer(self, qtbot, viewer):
        widget = ConfigurationPanel(viewer)
        qtbot.addWidget(widget)
        assert widget.lT is None
        assert widget.list_widget.count() == 0
        assert widget.time_slicer.value == slice(0, 30, 5)

    def test_labelled_roots_are_listed(self, panel):
        assert [n for n, _ in panel.list_of_selected_nodes] == [1, 10, 20]
        assert panel.list_widget.item(0).text() == (
            "A - 1 starts from 0 timepoint"
        )

    def test_default_roots(self, panel):
        assert set(panel.specific_roots) == {1, 10}

    def test_root_selection(self, panel):
        panel.list_widget.item(2).setSelected(True)
        assert panel.specific_roots == [20]
        panel.list_widget.item(2).setSelected(False)
        assert set(panel.specific_roots) == {1, 10}

    def test_times_from_range(self, panel):
        panel.time_slicer.value = slice(1, 10, 3)
        panel.times_selector()
        assert panel.times == [1, 4, 7]

    def test_single_time(self, panel):
        panel.time_slicer.value = slice(3, 3, 1)
        panel.times_selector()
        assert panel.times == [3]

    def test_times_from_list(self, panel):
        panel.time_list_check.setChecked(True)
        panel.time_list.setText("4, 2,4")
        panel.times_selector()
        assert panel.times == [2, 4]

    def test_start_before_the_dataset(self, qtbot, viewer, monkeypatch):
        errors = []
        monkeypatch.setattr(
            config_module.notifications, "show_error", errors.append
        )
        layer = add_lt_layer(viewer, make_lineage_tree(time_offset=10))
        viewer.layers.selection.active = layer
        widget = ConfigurationPanel(viewer)
        qtbot.addWidget(widget)
        widget.time_slicer.value = slice(0, 20, 1)
        widget.times_selector()
        assert widget.times == []
        assert len(errors) == 1

    def test_time_cropping(self, panel):
        panel.time_cropper.setText("4")
        panel.time_cropper.returnPressed.emit()
        assert panel.crop == 4
        assert panel.time_cropper.placeholderText() == "Final Timepoint: 4"
        panel.time_cropping()
        assert panel.crop is None

    def test_tree_style(self, panel):
        assert panel.styl == "simple"
        panel.tree_style_combobox.value = "downsampled"
        assert panel.styl == "downsampled"
        assert not panel.downsampling_widget.native.isHidden()
        panel.tree_style_combobox.value = "full"
        assert panel.styl == "full"
        assert panel.downsampling_widget.native.isHidden()

    def test_label_update(self, panel, lt):
        lt.labels[1] = "renamed"
        panel.label_update()
        assert panel.list_widget.item(0).text().startswith("renamed - 1")

    def test_layer_change(self, panel, viewer):
        layer = add_lt_layer(viewer, make_lineage_tree(time_offset=10), "b")
        viewer.layers.selection.active = layer
        assert panel.lT is layer.metadata["LineageTree"]
        assert panel.time_slicer.start.value == 10
        assert panel.time_slicer.stop.value == 40


class TestComparisonWorker:
    def test_yields_one_result_per_timepoint(self, panel):
        panel.times = [2, 3]
        results = run_worker(panel)
        assert len(results) == 2
        comps, names, norms, times = results[-1]
        assert times == [2, 3]
        # t=2: cells 3 and 12; t=3: cells 4, 5 and 13.
        assert {n[0] for n in names[0].values()} == {3, 12}
        assert {n[0] for n in names[1].values()} == {4, 5, 13}
        assert len(comps[1]) == 3
        assert set(norms[1]) == set(comps[1])
        for node, root, labelled in names[1].values():
            assert root == (1 if node in (4, 5) else 10)
            assert labelled == root

    def test_distances(self, panel):
        panel.times = [2]
        comps, names, _, _ = run_worker(panel)[-1]
        (distance,) = comps[0].values()
        expected = panel.lT.unordered_tree_edit_distance(
            3, 12, style="simple", downsample=2, norm=None
        )
        assert distance == pytest.approx(expected)

    def test_single_cell_timepoints_are_skipped(self, qtbot, viewer):
        # A single cell at t=0 that divides at t=1.
        lT = LineageTree(
            successor={0: [1, 2], 1: [3], 2: [4], 3: [], 4: []},
            time={0: 0, 1: 1, 2: 1, 3: 2, 4: 2},
            starting_time=None,
            pos={n: (n, 0, 0) for n in range(5)},
            labels={0: "root"},
        )
        viewer.layers.selection.active = add_lt_layer(viewer, lT)
        widget = ConfigurationPanel(viewer)
        qtbot.addWidget(widget)
        widget.times = [0, 1]
        results = run_worker(widget)
        assert len(results) == 1
        comps, names, _, _ = results[0]
        assert {n[0] for n in names[0].values()} == {1, 2}
        assert len(comps[0]) == 1

    def test_crop(self, panel):
        panel.times = [2, 3, 4]
        panel.crop = 4
        results = run_worker(panel)
        assert len(results) == 2

    def test_roots_born_later_are_skipped(self, panel):
        panel.specific_roots = [20]
        panel.times = [1, 3]
        results = run_worker(panel)
        assert len(results) == 1
        assert panel.times == [3]


class TestClusterMapCanvas:
    @pytest.fixture
    def canvas(self, qtbot, lt):
        figure = Figure()
        canvas = ClusterMapCanvas(figure, figure.add_subplot(111))
        qtbot.addWidget(canvas)
        comps, norms, names = fake_results(lt)
        canvas._receive_data(comps, norms, names, 3, lt)
        return canvas

    def test_plot(self, canvas):
        plot = canvas.plot
        assert plot.shape == (3, 3)
        np.testing.assert_allclose(plot, plot.T)
        np.testing.assert_allclose(np.diag(plot), 0)
        assert sorted(canvas.names_of_nodes) == [4, 5, 13]
        # The clustering puts the two closest sublineages side by side.
        order = canvas.names_of_nodes
        assert abs(order.index(4) - order.index(5)) == 1
        assert canvas.ax.get_title() == "Comparisons for Timepoint: 3"
        labels = [t.get_text() for t in canvas.ax.get_xticklabels()]
        assert sorted(labels) == ["A", "A", "B"]

    @pytest.mark.parametrize(
        ("norm", "expected"), [("sum", 6 / 6), ("max", 6 / 3), ("None", 6)]
    )
    def test_normalization(self, canvas, norm, expected):
        canvas._change_norm(norm)
        order = canvas.names_of_nodes
        value = canvas.plot[order.index(5), order.index(13)]
        assert value == pytest.approx(expected)

    def test_colormap(self, canvas):
        canvas._change_cmap(colormaps["magma"])
        assert canvas.ax.images[0].get_cmap().name == "magma"

    def test_empty_comparisons_are_not_plotted(self, qtbot, lt):
        figure = Figure()
        canvas = ClusterMapCanvas(figure, figure.add_subplot(111))
        qtbot.addWidget(canvas)
        canvas._receive_data({}, {}, {}, 0, lt)
        assert not hasattr(canvas, "plot")

    def test_click_emits_the_two_sublineages(self, canvas, qtbot):
        order = canvas.names_of_nodes
        event = mouse_event(canvas, canvas.ax, 0, 2)
        with qtbot.waitSignal(canvas.click_signal) as blocker:
            canvas._click(event)
        assert blocker.args == [[order[0], order[2]]]
        xlabels = [t.get_text() for t in canvas.ax.get_xticklabels()]
        assert xlabels[1:] == ["", ""]
        assert xlabels[0]

    def test_click_outside_restores_the_labels(self, canvas):
        canvas._click(mouse_event(canvas, canvas.ax, 0, 2))
        canvas._click(mouse_event(canvas, canvas.ax, 0, 2, button=3))
        xlabels = [t.get_text() for t in canvas.ax.get_xticklabels()]
        assert all(xlabels)

    def test_each_click_is_handled_once(self, canvas):
        emitted = []
        canvas.click_signal.connect(emitted.append)
        for _ in range(3):
            canvas.callbacks.process(
                "button_press_event", mouse_event(canvas, canvas.ax, 1, 1)
            )
        assert len(emitted) == 3

    def test_hover_annotation(self, canvas):
        order = canvas.names_of_nodes
        canvas.print_text((order.index(5), order.index(13)))
        text = canvas.hover_annotation.get_text()
        assert "Score: 1.00" in text
        canvas.remove_annotation()
        assert canvas.hover_annotation not in canvas.ax.texts

    def test_hover_starts_a_timer(self, canvas):
        canvas._on_hover(
            mouse_event(canvas, canvas.ax, 1, 1, "motion_notify_event")
        )
        assert canvas.timer is not None
        canvas._hover_text()
        assert canvas.timer is None
        assert canvas.hover_annotation is not None

    def test_hover_outside_the_axes(self, canvas):
        event = SimpleNamespace(xdata=None, ydata=None, inaxes=None)
        canvas._on_hover(event)
        assert canvas.timer is None

    def test_clear_data(self, canvas):
        canvas.clear_data()
        assert canvas.comps is None
        assert not canvas.ax.images


@pytest.fixture
def clustermap(qtbot, viewer, lt_layer, panel):
    widget = Clustermap(viewer, panel)
    qtbot.addWidget(widget)
    return widget


def load_results(clustermap, lt):
    comps, norms, names = fake_results(lt)
    clustermap.comps, clustermap.norms = [comps], [norms]
    clustermap.naming, clustermap.times = [names], [3]
    clustermap.send_data()


class TestClustermap:
    def test_send_data_without_results(self, clustermap):
        clustermap.send_data()
        assert not hasattr(clustermap.canvas, "plot")

    def test_send_data(self, clustermap, lt):
        load_results(clustermap, lt)
        assert sorted(clustermap.canvas.names_of_nodes) == [4, 5, 13]

    def test_click_colors_the_two_sublineages(self, clustermap, lt_layer):
        clustermap._click([4, 13])
        colors = lt_layer.face_color
        np.testing.assert_allclose(
            colors[points_of(lt_layer, [4, 6, 8])], [MAGENTA] * 3
        )
        np.testing.assert_allclose(
            colors[points_of(lt_layer, [13, 14, 15])], [CYAN] * 3
        )
        np.testing.assert_allclose(colors[points_of(lt_layer, [1, 5])], 1)
        assert all(ax.get_visible() for ax in clustermap.axes_for_tree_graphs)
        assert lt_layer.selected_data == set()

    def test_click_on_the_diagonal(self, clustermap):
        clustermap._click([4, 4])
        assert not clustermap.axes_for_tree_graphs[1].get_visible()

    def test_click_moves_in_time(self, clustermap, viewer):
        clustermap.time_mover.value = True
        clustermap._click([4, 13])
        assert viewer.dims.current_step[0] == 3

    def test_canvas_click_colors_the_points(self, clustermap, lt_layer, lt):
        load_results(clustermap, lt)
        canvas = clustermap.canvas
        canvas._click(mouse_event(canvas, canvas.ax, 0, 0))
        node = canvas.names_of_nodes[0]
        np.testing.assert_allclose(
            lt_layer.face_color[points_of(lt_layer, [node])], [MAGENTA]
        )

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: add_spot_on_graph subtracts len(get_predecessors(c)), "
        "which includes the cell itself, so the spot is one timepoint low",
    )
    def test_cell_inside_a_chain_is_drawn_at_its_time(self, clustermap, lt):
        clustermap._click([2, 12])
        ax = clustermap.axes_for_tree_graphs[0]
        spot = ax.collections[-1].get_offsets()[0]
        assert spot[1] == -lt.time[2]

    def test_reset_colors(self, clustermap, lt_layer):
        clustermap._click([4, 13])
        clustermap.reset_colors.click()
        np.testing.assert_allclose(
            lt_layer.face_color, lt_layer.metadata["default_colors"]
        )

    def test_save_dictionary(self, clustermap, lt, tmp_path):
        load_results(clustermap, lt)
        path = tmp_path / "comparisons.pkl"
        clustermap.save_pkl.value = path
        clustermap.save_dictionary()
        with open(path, "rb") as f:
            saved = pickle.load(f)
        assert saved["times"] == [3]
        assert saved["comparisons"] == clustermap.comps
        assert saved["names"] == clustermap.naming
        assert saved["labels"] == lt.labels

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: the saved end_time is the Clustermap's own `crop`, "
        "which is never updated from the configuration panel",
    )
    def test_saved_end_time_is_the_crop(self, clustermap, lt, tmp_path):
        clustermap.configuration.time_cropper.setText("4")
        clustermap.configuration.time_cropping()
        load_results(clustermap, lt)
        clustermap.save_pkl.value = tmp_path / "comparisons.pkl"
        clustermap.save_dictionary()
        with open(tmp_path / "comparisons.pkl", "rb") as f:
            assert pickle.load(f)["end_time"] == 4

    def test_layer_change(self, clustermap, viewer):
        layer = add_lt_layer(viewer, make_lineage_tree(), "other")
        viewer.layers.selection.active = layer
        assert clustermap.lT is layer.metadata["LineageTree"]

    def test_receive_new_labels(self, clustermap, lt):
        load_results(clustermap, lt)
        lt.labels[1] = "renamed"
        clustermap.receive_new_labels()
        labels = [t.get_text() for t in clustermap.canvas.ax.get_xticklabels()]
        assert labels.count("renamed") == 2

    def test_colormap_and_normalization_widgets(self, clustermap, lt):
        load_results(clustermap, lt)
        combobox = clustermap.colormap.combobox_continuous
        combobox.setCurrentIndex(combobox.findData("magma"))
        assert clustermap.canvas.cmap.name == "magma"
        clustermap.norm_combo.value = "None"
        assert clustermap.canvas.norm_method == "None"


@pytest.mark.xfail(
    strict=True,
    raises=IndexError,
    reason="BUG (lineagetree): get_labelled_ancestor indexes the empty "
    "predecessor of a root when no ancestor is labelled, so comparing "
    "unlabelled roots (the default selection) fails",
)
def test_unlabelled_roots(qtbot, viewer):
    lt = make_lineage_tree(labels={1: "A"})
    layer = add_lt_layer(viewer, lt)
    viewer.layers.selection.active = layer
    widget = ConfigurationPanel(viewer)
    qtbot.addWidget(widget)
    widget.times = [3]
    comps, names, norms, _ = run_worker(widget)[-1]
    figure = Figure()
    canvas = ClusterMapCanvas(figure, figure.add_subplot(111))
    qtbot.addWidget(canvas)
    canvas._receive_data(comps[0], norms[0], names[0], 3, lt)


class TestComparisonsHandler:
    @pytest.fixture
    def handler(self, qtbot, viewer, lt_layer):
        viewer.layers.selection.active = lt_layer
        widget = ComparisonsHandler(viewer)
        qtbot.addWidget(widget)
        return widget

    def test_initial_state(self, handler):
        assert handler.stopbutton.isChecked()
        assert not handler.runbutton.isChecked()
        assert handler.clustermap.configuration is handler.config

    def test_update_dictionary(self, handler, lt):
        comps, norms, names = fake_results(lt)
        handler.update_dictionary(
            ([comps, comps], [names, names], [norms] * 2, [3, 4])
        )
        assert handler.clustermap.time_slider.max == 1
        assert sorted(handler.clustermap.canvas.names_of_nodes) == [4, 5, 13]

    def test_run_the_comparisons(self, handler, qtbot):
        handler.config.time_slicer.value = slice(2, 4, 1)
        handler.thread_handler()
        assert handler.runbutton.isChecked()
        with qtbot.waitSignal(handler.worker.finished, timeout=20000):
            pass
        qtbot.waitUntil(lambda: handler.stopbutton.isChecked())
        assert not handler.runbutton.isChecked()
        assert len(handler.clustermap.comps) == 2
        assert handler.clustermap.time_slider.max == 1
        assert handler.pbr is None

    @pytest.mark.xfail(
        strict=True,
        raises=AttributeError,
        reason="BUG: kill_thread uses self.worker, which does not exist "
        "before the first run (Stop pressed first, or no timepoints)",
    )
    def test_stop_before_running(self, handler):
        # What the Stop button's released signal calls.
        handler.kill_thread()

    @pytest.mark.xfail(
        strict=True,
        raises=AttributeError,
        reason="BUG: with no valid timepoint, thread_handler calls "
        "kill_thread before any worker exists",
    )
    def test_run_without_valid_timepoints(self, handler, monkeypatch):
        monkeypatch.setattr(
            config_module.notifications, "show_error", lambda message: None
        )
        handler.config.time_slicer.value = slice(0, 0, 1)
        handler.config.lT = make_lineage_tree(time_offset=10)
        handler.thread_handler()
