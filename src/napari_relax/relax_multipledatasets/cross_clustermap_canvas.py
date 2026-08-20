
import matplotlib.pyplot as plt
import numpy as np
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

from ..lineage_tree_analysis.comparison_widget.clustermap_canvas import (
    ClusterMapCanvas,
)


class CrossClusterMapCanvas(ClusterMapCanvas):
    def clear_data(self):
        self.manager = None
        return super().clear_data()

    def _receive_data(self, comps=None, norms=None, names=None, manager=None):
        self.manager = manager
        self.comps = comps
        self.norms = norms
        self.names = names
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
        len_all_trees = len(self.names.keys())
        hierarchy = np.zeros((len_all_trees, len_all_trees))
        self.names_of_nodes = [
            self.names[n][0] for n in self.names
        ]  # lineagetrees
        self.labels_root = [self.names[n][2] for n in self.names]
        self.labels_node = [self.names[n][1] for n in self.names]
        self.labels = [
            self.manager.lineagetrees[self.names[n][0]].labels[
                self.manager.lineagetrees[
                    self.names[n][0]
                ].get_labelled_ancestor(self.names[n][1])
            ]
            for n in self.names
        ]

        self.labels_of_clustermap = [
            self.names[n][0] + "_" + str(self.labels[n]) for n in self.names
        ]  # the resulting labels
        self.labels_of_node_real = self.labels_of_clustermap
        for keys, values in self.comps:
            hierarchy[keys, values] = self.comps[
                keys, values
            ] / self.norm_dict[self.norm_method](self.norms[keys, values])
            hierarchy[values, keys] = hierarchy[keys, values]

        condensed_dist_matrix = squareform(hierarchy)

        linkage_data = linkage(condensed_dist_matrix, method="ward")
        order = dendrogram(linkage_data, no_plot=True)["leaves"]
        self.labels_of_clustermap = [
            self.labels_of_clustermap[i] for i in order
        ]
        self.names_of_nodes = [self.names_of_nodes[i] for i in order]
        self.labels_node = [self.labels_node[i] for i in order]
        self.labels_root = [self.labels_root[i] for i in order]

        self.plot = hierarchy[np.ix_(order, order)]
        plot = self.ax.imshow(self.plot, cmap=self.cmap)
        self.colorbar = self.figure.colorbar(plot, ax=self.ax)
        self.ax.set_xticks(
            np.arange(len(self.labels_of_clustermap)),
            labels=self.labels_of_clustermap,
        )
        self.ax.set_yticks(
            np.arange(len(self.labels_of_clustermap)),
            labels=self.labels_of_clustermap,
        )
        plt.setp(
            self.ax.get_xticklabels(),
            rotation=45,
            ha="right",
        )
        self.ax.set_aspect("auto")
        self.draw()

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

    def _click(self, event):
        if event.button == 1 and event.inaxes:
            self.mpl_disconnect(self._click)
            layers = [
                self.names_of_nodes[int(event.xdata + 0.5)],
                self.names_of_nodes[int(event.ydata + 0.5)],
            ]
            nodes = [
                self.labels_node[int(event.xdata + 0.5)],
                self.labels_node[int(event.ydata + 0.5)],
            ]
            self.click_signal.emit([layers, nodes])
            label1 = [""] * len(self.labels_of_clustermap)
            label1[int(event.xdata + 0.5)] = self.labels_of_clustermap[
                int(event.xdata + 0.5)
            ]
            label2 = [""] * len(self.labels_of_clustermap)
            label2[int(event.ydata + 0.5)] = self.labels_of_clustermap[
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
                np.arange(len(self.labels_of_clustermap)),
                labels=self.labels_of_clustermap,
            )
            self.ax.set_yticks(
                np.arange(len(self.labels_of_clustermap)),
                labels=self.labels_of_clustermap,
            )
            self.ax.tick_params(axis="both", labelsize=10)
            plt.setp(
                self.ax.get_xticklabels(),
                rotation=45,
                ha="right",
                rotation_mode="anchor",
            )
            self.draw()
