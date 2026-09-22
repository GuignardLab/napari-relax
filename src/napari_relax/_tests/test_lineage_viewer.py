from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest
from matplotlib.figure import Figure

from napari_relax.lineage_tree_analysis.lineage_viewer_widget.lineage_viewer.viewer import (  # noqa: E501
    SingleTreeProgeny,
)
from napari_relax.lineage_tree_analysis.lineage_viewer_widget.progeny_selection import (  # noqa: E501
    ProgenySelection,
)

from .conftest import (
    LINEAGE_A,
    LINEAGE_B,
    LINEAGE_C,
    add_lt_layer,
    key_event,
    make_lineage_tree,
    mouse_event,
    points_of,
)


def graph_index(layer, root):
    graphs = layer.metadata["graphs"][0]
    return next(i for i, g in graphs.items() if g["root"] == root)


@pytest.fixture
def progeny(qtbot, viewer, lt_layer):
    viewer.layers.selection.active = lt_layer
    widget = ProgenySelection(viewer)
    qtbot.addWidget(widget)
    return widget


class TestGetSublineage:
    def test_from_the_division(self, lt):
        scores = ProgenySelection.get_sublineage(3, lt)
        assert scores == dict.fromkeys(LINEAGE_A, 1)

    def test_from_a_daughter(self, lt):
        scores = ProgenySelection.get_sublineage(4, lt)
        # The sister branch is one division away.
        assert scores == {
            1: 1,
            2: 1,
            3: 1,
            4: 1,
            6: 1,
            8: 1,
            5: 2,
            7: 2,
            9: 2,
        }

    def test_lineage_without_division(self, lt):
        assert ProgenySelection.get_sublineage(12, lt) == dict.fromkeys(
            LINEAGE_B, 1
        )


class TestInitialisation:
    def test_empty_viewer(self, qtbot, viewer):
        widget = ProgenySelection(viewer)
        qtbot.addWidget(widget)
        assert widget.lT is None
        assert widget.graph_slider.maximum() == 0
        assert not widget.cell_id_spinbox.isEnabled()
        assert not widget.cell_id_go_button.isEnabled()
        assert "Load a lineagetree" in widget.w_lineedit.placeholderText()

    def test_with_a_lineage_layer(self, progeny, lt_layer, lt):
        assert progeny.lT is lt
        roots = [g["root"] for g in lt_layer.metadata["graphs"][0].values()]
        assert progeny.roots == roots
        assert progeny.graph_slider.maximum() == 2
        assert progeny.cell_id_spinbox.isEnabled()
        assert progeny.cell_id_spinbox.minimum() == 1
        assert progeny.cell_id_spinbox.maximum() == 25
        assert progeny.canvas.root == roots[0]
        label = lt.labels[roots[0]]
        assert progeny.w_lineedit.placeholderText() == (
            f"ID of root: {roots[0]} - Label: {label}"
        )

    def test_bridge_is_stored_in_the_layer(self, progeny, lt_layer):
        assert lt_layer.metadata["interaction_bridge"] is progeny.bridge

    def test_layer_added_after_the_widget(self, qtbot, viewer, lt):
        widget = ProgenySelection(viewer)
        qtbot.addWidget(widget)
        layer = add_lt_layer(viewer, lt)
        viewer.layers.selection.active = layer
        assert widget.lT is lt
        assert widget.graph_slider.maximum() == 2
        assert widget.cell_id_spinbox.isEnabled()
        assert widget.bridge is layer.metadata["interaction_bridge"]

    def test_only_one_click_callback(self, qtbot, viewer, progeny):
        other = ProgenySelection(viewer)
        qtbot.addWidget(other)
        callbacks = [
            c
            for c in viewer.mouse_drag_callbacks
            if "point_click" in c.__name__
        ]
        assert len(callbacks) == 1


class TestLineageSlider:
    def test_slider_changes_the_lineage(self, progeny, lt_layer, lt):
        progeny.graph_slider.setValue(graph_index(lt_layer, 10))
        assert progeny.canvas.root == 10
        assert progeny.w_lineedit.placeholderText() == (
            "ID of root: 10 - Label: B"
        )
        assert progeny.bridge.get_state("graph_slider_value") == (
            graph_index(lt_layer, 10)
        )

    def test_state_is_restored_per_layer(self, progeny, viewer, lt_layer):
        other = add_lt_layer(viewer, make_lineage_tree(), "other")
        viewer.layers.selection.active = lt_layer
        progeny.graph_slider.setValue(2)
        viewer.layers.selection.active = other
        assert progeny.bridge is other.metadata["interaction_bridge"]
        assert progeny.graph_slider.value() == 0
        viewer.layers.selection.active = lt_layer
        assert progeny.graph_slider.value() == 2
        assert progeny.canvas.root == progeny.roots[2]

    def test_time_line_follows_the_viewer(self, progeny, viewer):
        viewer.dims.current_step = (3, *viewer.dims.current_step[1:])
        line = progeny.canvas.line
        assert list(line.get_ydata()) == [-3, -3]
        assert line.get_visible()


class TestLabels:
    def test_label_changer(self, progeny, lt, qtbot):
        root = progeny.roots[0]
        progeny.w_lineedit.setText("New name")
        with qtbot.waitSignal(progeny.signal) as blocker:
            progeny.w_lineedit.returnPressed.emit()
        assert lt.labels[root] == "New name"
        assert blocker.args == [lt.labels]
        assert progeny.w_lineedit.placeholderText() == (
            f"ID of root: {root} - Label: New name"
        )
        assert progeny.w_lineedit.text() == ""

    @pytest.mark.xfail(
        strict=True,
        raises=KeyError,
        reason="BUG: the label is popped twice from the same LineageTree "
        "(self.lT is the layer's LineageTree)",
    )
    def test_label_remover(self, progeny, lt):
        root = progeny.roots[0]
        progeny.label_remover()
        assert root not in lt.labels

    def test_show_all_labels(self, progeny, modal_calls):
        progeny.show_all_labels()
        (box,) = modal_calls
        assert box.informativeText() == "1:A\n10:B\n20:C"


class TestSelection:
    def test_select_the_lineage(self, progeny, lt_layer):
        lt_layer.selected_data = set(points_of(lt_layer, [6]))
        progeny.select_the_lineage()
        assert lt_layer.selected_data == set(points_of(lt_layer, LINEAGE_A))
        assert progeny.graph_slider.value() == graph_index(lt_layer, 1)
        assert progeny.canvas.selected_subtree == LINEAGE_A
        assert progeny.bridge.get_state("selected_subtree") == LINEAGE_A

    def test_select_the_lineage_without_selection(self, progeny, lt_layer):
        assert progeny.select_the_lineage() == 0

    @pytest.mark.xfail(
        strict=True,
        raises=Warning,
        reason="BUG: lineages starting after the first timepoint are not "
        "found (val_finder returns None) and a Warning is raised",
    )
    def test_select_the_lineage_of_a_late_root(self, progeny, lt_layer):
        lt_layer.selected_data = set(points_of(lt_layer, [24]))
        progeny.select_the_lineage()
        assert lt_layer.selected_data == set(points_of(lt_layer, LINEAGE_C))

    def test_sub_point_painter(self, progeny, lt_layer):
        lt_layer.selected_data = set(points_of(lt_layer, [6]))
        progeny.sub_point_painter()
        assert lt_layer.selected_data == set(points_of(lt_layer, [4, 6, 8]))
        assert progeny.bridge.get_state("selected_subtree") == {4, 6, 8}
        assert progeny.w_lineedit.placeholderText() == (
            "ID of root: 4 - Label: Unlabeled"
        )

    def test_points_selector(self, progeny, lt_layer):
        lt_layer.selected_data = set(points_of(lt_layer, [12]))
        progeny.points_selector()
        assert lt_layer.selected_data == set(points_of(lt_layer, LINEAGE_B))


class TestCellIdSelector:
    def test_go_to_a_cell(self, progeny, viewer, lt_layer):
        progeny.cell_id_spinbox.setValue(6)
        progeny.cell_id_go_button.click()
        assert progeny.graph_slider.value() == graph_index(lt_layer, 1)
        assert progeny.canvas.marked_cell_id == 6
        assert progeny.canvas.selected_subtree == set()
        assert lt_layer.selected_data == set(points_of(lt_layer, [6]))
        assert viewer.dims.current_step[0] == 4
        assert progeny.w_lineedit.placeholderText() == (
            "ID of root: 6 - Label: Unlabeled"
        )

    def test_unknown_id_uses_the_closest_cell(self, progeny, lt_layer):
        progeny.cell_id_spinbox.setValue(17)
        progeny.cell_id_selector()
        assert progeny.cell_id_spinbox.value() == 15
        assert lt_layer.selected_data == set(points_of(lt_layer, [15]))

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: cells of lineages starting after the first timepoint "
        "are not found (val_finder returns None)",
    )
    def test_go_to_a_cell_of_a_late_lineage(self, progeny, lt_layer):
        progeny.cell_id_spinbox.setValue(24)
        progeny.cell_id_selector()
        assert lt_layer.selected_data == set(points_of(lt_layer, [24]))


class TestLineageViewerClicks:
    def test_click_selects_the_subtree(self, progeny, lt_layer):
        progeny._click_on_tree_graph({"value": 4, "dblclick": False})
        assert progeny.canvas.selected_subtree == {4, 6, 8}
        assert lt_layer.selected_data == set(points_of(lt_layer, [4, 6, 8]))
        assert progeny.cell_id_spinbox.value() == 4
        assert progeny.w_lineedit.placeholderText() == (
            "ID of root: 4 - Label: Unlabeled"
        )

    def test_double_click_moves_in_time(self, progeny, viewer):
        progeny._click_on_tree_graph({"value": 5, "dblclick": True})
        assert viewer.dims.current_step[0] == 3

    def test_background_click_resets(self, progeny, lt_layer):
        progeny._click_on_tree_graph({"value": 4, "dblclick": False})
        progeny.bridge.hide_lineages(list(LINEAGE_B))
        progeny._click_on_tree_graph({})
        assert lt_layer.selected_data == set()
        assert lt_layer.shown.all()

    def test_canvas_click_reaches_the_widget(self, progeny, lt_layer):
        canvas = progeny.canvas
        index = graph_index(lt_layer, 1)
        progeny.graph_slider.setValue(index)
        x, y = canvas.hier[3]
        canvas.callbacks.process(
            "button_press_event", mouse_event(canvas, canvas.ax, x, y)
        )
        assert progeny.canvas.selected_subtree == set(
            progeny.lT.get_subtree_nodes(3)
        )


class TestPointClick:
    @staticmethod
    def event(modifiers=("Shift",), button=2):
        return SimpleNamespace(
            modifiers=list(modifiers),
            button=button,
            position=np.zeros(4),
            view_direction=np.array([0, 1, 0, 0]),
            dims_displayed=[1, 2, 3],
        )

    def test_shift_right_click_selects_a_cell(self, progeny, lt_layer):
        progeny.bridge.find_node_at_position = MagicMock(
            return_value=(lt_layer, 6)
        )
        progeny.point_click(None, self.event())
        assert lt_layer.selected_data == set(points_of(lt_layer, [6]))
        assert progeny.cell_id_spinbox.value() == 6
        assert progeny.canvas.marked_cell_id == 6
        assert progeny.graph_slider.value() == graph_index(lt_layer, 1)

    def test_click_in_the_void(self, progeny, lt_layer):
        progeny.bridge.find_node_at_position = MagicMock(return_value=None)
        progeny.canvas.marked_cell_id = 3
        progeny.point_click(None, self.event())
        assert progeny.canvas.marked_cell_id is None

    @pytest.mark.parametrize(
        ("modifiers", "button"), [((), 2), (("Shift",), 1), (("Control",), 2)]
    )
    def test_other_clicks_are_ignored(
        self, progeny, lt_layer, modifiers, button
    ):
        progeny.bridge.find_node_at_position = MagicMock()
        progeny.point_click(None, self.event(modifiers, button))
        progeny.bridge.find_node_at_position.assert_not_called()


class TestVisibility:
    def test_hide_lineage(self, progeny, lt_layer):
        progeny._click_on_tree_graph({"value": 1, "dblclick": False})
        progeny.hide_lineage()
        assert not lt_layer.shown[points_of(lt_layer, LINEAGE_A)].any()
        assert lt_layer.shown[points_of(lt_layer, LINEAGE_B)].all()
        state = progeny.bridge.get_state()
        assert state["visibility_state"] == "lineage_hidden"
        assert set(state["hidden_lineage"]) == LINEAGE_A

    def test_hide_lineage_of_the_selected_point(self, progeny, lt_layer):
        progeny.canvas.selected_subtree = set()
        lt_layer.selected_data = set(points_of(lt_layer, [10]))
        progeny.hide_lineage()
        assert not lt_layer.shown[points_of(lt_layer, LINEAGE_B)].any()
        assert progeny.canvas.selected_subtree == LINEAGE_B

    def test_show_lineage_saves_the_state(self, progeny, lt_layer):
        progeny._click_on_tree_graph({"value": 1, "dblclick": False})
        progeny.show_lineage()
        state = progeny.bridge.get_state()
        assert state["visibility_state"] == "lineage_only"
        assert set(state["visible_lineage"]) == LINEAGE_A

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: PointsAdapter.show_only_nodes never hides the other "
        "points",
    )
    def test_show_lineage_hides_the_others(self, progeny, lt_layer):
        progeny._click_on_tree_graph({"value": 1, "dblclick": False})
        progeny.show_lineage()
        assert not lt_layer.shown[points_of(lt_layer, LINEAGE_B)].any()

    def test_show_all_restores_everything(self, progeny, lt_layer):
        progeny._click_on_tree_graph({"value": 4, "dblclick": False})
        progeny.bridge.hide_lineages(list(LINEAGE_B | LINEAGE_C))
        progeny.show_all()
        assert lt_layer.shown.all()
        # The selected subtree stays highlighted.
        assert lt_layer.selected_data == set(points_of(lt_layer, [4, 6, 8]))
        assert progeny.bridge.get_state("visibility_state") == "all_visible"

    def test_hide_all_saves_the_state(self, progeny):
        progeny.hide_all()
        assert progeny.bridge.get_state("visibility_state") == "all_hidden"

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: PointsAdapter.show_only_nodes([]) does not hide any "
        "point",
    )
    def test_hide_all_hides_the_points(self, progeny, lt_layer):
        progeny.hide_all()
        assert not lt_layer.shown.any()

    @pytest.mark.xfail(
        strict=True,
        raises=AttributeError,
        reason="BUG: once a Tracks layer is added, hiding a lineage "
        "fails in TracksAdapter (no `_track_connex` on Tracks layers)",
    )
    def test_hide_lineage_with_tracks(self, progeny, viewer, lt_layer):
        from napari_relax.lineage_tree_analysis.cells_size import CellSize

        CellSize(viewer).add_tracks(None)
        viewer.layers.selection.active = lt_layer
        progeny._click_on_tree_graph({"value": 1, "dblclick": False})
        progeny.hide_lineage()


def test_update_time_slider_uses_the_earliest_dataset(
    progeny, viewer, lt_layer
):
    add_lt_layer(viewer, make_lineage_tree(time_offset=10), "late")
    viewer.layers.selection.active = lt_layer
    progeny.update_time_slider_for_cell(6)
    assert viewer.dims.current_step[0] == 4


@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason="BUG: `if not active_layer and ...` dereferences None when no "
    "lineage layer is selected (should be `or`)",
)
def test_progeny_diagram_loader_without_layer(progeny, viewer):
    viewer.layers.selection.clear()
    progeny.progeny_diagram_loader()


class TestSingleTreeProgeny:
    @pytest.fixture
    def canvas(self, qtbot, lt_layer, lt):
        figure = Figure()
        ax = figure.add_subplot(111)
        canvas = SingleTreeProgeny(figure, ax)
        qtbot.addWidget(canvas)
        index = graph_index(lt_layer, 1)
        graphs, pos = lt_layer.metadata["graphs"]
        canvas.change_lineage(
            1, lt, graphs[index], pos[index], lt_layer.metadata
        )
        return canvas

    def test_change_lineage(self, canvas, lt):
        assert canvas.root == 1
        assert canvas.lT is lt
        assert canvas.lims_of_tree == (0, 5)
        assert canvas.xlim == (canvas.xmin, canvas.xmax)
        assert canvas.ax.get_xlim() == pytest.approx(canvas.xlim)

    def test_change_lineage_without_tree_does_nothing(self, canvas):
        canvas.change_lineage(10, None)
        assert canvas.root == 1

    def test_coloring_uses_the_layer_colors(self, canvas, lt_layer):
        index = lt_layer.metadata["lT2napari"][1]
        expected = lt_layer.metadata["default_colors"][index].tolist()
        assert canvas.coloring[1] == expected

    def test_selected_nodes_are_highlighted(self, canvas):
        canvas.selected_nodes = {4}
        assert canvas.coloring[4] == canvas.selected_color

    def test_current_face_colors_are_used(self, canvas, lt_layer):
        colors = np.tile([0.1, 0.2, 0.3, 1.0], (len(lt_layer.data), 1))
        canvas.update_face_colors(colors)
        assert lt_layer.metadata["current_face_colors"] is colors
        canvas.draw_graph()
        assert canvas.coloring[1] == pytest.approx([0.1, 0.2, 0.3, 1.0])

    def test_labels_are_drawn(self, canvas):
        texts = [t.get_text() for t in canvas.ax.texts]
        assert "Label: A\nID: 1" in texts
        assert "Label: 8\nID: 8" in texts

    def test_click_on_a_node(self, canvas, qtbot):
        x, y = canvas.hier[4]
        with qtbot.waitSignal(canvas.node_signal) as blocker:
            canvas.click(mouse_event(canvas, canvas.ax, x, y, dblclick=True))
        assert blocker.args == [{"value": 4, "dblclick": True}]
        assert canvas.marked_cell_id == 4
        assert set(canvas.selected_nodes) == {4, 6, 8}

    def test_click_on_the_background(self, canvas, qtbot):
        x = canvas.xmin + 0.01 * (canvas.xmax - canvas.xmin)
        y = canvas.ymin + 0.01 * (canvas.ymax - canvas.ymin)
        with qtbot.waitSignal(canvas.node_signal) as blocker:
            canvas.click(mouse_event(canvas, canvas.ax, x, y))
        assert blocker.args == [{}]
        assert canvas.marked_cell_id is None

    def test_other_buttons_are_ignored(self, canvas):
        emitted = []
        canvas.node_signal.connect(emitted.append)
        x, y = canvas.hier[4]
        canvas.click(mouse_event(canvas, canvas.ax, x, y, button=3))
        assert not emitted

    def test_scroll_zooms_around_the_cursor(self, canvas):
        x, y = canvas.hier[3]
        width = np.diff(canvas.ax.get_xlim())[0]
        event = mouse_event(canvas, canvas.ax, x, y, "scroll_event", "up")
        canvas.on_scroll(event)
        new_xlim = canvas.ax.get_xlim()
        assert np.diff(new_xlim)[0] == pytest.approx(width / 1.4)
        assert new_xlim[0] <= x <= new_xlim[1]

    def test_zooming_out_is_limited_to_the_tree(self, canvas):
        x, y = canvas.hier[3]
        event = mouse_event(canvas, canvas.ax, x, y, "scroll_event", "down")
        canvas.on_scroll(event)
        assert canvas.ax.get_xlim() == pytest.approx(canvas.xlim)
        assert canvas.ax.get_ylim() == pytest.approx(canvas.ylim)

    def test_pan(self, canvas):
        ax = canvas.ax
        xlim = ax.get_xlim()
        start = mouse_event(canvas, ax, *canvas.hier[3], button=3)
        canvas.pan_start(start)
        assert canvas.pan
        move = mouse_event(
            canvas, ax, *canvas.hier[3], "motion_notify_event", button=3
        )
        move.x += 50
        canvas.panning(move)
        assert ax.get_xlim()[0] < xlim[0]
        canvas.pan_stop(
            mouse_event(canvas, ax, 0, 0, "button_release_event", button=3)
        )
        assert not canvas.pan

    def test_reset_with_z(self, canvas):
        canvas.ax.set_xlim(0, 1)
        canvas.reset(key_event(canvas, "z"))
        assert canvas.ax.get_xlim() == pytest.approx(canvas.xlim)

    def test_cell_marker_on_a_node(self, canvas):
        before = len(canvas.ax.collections)
        canvas._draw_cell_marker(4)
        marker = canvas.ax.collections[before]
        np.testing.assert_allclose(marker.get_offsets()[0], canvas.hier[4])

    def test_cell_position_inside_a_chain(self, canvas):
        # Node 2 (t=1) is halfway between node 1 (t=0) and node 3 (t=2).
        position = canvas._calculate_cell_position_on_edge(2, 1)
        expected = (np.array(canvas.hier[1]) + canvas.hier[3]) / 2
        np.testing.assert_allclose(position, expected)

    def test_cell_marker_of_an_unknown_cell(self, canvas):
        before = len(canvas.ax.collections)
        canvas._draw_cell_marker(999)
        assert len(canvas.ax.collections) == before

    def test_time_line(self, canvas):
        canvas.time_line(SimpleNamespace(value=(2, 0, 0, 0)))
        assert list(canvas.line.get_ydata()) == [-2, -2]
        assert canvas.line.get_visible()
        canvas.time_line(SimpleNamespace(value=(40, 0, 0, 0)))
        assert not canvas.line.get_visible()

    def test_settings_change_the_drawing(self, canvas):
        from napari.settings import get_plugin_settings

        settings = get_plugin_settings("napari-relax").progeny_canvas
        settings.node_size = 3.5
        settings.font_size = 12
        assert canvas.node_size == 3.5
        assert canvas.fontsize == 12
        assert {t.get_fontsize() for t in canvas.ax.texts} == {12}
