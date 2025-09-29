import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from magicgui import widgets
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from napari.layers import Points
from qtpy.QtWidgets import (
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..._util_classes import LayerCorrectorTreeProducer
from ..._utils import _select_correct_layer
from .coloring import Coloring


class DisplayDistances(LayerCorrectorTreeProducer):
    name = "Attribute Based Recoloring"

    def slider_change(self):
        active_layer = _select_correct_layer(self, Points)
        if not active_layer and not self.time_nodes:
            return
        lT = active_layer.metadata["LineageTree"]
        times = list(range(lT.t_b, lT.t_e))
        nb_cells = [len(self.time_nodes[t]) for t in times]
        target_time = self.time_slider.value * (max(times) - min(times))
        if self.time_nodes.get(np.round(target_time)):
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

            self.ax.yaxis.set_label_coords(0.05, 1.1)
            self.ax.set_ylabel(
                f"#cells ({len(self.time_nodes.get(np.round(target_time))):04d})",
                rotation=45,
                va="bottom",
                ha="right",
            )
        self.fig.canvas.draw()

    def color_clones(self, *args, **kwargs):
        active_layer = _select_correct_layer(self, Points)
        if not active_layer or not self.time_nodes:
            return
        lT = active_layer.metadata["LineageTree"]
        min_t = lT.t_b
        max_t = lT.t_e
        times = list(range(lT.t_b, lT.t_e))
        nb_cells = np.array([len(self.time_nodes[t]) for t in times])
        last_change = {min_t: min_t}
        last_time_change = min_t
        for t, change in zip(
            times, nb_cells[1:] - nb_cells[:-1], strict=False
        ):
            if change == 0:
                last_change[t] = last_time_change
            else:
                last_change[t] = t
                last_time_change = t

        starting_time = last_change[
            (min_t + np.round(self.time_slider.value * (max_t - min_t)))
        ]
        colors = np.zeros((active_layer.data.shape[0], 4))
        cmap = mpl.colormaps[self.cmap_choice.value]
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
        self.cmap_choice = widgets.ComboBox(
            value="Accent", choices=self.qualitative_cmaps
        )
        cmap = widgets.Container(
            widgets=[
                recolor_text,
                self.cmap_choice,
            ],
            labels=False,
            layout="horizontal",
        )
        self.do_color = widgets.Button(text="Recolor Clones")
        w2 = widgets.Container(
            widgets=[
                cmap,
                self.do_color,
            ],
            labels=False,
            layout="vertical",
        )
        self.do_color.clicked.connect(self.color_clones)
        self.viewer.layers.selection.events.connect(self.layer_change)
        self.distance_layout = QVBoxLayout()
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

        layout = QVBoxLayout()

        tabs = QTabWidget()
        self.create_layout()
        self.clone_based_recoloring = QWidget()
        self.clone_based_recoloring.setLayout(self.distance_layout)
        self.coloring_widget = Coloring(self.viewer)
        tabs.addTab(self.clone_based_recoloring, "Clone base recoloring")
        tabs.addTab(self.coloring_widget, "Attribute based Recoloring")
        layout.addWidget(tabs)
        self.setLayout(layout)
        self.slider_change()
