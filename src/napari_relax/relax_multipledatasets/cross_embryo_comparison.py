"""Plots tab of the Cross Distance Calculation."""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
from magicgui import widgets
from matplotlib import colormaps
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from matplotlib.figure import Figure
from qtpy.QtWidgets import (
    QPushButton,
    QVBoxLayout,
)

from napari_relax._util_classes.custom_colorboxes.mpl_compatible_combobox import (
    MplCompatibleColorCombobox,
)

from .._reader import layer_preparation
from .._util_classes import (
    Containerize,
    LayerCorrectorTreeProducer,
    TooltipButton,
)
from .cross_clustermap_canvas import CrossClusterMapCanvas

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
    """Tree plots, clustermap and save widgets for cross-dataset results.

    Parameters
    ----------
    napari_viewer : napari.Viewer
        The napari viewer.
    dataset_viewers : list of napari.components.ViewerModel
        The two viewers showing the compared datasets.
    """

    name = "clustermap"

    def get_lt_manager(self, signal):
        """Receive the manager whenever it changes.

        Parameters
        ----------
        signal : LineageTreeManager
            The updated manager.
        """
        self.manager = signal

    def send_data(self):
        """Plot the comparisons of the level selected by the slider."""
        if not hasattr(self, "comps"):
            return
        t = self.time_slider.value
        if isinstance(self.comps, list):
            self.canvas._receive_data(
                self.comps[t], self.norms[t], self.names[t], self.manager
            )
        else:
            self.canvas._receive_data(
                self.comps, self.norms, self.names, self.manager
            )

    def add_spot_on_graph(self, cell, index, lineagetree_name):
        """Add a cell to its graph if it is in the middle of a chain.

        Parameters
        ----------
        cell : int
            ID of the cell.
        index : int
            Index of the graph in the list of graphs.
        lineagetree_name : str
            Name of the dataset in the layers and the manager.
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
        """Return the node colors of a graph with a sublineage highlighted.

        Parameters
        ----------
        cell : int
            Root of the sublineage.
        index : int
            Index of the graph in the list of graphs.
        color : int or color
            Highlight color; 0 means magenta and 1 cyan.
        lineagetree_name : str
            Name of the dataset in the layers and the manager.

        Returns
        -------
        list
            Color of each node of the graph; other nodes are black.
        """
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
        """Remove a cell added by `add_spot_on_graph` from its graph.

        Parameters
        ----------
        cell : int
            ID of the cell.
        index : int
            Index of the graph in the list of graphs.
        lineagetree_name : str
            Name of the dataset in the layers and the manager.
        """
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
        """Draw a lineage with a sublineage highlighted on a tree plot.

        Parameters
        ----------
        node : int
            The first node of the sublineage.
        lineagetree_name : str
            Name of the dataset in the manager and the layers.
        color : color
            Color of the sublineage.
        ax : matplotlib.axes.Axes
            Axes of the tree plot.
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
        """Show a dataset in a dataset viewer with a sublineage colored.

        Parameters
        ----------
        node : int
            The first node of the sublineage.
        lineagetree_name : str
            Name of the dataset in the manager and the layers.
        viewer : napari.components.ViewerModel
            The dataset viewer to draw in.
        color : color
            Color of the sublineage; other cells are white.
        """
        existing = [
            layer.metadata.get("name_for_manager")
            for layer in self.viewer.layers
        ]
        if lineagetree_name not in existing:
            data = layer_preparation(
                self.manager.lineagetrees[lineagetree_name],
                lineagetree_name + ".lT",
                no_graph=True,
                parameters={"scaling": False},
            )[0]
            data[1]["metadata"]["name_for_manager"] = lineagetree_name
            self.viewer.add_points(data[0], **data[1])
        viewer.layers.clear()
        viewer.dims.ndisplay = 3
        data = layer_preparation(
            self.manager.lineagetrees[lineagetree_name],
            lineagetree_name + ".lT",
            no_graph=True,
            parameters={"scaling": False},
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

    def _click(self, layers_nodes):
        layers, nodes = layers_nodes
        colors = [[1, 128 / 255, 1, 1], [0, 1, 1, 1]]
        for i, (node, lT) in enumerate(zip(nodes, layers, strict=False)):
            self.sub_points_painter(node, lT, self.viewers[i], colors[i])
            self.tree_painter(node, lT, colors[i], self.axes[i])

    def save_dictionary(self):
        """Save the comparisons and the manager to the selected ``.pkl`` file."""
        for _, lT in self.manager:
            if hasattr(lT, "_protected_predecessor"):
                del lT._protected_predecessor
            if hasattr(lT, "_protected_successor"):
                del lT._protected_successor
            if hasattr(lT, "_protected_time"):
                del lT._protected_time

        data = {
            "comparisons": self.comps,
            "norms": self.norms,
            "names": self.names,
            "ltm": self.manager,
        }
        with open(str(self.save_pkl.value), "wb") as f:
            pickle.dump(data, f)

    def time_changer(self):
        """Show the clustermap of the level selected by the slider."""
        self.time = self.time_slider.value
        self.send_data()

    def __init__(self, napari_viewer, dataset_viewers: list[ViewerModel]):
        super().__init__(napari_viewer)
        self.viewers = dataset_viewers
        self.colormap = MplCompatibleColorCombobox(
            self,
            {i: colormaps.get(i) for i in DICT_OF_CMAPS},
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
        self.ax1 = self.figure.add_subplot(111)
        self.canvas = CrossClusterMapCanvas(self.figure, self.ax1)
        layout.addSpacing(50)
        self.layout().addWidget(self.tree_canvas)

        self.layout().addWidget(
            Containerize([self.norm_combo.native, self.colormap])
        )
        self.norm_combo.changed.connect(
            lambda x: self.canvas._change_norm(self.norm_combo.value)
        )
        self.colormap.combobox_continuous.currentIndexChanged.connect(
            lambda x: self.canvas._change_cmap(self.colormap.get_cmap())
        )
        self.layout().addWidget(self.time_mover_box.native)
        self.layout().addWidget(self.canvas)
        self.layout().addWidget(self.time_slider.native)

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
        self.canvas.click_signal.connect(self._click)

    def resizeEvent(self, event):
        """Keep the help button in the top right corner.

        Parameters
        ----------
        event : QResizeEvent
            The resize event.
        """
        super().resizeEvent(event)
        self.node_tooltip.move(self.width() - self.node_tooltip.width(), 0)
