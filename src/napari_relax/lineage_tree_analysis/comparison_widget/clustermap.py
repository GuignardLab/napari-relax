import os
import pickle
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.cm as cm
import matplotlib.pyplot as plt

import numpy as np
from magicgui import widgets
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from matplotlib.figure import Figure
from qtpy.QtWidgets import QLineEdit, QPushButton, QVBoxLayout, QWidget
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

from ..._util_classes import (
    Containerize,
    LayerCorrectorTreeProducer,
    TooltipButton,
)
from .clustermap_canvas import ClusterMapCanvas
from ..._util_classes.custom_colorboxes import MplCompatibleColorCombobox
from ..._utils import _select_active_lt_layer

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


if TYPE_CHECKING:
    from .config import ConfigurationPanel


class Clustermap(LayerCorrectorTreeProducer):
    """Contains the clustermap and its interactions."""

    name = "Distance Calculation"

    def send_data(self):
        if not hasattr(self, "comps"):
            return
        t= self.time
        self.canvas._receive_data(self.comps[t], self.norms[t], self.naming[t], t, self.lT)

    def add_spot_on_graph(self, cell, val, color, ax):
        """
        Function to add a spot on the networkx graphs, which is in the middle of a
        life cycle of the cell and calculates the correct position of the new cell.

        Args:
        cell (int): id of the cell
        val (int): the index of the list of networkx graphs.
        """
        active_layer = _select_active_lt_layer(self.viewer)
        if not active_layer:
            return
        if cell not in active_layer.metadata["graphs"][1][val]:
            prev = self.lT.get_predecessors(cell)[0]
            prev_cycle = len(self.lT.get_predecessors(cell))
            after = self.lT.get_successors(cell)[-1]
            pos_prev = active_layer.metadata["graphs"][1][val][prev]
            pos_after = active_layer.metadata["graphs"][1][val][after]

            tmp_pos = np.array(pos_prev) - np.array([0, prev_cycle])
            ax.scatter(*tmp_pos, color=color, s=0.2, zorder=1001)
            ax.plot(
                (tmp_pos[0], pos_after[0]),
                (tmp_pos[1], pos_after[1]),
                color=color,
                linewidth=0.4,
                zorder=1000,
            )

    # def _click(self, event):
    #     """
    #     Handles the left click of the clustermap plot. When clicked the corresponding sublineages will be
    #     plotted on the tree graph section and the points will be painted with the same colors while the rest
    #     will be white.
    #     Has a togglable part where the camera is transported to the timepoint of the division.
    #     Args:
    #         event: Button click (Right Click)

    #     """
    #     if event.button == 1 and event.inaxes:
    #         self.figure.canvas.mpl_disconnect(self.click_signal)
    #         active_layer = _select_active_lt_layer(self.viewer)
    #         if not active_layer:
    #             return
    #         self.canvas.figure.set_constrained_layout(False)
    #         active_layer.face_color = "white"
    #         lineages = [
    #             self.names_of_nodes[int(event.xdata + 0.5)],
    #             self.names_of_nodes[int(event.ydata + 0.5)],
    #         ]
    #         label1 = [""] * len(self.labels_of_node_real)
    #         label1[int(event.xdata + 0.5)] = self.labels_of_node_real[
    #             int(event.xdata + 0.5)
    #         ]
    #         label2 = [""] * len(self.labels_of_node_real)
    #         label2[int(event.ydata + 0.5)] = self.labels_of_node_real[
    #             int(event.ydata + 0.5)
    #         ]
    #         self.ax_of_clustermap.set_xticks(
    #             np.arange(len(label1)), labels=label1
    #         )
    #         self.ax_of_clustermap.set_yticks(
    #             np.arange(len(label1)), labels=label2
    #         )
    #         self.ax_of_clustermap.tick_params(axis="x", colors="magenta")
    #         self.ax_of_clustermap.tick_params(axis="y", colors="cyan")
    #         plt.setp(
    #             self.ax_of_clustermap.get_xticklabels(),
    #             rotation=0,
    #             ha="center",
    #         )
    #         self.canvas.draw()
    #         colors = [[1, 128 / 255, 1, 1], [0, 1, 1, 1]]
    #         lineages = (
    #             [lineages[0]] if lineages[0] == lineages[1] else lineages
    #         )
    #         for i, cell in enumerate(lineages):
    #             if len(lineages) < 2:
    #                 self.axes_for_tree_graphs[1].set_visible(False)

    #             else:
    #                 for ax in self.axes_for_tree_graphs:
    #                     ax.set_visible(True)
    #             self.axes_for_tree_graphs[i].clear()

    #             active_layer.selected_data.add(
    #                 active_layer.metadata["lT2napari"][cell]
    #             )
    #             self.sub_points_selector()
    #             selection = list(active_layer.selected_data)
    #             active_layer.face_color[selection] = colors[i]
    #             val_for_graph = self.val_finder(
    #                 cell, lt=self.lT, graphs=active_layer.metadata["graphs"][0]
    #             )
    #             self.lT.draw_tree_graph(
    #                 active_layer.metadata["graphs"][1][val_for_graph],
    #                 active_layer.metadata["graphs"][0][val_for_graph],
    #                 selected_nodes=self.lT.get_subtree_nodes(cell),
    #                 selected_edges=self.lT.get_subtree_nodes(cell),
    #                 color_of_nodes=colors[i],
    #                 color_of_edges=colors[i],
    #                 ax=self.axes_for_tree_graphs[i],
    #             )
    #             self.add_spot_on_graph(
    #                 cell,
    #                 val=val_for_graph,
    #                 color=colors[i],
    #                 ax=self.axes_for_tree_graphs[i],
    #             )

    #             self.tree_canvas.draw()
    #             active_layer.selected_data.clear()
    #         active_layer.refresh()
    #         if self.time_mover.value:
    #             camera_pan = self.viewer.dims.current_step
    #             self.viewer.dims.current_step = (
    #                 active_layer.data[
    #                     active_layer.metadata["lT2napari"][lineages[0]]
    #                 ][0],
    #             ) + camera_pan[1:]
    #         self.click_signal = self.figure.canvas.mpl_connect(
    #             "button_press_event", self._click
    #        )

    def reset_colorer(self):
        """
        Resets colors of points.
        """
        active_layer = _select_active_lt_layer(self.viewer)
        if not active_layer:
            return
        active_layer.face_color = active_layer.metadata["clone2"]
        active_layer.refresh()

    def time_changer(self):
        """
        Called by the time_slider widget, will handle the time change and create the correct clustermap.
        """
        self.time = self.time_slider.value
        self.send_data()

   
    def save_dictionary(self):
        """
        Saves the pairwise comparisons and names locally.
        """
        data = {
            "times": self.times,
            "comparisons": self.comps,
            "norms": self.norms,
            "names": self.naming,
            "end_time": self.crop,
            "labels": self.lT.labels,
        }
        with open(str(self.save_pkl.value), "wb") as f:
            pickle.dump(data, f)

    def layer_change(self, event):
        """Handles the layer change event.

        Args:
            event : The signal of layer change, it's important to note that you need to have one layer selected.
        """
        if event.value:
            self.lT = self.get_lT()
            if self.lT:
                self.labels = self.lT.labels
            self.range = 1
            self.names_of_nodes = None
            self.names_of_roots = None
            self.layout().update()

    def receive_new_labels(self):
        self.labels = self.lT.labels
        self.send_data()

    def __init__(
        self, napari_viewer, configuration: "ConfigurationPanel" = None
    ):
        """
        Build the containers for the loading widget

        Args:
            napari_viewer (napari.Viewer): the parent napari viewer
        """
        super().__init__(napari_viewer)
        if configuration:
            self.configuration = configuration
            self.comps = None
            self.times = self.configuration.times
            self.norms = None
            self.naming = None
        self.viewer = napari_viewer
        self.range = 0
        self.lT = self.get_lT()
        if self.lT:
            self.specific_roots = self.lT.time_nodes[self.lT.t_b]
            self.labels = self.lT.labels
        self.time = 1
        self.crop = None
        self.names_of_nodes = None
        self.names_of_roots = None
        self.time_slider = widgets.IntSlider(min=0, max=self.range)
        self.time_slider.changed.connect(self.time_changer)
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
        self.figure = Figure(constrained_layout=True)
        self.ax_of_clustermap = self.figure.add_subplot(111)
        self.canvas = ClusterMapCanvas(self.figure, self.ax_of_clustermap)
        self.reset_colors = QPushButton("Reset Colors")
        self.norm_combo = widgets.ComboBox(
            value="max",
            choices=["max", "sum", "None"],
        )
        self.norm_dict = {"max": max, "sum": sum, "None": lambda x: 1}
        self.colormap = MplCompatibleColorCombobox(
            self,
            {i: cm.get_cmap(i) for i in DICT_OF_CMAPS},
        )
        self.norm_color_cont = Containerize(
            [self.norm_combo.native, self.colormap]
        )
        self.colormap.combobox_continuous.currentIndexChanged.connect(
            lambda x: self.canvas._change_cmap(self.colormap.get_cmap)
        )

        self.norm_combo.changed.connect( lambda x: self.canvas._change_norm(self.norm_combo.value))
        self.time_mover = widgets.Checkbox(value=False)
        time_mover_text = widgets.Label(value="Move in time")
        self.time_mover_box = widgets.Container(
            widgets=[time_mover_text, self.time_mover],
            layout="horizontal",
            labels=False,
        )
        # For plot tab
        self.figures, self.axes_for_tree_graphs = plt.subplots(
            nrows=1, ncols=2, figsize=(4, 3), sharey=True
        )
        for ax in self.axes_for_tree_graphs:
            ax.axis("off")
        self.figures.set_frameon(False)
        self.figures.subplots_adjust(wspace=0, hspace=0)
        self.tree_canvas = FigureCanvas(self.figures)
        self.time_cropper = QLineEdit(
            placeholderText="Cropping time of the dataset.",
            clearButtonEnabled=True,
        )  # type: ignore

        layout = QVBoxLayout()
        self.setLayout(layout)
        self.layout().setContentsMargins(2, 1, 2, 0)
        self.layout().addWidget(self.tree_canvas)
        self.layout().addWidget(
            Containerize(
                [
                    self.reset_colors,
                    self.time_mover_box.native,
                ]
            )
        )
        self.layout().addWidget(self.norm_color_cont)
        self.layout().addWidget(self.canvas)
        self.layout().addWidget(self.time_slider.native)
        self.layout().addWidget(container.native)

        self.reset_colors.clicked.connect(self.reset_colorer)
        # self.click_signal = self.figure.canvas.mpl_connect(
        #     "button_press_event", self._click
        # )
        self.viewer.layers.selection.events.active.connect(self.layer_change)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(
            os.path.join(current_dir, "clustermap.html"),
            encoding="utf-8",
        ) as f:
            txt = f.read()
        self.node_tooltip = TooltipButton(txt)
        self.node_tooltip.setParent(self)
        self.node_tooltip.move(self.width() - self.node_tooltip.width(), 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.node_tooltip.move(self.width() - self.node_tooltip.width(), 0)
