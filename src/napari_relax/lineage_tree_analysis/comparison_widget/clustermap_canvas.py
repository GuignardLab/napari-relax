import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from psygnal import Signal
from qtpy.QtWidgets import QWidget
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform
from matplotlib.offsetbox import TextArea, AnnotationBbox


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
        self.timer = None
        self.old_xy = None

    def clear_data(self):
        self.comps = None
        self.norms = None
        self.names = None
        self.time = None
        self.lT = None
        self.labels = None
        self.ax.cla()

    def _receive_data(
        self, comps=None, norms=None, names=None, time=None, lT=None
    ):
        self.comps = comps
        self.norms = norms
        self.names = names
        self.time = time
        self.lT = lT
        self.labels = self.lT.labels
        self._plot()

    def _plot(self):
        """
        Plots the clustermap for the timepoint specified by the time slider, where each element is the pairwise comparison of all the sublineages present in
        the timepoint selected.
        """
        if hasattr(self, "colorbar"):
            self.colorbar.remove()
        self.ax.cla()
        if not hasattr(self, "comps"):
            return
        comparisons = self.comps
        names = self.names
        self.range = len(comparisons)
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
            ] / self.norm_dict[self.norm_method](
                self.norms[keys, values]
            )
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

    def _change_cmap(self,cmap):
        self.cmap = cmap
        self._plot()

    def _change_norm(self, norm_method):
        self.norm_method = norm_method
        self._plot()

    def remove_annotation(self):
        if hasattr(self, "hover_annotation") and self.hover_annotation:
            try:
                self.hover_annotation.remove()
            except:
                self.hover_annotation = None

    def print_text(self, pos):
        self.remove_annotation()
        x, y = pos
        y_lim = self.ax.get_ylim()
        x_lim = self.ax.get_xlim()
        y_flip = "top" if (y<((y_lim[1]-y_lim[0])/4)) else "bottom"
        x_flip ="right" if (x<((x_lim[1]-x_lim[0])/4)) else "left"
        value =self.plot[int(x + 0.5),int(y + 0.5)]
        self.hover_annotation = self.ax.annotate(
            f"Lineage 1={self.labels_of_node_real[int(x + 0.5)]}\nLineage 2={self.labels_of_node_real[int(y + 0.5)]}\nScore: {value:.2f}",
            (x, y),
            xytext=(-10,-40),#(x_flip*5, y_flip*5),
            textcoords="offset points",
            ha="right",
            va="bottom",
            bbox=dict(
                boxstyle="round",
                fc="black",      # background color
                ec="none",       # no border
                alpha=0.5        # transparency (0=transparent, 1=opaque)
            ),
            color="white",
            clip_on= False
        )
        self.hover_annotation.set_clip_on(False)
        self.ax.figure.canvas.draw_idle()

    def _hover_text(self, event=None):
        print(event)
        self.timer.stop()
        self.timer = None
        if event is None:
            self.print_text(self.old_xy)

    def _on_hover(self,event):
        pos =  (event.xdata, event.ydata)
        self.remove_annotation()
        self.ax.figure.canvas.draw_idle()

        if event.inaxes and pos != self.old_xy:
            self.old_xy = pos
            self.timer = self.new_timer(200)
            self.timer.add_callback(self._hover_text)
            self.timer.start()
        else:
            self.timer = None

    def _click(self, event):
        if event.button == 1 and event  .inaxes:
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
            np.arange(len(self.labels_of_node_real)), labels=self.labels_of_node_real
        )
            self.ax.set_yticks(
                np.arange(len(self.labels_of_node_real)), labels=self.labels_of_node_real
            )
            self.ax.tick_params(axis="both", labelsize=10)
            plt.setp(
                self.ax.get_xticklabels(),
                rotation=45,
                ha="right",
                rotation_mode="anchor",
            )
            self.draw()

