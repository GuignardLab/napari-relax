import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from magicgui import widgets
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from scipy.spatial import KDTree
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget

from ..._util_classes import LayerCorrectorTreeProducer
from ..._utils import _select_active_lt_layer
from .coloring import Coloring


class DisplayDistances(LayerCorrectorTreeProducer):
    name = "Attribute Based Recoloring"

    def point_click(self, viewer, event):
        active_layer = _select_active_lt_layer(self.viewer)

        # Check if we found a valid active layer
        if active_layer is None:
            return

        # Get LineageTree from active layer or its linked layer
        lineage_tree = None
        if "LineageTree" in active_layer.metadata:
            lineage_tree = active_layer.metadata["LineageTree"]
        elif "link" in active_layer.metadata and hasattr(
            active_layer.metadata["link"], "metadata"
        ):
            linked_metadata = active_layer.metadata["link"].metadata
            if "LineageTree" in linked_metadata:
                lineage_tree = linked_metadata["LineageTree"]

        if (
            event.button == 2
            and "Shift" not in event.modifiers
            and "Control" in event.modifiers
            and lineage_tree is not None
            and active_layer
        ):
            current_position = event.position
            time = int(current_position[0])
            lT = lineage_tree
            near_point, far_point = active_layer.get_ray_intersections(
                np.array(event.position),
                event.view_direction,
                np.array(event.dims_displayed),
            )
            if (near_point is not None) and (far_point is not None):
                ray_points = (
                    np.linspace(near_point, far_point, 1000, endpoint=True)
                    # and self.time_nodes
                )
                indexes_of_slice = np.where(active_layer.data[:, 0] == time)
                data_in_slice = active_layer.data[indexes_of_slice][:, 1:]
                kdtree = KDTree(data_in_slice)
                dists, idx = kdtree.query(ray_points[:, 1:])
                cell = active_layer.metadata["napari2lT"][
                    indexes_of_slice[0][idx[np.argmin(dists)]]
                ]
                min_t = lT.t_b
                max_t = lT.t_e
                times = sorted(set(lT.time.values()))
                nb_cells = np.array([len(lT.time_nodes[t]) for t in times])
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
                    (np.round(self.time_slider.value * (max_t - min_t)))
                ]

                sub_trees = [
                    lT.get_subtree_nodes(c)
                    for c in self.time_nodes[starting_time]
                ]
                starting_cell = [
                    track[0] for track in sub_trees if cell in track
                ]
                if len(starting_cell) != 1:
                    return
                else:
                    starting_cell = starting_cell[0]

                dists = lT.unordered_tree_edit_distances_at_time_t(
                    starting_time
                )
                new_colors = np.zeros_like(active_layer.properties["clone"])
                lT2napari = active_layer.metadata["lT2napari"]
                max_D = max(dists.values())
                for tree in sub_trees:
                    start_tree = tree[0]
                    ordered = tuple(sorted((start_tree, starting_cell)))
                    D = (
                        0
                        if start_tree == starting_cell
                        else dists.get(ordered, max_D)
                    )
                    for c in tree:
                        new_colors[lT2napari[c]] = D

                baseline = np.min(new_colors[new_colors != 0]) / 2
                min_, max_ = np.percentile(
                    new_colors[new_colors != 0], 5
                ), np.percentile(new_colors[new_colors != 0], 95)
                new_colors[new_colors == 0] = baseline
                new_colors = 0.5 + (new_colors - min_) / (2 * (max_ - min_))
                if not self.change_size.value:
                    active_layer.properties["clone"][:] = new_colors[:]
                    active_layer.face_color = "clone"

                    if active_layer.face_color_mode != "colormap":
                        active_layer.face_color_mode = "colormap"
                else:
                    new_colors = 1 - new_colors
                    if isinstance(active_layer.size, np.ndarray):
                        active_layer.size = new_colors * 100
                    else:
                        active_layer.size = new_colors * active_layer.size

                active_layer.refresh()

    def slider_change(self):
        active_layer = _select_active_lt_layer(self.viewer)
        if not active_layer and not self.time_nodes:
            return
        lT = active_layer.metadata["LineageTree"]
        times = list(range(lT.t_b, lT.t_e))
        nb_cells = [len(self.time_nodes[t]) for t in times]
        target_time = self.time_slider.value * (max(times) - min(times)) + (
            min(times) / (max(times) - min(times))
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
        active_layer = _select_active_lt_layer(self.viewer)
        if not active_layer or not self.time_nodes:
            return
        lT = active_layer.metadata["LineageTree"]
        min_t = lT.t_b
        max_t = lT.t_e
        starting_time = np.round(self.time_slider.value * (max_t - min_t))
        if starting_time < min_t:
            starting_time = min_t
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

        layout = QVBoxLayout()

        tabs = QTabWidget()
        self.create_layout()
        self.clone_based_recoloring = QWidget()
        self.clone_based_recoloring.setLayout(self.distance_layout)
        self.coloring_widget = Coloring(self.viewer)
        tabs.addTab(self.clone_based_recoloring, "Clone based Recoloring")
        tabs.addTab(self.coloring_widget, "Node based Recoloring")
        layout.addWidget(tabs)
        self.setLayout(layout)
        self.slider_change()
