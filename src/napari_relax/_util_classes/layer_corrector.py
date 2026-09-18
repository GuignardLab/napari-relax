from lineagetree import LineageTree
from qtpy.QtWidgets import (
    QWidget,
)

from .._utils import _select_active_lt_layer
from .eventfilter_for_delayed_tooltip import DelayedTooltipEventFilter

# Default selection color - can be overridden by canvas settings
DEFAULT_SELECTION_COLOR_RGBA = [1, 0, 1, 1]  # magenta


class LayerCorrectorTreeProducer(QWidget):
    """Base class of the ReLAX widgets, without an interface of its own.

    It provides helpers shared by the widgets: reading the LineageTree
    of the active layer, selecting a cell and its descendants, and
    finding the Lineage Viewer graph of a cell.

    Parameters
    ----------
    napari_viewer : napari.Viewer
        The napari viewer.
    """

    def sub_points_selector(self):
        """Add all descendants of the selected point to the selection."""
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
        """Return the LineageTree of the active layer.

        Returns
        -------
        LineageTree or None
            The LineageTree, or None if no layer holds one.
        """
        active_layer = _select_active_lt_layer(self.viewer)
        if active_layer is None:
            return None
        return active_layer.metadata.get("LineageTree", None)

    def paint_nodes_of_same_tree(self, val):
        """Color the whole tree of a graph with the selection color.

        Used by widgets with a ``point_color_from_trees`` toggle.

        Parameters
        ----------
        val : int
            Index of the graph in the list of graphs.
        """
        active_layer = _select_active_lt_layer(self.viewer)
        active_layer.face_color = active_layer.metadata["default_colors"]
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
        """Find the graph that contains a cell.

        Parameters
        ----------
        cell : int
            ID of the node.
        lt : LineageTree
            The LineageTree.
        graphs : dict
            The Lineage Viewer graphs, keyed by index.

        Returns
        -------
        int or None
            The key of the graph whose root is the ancestor of the cell.
        """
        for i, g in graphs.items():
            if lt.get_ancestor_at_t(cell) == g["root"]:
                return i

    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        event_filt = DelayedTooltipEventFilter()
        self.installEventFilter(event_filt)
