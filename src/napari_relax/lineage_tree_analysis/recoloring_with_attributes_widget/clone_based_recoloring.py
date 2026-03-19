import os

import matplotlib.pyplot as plt
import numpy as np
from magicgui import widgets
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from napari.layers import Points
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLabel, QVBoxLayout

from ..._util_classes import (
    LayerCorrectorTreeProducer,
    TooltipButton,
)
from ..._util_classes.custom_colorboxes import (
    MplCompatibleColorCombobox,
)
from ..._utils import _select_correct_layer


class CloneRecoloring(LayerCorrectorTreeProducer):
    def slider_change(self):
        active_layer = _select_correct_layer(self, Points)
        if not active_layer and not self.time_nodes:
            return
        lT = active_layer.metadata["LineageTree"]
        times = list(range(lT.t_b, lT.t_e))
        nb_cells = [len(self.time_nodes[t]) for t in times]
        target_time = self.time_slider.value * (max(times) - min(times)) + (
            min(times)
        )
        if self.time_nodes:
            if active_layer != self.previous_layer:
                self.previous_layer = active_layer
                self.ax.clear()
                self.ax.plot(times, nb_cells)
                y_min, y_max = self.ax.get_ylim()
                (self.pos_line,) = self.ax.plot(
                    [target_time, target_time], [y_min - 1, y_max + 1], "r--"
                )
                self.ax.set_ylim(y_min, y_max)
                self.ax.set_xticks([])
                self.ax.set_yticks([])
            else:
                self.pos_line.set_xdata([target_time, target_time])

            self.ax.set_xlabel(f"time [{int(np.round(target_time)):03d}]")
            self.ax.set_ylabel(
                "#cells",
                rotation=0,
                va="bottom",
                ha="right",
            )
            self.ax.set_title(
                f"Number of cells \n({len(self.time_nodes.get(np.round(target_time), {})):04d})",
            )
        self.fig.canvas.draw()

    def color_clones(self, *args, **kwargs):
        active_layer = _select_correct_layer(self, Points)
        if not active_layer or not self.time_nodes:
            return
        lT = active_layer.metadata["LineageTree"]
        min_t = lT.t_b
        max_t = lT.t_e
        starting_time = np.round(self.time_slider.value * (max_t - min_t))
        if starting_time < min_t:
            starting_time = min_t
        colors = np.zeros((active_layer.data.shape[0], 4))
        cmap = self.combobox.get_cmap()
        if active_layer.face_color_mode != "direct":
            active_layer.face_color_mode = "direct"
        for i, c in enumerate(self.time_nodes[starting_time]):
            color = cmap(i / len(self.time_nodes[starting_time]))
            for ci in lT.get_subtree_nodes(c):
                colors[active_layer.metadata["lT2napari"][ci]] = color
        active_layer.face_color = colors

    def layer_change(self):
        self.lT = self.get_lT()
        if self.lT:
            self.time_nodes = self.lT.time_nodes
            self.previous_layer = None
            self.slider_change()
        else:
            self.time_nodes = None

    def reset_colors(self):
        active_layer = _select_correct_layer(self, Points)
        if active_layer is not None:
            active_layer.face_color = active_layer.metadata["clone2"]

    def create_layout(self):
        """Creates the layout for this widget."""
        self.fig, self.ax = plt.subplots(figsize=(2, 5))
        self.previous_layer = None
        self.qualitative_cmaps = [
            "Pastel1",
            "Pastel2",
            "Paired",
            "Accent",
            "Dark2",
            "Set1",
            "Set2",
            "Set3",
            "tab10",
            "tab20",
            "tab20b",
            "tab20c",
        ]
        self.time_slider = widgets.FloatSlider(value=0, max=1, step=0.01)
        self.time_slider.changed.connect(self.slider_change)
        fig_canvas = FigureCanvas(self.fig)
        fig_canvas.native = fig_canvas
        fig_canvas.name = ""
        container = widgets.Container(
            widgets=[
                fig_canvas,
                self.time_slider,
            ],
            labels=False,
        )

        recolor_text = widgets.Label(value="Color map:")
        self.combobox = MplCompatibleColorCombobox(self)
        self.cmap_choice = self.combobox.combobox_continuous
        self.combobox.native = self.combobox
        cmap = widgets.Container(
            widgets=[
                recolor_text,
                self.combobox,
            ],
            labels=False,
            layout="horizontal",
        )
        do_color = widgets.Button(text="Recolor Clones")
        reset_colors = widgets.Button(text="Reset Coloring")
        reset_colors.clicked.connect(self.reset_colors)
        recoloring_cont = widgets.Container(
            widgets=[do_color, reset_colors], layout="horizontal"
        )
        w2 = widgets.Container(
            widgets=[
                cmap,
                recoloring_cont,
            ],
            labels=False,
            layout="vertical",
        )
        do_color.clicked.connect(self.color_clones)
        self.viewer.layers.selection.events.connect(self.layer_change)
        self.distance_layout = QVBoxLayout()
        self.distance_layout.addWidget(
            QLabel(
                """<span style="font-family: Arial; font-size: 20px; color: white;">Population Graph</span>"""
            ),
            alignment=Qt.AlignHCenter,
        )
        self.distance_layout.addWidget(container.native)
        self.distance_layout.addWidget(w2.native)
        self.distance_layout.addStretch(1)

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)
        self.viewer = napari_viewer
        self.lT = self.get_lT()
        if self.lT:
            self.time_nodes = self.lT.time_nodes
        else:
            self.time_nodes = None
        self.create_layout()
        self.setLayout(self.distance_layout)

        self.slider_change()

        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(
            os.path.join(current_dir, "clone_recolor.html"),
            encoding="utf-8",
        ) as f:
            txt = f.read()
        self.clone_tooltip = TooltipButton(txt)
        self.clone_tooltip.setParent(self)
        self.clone_tooltip.move(
            self.width() - self.clone_tooltip.width(),
            0,
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.clone_tooltip.move(self.width() - self.clone_tooltip.width(), 0)
