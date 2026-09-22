import warnings

import numpy as np
import pytest
from lineagetree import LineageTree
from lineagetree._core.utils import hierarchical_pos
from qtpy.QtWidgets import QLabel, QMessageBox, QVBoxLayout, QWidget
from scipy.spatial.transform import Rotation

from napari_relax._utils import (
    _infer_point_size,
    _select_active_lt_layer,
    _transform_float_value_to_slider_int,
    _transform_slider_int_value_to_float,
    clear_layout,
    create_links_and_chains,
    custom_error,
    error_cell_selection,
    error_image_selection,
    extract_lineage,
    find_pair_with_the_longest_distance,
    inject_lineage,
    plot_lineages_for_tree_manip,
    rotate_3d,
)

from .conftest import LINEAGE_A, make_lineage_tree


def _chain_tree(n_times, spacing=1.0):
    """Two parallel chains of cells, ``spacing`` apart, over n_times."""
    successor = {}
    time = {}
    pos = {}
    for chain, x in enumerate((0.0, spacing)):
        nodes = [chain * n_times + t for t in range(n_times)]
        for t, node in enumerate(nodes):
            successor[node] = [nodes[t + 1]] if t + 1 < n_times else []
            time[node] = t
            pos[node] = (x, 0.0, 0.0)
    return LineageTree(
        successor=successor, time=time, starting_time=None, pos=pos
    )


class TestInferPointSize:
    def test_values_from_nearest_neighbours(self, lt):
        # Hand computed from conftest positions: the smallest median
        # nearest neighbour distance is 10 (t=4, t=5), the largest
        # nearest neighbour distance is 50 (t<=3).
        minimal, optimal, maximal = _infer_point_size(lt)
        assert optimal == pytest.approx(5.0)
        assert maximal == pytest.approx(25.0)
        assert minimal == pytest.approx(0.01 * optimal)

    def test_single_cell_per_timepoint_uses_defaults(self):
        lT = LineageTree(
            successor={0: [1], 1: [2], 2: []},
            time={0: 0, 1: 1, 2: 2},
            starting_time=None,
            pos={0: (0, 0, 0), 1: (1, 0, 0), 2: (2, 0, 0)},
        )
        assert _infer_point_size(lT) == (1.0, 100, 1000)

    def test_maximal_is_at_least_ten_times_optimal(self):
        # All nearest neighbour distances are equal, so max == optimal
        # and the heuristic spreads the range.
        minimal, optimal, maximal = _infer_point_size(_chain_tree(5, 4.0))
        assert optimal == pytest.approx(2.0)
        assert maximal == pytest.approx(20.0)

    def test_long_datasets_are_subsampled(self, monkeypatch):
        lT = _chain_tree(150, 2.0)
        queried = []
        original = LineageTree.idx3d

        def spy(self, t):
            queried.append(t)
            return original(self, t)

        monkeypatch.setattr(LineageTree, "idx3d", spy)
        _, optimal, _ = _infer_point_size(lT)
        assert optimal == pytest.approx(1.0)
        # 150 timepoints sampled every 150 // 10 = 15 timepoints.
        assert queried == list(range(0, 150, 15))


class TestSliderTransforms:
    @pytest.mark.parametrize("value", [0, 1, 20, 50, 99, 100])
    def test_round_trip(self, value):
        size = _transform_slider_int_value_to_float(value, 0.5, 10.5)
        assert _transform_float_value_to_slider_int(size, 0.5, 10.5) in (
            value - 1,
            value,
        )

    def test_linear_mapping(self):
        assert _transform_slider_int_value_to_float(0, 2, 12) == 2
        assert _transform_slider_int_value_to_float(50, 2, 12) == 7
        assert _transform_slider_int_value_to_float(100, 2, 12) == 12
        assert _transform_float_value_to_slider_int(7, 2, 12) == 50

    def test_missing_bounds_fall_back_to_identity(self):
        assert _transform_slider_int_value_to_float(42, None, None) == 42.0
        assert _transform_float_value_to_slider_int(4.7, None, 3) == 4

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: a lower bound of 0 is falsy, so the value is not mapped",
    )
    def test_zero_lower_bound_is_mapped(self):
        assert _transform_slider_int_value_to_float(50, 0, 10) == 5


class TestSelectActiveLtLayer:
    def test_no_layer(self, viewer):
        assert _select_active_lt_layer(viewer) is None

    def test_lineage_points_layer(self, viewer, lt_layer):
        viewer.layers.selection.active = lt_layer
        assert _select_active_lt_layer(viewer) is lt_layer

    def test_plain_points_layer(self, viewer):
        viewer.add_points(np.zeros((3, 4)))
        assert _select_active_lt_layer(viewer) is None

    def test_linked_layer_returns_its_points_layer(self, viewer, lt_layer):
        linked = viewer.add_points(np.zeros((1, 4)), metadata={})
        linked.metadata["link"] = lt_layer
        viewer.layers.selection.active = linked
        assert _select_active_lt_layer(viewer) is lt_layer

    def test_link_to_non_points_layer_is_ignored(self, viewer):
        image = viewer.add_image(np.zeros((4, 4)))
        other = viewer.add_image(np.zeros((4, 4)))
        other.metadata["link"] = image
        viewer.layers.selection.active = other
        assert _select_active_lt_layer(viewer) is None

    def test_several_selected_layers(self, viewer, lt_layer):
        other = viewer.add_points(np.zeros((1, 4)))
        viewer.layers.selection.update({lt_layer, other})
        assert _select_active_lt_layer(viewer) is None


class TestMessageBoxes:
    def test_error_image_selection(self, modal_calls):
        error_image_selection()
        (box,) = modal_calls
        assert isinstance(box, QMessageBox)
        assert box.text() == "Image selection error"
        assert box.icon() == QMessageBox.Critical

    def test_custom_error(self, modal_calls):
        custom_error("Title", "unused", informative="Details")
        (box,) = modal_calls
        assert box.text() == "Title"
        assert box.informativeText() == "Details"

    def test_custom_error_without_informative_text(self, modal_calls):
        custom_error("Title", "unused")
        assert modal_calls[0].informativeText() == ""

    def test_error_cell_selection(self, modal_calls):
        error_cell_selection()
        assert modal_calls[0].text() == "Cell selection error"


def test_clear_layout(qtbot):
    widget = QWidget()
    qtbot.addWidget(widget)
    layout = QVBoxLayout(widget)
    for i in range(3):
        layout.addWidget(QLabel(str(i)))
    clear_layout(widget)
    assert layout.count() == 0


def test_clear_layout_without_layout(qtbot):
    widget = QWidget()
    qtbot.addWidget(widget)
    clear_layout(widget)  # must not raise


class TestCreateLinksAndChains:
    def test_single_root(self, lt):
        result = create_links_and_chains(lt, 1)
        # Chains are represented by their first and last node.
        assert result["links"] == {1: 3, 3: (4, 5), 4: 8, 5: 9}
        assert result["times"] == {1: 2, 4: 2, 5: 2}

    def test_list_of_roots(self, lt):
        result = create_links_and_chains(lt, [1, 10])
        assert result["links"][10] == 15
        assert result["links"][1] == 3

    def test_empty_roots_uses_every_root(self, lt):
        result = create_links_and_chains(lt, [])
        assert {1, 10, 20} <= set(result["links"])


class TestPlotLineagesForTreeManip:
    def test_single_lineage(self, lt):
        graphs = lt._create_dict_of_plots([1])
        pos = {i: hierarchical_pos(g, g["root"]) for i, g in graphs.items()}
        figure, axes, ax2root, root2ax = plot_lineages_for_tree_manip(
            lt, graphs, pos, nrows=1
        )
        assert ax2root == {axes: 1}
        assert root2ax == {1: axes}
        assert [t.get_text() for t in axes.texts] == ["A"]
        assert not axes.get_xaxis().get_visible()

    def test_nrows_must_be_positive(self, lt):
        with pytest.raises(Warning, match="at least 1"):
            plot_lineages_for_tree_manip(lt, {}, {}, nrows=0)

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: plt.subplots returns an ndarray of axes, not a list, "
        "so the whole array is wrapped as a single axes",
    )
    def test_several_lineages(self, lt):
        graphs = lt._create_dict_of_plots([1, 10])
        pos = {i: hierarchical_pos(g, g["root"]) for i, g in graphs.items()}
        _, _, ax2root, _ = plot_lineages_for_tree_manip(
            lt, graphs, pos, nrows=1
        )
        assert sorted(ax2root.values()) == [1, 10]


class TestFindPairWithTheLongestDistance:
    def test_synthetic_tree(self, lt):
        # Only t=0 is sampled (range(0, 5, 10)): cells 1 and 10 are 50
        # apart.
        assert find_pair_with_the_longest_distance(lt) == pytest.approx(50)

    def test_uses_convex_hull_for_many_cells(self, rng):
        n = 30
        positions = rng.normal(size=(n, 3))
        lT = LineageTree(
            successor={i: [i + n] for i in range(n)}
            | {i + n: [] for i in range(n)},
            time=dict.fromkeys(range(n), 0) | {i + n: 1 for i in range(n)},
            starting_time=None,
            pos={i: positions[i] for i in range(n)}
            | {i + n: positions[i] for i in range(n)},
        )
        expected = max(
            np.linalg.norm(a - b) for a in positions for b in positions
        )
        assert find_pair_with_the_longest_distance(lT) == pytest.approx(
            expected
        )

    def test_zero_spread_warns_and_returns_one(self):
        lT = LineageTree(
            successor={0: [1], 1: [], 2: [3], 3: []},
            time={0: 0, 1: 1, 2: 0, 3: 1},
            starting_time=None,
            pos=dict.fromkeys(range(4), (0, 0, 0)),
        )
        with pytest.warns(UserWarning, match="spread"):
            assert find_pair_with_the_longest_distance(lT) == 1

    @pytest.mark.xfail(
        strict=True,
        raises=KeyError,
        reason="BUG: timepoints without cells (time gaps) raise a KeyError",
    )
    def test_time_gaps(self):
        lT = LineageTree(
            successor={0: [1], 1: [], 2: [3], 3: []},
            time={0: 1, 1: 30, 2: 1, 3: 30},
            starting_time=None,
            pos={0: (0, 0, 0), 1: (0, 0, 0), 2: (3, 0, 0), 3: (4, 0, 0)},
        )
        assert find_pair_with_the_longest_distance(lT) == pytest.approx(3)


class TestRotate3d:
    def test_identity_when_already_aligned(self):
        target = np.array([[0, 1, 0], [1, 0, 0], [0, 0, 1]])
        np.testing.assert_allclose(
            rotate_3d(target, target), np.eye(3), atol=1e-12
        )

    def test_returns_a_proper_rotation(self, rng):
        for _ in range(5):
            rotation = rotate_3d(rng.normal(size=(3, 3)))
            np.testing.assert_allclose(
                rotation @ rotation.T, np.eye(3), atol=1e-12
            )
            assert np.linalg.det(rotation) == pytest.approx(1)

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: the covariance is built in point space "
        "(A @ T.T) instead of coordinate space (A.T @ T), so a known "
        "rotation is not recovered (Kabsch)",
    )
    def test_recovers_a_known_rotation(self):
        target = np.array([[0, 1, 0], [1, 0, 0], [0, 0, 1]], dtype=float)
        rotation = Rotation.from_euler("z", 30, degrees=True).as_matrix()
        axes = target @ rotation.T
        centered = axes - axes.mean(axis=0)
        aligned = centered @ rotate_3d(axes, target).T
        np.testing.assert_allclose(
            aligned, target - target.mean(axis=0), atol=1e-9
        )


@pytest.mark.xfail(
    strict=True,
    reason="BUG: LineageTree >= 3 exposes read-only nodes/successor/"
    "time mappings, so the lineage cannot be copied this way",
)
def test_extract_lineage():
    lT = make_lineage_tree()
    new_lT = extract_lineage(lT, 1)
    assert set(new_lT.nodes) == LINEAGE_A


@pytest.mark.xfail(
    strict=True,
    reason="BUG: LineageTree >= 3 exposes read-only nodes/successor/"
    "time mappings, so they cannot be updated in place",
)
def test_inject_lineage():
    main = make_lineage_tree()
    other = LineageTree(
        successor={100: [101], 101: []},
        time={100: 0, 101: 1},
        starting_time=None,
        pos={100: (0, 0, 0), 101: (0, 0, 1)},
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        inject_lineage(main, other)
    assert {100, 101} <= set(main.nodes)
