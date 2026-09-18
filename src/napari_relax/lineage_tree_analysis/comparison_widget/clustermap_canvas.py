"""Matplotlib canvas drawing the interactive clustermap."""

import matplotlib.pyplot as plt
import numpy as np
from lineagetree import LineageTree
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.colors import Colormap
from psygnal import Signal
from qtpy.QtCore import QTimer
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import QWidget
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform


class ClusterMapCanvas(FigureCanvas):
    """Matplotlib canvas showing pairwise comparisons as a clustermap.

    Parameters
    ----------
    figure : matplotlib.figure.Figure
        The figure to draw on.
    ax : matplotlib.axes.Axes
        The axes of the clustermap.
    """

    norm_dict = {"max": max, "sum": sum, "None": lambda x: 1}

    click_signal = Signal(list)

    def __init__(self, figure: plt.Figure, ax: plt.Axes):
        """Create the canvas and connect the click and hover events.

        Parameters
        ----------
        figure : matplotlib.figure.Figure
            The figure to draw on.
        ax : matplotlib.axes.Axes
            The axes of the clustermap.
        """
        super().__init__(figure)
        self.figure = figure
        self.ax = ax
        self.setSizePolicy(
            QWidget.sizePolicy(self).Expanding,
            QWidget.sizePolicy(self).Expanding,
        )
        self.norm_method = "sum"
        self.cmap = "viridis"
        self.mpl_connect("button_press_event", self._click)
        self.mpl_connect("motion_notify_event", self._on_hover)
        self.remove_timer = QTimer()
        self.remove_timer.setInterval(100)
        self.remove_timer.timeout.connect(self.remove_on_leave)
        self.remove_timer.start()
        self.remove_flag = True
        self.timer = None
        self.old_xy = None

    def clear_data(self):
        """Clear the plot and remove all data."""
        self.comps = None
        self.norms = None
        self.names = None
        self.time = None
        self.lT = None
        self.labels = None
        self.ax.cla()

    def _receive_data(
        self,
        comps: dict = None,
        norms: dict = None,
        names: dict = None,
        time: int = None,
        lT: LineageTree = None,
    ):
        """Receive the comparisons of one timepoint and plot them.

        Parameters
        ----------
        comps : dict, optional
            Edit distance of each pair of sublineage indices.
        norms : dict, optional
            Normalization values of each pair.
        names : dict, optional
            Node, root and labelled ancestor of each sublineage index.
        time : int, optional
            The timepoint of the comparisons.
        lT : LineageTree, optional
            The compared LineageTree.
        """
        self.comps = comps
        self.norms = norms
        self.names = names
        self.time = time
        self.lT = lT
        self.labels = self.lT.labels
        if comps is not None and len(comps) > 0:
            self._plot()

    def _plot(self):
        """Plot the clustermap of the current timepoint.

        Each cell is the normalized distance between two sublineages;
        rows and columns are ordered by Ward hierarchical clustering.
        """
        try:
            if hasattr(self, "colorbar"):
                self.colorbar.remove()
        except:  # noqa: E722
            ...
        self.ax.cla()
        if not hasattr(self, "comps"):
            return
        comparisons = self.comps
        names = self.names
        len_all_trees = len(names.keys())
        hierarchy = np.zeros((len_all_trees, len_all_trees))
        labels_of_roots = [
            self.labels[names[i][1]] for i in range(len_all_trees)
        ]
        labels_of_nodes = [names[i][0] for i in range(len_all_trees)]

        labels_of_node_real = [
            self.labels[names[i][2]] for i in range(len_all_trees)
        ]
        for keys, values in comparisons:
            hierarchy[keys, values] = comparisons[
                keys, values
            ] / self.norm_dict[self.norm_method](self.norms[keys, values])
            hierarchy[values, keys] = hierarchy[keys, values]

        condensed_dist_matrix = squareform(hierarchy)

        linkage_data = linkage(condensed_dist_matrix, method="ward")
        order = dendrogram(linkage_data, no_plot=True)["leaves"]
        labels_of_roots = [labels_of_roots[i] for i in order]
        labels_of_nodes = [labels_of_nodes[i] for i in order]
        labels_of_node_real = [labels_of_node_real[i] for i in order]
        self.names_of_nodes = labels_of_nodes
        self.names_of_roots = labels_of_roots
        self.labels_of_node_real = labels_of_node_real
        self.plot = hierarchy[np.ix_(order, order)]
        plot = self.ax.imshow(self.plot, cmap=self.cmap)
        self.colorbar = self.figure.colorbar(plot, ax=self.ax)
        self.ax.set_xticks(
            np.arange(len(labels_of_node_real)), labels=labels_of_node_real
        )
        self.ax.set_yticks(
            np.arange(len(labels_of_node_real)), labels=labels_of_node_real
        )
        self.ax.tick_params(axis="both", labelsize=10)
        plt.setp(
            self.ax.get_xticklabels(),
            rotation=45,
            ha="right",
            rotation_mode="anchor",
        )
        self.ax.set_title(f"Comparisons for Timepoint: {self.time}")
        self.ax.set_aspect("auto")
        self.draw()

    def _change_cmap(self, cmap: Colormap):
        """Redraw the clustermap with a new colormap.

        Parameters
        ----------
        cmap : Colormap
            The new colormap.
        """
        self.cmap = cmap
        self._plot()

    def _change_norm(self, norm_method: str):
        """Redraw the clustermap with a new normalization.

        Parameters
        ----------
        norm_method : str
            One of "max", "sum" or "None".
        """
        self.norm_method = norm_method
        self._plot()

    def remove_annotation(self):
        """Remove the hover box from the axes."""
        if hasattr(self, "hover_annotation") and self.hover_annotation:
            try:
                self.hover_annotation.remove()
            except:  # noqa: E722
                self.hover_annotation = None

    def is_mouse_on_figure(self) -> bool:
        """Check whether the mouse is on the figure.

        Returns
        -------
        bool
            True if the mouse is on the figure else False.
        """
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)
        return self.rect().contains(local_pos)

    def remove_on_leave(self):
        """Remove the hover box once the mouse has left the figure."""
        if not self.is_mouse_on_figure():
            self.remove_annotation()
            self.ax.figure.canvas.draw_idle()

    def annotation_maker(self, x, y, offset_xy, ha, value):
        """Create the hover box of a clustermap cell.

        Parameters
        ----------
        x : float
            Column of the cell.
        y : float
            Row of the cell.
        offset_xy : tuple of int
            Offset of the box from the cell, in points.
        ha : str
            Horizontal alignment of the box.
        value : float
            Score shown in the box.
        """
        self.hover_annotation = self.ax.annotate(
            f"Lineage 1: {self.labels_of_node_real[int(x + 0.5)]}\nLineage 2: {self.labels_of_node_real[int(y + 0.5)]}\nScore: {value:.2f}",
            (x, y),
            xytext=offset_xy,
            textcoords="offset points",
            ha=ha,
            va="bottom",
            bbox={
                "boxstyle": "round",
                "fc": "black",
                "ec": "none",
                "alpha": 0.5,
            },
            color="white",
            clip_on=False,
        )

    def print_text(self, pos: tuple[int, int]):
        """Show the hover box of the cell under the cursor.

        Parameters
        ----------
        pos : tuple[int, int]
            The position of the cursor.
        """
        if not hasattr(self, "plot"):
            return
        self.remove_annotation()
        x, y = pos
        value = self.plot[int(x + 0.5), int(y + 0.5)]
        if (self.ax.get_xlim()[1] - self.ax.get_xlim()[0]) / 2 > x:
            offset_xy = (15, -40)
            ha = "left"
        else:
            offset_xy = (-10, -40)
            ha = "right"
        self.annotation_maker(
            x=x, y=y, offset_xy=offset_xy, ha=ha, value=value
        )
        self.hover_annotation.set_clip_on(False)
        self.ax.figure.canvas.draw_idle()

    def _hover_text(self, event=None):
        """Stop the hover timer and show the hover box.

        Parameters
        ----------
        event : object, optional
            Timer event; the box is only shown when it is None.
        """
        self.timer.stop()
        self.timer = None
        if event is None:
            self.print_text(self.old_xy)

    def _on_hover(self, event):
        """Restart the hover timer when the mouse moves.

        Parameters
        ----------
        event : matplotlib.backend_bases.MouseEvent
            The mouse move event.
        """
        pos = (event.xdata, event.ydata)
        self.remove_annotation()
        self.ax.figure.canvas.draw_idle()
        if event.inaxes and pos != self.old_xy:
            self.old_xy = pos
            self.timer = self.new_timer(100)
            self.timer.add_callback(self._hover_text)
            self.timer.start()
        else:
            self.timer = None

    def _click(self, event):
        """Highlight the clicked pair and send it to recolor the dataset.

        Parameters
        ----------
        event : matplotlib.backend_bases.MouseEvent
            The click event.
        """
        if event.button == 1 and event.inaxes:
            self.mpl_disconnect(self._click)
            lineages = [
                self.names_of_nodes[int(event.xdata + 0.5)],
                self.names_of_nodes[int(event.ydata + 0.5)],
            ]
            self.click_signal.emit(lineages)
            label1 = [""] * len(self.labels_of_node_real)
            label1[int(event.xdata + 0.5)] = self.labels_of_node_real[
                int(event.xdata + 0.5)
            ]
            label2 = [""] * len(self.labels_of_node_real)
            label2[int(event.ydata + 0.5)] = self.labels_of_node_real[
                int(event.ydata + 0.5)
            ]
            self.ax.set_xticks(np.arange(len(label1)), labels=label1)
            self.ax.set_yticks(np.arange(len(label1)), labels=label2)
            self.ax.tick_params(axis="x", colors="magenta")
            self.ax.tick_params(axis="y", colors="cyan")
            plt.setp(
                self.ax.get_xticklabels(),
                rotation=45,
                ha="right",
                rotation_mode="anchor",
            )
            self.figure.canvas.mpl_connect("button_press_event", self._click)
            self.draw()
        else:
            self.ax.set_xticks(
                np.arange(len(self.labels_of_node_real)),
                labels=self.labels_of_node_real,
            )
            self.ax.set_yticks(
                np.arange(len(self.labels_of_node_real)),
                labels=self.labels_of_node_real,
            )
            self.ax.tick_params(axis="both", labelsize=10)
            plt.setp(
                self.ax.get_xticklabels(),
                rotation=45,
                ha="right",
                rotation_mode="anchor",
            )
            self.draw()
