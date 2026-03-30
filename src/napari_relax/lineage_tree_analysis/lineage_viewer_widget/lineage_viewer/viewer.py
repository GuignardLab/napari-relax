import numpy as np
from lineagetree import LineageTree
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from psygnal import Signal
from scipy.spatial import KDTree

from .canvas_interaction_events import CanvasUtils


class SingleTreeProgeny(FigureCanvas, CanvasUtils):
    node_signal = Signal(dict)
    node_size = 10
    lw = 0.3
    fontsize = 6
    all_selected = False
    margins_of_plot = 0.05
    selected_color = (1, 0, 1)

    def change_attributes(self, signal):
        """
        Receives a signal to change the attributes of the plot.
        """
        self.node_size = signal.get("node_size", self.node_size)
        self.lw = signal.get("lw", self.lw)

        self.fontsize = signal.get("fontsize", self.fontsize)
        self.back_ground = signal.get("back_ground", self.back_ground)

        if "quant_colors" in signal:
            self.node_colors = signal["node_colors"]
        self.draw_graph()

    def _generate_info_to_draw_graph(self):
        """Calculates everything needed to draw the graph, used on initiation and lineage_change"""
        self.calculate_axes()

        self.pan = False
        self.labels = False
        self.node_colors, self.lT2napari = self._get_metadata_mappings()
        self._extract_default_colors_from_points_layer()

        self.marked_cell_id = None

        # Initialize marked cell for circle highlighting
        self.marked_cell_id = None  # make it a property TODO
        # self.ax.set_margins(0)
        self.ax.axis("off")
        # self.lims_of_tree = (self.lT.t_b, max(self.lT.time[node] for node in (self.lT.leaves|self.lT.get_subtree_nodes(self.root))))

    def __init__(
        self,
        figure,
        ax,
    ):
        super().__init__(figure)
        self.ax = ax
        self.selected_nodes = set()
        self.connect_signals()

    @property
    def coloring(self):
        if not hasattr(self, "node_colors"):
            self.node_colors = self.default_colors.copy()
        return self.node_colors | dict.fromkeys(
            self.selected_nodes, self.selected_color
        )

    def _get_metadata_mappings(self):
        """Get the color and node mappings from metadata.

        Returns:
            tuple: (default_colors, lT2napari) or (None, None) if not available.
        """
        if not self.points_layer_metadata:
            return None, None

        self._default_layer_colors = self.points_layer_metadata.get(
            "default_colors"
        )
        self.lT2napari = self.points_layer_metadata.get("lT2napari")
        if self._default_layer_colors is None or self.lT2napari is None:
            self._default_layer_colors = "black"
            return "black", None
        return self._default_layer_colors, self.lT2napari

    def _extract_default_colors_from_points_layer(self):

        if self.lT2napari is None:
            return None
        if hasattr(self, "lT") and self.lT:
            # lineage_nodes = [c[0] for c in  self.lT.get_all_chains_of_subtree(self.root)]
            lineage_nodes = {
                node
                for c in self.lT.get_all_chains_of_subtree(self.root)
                for node in (c[0], c[-1])
            }
        else:
            return None
        default_colors = {}
        for node in lineage_nodes:
            if node in self.lT2napari:
                napari_idx = self.lT2napari[node]
                color = self._default_layer_colors[napari_idx]
                default_colors[node] = self._convert_color_to_list(color)
        self.default_colors = default_colors

    def _convert_color_to_list(self, color):
        """Normalize color to a list format.

        Args:
            color: Color in various formats (numpy array, list, tuple)

        Returns:
            list: Normalized color as list
        """
        if hasattr(color, "tolist"):
            return color.tolist()
        else:
            return list(color)

    def _extract_current_lineage_color(self):
        """Extract the current color for this lineage from the active Points layer.

        This method checks the actual face_color of points in the current lineage,
        which may be different from the original default_colors if quantitative
        recoloring has been applied.

        Returns:
            dict: Dictionary with 'color' (single color if uniform) and 'is_uniform' (bool)
                  indicating whether all nodes in the lineage have the same color.
                  Returns None if no data is available.
        """
        if self.lT2napari is None:
            return None

        # Get all nodes in the current lineage
        if hasattr(self, "lT") and self.lT:
            lineage_nodes = {
                node
                for c in self.lT.get_all_chains_of_subtree(self.root)
                for node in (c[0], c[-1])
            }
        else:
            return None
        current_face_colors = self.points_layer_metadata.get(
            "current_face_colors"
        )
        if current_face_colors is None:
            # Fallback to original default_colors
            self.node_colors = self.default_colors.copy()
            return

        # Collect colors for all nodes in this lineage
        lineage_colors = {}
        for node in lineage_nodes:
            if node in self.lT2napari:
                napari_idx = self.lT2napari[node]
                color = current_face_colors[napari_idx]
                lineage_colors[node] = self._convert_color_to_list(color)

        if not lineage_colors:
            self.node_colors = self.default_colors.copy()
            return
        self.node_colors = lineage_colors

    def update_face_colors(self, face_colors):
        """Update the metadata with provided face colors."""
        if self.points_layer_metadata is not None:
            self.points_layer_metadata["current_face_colors"] = face_colors

    def change_lineage(
        self,
        root=None,
        lT: LineageTree = None,
        lnks_tms=None,
        hier: dict | None = None,
        points_layer_metadata=None,
    ):
        if lT:
            self.lT = lT
            self.root = root
            self.lnks_tms = lnks_tms
            self.hier = hier
            self.points_layer_metadata = points_layer_metadata
            self._generate_info_to_draw_graph()
            self.draw_graph(reset=True)


    def draw_graph(self, reset=False):
        """Plots the tree, if reset is true it sets the new axes, otherwise it works with the old ones.

        Parameters
        ----------
        reset : bool, by default False
            If `True` reset the axes, by default False
        """

        # Safety check: Don't draw if canvas is not properly initialized
        if not hasattr(self, "ax") or self.ax is None:
            return

        if reset:
            self.calculate_axes()
            xlim = self.xlim  # full tree bounds on reset
            ylim = self.ylim
        else:
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()

        self.ax.cla()
        # Extract current colors from the active layer (handles quantitative coloring)
        self.node_colors, self.lT2napari = self._get_metadata_mappings()
        self._extract_current_lineage_color()
        self.lT.draw_tree_graph(
            self.hier,
            self.lnks_tms,
            lw=float(self.lw),
            size=float(self.node_size),
            color_of_nodes=self.coloring,
            color_of_edges=self.coloring,
            ax=self.ax,
        )
        self._plot_labels()

        # Draw circle marker for marked cell if specified
        if self.marked_cell_id is not None:
            self._draw_cell_marker(self.marked_cell_id)

            self.labels = True

        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        self.draw()

    def _plot_labels(self):
        for text in self.ax.texts[:]:
            text.remove()
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        with_labels = (xlim[1] - xlim[0]) <= self.xlim_min + 70
        self.labels = with_labels
        if with_labels:
            for node, pos in self.hier.items():
                if xlim[0] < pos[0] < xlim[1] and ylim[0] < pos[1] < ylim[1]:
                    self.ax.text(
                        *pos,
                        "Label: "
                        + str(self.lT.labels.get(node, node))
                        + "\n"
                        + "ID: "
                        + str(node),
                        fontsize=self.fontsize,
                        rotation=34,
                    )

    def calculate_axes(self):
        data = np.array(list(self.hier.values()))  # shape (N, 2)
        self.xmin, self.xmax = data[:, 0].min(), data[:, 0].max()
        self.ymin, self.ymax = data[:, 1].min(), data[:, 1].max()
        range_x = self.xmax - self.xmin
        range_y = self.ymax - self.ymin
        margin = self.margins_of_plot
        self.xmin -= range_x * margin
        self.xmax += range_x * margin
        self.ymin -= range_y * margin
        self.ymax += range_y * margin
        self.xlim = (self.xmin, self.xmax)
        self.ylim = (self.ymin, self.ymax)
        self.xlim_min = (self.xmax - self.xmin) / 50

    def click(self, event):
        if event.button == 1 and event.inaxes and self.lT:
            self.selected_nodes = {}
            self.marked_cell_id = None
            kdtree = KDTree(list(self.hier.values()))
            dist, ind = kdtree.query([event.xdata, event.ydata])
            max_x = self.xmin, self.xmax
            max_y = self.ymin, self.ymax
            max_dist = (
                np.sqrt(
                    (max_x[1] - max_x[0]) ** 2 + (max_y[1] - max_y[0]) ** 2
                )
                / 97
            )
            if dist > (max_dist):
                # Background click - clear selections and marked cell
                self.node_signal.emit({})
                self.draw_graph()
                return
            cell = list(self.hier.keys())[ind]
            self.node_signal.emit({"value": cell, "dblclick": event.dblclick})
            self.marked_cell_id = cell
            self.selected_nodes = self.lT.get_subtree_nodes(cell)
            self.draw_graph()
            return 
