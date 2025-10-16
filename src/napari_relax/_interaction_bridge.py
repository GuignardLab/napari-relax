"""
Simple interaction bridge for coordinating multi-layer lineage interactions.

This module provides a lightweight system for coordinating interactions between
Points, Surface, Labels, and Tracks layers in napari-relax.
"""

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
from napari.layers import Points, Surface, Tracks
from scipy.spatial import KDTree


class LayerAdapter(ABC):
    """Abstract adapter for layer-specific interactions."""

    def __init__(
        self,
        layer,
        node_to_napari: dict[int, Any],
        napari_to_node: dict[Any, int],
    ):
        """
        Initialize adapter with mappings between LineageTree nodes and napari indices.

        Parameters
        ----------
        layer : napari.layers.Layer
            The napari layer to adapt
        node_to_napari : dict
            Mapping from LineageTree node_id to napari indices
        napari_to_node : dict
            Mapping from napari indices to LineageTree node_id
        """
        self.layer = layer
        self.node_to_napari = node_to_napari
        self.napari_to_node = napari_to_node
        self._store_original_state()

    def _store_original_state(self):
        """Store original layer state for reset functionality."""
        self.original_state = {}
        # Store common properties that might be modified
        for prop in [
            "shown",
            "face_color",
            "vertex_colors",
            "opacity",
            "blending",
            "_track_connex",
        ]:
            if hasattr(self.layer, prop):
                value = getattr(self.layer, prop)
                if hasattr(value, "copy"):
                    self.original_state[prop] = value.copy()
                else:
                    self.original_state[prop] = value

    @abstractmethod
    def show_only_nodes(self, node_ids: list[int]) -> None:
        """Show only the specified nodes, hide all others."""

    @abstractmethod
    def reset_visibility(self) -> None:
        """Reset all nodes to be visible."""

    @abstractmethod
    def restore_visibility(self) -> None:
        """Restore all nodes to be visible without affecting selection."""

    def get_node_at_position(
        self, position: np.ndarray, time: int
    ) -> int | None:
        """
        Get the node ID at the given position and time.
        Default implementation returns None - override for clickable layers.
        """
        return None


class PointsAdapter(LayerAdapter):
    """Adapter for Points layers."""

    def show_only_nodes(self, node_ids: list[int]) -> None:
        """Hide unselected lineages by setting their visibility."""
        # Get napari indices for visible nodes
        visible_indices = set()
        for node_id in node_ids:
            if node_id in self.node_to_napari:
                visible_indices.add(self.node_to_napari[node_id])

        # set visibility: visible nodes = True, others = False
        shown = np.zeros(len(self.layer.data), dtype=bool)
        for i in visible_indices:
            if i < len(shown):
                shown[i] = True

        self.layer.shown = shown
        # Don't modify selection - only control visibility
        self.layer.refresh()

    def reset_visibility(self) -> None:
        """Restore original visibility and clear selection."""
        if "shown" in self.original_state:
            self.layer.shown = self.original_state["shown"].copy()
        else:
            # Show all points
            self.layer.shown = np.ones(len(self.layer.data), dtype=bool)
        self.layer.selected_data = set()
        self.layer.refresh()

    def restore_visibility(self) -> None:
        """Restore original visibility without affecting selection."""
        if "shown" in self.original_state:
            self.layer.shown = self.original_state["shown"].copy()
        else:
            # Show all points
            self.layer.shown = np.ones(len(self.layer.data), dtype=bool)
        self.layer.refresh()

    def select_nodes(self, node_ids: list[int]) -> None:
        """Select nodes without hiding others."""
        # Get napari indices for the nodes to select
        selected_indices = set()
        for node_id in node_ids:
            if node_id in self.node_to_napari:
                selected_indices.add(self.node_to_napari[node_id])

        # set selection without modifying visibility
        self.layer.selected_data = selected_indices

    def hide_nodes(self, node_ids: list[int]) -> None:
        """Hide specific nodes while preserving visibility of others."""
        # Get napari indices for nodes to hide
        indices_to_hide = set()
        for node_id in node_ids:
            if node_id in self.node_to_napari:
                indices_to_hide.add(self.node_to_napari[node_id])

        # Get current visibility state or assume all visible
        current_shown = self.layer.shown.copy()

        # Hide the specified indices
        for idx in indices_to_hide:
            if idx < len(current_shown):
                current_shown[idx] = False

        self.layer.shown = current_shown
        self.layer.refresh()

    def get_node_at_position(
        self, position: np.ndarray, time: int
    ) -> int | None:
        """Find the node at the clicked position."""
        from scipy.spatial import KDTree

        # Get points at the specified time
        time_mask = np.isclose(self.layer.data[:, 0], time)
        if not np.any(time_mask):
            return None

        points_at_time = self.layer.data[time_mask]
        indices_at_time = np.where(time_mask)[0]

        if len(points_at_time) == 0:
            return None

        # Find closest point using KDTree
        spatial_coords = points_at_time[:, 1:]  # Skip time dimension
        tree = KDTree(spatial_coords)

        # Query for the closest point
        distances, closest_idx = tree.query(
            position[1:], k=1
        )  # Skip time dimension

        if distances < 50:  # Distance threshold for clicking
            napari_idx = indices_at_time[closest_idx]
            return self.napari_to_node.get(napari_idx)

        return None

    def get_node_at_3d_position(
        self,
        position: np.ndarray,
        view_direction: np.ndarray,
        dims_displayed: np.ndarray,
    ) -> int | None:
        """Find the node at the clicked position using 3D ray intersection."""

        time = position[0]

        # Get ray intersections from the layer
        near_point, far_point = self.layer.get_ray_intersections(
            np.array(position), view_direction, dims_displayed
        )

        if near_point is None or far_point is None:
            return None

        # Sample points along the ray
        ray_points = np.linspace(near_point, far_point, 1000, endpoint=True)

        # Get points at the current time
        time_mask = np.isclose(self.layer.data[:, 0], time)
        if not np.any(time_mask):
            return None

        points_at_time = self.layer.data[time_mask]
        indices_at_time = np.where(time_mask)[0]

        if len(points_at_time) == 0:
            return None

        # Find closest point along the ray
        spatial_coords = points_at_time[:, 1:]  # Skip time dimension
        tree = KDTree(spatial_coords)

        # Query for closest points along the ray (skip time dimension)
        ray_spatial = (
            ray_points[:, 1:]
            if ray_points.shape[1] > spatial_coords.shape[1]
            else ray_points
        )

        # Ensure dimensions match
        if ray_spatial.shape[1] != spatial_coords.shape[1]:
            # Adjust dimensions to match
            min_dims = min(ray_spatial.shape[1], spatial_coords.shape[1])
            ray_spatial = ray_spatial[:, :min_dims]
            if spatial_coords.shape[1] > min_dims:
                spatial_coords = spatial_coords[:, :min_dims]
                tree = KDTree(spatial_coords)

        distances, idx = tree.query(ray_spatial)

        # Find the closest intersection
        min_dist_idx = np.argmin(distances)
        if distances[min_dist_idx] < 10:  # Tighter threshold for 3D clicking
            napari_idx = indices_at_time[idx[min_dist_idx]]
            return self.napari_to_node.get(napari_idx)

        return None


class SurfaceAdapter(LayerAdapter):
    """Adapter for Surface layers."""

    def __init__(self, layer, node_to_vertex_range: dict[int, tuple]):
        """
        Initialize surface adapter with vertex range mappings.
        Gets node mappings from the linked Points layer.

        Parameters
        ----------
        layer : napari.layers.Surface
            The Surface layer to adapt
        node_to_vertex_range : dict
            Mapping from node_id to (start_vertex_idx, end_vertex_idx) in surface data
        """
        # Get mappings from the linked Points layer
        if "link" in layer.metadata and hasattr(
            layer.metadata["link"], "metadata"
        ):
            points_metadata = layer.metadata["link"].metadata
            node_to_napari = points_metadata.get("lT2napari", {})
            napari_to_node = points_metadata.get("napari2lT", {})
        else:
            raise ValueError(
                "Surface layer must have a 'link' to a Points layer with node mappings"
            )

        super().__init__(layer, node_to_napari, napari_to_node)
        self.node_to_vertex_range = node_to_vertex_range

    def show_only_nodes(self, node_ids: list[int]) -> None:
        """Hide unselected lineages by setting their alpha to 0."""
        # Store current blending if not already stored
        if "blending" not in self.original_state:
            self.original_state["blending"] = self.layer.blending

        # Switch to translucent_no_depth to prevent depth sorting issues
        self.layer.blending = "translucent_no_depth"

        # Ensure we have vertex colors and alpha channel
        vertex_colors = self.layer.vertex_colors
        if vertex_colors is None:
            # Create default colors (white) for all vertices
            num_vertices = len(self.layer.data[0])  # data[0] is vertices
            vertex_colors = np.ones((num_vertices, 4))  # RGBA
        elif vertex_colors.shape[1] == 3:
            # Add alpha channel
            alpha = np.ones((vertex_colors.shape[0], 1))
            vertex_colors = np.hstack([vertex_colors, alpha])

        vertex_colors = vertex_colors.copy()

        # Get vertex ranges for visible nodes
        visible_vertex_indices = set()
        for node_id in node_ids:
            if node_id in self.node_to_vertex_range:
                start_idx, end_idx = self.node_to_vertex_range[node_id]
                visible_vertex_indices.update(range(start_idx, end_idx))

        # set alpha: visible vertices = 1.0, others = 0.0
        for i in range(vertex_colors.shape[0]):
            vertex_colors[i, 3] = 1.0 if i in visible_vertex_indices else 0.0

        self.layer.vertex_colors = vertex_colors

    def hide_nodes(self, node_ids: list[int]) -> None:
        """Hide specific nodes by setting their alpha to 0, preserving other visibility."""
        # Get current vertex colors or create default
        vertex_colors = self.layer.vertex_colors
        if vertex_colors is None:
            num_vertices = len(self.layer.data[0])
            vertex_colors = np.ones((num_vertices, 4))
        elif vertex_colors.shape[1] == 3:
            alpha = np.ones((vertex_colors.shape[0], 1))
            vertex_colors = np.hstack([vertex_colors, alpha])

        vertex_colors = vertex_colors.copy()

        # Get vertex ranges for nodes to hide
        vertices_to_hide = set()
        for node_id in node_ids:
            if node_id in self.node_to_vertex_range:
                start_idx, end_idx = self.node_to_vertex_range[node_id]
                vertices_to_hide.update(range(start_idx, end_idx))

        # Hide the specified vertices by setting alpha to 0
        for idx in vertices_to_hide:
            if idx < vertex_colors.shape[0]:
                vertex_colors[idx, 3] = 0.0

        self.layer.vertex_colors = vertex_colors

    def reset_visibility(self) -> None:
        """Restore original vertex colors and blending."""
        if "vertex_colors" in self.original_state:
            if self.original_state["vertex_colors"] is None:
                self.layer.vertex_colors = None
            else:
                self.layer.vertex_colors = self.original_state[
                    "vertex_colors"
                ].copy()
        elif (
            self.layer.vertex_colors is not None
            and self.layer.vertex_colors.shape[1] >= 4
        ):
            # set all alpha to 1.0
            vertex_colors = self.layer.vertex_colors.copy()
            vertex_colors[:, 3] = 1.0
            self.layer.vertex_colors = vertex_colors

        # Restore original blending mode
        if "blending" in self.original_state:
            self.layer.blending = self.original_state["blending"]

    def restore_visibility(self) -> None:
        """Restore original vertex colors and blending without affecting selection."""
        if "vertex_colors" in self.original_state:
            if self.original_state["vertex_colors"] is None:
                self.layer.vertex_colors = None
            else:
                self.layer.vertex_colors = self.original_state[
                    "vertex_colors"
                ].copy()
        elif (
            self.layer.vertex_colors is not None
            and self.layer.vertex_colors.shape[1] >= 4
        ):
            # set all alpha to 1.0
            vertex_colors = self.layer.vertex_colors.copy()
            vertex_colors[:, 3] = 1.0
            self.layer.vertex_colors = vertex_colors

        # Restore original blending mode
        if "blending" in self.original_state:
            self.layer.blending = self.original_state["blending"]


class TracksAdapter(LayerAdapter):
    """Adapter for Tracks layers."""

    def __init__(self, layer):
        """
        Initialize tracks adapter.
        Gets node mappings from the linked Points layer.

        Parameters
        ----------
        layer : napari.layers.Tracks
            The Tracks layer to adapt
        """
        # Get mappings from the linked Points layer
        if "link" in layer.metadata and hasattr(
            layer.metadata["link"], "metadata"
        ):
            points_metadata = layer.metadata["link"].metadata
            node_to_napari = points_metadata.get("lT2napari", {})
            napari_to_node = points_metadata.get("napari2lT", {})
        else:
            raise ValueError(
                "Tracks layer must have a 'link' to a Points layer with node mappings"
            )

        super().__init__(layer, node_to_napari, napari_to_node)

    def show_only_nodes(self, node_ids: list[int]) -> None:
        """Show only specified tracks."""
        # For tracks, we manipulate the track_connex property to control visibility
        # Get track IDs for visible nodes
        visible_track_ids = set()
        for node_id in node_ids:
            if node_id in self.node_to_napari:
                visible_track_ids.add(self.node_to_napari[node_id])

        # Create a mask to hide all tracks first
        track_connex = np.zeros_like(self.layer._track_connex, dtype=bool)

        # Show only the specified tracks by setting their segments to True
        for i, track_id in enumerate(self.layer.data[:, 0]):
            if track_id in visible_track_ids:
                track_connex[i] = self.layer._track_connex[
                    i
                ]  # Preserve original connectivity

        self.layer._track_connex = track_connex
        self.layer.refresh()

    def hide_nodes(self, node_ids: list[int]) -> None:
        """Hide specific tracks while preserving visibility of others."""
        # Get current track_connex state
        current_track_connex = self.layer._track_connex.copy()

        # Get track IDs for nodes to hide
        track_ids_to_hide = set()
        for node_id in node_ids:
            if node_id in self.node_to_napari:
                track_ids_to_hide.add(self.node_to_napari[node_id])

        # Hide the specified tracks by setting their segments to False
        for i, track_id in enumerate(self.layer.data[:, 0]):
            if track_id in track_ids_to_hide:
                current_track_connex[i] = False

        self.layer._track_connex = current_track_connex
        self.layer.refresh()

    def reset_visibility(self) -> None:
        """Restore original track visibility."""
        if "_track_connex" in self.original_state:
            self.layer._track_connex = self.original_state[
                "_track_connex"
            ].copy()
            self.layer.refresh()
        else:
            # Restore all track connections - this requires rebuilding tracks
            self.layer.build_tracks()

        if "opacity" in self.original_state:
            self.layer.opacity = self.original_state["opacity"]

    def restore_visibility(self) -> None:
        """Restore original track visibility without affecting selection."""
        if "_track_connex" in self.original_state:
            self.layer._track_connex = self.original_state[
                "_track_connex"
            ].copy()
            self.layer.refresh()
        else:
            # Restore all track connections - this requires rebuilding tracks
            self.layer.build_tracks()


class InteractionBridge:
    """
    Coordinator for multi-layer lineage interactions with state management.

    This class discovers related layers through shared metadata, coordinates
    interactions between them, and maintains state for a specific lineage tree.
    """

    def __init__(self, viewer=None, primary_points=None):
        self.adapters: dict[str, LayerAdapter] = {}
        self.metadata_key = "lineage_bridge_metadata"
        self.viewer = viewer
        self.primary_points = primary_points

        # State storage for this specific lineage tree
        self.state = {
            "graph_slider_value": 0,
            "selected_lineage": None,
            "selected_subtree": set(),
            "canvas_state": None,
            "visibility_state": "all_visible",  # 'all_visible', 'lineage_hidden', 'lineage_only'
        }

        # If viewer is provided, set up automatic rediscovery
        if self.viewer:
            # Establish links for companion layers first
            self._establish_layer_links()
            # Then discover layers
            self.discover_layers(self.viewer, primary_points)
            # Connect to layer events to automatically rediscover when layers change
            self.viewer.layers.events.inserted.connect(self._on_layers_changed)
            self.viewer.layers.events.removed.connect(self._on_layers_changed)

    def _on_layers_changed(self, event):
        """Handle layer list changes by rediscovering layers."""
        if self.viewer:
            # First establish links for any new companion layers
            self._establish_layer_links()
            # Then rediscover layers (which will now find the newly linked layers)
            self.discover_layers(self.viewer, self.primary_points)

    def _establish_layer_links(self):
        """Establish links from companion layers to the primary Points layer."""
        if not self.viewer or not self.primary_points:
            return

        # Get the unique lineage tree ID from the primary Points layer
        if (
            not hasattr(self.primary_points, "metadata")
            or "lineage_tree_id" not in self.primary_points.metadata
        ):
            return  # Cannot establish links without unique ID

        lineage_tree_id = self.primary_points.metadata["lineage_tree_id"]

        for layer in self.viewer.layers:
            if (
                hasattr(layer, "metadata")
                and "lineage_tree_id" in layer.metadata
                and layer.metadata["lineage_tree_id"] == lineage_tree_id
                and "link" not in layer.metadata
            ):  # Only link if not already linked
                layer.metadata["link"] = self.primary_points

    def discover_layers(self, viewer, primary_points=None) -> bool:
        """
        Discover and register related layers in the viewer.

        Parameters
        ----------
        viewer : napari.Viewer
            The napari viewer instance
        primary_points : napari.layers.Points, optional
            Specific Points layer to use. If None, finds the first one with LineageTree metadata.

        Returns
        -------
        bool
            True if any compatible layers were found
        """

        self.adapters.clear()

        # Find the primary Points layer with LineageTree metadata
        if primary_points is None:
            for layer in viewer.layers:
                if (
                    isinstance(layer, Points)
                    and hasattr(layer, "metadata")
                    and "LineageTree" in layer.metadata
                ):
                    primary_points = layer
                    break

        if not primary_points or not isinstance(primary_points, Points):
            return False

        # Extract mappings from Points layer
        node_to_napari = primary_points.metadata.get("lT2napari", {})
        napari_to_node = primary_points.metadata.get("napari2lT", {})

        if not node_to_napari or not napari_to_node:
            return False

        # Register Points adapter
        self.adapters["points"] = PointsAdapter(
            primary_points, node_to_napari, napari_to_node
        )

        # Look for related Surface layers using the 'link' metadata
        for layer in viewer.layers:
            if (
                isinstance(layer, Surface)
                and hasattr(layer, "metadata")
                and "link" in layer.metadata
                and layer.metadata["link"] == primary_points
                and "node_to_vertex_range" in layer.metadata
            ):

                adapter = SurfaceAdapter(
                    layer, layer.metadata["node_to_vertex_range"]
                )
                self.adapters["surface"] = adapter
                break

        # Look for related Tracks layers
        for layer in viewer.layers:
            if (
                isinstance(layer, Tracks)
                and hasattr(layer, "metadata")
                and "link" in layer.metadata
                and layer.metadata["link"] == primary_points
            ):

                adapter = TracksAdapter(layer)
                self.adapters["tracks"] = adapter
                break

        return len(self.adapters) > 0

    def show_only_lineages(self, node_ids: list[int]) -> None:
        """Show only the specified lineages across all registered layers."""
        for adapter in self.adapters.values():
            adapter.show_only_nodes(node_ids)

    def show_only_nodes(self, node_ids: list[int]) -> None:
        """Show only the specified nodes across all registered layers."""
        for adapter in self.adapters.values():
            adapter.show_only_nodes(node_ids)

    def hide_lineages(self, node_ids_to_hide: list[int]) -> None:
        """Hide specific lineages while preserving current visibility of other lineages."""
        for adapter in self.adapters.values():
            adapter.hide_nodes(node_ids_to_hide)

    def highlight_lineages(self, node_ids: list[int]) -> None:
        """Highlight the specified lineages. For Points, this selects them without hiding others."""
        for adapter in self.adapters.values():
            if hasattr(adapter, "select_nodes"):
                # For layers that support selection, select the nodes
                adapter.select_nodes(node_ids)

    def reset_visibility(self) -> None:
        """Reset visibility across all registered layers."""
        for adapter in self.adapters.values():
            adapter.reset_visibility()

    def restore_visibility(self) -> None:
        """Restore visibility across all registered layers without affecting selection."""
        for adapter in self.adapters.values():
            adapter.restore_visibility()

    def find_node_at_position(
        self,
        position: np.ndarray,
        view_direction: np.ndarray,
        dims_displayed: np.ndarray,
    ) -> tuple | None:
        """
        Find a node at the given position across all clickable layers.

        Returns tuple of (layer, node_idx, node_id) if found, None otherwise.
        Prioritizes: Points > Surface > Tracks
        """
        time = position[0]  # Extract time from position

        for layer_type in ["points", "surface", "tracks"]:
            if layer_type in self.adapters:
                adapter = self.adapters[layer_type]
                # For 3D interaction, we need to handle ray intersections
                if hasattr(adapter, "get_node_at_3d_position"):
                    result = adapter.get_node_at_3d_position(
                        position, view_direction, dims_displayed
                    )
                else:
                    # Fallback to 2D position method
                    result = adapter.get_node_at_position(position, time)

                if result is not None:
                    return (
                        adapter.layer,
                        result,
                    )  # (layer, node_id)
        return None

    def get_registered_layers(self) -> list[str]:
        """Get list of registered layer types."""
        return list(self.adapters.keys())

    def update_state(self, **kwargs) -> None:
        """Save state parameters for this lineage tree."""
        self.state.update(kwargs)

    def get_state(self, key: str = None):
        """Get state value(s) for this lineage tree."""
        if key is None:
            return self.state.copy()
        return self.state.get(key)

    def restore_state(self, widget) -> None:
        """Restore widget visibility state from saved state."""
        # Note: graph_slider_value and canvas state are restored in the widget's layer_change method

        # Restore visibility state
        visibility_state = self.state.get("visibility_state", "all_visible")
        if visibility_state == "all_visible":
            self.restore_visibility()
        elif visibility_state == "lineage_only" and self.state.get(
            "visible_lineage"
        ):
            self.show_only_lineages(list(self.state["visible_lineage"]))
        elif visibility_state == "lineage_hidden" and self.state.get(
            "hidden_lineage"
        ):
            self.hide_lineages(list(self.state["hidden_lineage"]))
        elif visibility_state == "all_hidden":
            self.show_only_nodes([])

    @classmethod
    def get_bridge_for_layer(cls, layer):
        """Get the InteractionBridge associated with a layer."""
        # For Points layers, get bridge directly from metadata
        if (
            hasattr(layer, "metadata")
            and "interaction_bridge" in layer.metadata
        ):
            return layer.metadata["interaction_bridge"]

        # For companion layers, follow the link to get the bridge
        if (
            hasattr(layer, "metadata")
            and "link" in layer.metadata
            and hasattr(layer.metadata["link"], "metadata")
            and "interaction_bridge" in layer.metadata["link"].metadata
        ):
            return layer.metadata["link"].metadata["interaction_bridge"]

        return None

    @classmethod
    def create_bridge_for_points_layer(cls, viewer, points_layer):
        """Create and store an InteractionBridge in a Points layer's metadata."""
        bridge = cls(viewer, points_layer)
        points_layer.metadata["interaction_bridge"] = bridge

        # Initialize with default state
        bridge.update_state(
            graph_slider_value=0,
            selected_subtree=set(),
            visibility_state="all_visible",
        )

        return bridge
