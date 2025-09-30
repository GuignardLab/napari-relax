from qtpy.QtWidgets import QWidget

from .._data_management import LineageTreeDataManager
from .._signal_hub import PluginSignalHub

# Default selection color - can be overridden by canvas settings
DEFAULT_SELECTION_COLOR_RGBA = [1, 0, 1, 1]  # magenta


class LineageTreeWidgetBase(QWidget):
    """
    Parent Class that is called inside the plugin, it produces no interface.
    Updated to use composition with LineageTreeDataManager.

    Contains functions that are useful for the used Widgets inside the plugin:
        -Selector for cell and all descendants
        -Producing the lineagetree object
        -All the graphs, so that they may be inherited to the rest of the classes.
         The graphs are calculated when the Layer corrector is first loaded and the passed on to its children.

    Generally functions that are used by other classes are added here.
    """

    def __init__(self, napari_viewer, signal_hub: PluginSignalHub = None):
        super().__init__()
        self.viewer = napari_viewer

        # Create signal hub if not provided (for backward compatibility)
        if signal_hub is None:
            signal_hub = PluginSignalHub()
        self.signal_hub = signal_hub

        # Use composition with data manager for cleaner architecture
        self._data_manager = LineageTreeDataManager(napari_viewer)

    def select_progeny_points(self):
        """
        Adds all descendants of a cell to selected_data.
        Reads the selected data from napari.layer and it will select all the cells that are ancestors of this point.
        """
        return self._data_manager.select_subtree()

    def paint_nodes_of_same_tree(self, val):
        """
        Specific of Progeny selection class. Changes the color of the subtree or the whole
        tree according to the state of the toggleable point_color_from_trees.value.

        Args:
        val (int): index of the list of graphs
        """
        # Check if the widget has the point_color_from_trees attribute
        color_from_trees = False
        if hasattr(self, "point_color_from_trees"):
            color_from_trees = self.point_color_from_trees.value

        self._data_manager.paint_tree_nodes(val, color_from_trees)

    def find_graph_index(self, cell, lt, graphs):
        """
        Useful function for selecting the right index in the list of graphs
        Args:
            cell (int): id of the node
            lt (LineageTree object): The LineageTree class
            graphs: The list of graphs

        Returns:
            i (int): The key of the graphs list
        """
        return self._data_manager.find_graph_index(cell, lt, graphs)

    def emit_selection_change(self, selected_cells):
        """Emit selection change through signal hub."""
        self.signal_hub.emit_selection_change(selected_cells)

    def emit_color_change(self, color_mapping):
        """Emit color change through signal hub."""
        self.signal_hub.emit_color_change(color_mapping)

    def emit_label_update(self, label_text):
        """Emit label update through signal hub."""
        self.signal_hub.emit_label_update(label_text)
