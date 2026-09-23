import numpy as np
import pytest
from matplotlib import colormaps
from qtpy.QtWidgets import QTabWidget

from napari_relax.lineage_tree_analysis.recoloring_with_attributes_widget import (  # noqa: E501
    node_based_recoloring,
)
from napari_relax.lineage_tree_analysis.recoloring_with_attributes_widget.clone_based_recoloring import (  # noqa: E501
    CloneRecoloring,
)
from napari_relax.lineage_tree_analysis.recoloring_with_attributes_widget.node_based_recoloring import (  # noqa: E501
    Coloring,
    LineeditCheckbox,
    MissingData,
    Quantitative,
    filter_dicts_of_objects_by_values,
)
from napari_relax.lineage_tree_analysis.recoloring_with_attributes_widget.recoloring_widget import (  # noqa: E501
    RecoloringWidget,
)

from .conftest import (
    LINEAGE_A,
    LINEAGE_B,
    LINEAGE_C,
    TIME,
    add_lt_layer,
    make_lineage_tree,
    points_of,
)

BLACK = [0, 0, 0, 1]


def colors_of(layer, nodes):
    return layer.face_color[points_of(layer, nodes)]


def color_set(colors):
    """Distinct colors, rounded as napari stores them in float32."""
    return {tuple(np.round(c, 5)) for c in colors}


class TestFilterDictsOfObjectsByValues:
    def test_numeric_attributes(self, lt):
        lt.volume = {n: float(n) for n in TIME}
        lt.cell_type = dict.fromkeys(TIME, "neuron")
        lt.empty = {}
        numeric = filter_dicts_of_objects_by_values(lt, (int, float))
        assert "volume" in numeric
        assert "cell_type" not in numeric
        assert "empty" not in numeric
        # Topology and time are never offered.
        assert not {"_successor", "_predecessor", "_time"} & set(numeric)

    def test_string_attributes(self, lt):
        lt.cell_type = dict.fromkeys(TIME, "neuron")
        assert "cell_type" in filter_dicts_of_objects_by_values(lt, str)


class TestMissingData:
    @pytest.fixture
    def missing(self, qtbot):
        widget = MissingData()
        qtbot.addWidget(widget)
        return widget

    def test_default_is_black(self, missing):
        assert missing.selected() == "Black"
        assert all(b.isHidden() for b in missing.buttongroup_default.buttons())

    def test_propagate(self, missing):
        missing.check_propagate.click()
        assert missing.selected() == "Propagate from Ancestor"

    def test_default_value_options(self, missing):
        missing.check_default_value.click()
        assert not any(
            b.isHidden() for b in missing.buttongroup_default.buttons()
        )
        assert missing.custom.isChecked()
        missing.median.click()
        assert missing.selected() == "Median"
        missing.check_black.click()
        assert all(b.isHidden() for b in missing.buttongroup_default.buttons())

    def test_custom_value(self, missing):
        missing.check_default_value.click()
        missing.custom.setText(3)
        assert missing.selected() == 3

    @pytest.mark.xfail(
        strict=True,
        raises=ValueError,
        reason="BUG: 'Default Value' checks 'Custom value' with an empty "
        "field, and int('') raises",
    )
    def test_default_value_without_typing(self, missing):
        missing.check_default_value.click()
        missing.selected()

    def test_nothing_selected_warns(self, missing):
        missing.buttongroup.setExclusive(False)
        missing.check_black.setChecked(False)
        with pytest.warns(UserWarning, match="select a method"):
            assert missing.selected() is None


class TestLineeditCheckbox:
    def test_text(self, qtbot):
        checkbox = LineeditCheckbox()
        qtbot.addWidget(checkbox)
        checkbox.setText(12)
        assert checkbox.lineedit.text() == "12"
        assert checkbox.text() == 12

    @pytest.mark.xfail(
        strict=True,
        raises=ValueError,
        reason="BUG: the field accepts decimals (QDoubleValidator) but "
        "text() calls int() on them",
    )
    def test_decimal_text(self, qtbot):
        checkbox = LineeditCheckbox()
        qtbot.addWidget(checkbox)
        checkbox.setText(2.5)
        assert checkbox.text() == 2.5


@pytest.fixture
def quantitative(qtbot, viewer, lt_layer, lt):
    viewer.layers.selection.active = lt_layer
    widget = Quantitative(viewer)
    qtbot.addWidget(widget)
    return widget


def recolor(widget, attribute, values, method=None):
    """Set a node attribute and recolor with a missing-data method."""
    setattr(widget.lT, attribute, values)
    widget.layer_change()
    widget.selected_attribute.setCurrentText(attribute)
    if method is not None:
        method()
    widget.generate_colors()


class TestQuantitative:
    def cmap(self, widget, value):
        return widget.colorbox.get_cmap().map(value)[0]

    def test_attributes_are_listed(self, qtbot, viewer, lt):
        lt.volume = {n: float(n) for n in TIME}
        viewer.layers.selection.active = add_lt_layer(viewer, lt)
        widget = Quantitative(viewer)
        qtbot.addWidget(widget)
        items = [
            widget.selected_attribute.itemText(i)
            for i in range(widget.selected_attribute.count())
        ]
        assert items[0] == "None"
        assert "volume" in items

    def test_empty_viewer(self, qtbot, viewer):
        widget = Quantitative(viewer)
        qtbot.addWidget(widget)
        assert widget.selected_attribute.count() == 1

    def test_layer_change(self, quantitative, viewer):
        other_lt = make_lineage_tree()
        other_lt.speed = dict.fromkeys(TIME, 1.5)
        other = add_lt_layer(viewer, other_lt, "other")
        viewer.layers.selection.active = other
        assert quantitative.selected_attribute.findText("speed") > 0
        viewer.layers.selection.clear()
        assert quantitative.selected_attribute.count() == 1

    def test_none_attribute_warns(self, quantitative):
        with pytest.warns(UserWarning, match="valid attribute"):
            quantitative.generate_colors()

    def test_every_node_colored(self, quantitative, lt_layer, qtbot):
        values = {n: 0.5 + n for n in TIME}
        with qtbot.waitSignal(quantitative.color_signal):
            recolor(quantitative, "volume", values)
        low, high = min(values.values()), max(values.values())
        for node, value in values.items():
            expected = self.cmap(quantitative, (value - low) / (high - low))
            np.testing.assert_allclose(
                colors_of(lt_layer, [node])[0], expected, atol=1e-6
            )

    def test_missing_nodes_in_black(self, quantitative, lt_layer):
        recolor(quantitative, "volume", {1: 0.5, 2: 1.5})
        np.testing.assert_allclose(colors_of(lt_layer, LINEAGE_B), [BLACK] * 6)
        np.testing.assert_allclose(
            colors_of(lt_layer, [2])[0], self.cmap(quantitative, 1.0)
        )

    def test_propagate_from_ancestor(self, quantitative, lt_layer):
        values = {1: 0.5, 4: 2.5, 5: 1.5}
        recolor(
            quantitative,
            "volume",
            values,
            quantitative.miss_data.check_propagate.click,
        )
        for node, ancestor in [(2, 1), (3, 1), (6, 4), (8, 4), (9, 5)]:
            np.testing.assert_allclose(
                colors_of(lt_layer, [node]), colors_of(lt_layer, [ancestor])
            )
        np.testing.assert_allclose(colors_of(lt_layer, LINEAGE_C), [BLACK] * 6)

    def test_propagate_from_sibling_is_not_implemented(
        self, quantitative, lt_layer, monkeypatch
    ):
        messages = []
        monkeypatch.setattr(
            node_based_recoloring, "show_warning", messages.append
        )
        before = lt_layer.face_color.copy()
        recolor(
            quantitative,
            "volume",
            {1: 0.5, 2: 1.5},
            quantitative.miss_data.sibling.click,
        )
        assert messages == ["Not implemented yet!"]
        np.testing.assert_allclose(lt_layer.face_color, before)

    @pytest.mark.parametrize(
        ("option", "expected"),
        [("min", 0.0), ("mean", 0.375), ("median", 0.125)],
    )
    def test_default_values_of_missing_nodes(
        self, quantitative, lt_layer, option, expected
    ):
        def choose():
            quantitative.miss_data.check_default_value.click()
            getattr(quantitative.miss_data, option).click()

        # Mean 1.25 and median 0.75, normalized on the [0.5, 2.5] range.
        recolor(quantitative, "volume", {1: 0.5, 2: 0.75, 3: 2.5}, choose)
        np.testing.assert_allclose(
            colors_of(lt_layer, LINEAGE_B),
            [self.cmap(quantitative, expected)] * 6,
            atol=1e-6,
        )

    def test_custom_value_of_missing_nodes(self, quantitative, lt_layer):
        def choose():
            quantitative.miss_data.check_default_value.click()
            quantitative.miss_data.custom.setText(2)

        recolor(quantitative, "volume", {1: 0.5, 3: 4.5}, choose)
        np.testing.assert_allclose(
            colors_of(lt_layer, [10])[0],
            self.cmap(quantitative, (2 - 0.5) / 4),
            atol=1e-6,
        )

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: nodes missing a value are computed from the "
        "attribute values instead of its keys, so nodes that have a "
        "value are also given the default color",
    )
    def test_default_value_keeps_the_nodes_with_values(
        self, quantitative, lt_layer
    ):
        def choose():
            quantitative.miss_data.check_default_value.click()
            quantitative.miss_data.min.click()

        recolor(quantitative, "volume", {1: 0.5, 2: 2.5}, choose)
        np.testing.assert_allclose(
            colors_of(lt_layer, [2])[0], self.cmap(quantitative, 1.0)
        )

    @pytest.mark.xfail(
        strict=True,
        raises=ZeroDivisionError,
        reason="BUG: a constant attribute divides by max - min == 0",
    )
    def test_constant_attribute(self, quantitative):
        recolor(quantitative, "volume", dict.fromkeys(TIME, 1.0))

    def test_reset(self, quantitative, lt_layer, qtbot):
        recolor(quantitative, "volume", {n: 0.5 + n for n in TIME})
        with qtbot.waitSignal(quantitative.color_signal):
            quantitative.reset_button_pr()
        np.testing.assert_allclose(
            lt_layer.face_color, lt_layer.metadata["default_colors"]
        )

    def test_reset_without_layer(self, quantitative, viewer):
        viewer.layers.selection.clear()
        emitted = []
        quantitative.color_signal.connect(lambda: emitted.append(1))
        quantitative.reset_button_pr()
        assert not emitted


def test_coloring_switches_between_tabs(qtbot, viewer):
    widget = Coloring(viewer)
    qtbot.addWidget(widget)
    stack = widget.quant.parent()
    assert stack.currentWidget() is widget.quant
    widget.combobox.setCurrentIndex(1)
    assert stack.currentIndex() == 1


def test_recoloring_widget_tabs(qtbot, viewer):
    widget = RecoloringWidget(viewer)
    qtbot.addWidget(widget)
    tabs = widget.findChild(QTabWidget)
    assert [tabs.tabText(i) for i in range(tabs.count())] == [
        "Clone based Recoloring",
        "Node based Recoloring",
    ]
    assert widget.name == "Attribute Based Recoloring"


@pytest.fixture
def clones(qtbot, viewer, lt_layer):
    viewer.layers.selection.active = lt_layer
    widget = CloneRecoloring(viewer)
    qtbot.addWidget(widget)
    return widget


class TestCloneRecoloring:
    def test_population_graph(self, clones):
        population, marker = clones.ax.lines
        np.testing.assert_array_equal(population.get_xdata(), range(5))
        np.testing.assert_array_equal(population.get_ydata(), [2, 2, 3, 4, 5])
        assert list(marker.get_xdata()) == [0, 0]
        assert clones.ax.get_title() == "Number of cells \n(0002)"

    def test_slider_moves_the_marker(self, clones):
        clones.time_slider.value = 0.5
        assert list(clones.pos_line.get_xdata()) == [2, 2]
        assert clones.ax.get_xlabel() == "time [002]"
        assert clones.ax.get_title() == "Number of cells \n(0003)"

    def test_color_clones_at_the_first_timepoint(self, clones, lt_layer):
        clones.color_clones()
        cmap = clones.combobox.get_cmap()
        a, b = colors_of(lt_layer, LINEAGE_A), colors_of(lt_layer, LINEAGE_B)
        assert len(np.unique(a, axis=0)) == 1
        assert len(np.unique(b, axis=0)) == 1
        assert color_set([a[0], b[0]]) == color_set([cmap(0.0), cmap(0.5)])
        # Cells that are not descendants of the clones are not colored.
        np.testing.assert_allclose(colors_of(lt_layer, LINEAGE_C), 0)

    def test_color_clones_after_divisions(self, clones, lt_layer):
        clones.time_slider.value = 0.6  # round(0.6 * 5) = t3
        clones.color_clones()
        clone_colors = [
            tuple(colors_of(lt_layer, [n])[0]) for n in (4, 5, 13, 21)
        ]
        assert len(set(clone_colors)) == 4
        np.testing.assert_allclose(
            colors_of(lt_layer, [6, 8]), [clone_colors[0]] * 2
        )
        np.testing.assert_allclose(colors_of(lt_layer, [1, 2, 3, 20]), 0)

    def test_colormap_choice(self, clones, lt_layer):
        clones.cmap_choice.setCurrentIndex(clones.cmap_choice.findData("Set1"))
        clones.color_clones()
        cmap = colormaps["Set1"]
        assert color_set(colors_of(lt_layer, [1, 10])) == color_set(
            [cmap(0.0), cmap(0.5)]
        )

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: color_clones ignores the first timepoint (t_b) when "
        "converting the slider value, unlike the population graph",
    )
    def test_color_clones_follows_the_graph(self, qtbot, viewer):
        layer = add_lt_layer(viewer, make_lineage_tree(time_offset=10))
        viewer.layers.selection.active = layer
        widget = CloneRecoloring(viewer)
        qtbot.addWidget(widget)
        widget.time_slider.value = 0.5
        assert list(widget.pos_line.get_xdata()) == [12, 12]
        widget.color_clones()
        # The clones of t=12 are the cells 3, 12 and 20: lineage C is
        # colored and the cells before t=12 are not.
        assert len(color_set(colors_of(layer, [3, 12, 20]))) == 3
        np.testing.assert_allclose(colors_of(layer, [20, 25])[:, 3], 1)
        np.testing.assert_allclose(colors_of(layer, [1, 2, 10, 11]), 0)

    def test_reset_colors(self, clones, lt_layer):
        clones.color_clones()
        clones.reset_colors()
        np.testing.assert_allclose(
            lt_layer.face_color, lt_layer.metadata["default_colors"]
        )

    def test_without_lineage_layer(self, qtbot, viewer):
        widget = CloneRecoloring(viewer)
        qtbot.addWidget(widget)
        assert widget.time_nodes is None
        widget.color_clones()

    def test_layer_change(self, clones, viewer):
        other = add_lt_layer(viewer, make_lineage_tree(time_offset=3), "late")
        viewer.layers.selection.active = other
        assert clones.lT is other.metadata["LineageTree"]
        population, _ = clones.ax.lines
        np.testing.assert_array_equal(population.get_xdata(), range(3, 8))
        viewer.layers.selection.clear()
        assert clones.time_nodes is None
