import contextlib
import os
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from magicgui import widgets
from matplotlib.figure import Figure
from napari.layers import Points
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpacerItem,
    QVBoxLayout,
)
from scipy.spatial import KDTree

from ..._util_classes import (
    Layer_corrector_Tree_Producer,
    containerize,
    delayedtooltipeventfilter,
    popable_window_for_tree_graph,
    tooltip_button,
)
from ..._utils import _select_correct_layer
from .canvas_for_progeny import single_tree_progeny

if TYPE_CHECKING:
    from lineagetree import LineageTree


class ProgenySelection(Layer_corrector_Tree_Producer):
    # your QWidget.__init__ can optionally request the napari viewer instance
    # in one of two ways:
    # 1. use a parameter called `napari_viewer`, as done here
    # 2. use a type annotation of 'napari.viewer.Viewer' for any parameter
    name = "Explore and Relabel"

    @staticmethod
    def get_sublineage(cell, lT):
        score = dict.fromkeys(lT.get_subtree_nodes(cell), 1)
        sup = [cell]
        branching = []
        if len(lT.successor.get(cell, [])) >= 2:
            branching = [cell]
        while sup[0] in lT.predecessor and lT.predecessor[sup[0]] != ():
            prev = lT.predecessor[sup[0]][0]
            if len(lT.successor.get(prev, [])) >= 2:
                branching.append(prev)
                score[prev] = score[sup[0]] + 1
            else:
                score[prev] = score[sup[0]]
            sup.insert(0, prev)
        for c in branching:
            for ci in lT.successor[c]:
                if ci not in score:
                    for d in lT.get_subtree_nodes(ci):
                        score[d] = score[c]
        for c in sup:
            score[c] = 1
        return score

    def points_selector(self):
        """
        If a Point is selected it selects the whole Lineage.
        """
        active_layer = _select_correct_layer(self, Points)
        if not active_layer:
            return
        if not active_layer.selected_data:
            return 0
        cell = active_layer.selected_data.pop()
        active_layer.selected_data = {cell}
        scores = self.get_sublineage(
            active_layer.metadata["napari2lT"][cell], self.lT
        )
        for key in scores:
            active_layer.selected_data.add(
                active_layer.metadata["lT2napari"][key]
            )
        active_layer.refresh()
        val = self.val_finder(
            active_layer.metadata["napari2lT"][cell],
            self.lT,
            active_layer.metadata["graphs"][0],
        )
        if val is not None:
            self.graph_slider.setValue(int(val))
            selected_cells = self.lT.get_subtree_nodes(
                self.lT.get_ancestor_at_t(
                    active_layer.metadata["napari2lT"][cell]  # type: ignore
                )
            )
            self.canvas.change_lineage(
                self.figure,
                self.ax_for_tree_graph,
                val,
                self.lT,
                active_layer.metadata["graphs"][0][val],
                active_layer.metadata["graphs"][1][val],
            )
            self.canvas.selected_subtree = set(selected_cells)
            self.canvas.draw_graph()
        else:
            raise Warning(
                "No tree for this node, because it has no progenitor in roots"
            )

    def point_click(self, viewer, event):
        """Function for clicking on the viewer to select a Point from the Points layer.

        Args:
            viewer (napari_viewer): The viewer of napari.
            event : The event signal that contains the spatial information of the action taken.
        """
        active_layer = _select_correct_layer(self, Points)
        if not active_layer:
            return
        if (
            "Shift" in event.modifiers
            and event.button == 2
            and "LineageTree" in active_layer.metadata
            and active_layer
        ):
            for layer in viewer.layers:
                with contextlib.suppress(Exception):
                    layer.selected_data.clear()
            current_position = event.position
            time = current_position[0]
            near_point, far_point = active_layer.get_ray_intersections(
                np.array(event.position),
                event.view_direction,
                np.array(event.dims_displayed),
            )
            if (near_point is not None) and (far_point is not None):
                ray_points = np.linspace(
                    near_point, far_point, 30, endpoint=True
                )
                indexes_of_slice = np.where(active_layer.data[:, 0] == time)
                data_in_slice = active_layer.data[indexes_of_slice][:, 1:]
                kdtree = KDTree(data_in_slice)
                dists, idx = kdtree.query(ray_points[:, 1:])
                active_layer.selected_data.add(
                    indexes_of_slice[0][idx[np.argmin(dists)]]
                )
                color = active_layer.face_color[
                    indexes_of_slice[0][idx[np.argmin(dists)]]
                ]
                active_layer._face.current_color = color
                self.Progeny_diagram_loader()
                active_layer.refresh()
                cell = active_layer.selected_data.pop()
                active_layer.selected_data = {cell}
                val = self.val_finder(
                    active_layer.metadata["napari2lT"][cell],
                    self.lT,
                    active_layer.metadata["graphs"][0],
                )
                if val is not None:
                    self.graph_slider.setValue(int(val))
                    self.canvas.change_lineage(
                        self.figure,
                        self.ax_for_tree_graph,
                        val,
                        self.lT,
                        active_layer.metadata["graphs"][0][val],
                        active_layer.metadata["graphs"][1][val],
                    )
                    self.canvas.draw_graph()
                else:
                    self.canvas.ax.clear()
                    self.canvas.draw()

    def Progeny_diagram_loader(self):
        """
        Program to load the diagrams in black or magenta. Reads the attributes to load different graphs.
        """
        active_layer = _select_correct_layer(self, Points)
        if not active_layer:
            return
        self.ax_for_tree_graph.clear()
        val = int(self.graph_slider.value())
        self.canvas.change_lineage(
            self.figure,
            self.ax_for_tree_graph,
            val,
            self.lT,
            active_layer.metadata["graphs"][0][val],
            active_layer.metadata["graphs"][1][val],
            False,
        )

        self.canvas.setFocusPolicy(Qt.WheelFocus)
        self.canvas.setFocus()
        if self.lT is not None:
            self.w_lineedit.setPlaceholderText(
                f"ID of root: {self.roots[int(self.graph_slider.value())]} - Label: {self.lT.labels[self.roots[int(self.graph_slider.value())]]}"
            )
        self.w_lineedit.clear()
        self.w_lineedit.update()

    def _click_on_tree_graph(self, event):
        """This functions handle the left-click interaction with the tree graph. Finds the node clicked
        and colors is subtree.

        Args:
            event : The signal that contains the spatial information of the graph click.
        """
        active_layer = _select_correct_layer(self, Points)
        if not active_layer:
            return
        active_layer.selected_data.clear()
        if not event:
            active_layer.refresh()
            return
        cell_id = event["value"]
        cell = active_layer.metadata["lT2napari"][cell_id]
        color = active_layer.face_color[cell]
        active_layer._face.current_color = color
        active_layer.selected_data.add(cell)
        self.sub_points_selector()

        normal_label = "Unlabeled"
        self.w_lineedit.setPlaceholderText(
            f"ID of root: {cell_id} - Label: {self.lT.labels.get(cell_id,normal_label)}"
        )
        if event["dblclick"]:
            camera_pan = self.viewer.dims.current_step
            self.viewer.dims.current_step = [
                self.lT.time[cell_id]
                - min(
                    {
                        layer.metadata.get("LineageTree").t_b
                        for layer in self.viewer.layers
                        if layer.metadata.get("LineageTree")
                    }
                ),  # min is important if the dataset does not start from 0.
            ] + list(camera_pan[1:])

    def sub_point_painter(self):
        """Paints specific part of the lineagetree when a sublineage is selected"""
        active_layer = _select_correct_layer(self, Points)
        if not active_layer:
            return
        cell = active_layer.selected_data.pop()
        val = self.val_finder(
            active_layer.metadata["napari2lT"][cell],
            self.lT,
            active_layer.metadata["graphs"][0],
        )
        if val is not None:
            selected_cells = self.lT.get_subtree_nodes(
                self.lT.get_predecessors(
                    active_layer.metadata["napari2lT"][cell]
                )[0]
            )
            self.graph_slider.setValue(val)
            self.ax_for_tree_graph.clear()
            self.canvas.change_lineage(
                self.figure,
                self.ax_for_tree_graph,
                val,
                self.lT,
                active_layer.metadata["graphs"][0][val],
                active_layer.metadata["graphs"][1][val],
            )
            self.canvas.selected_subtree = set(selected_cells)
            self.canvas.draw_graph()
            active_layer.selected_data = {cell}
            self.sub_points_selector()
            lT_cell = self.lT.get_chain_of_node(
                active_layer.metadata["napari2lT"][cell]
            )[0]
            normal_text = "Unlabeled"
            self.w_lineedit.setPlaceholderText(
                f"ID of root: {lT_cell} - Label: {self.lT.labels.get(lT_cell, normal_text)}"
            )
        else:
            raise Warning("Selected cell is not part of an important lineage.")

    def layer_change(self, event):
        """
        Function that handles the layer change event.
        Replaces the widgets of the ui of progeny selection, to fit the new layer.

        """
        active_layer = _select_correct_layer(self, Points)
        if active_layer is None:
            return
        if len(self.viewer.layers.selection) == 1:
            self.lT: LineageTree = self.get_lT()
            if self.lT:
                self.labels = self.lT.labels
                self.roots = [
                    g["root"]
                    for g in active_layer.metadata["graphs"][0].values()
                ]
                self.range = len(self.roots) - 1
                self.graph_slider.setMinimum(0)
                self.graph_slider.setMaximum(self.range)
                self.graph_slider.setValue(0)
                self.w_lineedit.setPlaceholderText(
                    f"ID of root: {self.roots[0]} - Label: {self.lT.labels[self.roots[0]]}"
                )
                self.graph_slider.setToolTip(
                    f"Currently {self.range+1} lineages present."
                )
                self.w_lineedit.update()
                self.Progeny_diagram_loader()

    def label_remover(self):
        active_layer = _select_correct_layer(self, Points)
        if active_layer is None:
            return
        to_remove = int(self.w_lineedit.placeholderText().split()[3])
        self.lT.labels.pop(to_remove)
        active_layer.metadata["LineageTree"].labels.pop(to_remove)
        self.Progeny_diagram_loader()

    def show_all_labels(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText("Labels")
        msg.setInformativeText(
            "\n".join(f"{k}:{v}" for k, v in self.lT.labels.items())
        )
        msg.exec_()

    signal = Signal(dict)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.tooltip.move(self.width() - self.tooltip.width(), 0)

    def label_changer(self):
        """Handles the change of labels and sends a signal that contains the labels to Comparison widget and
        saves the new names to the LineageTree loaded on the Points Layer.
        """
        text = self.w_lineedit.text()
        node = int(self.w_lineedit.placeholderText().split()[3])
        self.lT.labels[node] = text
        self.w_lineedit.setPlaceholderText(
            f"ID of root: {node} - Label: {text}"
        )
        self.labels = self.lT.labels
        self.w_lineedit.update()
        self.w_lineedit.clear()
        self.signal.emit(self.labels)
        self.canvas.draw_graph()

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)

        self.lT: LineageTree = self.get_lT()
        if self.lT:
            self.graph_slider = QSlider()
            self.graph_slider.setOrientation(Qt.Orientation.Horizontal)
            self.graph_slider.setTickInterval(1)
            self.graph_slider.setMinimum(0)
            self.graph_slider.setValue(0)
            self.roots = [
                g["root"]
                for g in _select_correct_layer(self, Points)
                .metadata["graphs"][0]
                .values()
            ]
            self.range = len(self.roots) - 1
            self.graph_slider.setMaximum(self.range)
            root_id = self.roots[int(self.graph_slider.value())]
            tmp = "Unlabelled"
            self.w_lineedit = QLineEdit(
                placeholderText=f"ID of root: {root_id} - Label: {self.lT.labels.get(root_id, tmp)}",
                clearButtonEnabled=True,
            )  # type: ignore
        else:
            self.w_lineedit = QLineEdit(
                placeholderText="Load a lineagetree/mastodon file",
                clearButtonEnabled=True,
            )  # type: ignore
            self.graph_slider = QSlider()
            self.graph_slider.setOrientation(Qt.Orientation.Horizontal)
            self.range = 0
            self.graph_slider.setMaximum(0)
        self.graph_slider.valueChanged.connect(self.Progeny_diagram_loader)
        remove_label = widgets.Button(text="Remove this label")
        remove_label.clicked.connect(self.label_remover)
        show_labels = widgets.Button(text="Show Labels")
        show_labels.clicked.connect(self.show_all_labels)
        self.w_lineedit.returnPressed.connect(self.label_changer)
        w = widgets.Label(
            value=(
                "Ctrl-Right click on a Point to compare it to other sub-lineages."
            )
        )
        w2 = widgets.Label(
            value=(
                "Shift-Right click on a point to select it and press on the buttons to select a lineage \n"
            )
        )
        cutoff2 = widgets.Button(text="Select Lineage")
        cutoff2.tooltip = "Select the lineage that spawns this node"
        event_filt = delayedtooltipeventfilter()
        self.installEventFilter(event_filt)
        cutoff2.clicked.connect(self.points_selector)
        cutoff3 = widgets.Button(text="Select Sub-Lineage")
        cutoff3.tooltip = "Select the sublineage spawned by this node"
        cutoff3.clicked.connect(self.sub_point_painter)
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(0)
        self.setLayout(layout)
        self.figure = Figure(figsize=(1, 3), frameon=False)
        self.ax_for_tree_graph = self.figure.add_subplot(111)
        self.canvas = single_tree_progeny(self.figure, self.ax_for_tree_graph)
        label1 = widgets.Label(
            value="""<span style="font-family: Arial; font-size: 20px; color: white;">Lineage Viewer</span>"""
        ).native
        label1.setStyleSheet("margin: 0px;padding: 0px;")
        self.layout().addWidget(label1, alignment=Qt.AlignHCenter)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(
            os.path.join(current_dir, "progeny_selection.html"),
            encoding="utf-8",
        ) as f:
            txt = f.read()
        self.tooltip = tooltip_button(txt)
        self.tooltip.setParent(self)
        self.tooltip.move(int(self.width() - self.tooltip.width()), 0)
        label1.move(int(self.width() / 2) + 10, 0)
        self.layout().addItem(QSpacerItem(10, 10))
        self.layout().addWidget(self.canvas, stretch=100)
        self.tooltip.move(0, 0)
        self.config_settings = QPushButton(text="")
        self.config_settings.setIcon(
            QIcon(str(Path(__file__).parent / "gear-bold.svg"))
        )
        self.pop_win = popable_window_for_tree_graph.setup(self.canvas)
        self.config_settings.clicked.connect(lambda x: self.pop_win.exec_())
        self.config_settings.setFixedSize(30, 30)

        self.config_settings.setParent(self)
        self.pop_win.sig.connect(self.canvas.change_attributes)

        if self.lT:
            self.Progeny_diagram_loader()
        self.graph_slider.setToolTip(
            f"Currently {self.range+1} lineages present."
        )
        self.slider_box = containerize(
            [
                widgets.Label(value="Lineage slider").native,
                self.graph_slider,
            ]
        )
        self.layout().addWidget(self.slider_box)
        self.layout().addWidget(
            containerize(
                [self.w_lineedit, show_labels.native, remove_label.native]
            )
        )
        self.layout().addWidget(w2.native)
        self.layout().addWidget(containerize([cutoff2.native, cutoff3.native]))
        self.layout().addWidget(w.native)
        self.viewer.mouse_drag_callbacks.append(self.point_click)
        self.viewer.layers.selection.events.connect(self.layer_change)
        self.canvas.node_signal.connect(self._click_on_tree_graph)
        self.canvas.setFocusPolicy(Qt.WheelFocus)
        self.canvas.setFocus()
        self.viewer.dims.events.emitters["current_step"].connect(
            self.canvas.time_line
        )
