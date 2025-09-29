from lineagetree import LineageTree
from qtpy.QtWidgets import (
    QWidget,
)

from .._utils import _select_active_lt_layer

# Default selection color - can be overridden by canvas settings
DEFAULT_SELECTION_COLOR_RGBA = [1, 0, 1, 1]  # magenta


class LayerCorrectorTreeProducer(QWidget):
    """
    Parent Class that is called inside the plugin, it produces no interface.
    Contains functions that are useful for the used Widgets inside the plugin:
        -Selector for cell and all descendants
        -Producing the lineagetree object
        -All the graphs, so that they may be inherited to the rest of the classes.
         The graphs are calculated when the Layer corrector is first loaded and the passed on to its children.

    Generally functions that are used by other classes are added here.
    """

    def sub_points_selector(self):
        """
        Adds all descendants of a cell to selected_data.
        Reads the selected data from napari.layer and it will select all the cells that are ancestors of this point.
        """
        active_layer = _select_active_lt_layer(self.viewer)
        if not active_layer.selected_data:
            return 0
        lT = active_layer.metadata["LineageTree"]
        cell = active_layer.selected_data.pop()
        active_layer.selected_data = {cell}
        scores = lT.get_subtree_nodes(active_layer.metadata["napari2lT"][cell])
        for val in scores:
            active_layer.selected_data.add(
                active_layer.metadata["lT2napari"][val]
            )
        active_layer.refresh()

    def get_lT(self) -> LineageTree:
        """
        Function that reads the LineageTree structure through one of the layers.

        """
        active_layer = _select_active_lt_layer(self.viewer)
        if active_layer is None:
            return None
        return active_layer.metadata.get("LineageTree", None)

    def paint_nodes_of_same_tree(self, val):
        """
        Specific of Progeny selection class. Changes the color of the subtree or the whole
        tree accordng the the state of the toggleble point_color_from_trees.value.

        Args:
        val (int): index of the list of graphs
        """
        active_layer = _select_active_lt_layer(self.viewer)
        active_layer.face_color = active_layer.metadata["clone2"]
        if self.point_color_from_trees.value:
            root = [
                i
                for i, d in active_layer.metadata["graphs"][0][val].in_degree()
                if d == 0
            ]
            active_layer.selected_data.add(
                active_layer.metadata["lT2napari"][root[0]]
            )
            self.sub_points_selector()
            selection = list(active_layer.selected_data)
            active_layer.face_color[selection] = DEFAULT_SELECTION_COLOR_RGBA
            active_layer.selected_data.clear()
            active_layer.refresh()

    def val_finder(self, cell, lt, graphs):
        """
        Useful function for selecting the right index in the list of graphs
        Args:
            cell (int): id of the node
            lt (LineageTree object): The LineageTree class
            graphs: The list of graphs

        Returns:
            i (int): The key of the graphs list
        """
        for i, g in graphs.items():
            if lt.get_ancestor_at_t(cell) == g["root"]:
                return i

    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
