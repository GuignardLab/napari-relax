"""
Central signal hub for coordinating communication between plugin components.
Reduces coupling between widgets by providing a centralized event system.
"""

from typing import Any

from lineagetree import LineageTree
from qtpy.QtCore import QObject, Signal


class PluginSignalHub(QObject):
    """
    Central signal coordinator for the napari-relax plugin.
    Manages communication between widgets without tight coupling.
    """

    # Core data signals
    lineage_tree_updated = Signal(LineageTree)
    lineage_tree_manager_updated = Signal(object)  # LineageTreeManager

    # Selection and interaction signals
    cell_selection_changed = Signal(set)  # set of selected cell IDs
    subtree_selection_requested = Signal(int)  # Cell ID for subtree selection

    # Legacy visualization signals (maintained for backward compatibility)
    colors_changed = Signal(dict)  # Color mapping updates (legacy)
    graph_colors_updated = Signal(int, bool)  # graph_index, color_from_trees
    layer_refresh_requested = Signal()

    # Enhanced color and visual signals
    color_mapping_updated = Signal(dict)  # Structured color mapping updates
    visual_settings_updated = Signal(dict)  # Canvas styling settings
    layer_colors_changed = Signal(object, object)  # (layer, face_colors)
    quantitative_coloring_applied = Signal(dict)  # Quantitative coloring data
    coloring_reset_requested = Signal()  # Reset coloring to defaults

    # Widget coordination signals
    label_update_requested = Signal(str)  # For label propagation
    analysis_results_ready = Signal(dict)  # Analysis results to share

    # Cross-embryo comparison signals
    manager_ready = Signal(object)  # LineageTreeManager ready for use
    embryo_comparison_requested = Signal(list)  # list of embryo identifiers

    def __init__(self):
        super().__init__()
        self._registered_widgets = []
        self._widget_connections = {}
        
        # Set up central color coordination
        self._setup_color_coordination()

    def register_widget(self, widget_name: str, widget_instance) -> None:
        """
        Register a widget with the signal hub.

        Args:
            widget_name: Unique name for the widget
            widget_instance: The widget instance to register
        """
        if widget_name not in self._registered_widgets:
            self._registered_widgets.append(widget_name)
            self._widget_connections[widget_name] = widget_instance

            # Auto-connect common signals if widget has standard methods
            self._auto_connect_widget(widget_name, widget_instance)

    def unregister_widget(self, widget_name: str) -> None:
        """
        Unregister a widget from the signal hub.

        Args:
            widget_name: Name of the widget to unregister
        """
        if widget_name in self._registered_widgets:
            self._registered_widgets.remove(widget_name)
            del self._widget_connections[widget_name]

    def _auto_connect_widget(self, widget_name: str, widget_instance) -> None:
        """
        Automatically connect standard widget methods to hub signals.

        Args:
            widget_name: Name of the widget
            widget_instance: Widget instance to connect
        """
        # Connect common update methods - BaseAnalysisWidget implements all of these
        self.lineage_tree_updated.connect(widget_instance.update_lineage_tree)
        self.cell_selection_changed.connect(
            widget_instance.handle_selection_change
        )
        self.colors_changed.connect(widget_instance.handle_color_change)
        self.label_update_requested.connect(
            widget_instance.handle_label_update
        )
        
        # Connect enhanced color signals
        if hasattr(widget_instance, 'handle_color_mapping'):
            self.color_mapping_updated.connect(widget_instance.handle_color_mapping)
        if hasattr(widget_instance, 'handle_visual_settings'):
            self.visual_settings_updated.connect(widget_instance.handle_visual_settings)
        if hasattr(widget_instance, 'handle_quantitative_coloring'):
            self.quantitative_coloring_applied.connect(widget_instance.handle_quantitative_coloring)
        if hasattr(widget_instance, 'handle_coloring_reset'):
            self.coloring_reset_requested.connect(widget_instance.handle_coloring_reset)

        # Widget-specific connections (keep hasattr for optional methods)
        if widget_name == "manager" and hasattr(
            widget_instance, "handle_manager_update"
        ):
            self.lineage_tree_manager_updated.connect(
                widget_instance.handle_manager_update
            )

    def emit_lineage_tree_update(self, lineage_tree: LineageTree) -> None:
        """Emit signal when lineage tree is updated."""
        self.lineage_tree_updated.emit(lineage_tree)

    def emit_selection_change(self, selected_cells: set[int]) -> None:
        """Emit signal when cell selection changes."""
        self.cell_selection_changed.emit(selected_cells)

    def emit_color_change(self, color_mapping: dict[str, Any]) -> None:
        """Emit signal when colors are updated (legacy support)."""
        self.colors_changed.emit(color_mapping)
        
        # Also emit through new structured signals for better handling
        self._route_legacy_color_signal(color_mapping)

    def emit_color_mapping_update(self, mapping_data: dict) -> None:
        """Emit structured color mapping update."""
        self.color_mapping_updated.emit(mapping_data)

    def emit_visual_settings_update(self, settings: dict) -> None:
        """Emit visual settings update."""
        self.visual_settings_updated.emit(settings)

    def emit_quantitative_coloring(self, coloring_data: dict) -> None:
        """Emit quantitative coloring update."""
        self.quantitative_coloring_applied.emit(coloring_data)

    def emit_coloring_reset(self) -> None:
        """Emit coloring reset request."""
        self.coloring_reset_requested.emit()

    def emit_label_update(self, label_text: str) -> None:
        """Emit signal for label updates."""
        self.label_update_requested.emit(label_text)

    def emit_manager_ready(self, manager) -> None:
        """Emit signal when LineageTreeManager is ready."""
        self.manager_ready.emit(manager)

    def get_registered_widgets(self) -> list[str]:
        """Get list of registered widget names."""
        return self._registered_widgets.copy()

    def get_widget_instance(self, widget_name: str):
        """Get widget instance by name."""
        return self._widget_connections.get(widget_name, None)

    def _setup_color_coordination(self) -> None:
        """Set up central color signal coordination."""
        # Connect new structured signals to legacy ones for backward compatibility
        self.color_mapping_updated.connect(self._handle_color_mapping_update)
        self.visual_settings_updated.connect(self._handle_visual_settings_update)

    def _route_legacy_color_signal(self, color_data: dict) -> None:
        """Route legacy color signals to appropriate new structured signals."""
        if color_data.get('quantitative_coloring'):
            # Route quantitative coloring to new signal
            quantitative_data = {
                'type': 'quantitative',
                'node_colors': color_data.get('node_colors', {}),
                'face_colors': color_data.get('face_colors', []),
                'selected_nodes': color_data.get('selected_nodes', set()),
            }
            self.emit_quantitative_coloring(quantitative_data)
        elif color_data.get('quantitative_coloring') is False:
            # Route reset signal
            self.emit_coloring_reset()
        
        # Route visual settings
        visual_settings = {}
        for key in ['color_of_nodes', 'color_of_edges', 'node_size', 'lw', 'fontsize']:
            if key in color_data:
                visual_settings[key] = color_data[key]
        
        if visual_settings:
            self.emit_visual_settings_update(visual_settings)

    def _handle_color_mapping_update(self, mapping_data: dict) -> None:
        """Central handler for color mapping updates."""
        # Route to widgets that can handle color mapping
        for widget_name, widget_instance in self._widget_connections.items():
            if hasattr(widget_instance, 'handle_color_mapping'):
                widget_instance.handle_color_mapping(mapping_data)

    def _handle_visual_settings_update(self, settings: dict) -> None:
        """Central handler for visual settings updates."""
        # Route to widgets that can handle visual settings
        for widget_name, widget_instance in self._widget_connections.items():
            if hasattr(widget_instance, 'handle_visual_settings'):
                widget_instance.handle_visual_settings(settings)
