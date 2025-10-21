from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.cm as cm
import matplotlib.pyplot as plt
import mplcursors
import numpy as np
from magicgui import widgets
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from matplotlib.figure import Figure
from qtpy.QtWidgets import (
    QPushButton,
    QVBoxLayout,
)
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

from napari_relax._util_classes.custom_colorboxes.mpl_compatible_combobox import (
    MplCompatibleColorCombobox,
)

from .._reader import layer_preparation
from .._util_classes import (
    Containerize,
    LayerCorrectorTreeProducer,
    TooltipButton,
)

if TYPE_CHECKING:
    from napari.components.viewer_model import ViewerModel

DICT_OF_CMAPS: list[str] = [
    "viridis",
    "plasma",
    "inferno",
    "magma",
    "cividis",
    "Greys",
    "Purples",
    "Blues",
    "Greens",
    "Oranges",
    "Reds",
    "YlOrBr",
    "YlOrRd",
    "OrRd",
    "PuRd",
    "RdPu",
    "BuPu",
    "GnBu",
    "PuBu",
    "YlGnBu",
    "PuBuGn",
    "BuGn",
    "YlGn",
]


class CrossClustermap(LayerCorrectorTreeProducer):
    name = "clustermap"

    def get_lt_manager(self, signal):
        """
        Gets the lineagetree manager object every time is
        changed Manager class.
        """
        self.manager = signal

    def add_spot_on_graph(self, cell, index, lineagetree_name):
        """Adds a spot on the graph on the correct place if it does not exist on the graph.

        Args:
            cell (int): The if of the cell
            index (int): Index of the list of networkx graphs
            lineagetree_name (str): The name of the lineagetree on the layers and self.manager
        """
        lt = self.manager.lineagetrees[lineagetree_name]
        graph = self.layers[lineagetree_name].metadata["graphs"][0][index]
        pos = self.layers[lineagetree_name].metadata["graphs"][1][index]

        if cell not in graph:
            prev = lt.get_predecessors(cell)[0]
            after = lt.get_successors(cell)[-1]
            graph.remove_edge(prev, after)
            graph.add_node(cell)
            graph.add_edge(prev, cell)
            graph.add_edge(cell, after)
            vector = np.array(pos[list(graph.pred[cell])[0]])
            pos[cell] = vector - [0, len(lt.get_predecessors(cell))]

    def paint_sublineage(self, cell, index, color, lineagetree_name):
        if isinstance(color, int):
            color = "magenta" if color == 0 else "cyan"
        color_map = []
        active_layer = self.layers[lineagetree_name]
        lT = self.manager.lineagetrees[lineagetree_name]
        sub_tree = set(lT.get_subtree_nodes(cell))
        for cell1 in active_layer.metadata["graphs"][0][index]:
            if cell1 in sub_tree:
                color_map.append(color)
            else:
                color_map.append("black")
        return color_map

    def reset_graph(self, cell, index, lineagetree_name):
        layer = self.layers[lineagetree_name]
        lt = layer.metadata["LineageTree"]
        if cell in layer.metadata["graphs"][0][index]:
            prev, after = (
                lt.get_node_chain(cell)[0],
                lt.get_node_chain(cell)[-1],
            )
            layer.metadata["graphs"][0][index].remove_node(cell)
            layer.metadata["graphs"][0][index].add_edge(prev, after)

    def tree_painter(self, node, lineagetree_name, color, ax):
        """Paints the correct sublineage on the tree graph

        Args:
            node (int): The name of the first node of the sub/-lineage
            lineagetree_name (str): The name of the lineagetree saved in the manager and the layers.
            color (list|color): The color the tree has to be painted.
            ax (ax object): Matplotlib object where the tree will be graphed.
        """
        lT = self.manager.lineagetrees[lineagetree_name]
        index = LayerCorrectorTreeProducer(self.viewer).val_finder(
            node, lT, self.layers[lineagetree_name].metadata["graphs"][0]
        )
        ax.clear()
        lT.draw_tree_graph(
            self.layers[lineagetree_name].metadata["graphs"][1][index],
            self.layers[lineagetree_name].metadata["graphs"][0][index],
            selected_nodes=lT.get_subtree_nodes(node),
            selected_edges=lT.get_subtree_nodes(node),
            color_of_nodes=color,
            color_of_edges=color,
            ax=ax,
        )
        self.tree_canvas.draw()

    def sub_points_painter(self, node, lineagetree_name, viewer, color):
        """
        Adds all descendants of a cell to selected_data.
        Reads the selected data from napari.layer and it will select all the cells that are ancestors of this point.
        """
        existing = [
            layer.metadata.get("name_for_manager")
            for layer in self.viewer.layers
        ]
        if lineagetree_name not in existing:
            data = layer_preparation(
                self.manager.lineagetrees[lineagetree_name],
                path=lineagetree_name + ".lT",
                from_cross=True,
            )[0]
            data[1]["metadata"]["name_for_manager"] = lineagetree_name
            self.viewer.add_points(data[0], **data[1])
        viewer.layers.clear()
        viewer.dims.ndisplay = 3
        data = layer_preparation(
            self.manager.lineagetrees[lineagetree_name],
            path=lineagetree_name + ".lT",
            from_cross=True,
        )[0]
        data[1]["metadata"]["name_for_manager"] = lineagetree_name
        viewer.add_points(data[0], **data[1])
        for layer in viewer.layers:
            layer.face_color = "white"
        self.layers = {
            layer.metadata.get("name_for_manager", ""): layer
            for layer in self.viewer.layers
        }
        self.viewer.layers.selection.active = self.layers[lineagetree_name]
        active_layer = viewer.layers.selection.active
        lT = active_layer.metadata["LineageTree"]
        active_layer.selected_data.add(
            active_layer.metadata["lT2napari"][node]
        )
        scores = lT.get_subtree_nodes(node)
        for val in scores:
            active_layer.selected_data.add(
                active_layer.metadata["lT2napari"][val]
            )
        active_layer.face_color[list(active_layer.selected_data)] = color
        active_layer.selected_data.clear()
        active_layer.refresh()

    def _click(self, event):
        if event.button == 1:
            self.canvas.figure.set_constrained_layout(False)
            layers = [
                self.labels_lT[int(event.xdata + 0.5)],
                self.labels_lT[int(event.ydata + 0.5)],
            ]
            nodes = [
                self.labels_node[int(event.xdata + 0.5)],
                self.labels_node[int(event.ydata + 0.5)],
            ]
            colors = [[1, 128 / 255, 1, 1], [0, 1, 1, 1]]
            for i, (node, lT) in enumerate(zip(nodes, layers, strict=False)):
                self.sub_points_painter(node, lT, self.viewers[i], colors[i])
                self.tree_painter(node, lT, colors[i], self.axes[i])
            label1 = [""] * len(self.labels_of_clustermap)
            label1[int(event.xdata + 0.5)] = self.labels_of_clustermap[
                int(event.xdata + 0.5)
            ]
            label2 = [""] * len(self.labels_of_clustermap)
            label2[int(event.ydata + 0.5)] = self.labels_of_clustermap[
                int(event.ydata + 0.5)
            ]
            self.ax1.set_xticks(np.arange(len(label1)), labels=label1)
            self.ax1.set_yticks(np.arange(len(label1)), labels=label2)
            self.ax1.tick_params(axis="x", colors="magenta")
            self.ax1.tick_params(axis="y", colors="cyan")
            plt.setp(
                self.ax1.get_xticklabels(),
                rotation=45,
                ha="center",
            )
            self.canvas.draw()

    def clustermap_creator(self):
        plt.close("all")
        time = int(self.time_slider.value)
        self.canvas.figure.set_constrained_layout(True)
        self.range = len(self.comparisons)

        len_all_trees = len(self.names[time].keys())
        hierarchy = np.zeros((len_all_trees, len_all_trees))
        self.labels_lT = [self.names[time][n][0] for n in self.names[time]]
        self.labels_root = [self.names[time][n][2] for n in self.names[time]]
        self.labels_node = [self.names[time][n][1] for n in self.names[time]]
        self.labels = [
            self.manager.lineagetrees[self.names[time][n][0]].labels[
                self.manager.lineagetrees[
                    self.names[time][n][0]
                ].get_labelled_ancestor(self.names[time][n][1])
            ]
            for n in self.names[time]
        ]
        self.labels_of_clustermap = [
            self.names[time][n][0] + "_" + str(self.labels[n])
            for n in self.names[time]
        ]
        for keys, values in self.comparisons[time]:
            hierarchy[keys, values] = self.comparisons[time][
                keys, values
            ] / self.norm_dict[str(self.norm_combo.value)](
                self.norms[time][keys, values]
            )
            hierarchy[values, keys] = hierarchy[keys, values]

        condensed_dist_matrix = squareform(hierarchy)

        linkage_data = linkage(condensed_dist_matrix, method="ward")
        order = dendrogram(linkage_data, no_plot=True)["leaves"]
        self.labels_of_clustermap = [
            self.labels_of_clustermap[i] for i in order
        ]
        self.labels_lT = [self.labels_lT[i] for i in order]
        self.labels_node = [self.labels_node[i] for i in order]
        self.labels_root = [self.labels_root[i] for i in order]

        self.plot = hierarchy[np.ix_(order, order)]
        plot = self.ax1.imshow(self.plot, cmap=self.colormap.get_cmap())
        if self.colorbar:
            self.colorbar.remove()
        self.colorbar = self.figure.colorbar(plot, ax=self.ax1)
        self.ax1.set_xticks(
            np.arange(len(self.labels_of_clustermap)),
            labels=self.labels_of_clustermap,
        )
        self.ax1.set_yticks(
            np.arange(len(self.labels_of_clustermap)),
            labels=self.labels_of_clustermap,
        )
        plt.setp(
            self.ax1.get_xticklabels(),
            rotation=45,
            ha="right",
        )
        self.ax1.set_aspect("auto")
        cursor = mplcursors.cursor(
            self.ax1,
            hover=2,  # Transient
            annotation_kwargs={
                "bbox": {
                    "boxstyle": "square,pad=0.2",
                    "facecolor": "white",
                    "alpha": 0.2,
                    "edgecolor": "#ddd",
                    "linewidth": 0.3,
                },
                "linespacing": 1,
                "arrowprops": None,
            },
        )
        cursor.connect(
            "add",
            lambda sel: sel.annotation.set_text(
                f"Value: {str(np.round(self.plot[[sel.index][0]],2))}\nNodes: {self.labels_of_clustermap[[sel.index][0][0]]} ,({self.labels_node[[sel.index][0][0]]}, Time: {self.manager.lineagetrees[self.labels_lT[[sel.index][0][0]]].time[self.labels_node[[sel.index][0][0]]]}) \nvs\n{self.labels_of_clustermap[[sel.index][0][1]]}({self.labels_node[[sel.index][0][1]]}, Time: {self.manager.lineagetrees[self.labels_lT[[sel.index][0][1]]].time[self.labels_node[[sel.index][0][1]]]})"
            ),
        )
        self.canvas.draw()

    def save_dictionary(self):
        roots = {}
        times = {}
        end_times = {}
        for tab in self.tab_dictionary:
            roots[tab] = self.tab_dictionary[tab].show_roots()
            times[tab] = self.tab_dictionary[tab].ret_times()
            end_times[tab] = self.tab_dictionary[tab].time_crop

        data = {
            "roots": roots,
            "times": times,
            "end_times": end_times,
            "comparisons": self.comparisons,
            "norms": self.norms,
            "names": self.names,
        }
        with open(str(self.save_pkl.value), "wb") as f:
            pickle.dump(data, f)

    def time_changer(self):
        self.time = self.time_slider.value
        self.clustermap_creator()

    def __init__(self, napari_viewer, dataset_viewers: list[ViewerModel]):
        super().__init__(napari_viewer)
        self.viewers = dataset_viewers
        self.colormap = MplCompatibleColorCombobox(
            self,
            {i: cm.get_cmap(i) for i in DICT_OF_CMAPS},
        )
        self.norm_combo = widgets.ComboBox(
            value="max",
            choices=["max", "sum", "None"],
        )
        self.norm_dict = {"max": max, "sum": sum, "None": lambda x: 1}

        self.figures, self.axes = plt.subplots(
            nrows=1, ncols=2, figsize=(4, 3), sharey=True
        )
        for ax in self.axes:
            ax.axis("off")
        self.tree_canvas = FigureCanvas(self.figures)
        self.time_mover = widgets.Checkbox(value=False)
        time_mover_text = widgets.Label(value="Move in time")
        self.time_mover_box = widgets.Container(
            widgets=[time_mover_text, self.time_mover],
            layout="horizontal",
            labels=False,
        )
        self.range = 0
        self.time_slider = widgets.IntSlider(min=0, max=self.range)
        self.time_slider.changed.connect(self.time_changer)
        layout = QVBoxLayout()
        layout.addStretch(1)
        self.setLayout(layout)
        self.figure = Figure(constrained_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.colorbar = None
        self.ax1 = self.figure.add_subplot(111)
        layout.addSpacing(50)
        self.layout().addWidget(self.tree_canvas)

        self.layout().addWidget(
            Containerize([self.norm_combo.native, self.colormap])
        )
        self.norm_combo.changed.connect(self.clustermap_creator)
        self.colormap.combobox_continuous.currentIndexChanged.connect(
            self.clustermap_creator
        )
        self.layout().addWidget(self.time_mover_box.native)
        self.layout().addWidget(self.canvas)
        self.layout().addWidget(self.time_slider.native)

        self.figure.canvas.mpl_connect("button_press_event", self._click)
        self.save_pkl = widgets.FileEdit(
            mode="w", value=Path(".").absolute(), filter="*.pkl*"
        )
        self.save_button = QPushButton("Save Comparisons")
        self.save_button.native = self.save_button
        self.save_button.name = "save_button"
        self.save_button.pressed.connect(self.save_dictionary)
        container = widgets.Container(
            widgets=[self.save_pkl, self.save_button],
            layout="horizontal",
            labels=False,
        )
        self.layout().addWidget(container.native)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(
            os.path.join(current_dir, "cross_comparison.html"),
            encoding="utf-8",
        ) as f:
            txt = f.read()
        self.node_tooltip = TooltipButton(txt)
        self.node_tooltip.setParent(self)
        self.node_tooltip.move(self.width() - self.node_tooltip.width(), 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.node_tooltip.move(self.width() - self.node_tooltip.width(), 0)
