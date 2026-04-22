import matplotlib.pyplot as plt
import numpy as np
from lineagetree import LineageTree
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from matplotlib.colors import Colormap
from psygnal import Signal
from PyQt5.QtGui import QCursor
from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QWidget
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform


class ClusterMapCanvas(FigureCanvas):
    """Clustermap that shows comparisons.

    Parameters
    ----------
    FigureCanvas : FigureCanvasQTAgg
        The Figure canvas with qt backend.
    """

    norm_dict = {"max": max, "sum": sum, "None": lambda x: 1}

    click_signal = Signal(list)

    def __init__(self, figure: plt.Figure, ax: plt.Axes):
        """
        Parameters
        ----------
        figure : plt.Figure
            _description_
        ax : plt.Axes
            _description_
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
        """Clears the plot and removes all data"""
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
        """Function used to receive data from the Clustermap class

        Parameters
        ----------
        comps : dict, optional
            _description_, by default None
        norms : dict, optional
            _description_, by default None
        names : dict, optional
            _description_, by default None
        time : int, optional
            _description_, by default None
        lT : LineageTree, optional
            _description_, by default None
        """
        self.comps = comps
        self.norms = norms
        self.names = names
        self.time = time
        self.lT = lT
        self.labels = self.lT.labels
        if comps is not None and len(comps)>0:
            self._plot()

    def _plot(self):
        """
        Plots the clustermap for the timepoint specified by the time slider, where each element is the pairwise comparison of all the sublineages present in
        the timepoint selected.
        """
        try:
            if hasattr(self, "colorbar"):
                self.colorbar.remove()
        except:
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
        """Gets called when a new cmap is applied.

        Parameters
        ----------
        cmap : Colormap
            The new colormap.
        """
        self.cmap = cmap
        self._plot()

    def _change_norm(self, norm_method: str):
        """Gets called when a new norm is applied.

        Parameters
        ----------
        norm_method : str
            The new norm.
        """
        self.norm_method = norm_method
        self._plot()

    def remove_annotation(self):
        """Removes the hoverbox from the axis"""
        if hasattr(self, "hover_annotation") and self.hover_annotation:
            try:
                self.hover_annotation.remove()
            except:
                self.hover_annotation = None

    def is_mouse_on_figure(self) -> bool:
        """Checks if the mouse is on the figure.

        Returns
        -------
        bool
            True if the mouse is on the figure else False.
        """
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)
        return self.rect().contains(local_pos)

    def remove_on_leave(self):
        """Should run if the mouse has left the figure."""
        if not self.is_mouse_on_figure():
            self.remove_annotation()
            self.ax.figure.canvas.draw_idle()

    def annotation_maker(self, x, y, offset_xy, ha, value):
        self.hover_annotation = self.ax.annotate(
            f"Lineage 1: {self.labels_of_node_real[int(x + 0.5)]}\nLineage 2: {self.labels_of_node_real[int(y + 0.5)]}\nScore: {value:.2f}",
            (x, y),
            xytext=offset_xy,
            textcoords="offset points",
            ha=ha,
            va="bottom",
            bbox=dict(boxstyle="round", fc="black", ec="none", alpha=0.5),
            color="white",
            clip_on=False,
        )

    def print_text(self, pos: tuple[int, int]):
        """Handles the printing of the hoverbox.

        Parameters
        ----------
        pos : tuple[int,int]
            The position of the cursor.
        """
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
        """Stops the timer and calls print text to creazte the hoverbox.

        Parameters
        ----------
        event : Event, optional
        """
        self.timer.stop()
        self.timer = None
        if event is None:
            self.print_text(self.old_xy)

    def _on_hover(self, event):
        """Creates a new timer whenever the mouse moves and resets the plot otherwise it runs _hover_text.

        Parameters
        ----------
        event : mpl._mouse_notification_event
            mpl._mouse_notification_event.
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
        """Removes all labels excepot the ones that were clicked and sends a signal to recolor the dataset.

        Parameters
        ----------
        event : mpl.click_event
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
