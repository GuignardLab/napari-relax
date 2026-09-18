"""Clustermap tab of the Distance Calculation."""

import os
import pickle
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
from magicgui import widgets
from matplotlib import colormaps
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from qtpy.QtWidgets import QLineEdit, QPushButton, QVBoxLayout

from ..._util_classes import (
    Containerize,
    LayerCorrectorTreeProducer,
    TooltipButton,
)
from ..._util_classes.custom_colorboxes import MplCompatibleColorCombobox
from ..._utils import _select_active_lt_layer
from .clustermap_canvas import ClusterMapCanvas

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
        """Plot the comparisons of the timepoint selected by the slider."""
        if not hasattr(self, "comps"):
            return
        t = self.time_slider.value
        if isinstance(self.comps, list):
            self.canvas._receive_data(
                self.comps[t], self.norms[t], self.naming[t], t, self.lT
            )
        else:
            self.canvas._receive_data(
                self.comps, self.norms, self.naming, t, self.lT
            )

    def add_spot_on_graph(self, cell, val, color, ax):
        """Draw a cell that is in the middle of a chain on a tree plot.

        Parameters
        ----------
        cell : int
            ID of the cell.
        val : int
            Index of the graph in the list of graphs.
        color : color
            Color of the spot.
        ax : matplotlib.axes.Axes
            Axes of the tree plot.
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

    def _click(self, lineages):
        """Show the two sublineages of a clicked clustermap cell.

        They are drawn on the tree plots and colored in magenta and cyan
        in the viewer, the other cells in white. If "Move in time" is
        ticked, the viewer moves to the first timepoint of the first
        sublineage.

        Parameters
        ----------
        lineages : list of int
            Root IDs of the two compared sublineages.
        """
        active_layer = _select_active_lt_layer(self.viewer)
        if not active_layer:
            return
        colors = [[1, 128 / 255, 1, 1], [0, 1, 1, 1]]
        active_layer.face_color = [1, 1, 1, 1]
        lineages = [lineages[0]] if lineages[0] == lineages[1] else lineages
        for i, cell in enumerate(lineages):
            if len(lineages) < 2:
                self.axes_for_tree_graphs[1].set_visible(False)

            else:
                for ax in self.axes_for_tree_graphs:
                    ax.set_visible(True)
            self.axes_for_tree_graphs[i].clear()

            active_layer.selected_data.add(
                active_layer.metadata["lT2napari"][cell]
            )
            self.sub_points_selector()
            selection = list(active_layer.selected_data)
            active_layer.face_color[selection] = colors[i]
            val_for_graph = self.val_finder(
                cell, lt=self.lT, graphs=active_layer.metadata["graphs"][0]
            )
            self.lT.draw_tree_graph(
                active_layer.metadata["graphs"][1][val_for_graph],
                active_layer.metadata["graphs"][0][val_for_graph],
                selected_nodes=self.lT.get_subtree_nodes(cell),
                selected_edges=self.lT.get_subtree_nodes(cell),
                color_of_nodes=colors[i],
                color_of_edges=colors[i],
                ax=self.axes_for_tree_graphs[i],
            )
            self.add_spot_on_graph(
                cell,
                val=val_for_graph,
                color=colors[i],
                ax=self.axes_for_tree_graphs[i],
            )

            self.tree_canvas.draw()
            active_layer.selected_data.clear()
        active_layer.refresh()
        if self.time_mover.value:
            camera_pan = self.viewer.dims.current_step
            self.viewer.dims.current_step = (
                active_layer.data[
                    active_layer.metadata["lT2napari"][lineages[0]]
                ][0],
            ) + camera_pan[1:]

    def reset_colorer(self):
        """Restore the original colors of the points."""
        active_layer = _select_active_lt_layer(self.viewer)
        if not active_layer:
            return
        active_layer.face_color = active_layer.metadata["default_colors"]
        active_layer.refresh()

    def time_changer(self):
        """Show the clustermap of the timepoint selected by the slider."""
        self.time = self.time_slider.value
        self.send_data()

    def save_dictionary(self):
        """Save the comparisons to the selected ``.pkl`` file.

        The file holds a dict with ``times``, ``comparisons``, ``norms``,
        ``names``, ``end_time`` and ``labels``.
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
        """Update the tab for the LineageTree of the new active layer.

        Parameters
        ----------
        event : napari.utils.events.Event
            The layer selection event; exactly one layer must be selected.
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
        """Redraw the clustermap after a label change."""
        self.labels = self.lT.labels
        self.send_data()

    def __init__(
        self, napari_viewer, configuration: "ConfigurationPanel" = None
    ):
        """Build the tree plots, clustermap and save widgets.

        Parameters
        ----------
        napari_viewer : napari.Viewer
            The napari viewer.
        configuration : ConfigurationPanel, optional
            The configuration tab providing the timepoints.
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
            {i: colormaps.get(i) for i in DICT_OF_CMAPS},
        )
        self.norm_color_cont = Containerize(
            [self.norm_combo.native, self.colormap]
        )
        self.colormap.combobox_continuous.currentIndexChanged.connect(
            lambda x: self.canvas._change_cmap(self.colormap.get_cmap())
        )

        self.norm_combo.changed.connect(
            lambda x: self.canvas._change_norm(self.norm_combo.value)
        )
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
