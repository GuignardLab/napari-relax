"""
Base widget classes and protocols for the napari-relax plugin.
Provides standardized interface for analysis widgets.
"""

from typing import Any, Protocol

from lineagetree import LineageTree
from qtpy.QtWidgets import QWidget

from ._data_management import LineageTreeDataManager
from ._signal_hub import PluginSignalHub


class AnalysisWidgetProtocol(Protocol):
    """
    Protocol defining the standard interface for analysis widgets.
    All analysis widgets should implement these methods.
    """

    @property
    def name(self) -> str:
        """Widget display name."""
        ...

    def update_lineage_tree(self, lineage_tree: LineageTree) -> None:
        """Update widget with new lineage tree data."""
        ...

    def handle_selection_change(self, selected_ids: set[int]) -> None:
        """Handle changes in cell selection."""
        ...

    def handle_color_change(self, color_mapping: dict[str, Any]) -> None:
        """Handle color mapping updates."""
        ...

    def get_analysis_results(self) -> dict[str, Any]:
        """Get current analysis results from widget."""
        ...

    def reset_widget(self) -> None:
        """Reset widget to initial state."""
        ...


class BaseAnalysisWidget(QWidget):
    """
    Base class for all analysis widgets using composition instead of inheritance.
    Provides common functionality while maintaining clean separation of concerns.
    """

    def __init__(self, napari_viewer, signal_hub: PluginSignalHub):
        super().__init__()
        self.viewer = napari_viewer
        self.signal_hub = signal_hub
        self.data_manager = LineageTreeDataManager(napari_viewer)
        self._name = "Base Analysis Widget"

        # Register with signal hub
        self.signal_hub.register_widget(self._name, self)

    @property
    def name(self) -> str:
        """Widget display name."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """set widget display name."""
        self._name = value

    def update_lineage_tree(self, lineage_tree: LineageTree) -> None:
        """
        Update widget with new lineage tree data.
        Override in subclasses for specific behavior.
        """
        # Default implementation - can be overridden

    def handle_selection_change(self, selected_ids: set[int]) -> None:
        """
        Handle changes in cell selection.
        Override in subclasses for specific behavior.
        """
        # Default implementation - can be overridden

    def handle_color_change(self, color_mapping: dict[str, Any]) -> None:
        """
        Handle color mapping updates.
        Override in subclasses for specific behavior.
        """
        # Default implementation - can be overridden

    def handle_label_update(self, label_text: str) -> None:
        """
        Handle label updates from other widgets.
        Override in subclasses for specific behavior.
        """
        # Default implementation - can be overridden

    def get_analysis_results(self) -> dict[str, Any]:
        """
        Get current analysis results from widget.
        Override in subclasses to return specific results.
        """
        return {}

    def reset_widget(self) -> None:
        """
        Reset widget to initial state.
        Override in subclasses for specific reset behavior.
        """

    def get_current_lineage_tree(self) -> LineageTree | None:
        """Get current lineage tree from data manager."""
        return self.data_manager.get_lineage_tree()

    def select_subtree(self, cell_id: int | None = None) -> int:
        """Select subtree using data manager."""
        return self.data_manager.select_subtree(cell_id)

    def paint_tree_nodes(
        self, graph_index: int, color_from_trees: bool = False
    ) -> None:
        """Paint tree nodes using data manager."""
        self.data_manager.paint_tree_nodes(graph_index, color_from_trees)

    def find_graph_index(
        self, cell_id: int, lineage_tree: LineageTree, graphs: dict
    ) -> int | None:
        """Find graph index using data manager."""
        return self.data_manager.find_graph_index(
            cell_id, lineage_tree, graphs
        )

    def emit_selection_change(self, selected_cells: set[int]) -> None:
        """Emit selection change through signal hub."""
        self.signal_hub.emit_selection_change(selected_cells)

    def emit_color_change(self, color_mapping: dict[str, Any]) -> None:
        """Emit color change through signal hub."""
        self.signal_hub.emit_color_change(color_mapping)

    def emit_label_update(self, label_text: str) -> None:
        """Emit label update through signal hub."""
        self.signal_hub.emit_label_update(label_text)

    def cleanup(self) -> None:
        """Cleanup when widget is destroyed."""
        self.signal_hub.unregister_widget(self._name)
