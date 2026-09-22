from unittest.mock import MagicMock

import numpy as np
import pytest

from napari_relax._interaction_bridge import (
    InteractionBridge,
    PointsAdapter,
    SurfaceAdapter,
    TracksAdapter,
)

from .conftest import LINEAGE_A, LINEAGE_B, LINEAGE_C, points_of


def add_surface(viewer, points_layer, link=False, rgb=False):
    """Add a Surface layer with one triangle for nodes 1 and 10."""
    vertices = np.array(
        [[0, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]] * 2, dtype=float
    )
    vertices[3:, 3] += 50
    colors = np.full((6, 3 if rgb else 4), 0.5)
    metadata = {
        "node_to_vertex_range": {1: (0, 3), 10: (3, 6)},
        "lineage_tree_id": points_layer.metadata["lineage_tree_id"],
    }
    if link:
        metadata["link"] = points_layer
    return viewer.add_surface(
        (vertices, np.array([[0, 1, 2], [3, 4, 5]])),
        vertex_colors=colors,
        metadata=metadata,
    )


def add_tracks(viewer, points_layer):
    tracks = points_layer.metadata["graph_to_create_tracks"]
    return viewer.add_tracks(
        points_layer.metadata["data"],
        graph=tracks["graph"],
        metadata={"link": points_layer},
    )


@pytest.fixture
def points_adapter(lt_layer):
    return PointsAdapter(
        lt_layer,
        lt_layer.metadata["lT2napari"],
        lt_layer.metadata["napari2lT"],
    )


class TestPointsAdapter:
    def test_select_nodes(self, points_adapter, lt_layer):
        points_adapter.select_nodes([1, 2, 999])
        assert lt_layer.selected_data == set(points_of(lt_layer, [1, 2]))
        assert lt_layer.shown.all()

    def test_hide_nodes(self, points_adapter, lt_layer):
        points_adapter.hide_nodes(list(LINEAGE_A))
        hidden = points_of(lt_layer, LINEAGE_A)
        assert not lt_layer.shown[hidden].any()
        assert lt_layer.shown[points_of(lt_layer, LINEAGE_B)].all()

    def test_hide_nodes_accumulates(self, points_adapter, lt_layer):
        points_adapter.hide_nodes(list(LINEAGE_A))
        points_adapter.hide_nodes(list(LINEAGE_B))
        assert lt_layer.shown.sum() == len(LINEAGE_C)

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: PointsAdapter.show_only_nodes never hides the other "
        "points (the reset of `shown` is commented out)",
    )
    def test_show_only_nodes(self, points_adapter, lt_layer):
        points_adapter.show_only_nodes(list(LINEAGE_A))
        assert lt_layer.shown.sum() == len(LINEAGE_A)

    def test_show_only_nodes_shows_hidden_nodes(
        self, points_adapter, lt_layer
    ):
        points_adapter.hide_nodes(list(LINEAGE_A))
        points_adapter.show_only_nodes(list(LINEAGE_A))
        assert lt_layer.shown[points_of(lt_layer, LINEAGE_A)].all()

    def test_reset_visibility_clears_selection(self, points_adapter, lt_layer):
        points_adapter.hide_nodes(list(LINEAGE_A))
        points_adapter.select_nodes([10])
        points_adapter.reset_visibility()
        assert lt_layer.shown.all()
        assert lt_layer.selected_data == set()

    def test_restore_visibility_keeps_selection(
        self, points_adapter, lt_layer
    ):
        points_adapter.hide_nodes(list(LINEAGE_A))
        points_adapter.select_nodes([10])
        points_adapter.restore_visibility()
        assert lt_layer.shown.all()
        assert lt_layer.selected_data == set(points_of(lt_layer, [10]))

    def test_get_node_at_position(self, points_adapter, lt_layer):
        index = lt_layer.metadata["lT2napari"][4]
        position = lt_layer.data[index] + [0, 0.5, 0.5, 0.5]
        assert points_adapter.get_node_at_position(position, 3) == 4

    def test_get_node_at_position_too_far(self, points_adapter, lt_layer):
        position = np.array([3, 1000, 1000, 1000])
        assert points_adapter.get_node_at_position(position, 3) is None

    def test_get_node_at_position_empty_timepoint(self, points_adapter):
        assert points_adapter.get_node_at_position(np.zeros(4), 42) is None

    def test_get_node_at_3d_position(self, points_adapter, lt_layer):
        # A ray along z through node 13 (t=3).
        index = lt_layer.metadata["lT2napari"][13]
        t, z, y, x = lt_layer.data[index]
        node = points_adapter.get_node_at_3d_position(
            np.array([t, z - 20, y, x]),
            np.array([0, 1, 0, 0]),
            np.array([1, 2, 3]),
        )
        assert node == 13

    def test_get_node_at_3d_position_misses(self, points_adapter, lt_layer):
        index = lt_layer.metadata["lT2napari"][13]
        t, z, y, x = lt_layer.data[index]
        node = points_adapter.get_node_at_3d_position(
            np.array([t, z, y + 30, x + 30]),
            np.array([0, 1, 0, 0]),
            np.array([1, 2, 3]),
        )
        assert node is None


class TestSurfaceAdapter:
    def test_requires_a_link(self, viewer, lt_layer):
        surface = add_surface(viewer, lt_layer)
        surface.metadata.pop("link", None)
        with pytest.raises(ValueError, match="link"):
            SurfaceAdapter(surface, surface.metadata["node_to_vertex_range"])

    @pytest.fixture
    def surface_adapter(self, viewer, lt_layer):
        surface = add_surface(viewer, lt_layer, link=True)
        return SurfaceAdapter(
            surface, surface.metadata["node_to_vertex_range"]
        )

    def test_mappings_come_from_the_points_layer(
        self, surface_adapter, lt_layer
    ):
        assert surface_adapter.node_to_napari is lt_layer.metadata["lT2napari"]
        assert surface_adapter.napari_to_node is lt_layer.metadata["napari2lT"]

    def test_show_only_nodes(self, surface_adapter):
        surface_adapter.show_only_nodes([1])
        layer = surface_adapter.layer
        assert layer.vertex_colors[:3, 3].tolist() == [1, 1, 1]
        assert layer.vertex_colors[3:, 3].tolist() == [0, 0, 0]
        assert layer.blending == "translucent_no_depth"

    def test_hide_nodes(self, surface_adapter):
        surface_adapter.hide_nodes([10])
        alpha = surface_adapter.layer.vertex_colors[:, 3]
        assert alpha.tolist() == [0.5, 0.5, 0.5, 0, 0, 0]

    @pytest.mark.parametrize(
        "method", ["reset_visibility", "restore_visibility"]
    )
    def test_reset(self, surface_adapter, method):
        layer = surface_adapter.layer
        original_blending = layer.blending
        surface_adapter.show_only_nodes([1])
        getattr(surface_adapter, method)()
        np.testing.assert_allclose(layer.vertex_colors, 0.5)
        assert layer.blending == original_blending

    def test_rgb_colors_get_an_alpha_channel(self, viewer, lt_layer):
        surface = add_surface(viewer, lt_layer, link=True, rgb=True)
        adapter = SurfaceAdapter(
            surface, surface.metadata["node_to_vertex_range"]
        )
        adapter.hide_nodes([1])
        assert surface.vertex_colors.shape == (6, 4)
        assert surface.vertex_colors[:, 3].tolist() == [0, 0, 0, 1, 1, 1]


class TestTracksAdapter:
    def test_requires_a_link(self, viewer, lt_layer):
        tracks = add_tracks(viewer, lt_layer)
        tracks.metadata.pop("link")
        with pytest.raises(ValueError, match="link"):
            TracksAdapter(tracks)

    def test_mappings_come_from_the_points_layer(self, viewer, lt_layer):
        adapter = TracksAdapter(add_tracks(viewer, lt_layer))
        assert adapter.node_to_napari is lt_layer.metadata["lT2napari"]

    @pytest.mark.xfail(
        strict=True,
        raises=AttributeError,
        reason="BUG: napari Tracks layers have no `_track_connex` "
        "attribute (it belongs to the internal track manager)",
    )
    def test_hide_nodes(self, viewer, lt_layer):
        adapter = TracksAdapter(add_tracks(viewer, lt_layer))
        adapter.hide_nodes(list(LINEAGE_A))

    @pytest.mark.xfail(
        strict=True,
        raises=AttributeError,
        reason="BUG: napari Tracks layers have no `_track_connex` "
        "attribute (it belongs to the internal track manager)",
    )
    def test_show_only_nodes(self, viewer, lt_layer):
        adapter = TracksAdapter(add_tracks(viewer, lt_layer))
        adapter.show_only_nodes(list(LINEAGE_A))

    def test_reset_visibility_is_harmless(self, viewer, lt_layer):
        tracks = add_tracks(viewer, lt_layer)
        adapter = TracksAdapter(tracks)
        tracks.opacity = 0.2
        adapter.reset_visibility()
        assert tracks.opacity == 1
        adapter.restore_visibility()


class TestInteractionBridge:
    def test_without_viewer(self):
        bridge = InteractionBridge()
        assert bridge.get_registered_layers() == []
        assert bridge.get_state("visibility_state") == "all_visible"

    def test_discovers_the_points_layer(self, viewer, lt_layer):
        bridge = InteractionBridge(viewer, lt_layer)
        assert bridge.get_registered_layers() == ["points"]
        assert bridge.adapters["points"].layer is lt_layer

    def test_discover_without_primary_layer(self, viewer, lt_layer):
        viewer.add_points(np.zeros((2, 4)))
        bridge = InteractionBridge()
        assert bridge.discover_layers(viewer)
        assert bridge.adapters["points"].layer is lt_layer

    def test_discover_without_lineage_layer(self, viewer):
        viewer.add_points(np.zeros((2, 4)))
        assert not InteractionBridge().discover_layers(viewer)

    def test_discover_without_mappings(self, viewer):
        layer = viewer.add_points(np.zeros((2, 4)), metadata={})
        layer.metadata["LineageTree"] = object()
        assert not InteractionBridge().discover_layers(viewer, layer)

    def test_companion_layers_are_linked_and_discovered(
        self, viewer, lt_layer
    ):
        bridge = InteractionBridge(viewer, lt_layer)
        surface = add_surface(viewer, lt_layer)
        assert surface.metadata["link"] is lt_layer
        tracks = add_tracks(viewer, lt_layer)
        assert set(bridge.get_registered_layers()) == {
            "points",
            "surface",
            "tracks",
        }
        assert bridge.adapters["surface"].layer is surface
        assert bridge.adapters["tracks"].layer is tracks

    def test_other_datasets_are_not_linked(self, viewer, lt_layer, lt):
        from .conftest import add_lt_layer

        other = add_lt_layer(viewer, lt, "other")
        bridge = InteractionBridge(viewer, lt_layer)
        surface = add_surface(viewer, other)
        assert surface.metadata.get("link") is not lt_layer
        assert "surface" not in bridge.get_registered_layers()

    def test_existing_links_are_kept(self, viewer, lt_layer):
        surface = add_surface(viewer, lt_layer)
        surface.metadata["link"] = "something else"
        InteractionBridge(viewer, lt_layer)
        assert surface.metadata["link"] == "something else"

    def test_removed_layers_are_forgotten(self, viewer, lt_layer):
        bridge = InteractionBridge(viewer, lt_layer)
        surface = add_surface(viewer, lt_layer)
        assert "surface" in bridge.adapters
        viewer.layers.remove(surface)
        assert "surface" not in bridge.adapters

    def test_create_and_get_bridge(self, viewer, lt_layer):
        bridge = InteractionBridge.create_bridge_for_points_layer(
            viewer, lt_layer
        )
        assert lt_layer.metadata["interaction_bridge"] is bridge
        assert InteractionBridge.get_bridge_for_layer(lt_layer) is bridge
        surface = add_surface(viewer, lt_layer)
        assert InteractionBridge.get_bridge_for_layer(surface) is bridge
        assert bridge.get_state("selected_subtree") == set()

    def test_get_bridge_without_bridge(self, viewer, lt_layer):
        assert InteractionBridge.get_bridge_for_layer(lt_layer) is None
        assert InteractionBridge.get_bridge_for_layer(object()) is None

    def test_state(self):
        bridge = InteractionBridge()
        bridge.update_state(graph_slider_value=3, custom="value")
        state = bridge.get_state()
        assert state["graph_slider_value"] == 3
        assert state["custom"] == "value"
        state["custom"] = "changed"
        assert bridge.get_state("custom") == "value"
        assert bridge.get_state("missing") is None

    def test_actions_are_forwarded_to_every_adapter(self):
        bridge = InteractionBridge()
        points, surface = MagicMock(), MagicMock(spec=SurfaceAdapter)
        bridge.adapters = {"points": points, "surface": surface}
        bridge.show_only_lineages([1])
        bridge.show_only_nodes([2])
        bridge.hide_lineages([3])
        bridge.reset_visibility()
        bridge.restore_visibility()
        bridge.highlight_lineages([4])
        for adapter in (points, surface):
            assert adapter.show_only_nodes.call_args_list[0].args == ([1],)
            assert adapter.show_only_nodes.call_args_list[1].args == ([2],)
            adapter.hide_nodes.assert_called_once_with([3])
            adapter.reset_visibility.assert_called_once()
            adapter.restore_visibility.assert_called_once()
        # Only adapters supporting selection highlight.
        points.select_nodes.assert_called_once_with([4])

    @pytest.mark.parametrize(
        ("state", "method", "argument"),
        [
            ({"visibility_state": "all_visible"}, "restore_visibility", None),
            (
                {"visibility_state": "lineage_only", "visible_lineage": {1}},
                "show_only_lineages",
                [1],
            ),
            (
                {"visibility_state": "lineage_hidden", "hidden_lineage": {2}},
                "hide_lineages",
                [2],
            ),
            ({"visibility_state": "all_hidden"}, "show_only_nodes", []),
        ],
    )
    def test_restore_state(self, monkeypatch, state, method, argument):
        bridge = InteractionBridge()
        bridge.update_state(**state)
        mocked = MagicMock()
        monkeypatch.setattr(bridge, method, mocked)
        bridge.restore_state(widget=None)
        if argument is None:
            mocked.assert_called_once_with()
        else:
            mocked.assert_called_once_with(argument)

    def test_find_node_prefers_points(self):
        bridge = InteractionBridge()
        points = MagicMock()
        points.get_node_at_3d_position.return_value = 7
        surface = MagicMock(spec=SurfaceAdapter)
        surface.get_node_at_position.return_value = 9
        bridge.adapters = {"surface": surface, "points": points}
        assert bridge.find_node_at_position(np.zeros(4), None, None) == (
            points.layer,
            7,
        )

    def test_find_node_falls_back_to_other_layers(self):
        bridge = InteractionBridge()
        points = MagicMock()
        points.get_node_at_3d_position.return_value = None
        surface = MagicMock(spec=SurfaceAdapter)
        surface.layer = "surface layer"
        surface.get_node_at_position.return_value = 9
        bridge.adapters = {"points": points, "surface": surface}
        assert bridge.find_node_at_position(np.zeros(4), None, None) == (
            "surface layer",
            9,
        )

    def test_find_node_nothing_found(self):
        assert (
            InteractionBridge().find_node_at_position(np.zeros(4), None, None)
            is None
        )
