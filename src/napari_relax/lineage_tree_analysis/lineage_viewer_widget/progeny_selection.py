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
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpacerItem,
    QSpinBox,
    QVBoxLayout,
)
from scipy.spatial import KDTree

from ..._util_classes import (
    Containerize,
    DelayedTooltipEventFilter,
    LayerCorrectorTreeProducer,
    TooltipButton,
)
from ..._util_classes.popable_window_for_tree_graph import Setup, _update_napari_highlight_color
from ..._utils import _select_correct_layer
from .canvas_for_progeny import SingleTreeProgeny

if TYPE_CHECKING:
    from lineagetree import LineageTree


class ProgenySelection(LayerCorrectorTreeProducer):
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
                points_layer_metadata=active_layer.metadata,
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
                
                # Update the cell ID spinbox to show the clicked cell
                cell_id = active_layer.metadata["napari2lT"][cell]
                self.cell_id_spinbox.setValue(cell_id)
                
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
                        points_layer_metadata=active_layer.metadata,
                    )
                    
                    # Add circle marker for the clicked cell
                    self.canvas.marked_cell_id = active_layer.metadata["napari2lT"][cell]
                    
                    self.canvas.draw_graph()
                else:
                    self.canvas.ax.clear()
                    self.canvas.draw()

    def update_lineage_color_box(self):
        """Update the color box to show the current lineage color."""
        if not hasattr(self, 'lineage_color_box'):
            return
        
        # Update the canvas with current face colors before extracting color
        self._update_canvas_with_current_colors()
            
        # Get the color info from the canvas using the new method
        color_info = None
        if (hasattr(self, 'canvas') and 
            hasattr(self.canvas, '_extract_current_lineage_color') and
            hasattr(self.canvas, 'points_layer_metadata') and
            self.canvas.points_layer_metadata is not None):
            try:
                color_info = self.canvas._extract_current_lineage_color()
            except (AttributeError, KeyError):
                # Handle cases where the canvas isn't fully initialized yet
                color_info = None
        
        if color_info and color_info.get('color'):
            color = color_info['color']
            is_uniform = color_info.get('is_uniform', True)
            
            # Convert to RGB tuple (0-255 range) if needed
            if isinstance(color, (list, tuple)) and len(color) >= 3:
                rgb_color = tuple(int(c * 255) if c <= 1.0 else int(c) for c in color[:3])
                
                if is_uniform:
                    # Solid color for uniform lineage colors
                    self.lineage_color_box.setStyleSheet(
                        f"QLabel {{ background-color: rgb({rgb_color[0]}, {rgb_color[1]}, {rgb_color[2]}); "
                        f"border: 1px solid black; border-radius: 3px; }}"
                    )
                    self.lineage_color_box.setToolTip("Current lineage color (uniform)")
                else:
                    # Gradient or pattern for non-uniform colors (quantitative coloring applied)
                    self.lineage_color_box.setStyleSheet(
                        f"QLabel {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                        f"stop:0 rgb({rgb_color[0]}, {rgb_color[1]}, {rgb_color[2]}), "
                        f"stop:0.5 rgb(255, 255, 255), stop:1 rgb({rgb_color[0]}, {rgb_color[1]}, {rgb_color[2]})); "
                        f"border: 1px solid black; border-radius: 3px; }}"
                    )
                    self.lineage_color_box.setToolTip("Lineage has mixed colors (quantitative coloring applied)")
            else:
                # Fallback to default color
                self._set_default_color_box()
        else:
            # Default gray color if no color is available
            self._set_default_color_box()
    
    def _update_canvas_with_current_colors(self):
        """Update the canvas metadata with current face colors from the active layer."""
        active_layer = _select_correct_layer(self, Points)
        if active_layer and hasattr(self, 'canvas'):
            # Just update the metadata, the canvas handles its own redrawing
            self.canvas.update_face_colors(active_layer.face_color)
    
    def _set_default_color_box(self):
        """Set the color box to default gray color."""
        self.lineage_color_box.setStyleSheet(
            "QLabel { background-color: rgb(128, 128, 128); "
            "border: 1px solid black; border-radius: 3px; }"
        )
        self.lineage_color_box.setToolTip("Current lineage color")

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
            points_layer_metadata=active_layer.metadata,
        )

        # Clear any marked cell from spinbox selection
        self.canvas.marked_cell_id = None

        self.canvas.setFocusPolicy(Qt.WheelFocus)
        self.canvas.setFocus()
        if self.lT is not None:
            label = self.lT.labels.get(
                self.roots[int(self.graph_slider.value())], "Unlabeled"
            )
            self.w_lineedit.setPlaceholderText(
                f"ID of root: {self.roots[int(self.graph_slider.value())]} - Label: {label}"
            )
        self.w_lineedit.clear()
        self.w_lineedit.update()
        
        # Update the lineage color box
        self.update_lineage_color_box()

    def _click_on_tree_graph(self, event):
        """This functions handle the left-click interaction with the tree graph. Finds the node clicked
        and colors its subtree.

        Args:
            event : The signal that contains the spatial information of the graph click.
        """
        active_layer = _select_correct_layer(self, Points)
        if not active_layer:
            return
        active_layer.selected_data.clear()
        
        # Clear any marked cell from spinbox selection
        self.canvas.marked_cell_id = None
        
        if not event:
            # Background click - clear selections and refresh
            active_layer.refresh()
            return
            
        cell_id = event["value"]
        cell = active_layer.metadata["lT2napari"][cell_id]
        color = active_layer.face_color[cell]
        active_layer._face.current_color = color
        
        # Select the full sublineage (original behavior)
        selected_cells = self.lT.get_subtree_nodes(cell_id)
        points_to_select = set()
        for cell in selected_cells:
            if cell in active_layer.metadata["lT2napari"]:
                points_to_select.add(active_layer.metadata["lT2napari"][cell])
        
        active_layer.selected_data = points_to_select
        active_layer.refresh()

        # Update the cell ID spinbox to show the clicked cell
        try:
            self.cell_id_spinbox.setValue(cell_id)
        except:
            pass
            

        normal_label = "Unlabeled"
        self.w_lineedit.setPlaceholderText(
            f"ID of root: {cell_id} - Label: {self.lT.labels.get(cell_id,normal_label)}"
        )
        
        # Only move time slider on double click (original behavior)
        if event["dblclick"]:
            self.update_time_slider_for_cell(cell_id)

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
                points_layer_metadata=active_layer.metadata,
            )
            self.canvas.selected_subtree = set(selected_cells)
            self.canvas.draw_graph()
            
            # Select the corresponding points in the 3D view
            points_to_select = set()
            for cell in selected_cells:
                if cell in active_layer.metadata["lT2napari"]:
                    points_to_select.add(active_layer.metadata["lT2napari"][cell])
            
            active_layer.selected_data = points_to_select
            active_layer.refresh()
            
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
                label = self.lT.labels.get(self.roots[0], "Unlabeled")
                self.w_lineedit.setPlaceholderText(
                    f"ID of root: {self.roots[int(self.graph_slider.value())]} - Label: {label}"
                )

                self.graph_slider.setToolTip(
                    f"Currently {self.range+1} lineages present."
                )
                
                # Update cell ID spinbox with new lineage tree
                all_cell_ids = list(self.lT.nodes)
                min_cell_id = min(all_cell_ids)
                max_cell_id = max(all_cell_ids)
                
                self.cell_id_spinbox.setMinimum(min_cell_id)
                self.cell_id_spinbox.setMaximum(max_cell_id)
                self.cell_id_spinbox.setValue(min_cell_id)
                self.cell_id_spinbox.setEnabled(True)
                
                # Enable the Go button and connect it to the selector
                self.cell_id_go_button.setEnabled(True)
                # Disconnect any existing connections to avoid duplicates
                try:
                    self.cell_id_go_button.clicked.disconnect()
                    self.cell_id_spinbox.editingFinished.disconnect()
                except:
                    pass
                
                # Connect the signals
                self.cell_id_go_button.clicked.connect(self.cell_id_selector)
                self.cell_id_spinbox.editingFinished.connect(self.cell_id_selector)
                
                self.w_lineedit.update()
                self.Progeny_diagram_loader()
            else:
                # Disable spinbox and button if no lineage tree
                self.cell_id_spinbox.setEnabled(False)
                self.cell_id_go_button.setEnabled(False)

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

    def show_all(self):
        active_layer = _select_correct_layer(self, Points)
        if active_layer is None:
            return
        active_layer.shown = True

    def hide_all(self):
        active_layer = _select_correct_layer(self, Points)
        if active_layer is None:
            return
        active_layer.shown = False

    def hide_lineage(self):
        active_layer = _select_correct_layer(self, Points)
        if active_layer is None:
            return
        active_layer.shown[list(active_layer.selected_data)] = False
        active_layer.refresh()

    def show_lineage(self):
        active_layer = _select_correct_layer(self, Points)
        if active_layer is None:
            return
        active_layer.shown[list(active_layer.selected_data)] = True
        active_layer.refresh()

    def cell_id_selector(self):
        """
        Select lineage based on cell ID input from spinbox.
        Moves slider to lineage containing this cell and shows a circle marker on lineage graph.
        """
        active_layer = _select_correct_layer(self, Points)
        if not active_layer or not self.lT:
            return
            
        cell_id = self.cell_id_spinbox.value()
        
        # Check if cell_id exists in the lineage tree
        if cell_id not in self.lT.nodes:
            # If cell doesn't exist, find the closest existing cell ID
            all_nodes = sorted(self.lT.nodes)
            closest_node = min(all_nodes, key=lambda x: abs(x - cell_id))
            self.cell_id_spinbox.setValue(closest_node)
            cell_id = closest_node
            
        # Find which lineage (root) this cell belongs to
        val = self.val_finder(
            cell_id,
            self.lT,
            active_layer.metadata["graphs"][0],
        )
        
        if val is not None:
            # Update the slider to the correct lineage
            self.graph_slider.setValue(int(val))
            
            # Update the canvas to show the correct lineage without sublineage highlighting
            self.canvas.change_lineage(
                self.figure,
                self.ax_for_tree_graph,
                val,
                self.lT,
                active_layer.metadata["graphs"][0][val],
                active_layer.metadata["graphs"][1][val],
                points_layer_metadata=active_layer.metadata,
            )
            
            # Clear any previous subtree selection and draw with circle marker
            self.canvas.selected_subtree = set()
            self.canvas.marked_cell_id = cell_id  # Store the cell to mark with circle
            self.canvas.draw_graph()
            
            # Select only the single cell in the 3D view (not sublineage)
            points_to_select = set()
            if cell_id in active_layer.metadata["lT2napari"]:
                points_to_select.add(active_layer.metadata["lT2napari"][cell_id])
            
            active_layer.selected_data = points_to_select
            active_layer.refresh()
            
            # Update the label text field
            normal_label = "Unlabeled"
            self.w_lineedit.setPlaceholderText(
                f"ID of root: {cell_id} - Label: {self.lT.labels.get(cell_id, normal_label)}"
            )
            
            # Update time slider to show when this cell first appears
            self.update_time_slider_for_cell(cell_id)
            
            # Update the lineage color box
            self.update_lineage_color_box()

    def update_time_slider_for_cell(self, cell_id):
        """Update the time slider to show when the given cell first appears."""
        if not self.lT or cell_id not in self.lT.time:
            return
            
        # Calculate the time step for this cell
        cell_time = self.lT.time[cell_id]
        
        # Get the minimum time from all lineage tree layers (important if dataset doesn't start from 0)
        min_time = min(
            {
                layer.metadata.get("LineageTree").t_b
                for layer in self.viewer.layers
                if layer.metadata.get("LineageTree")
            }
        )
        
        # Set the time slider to show when this cell appears
        time_step = cell_time - min_time
        current_step = list(self.viewer.dims.current_step)
        current_step[0] = time_step
        self.viewer.dims.current_step = current_step

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
        event_filt = DelayedTooltipEventFilter()
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
        self.canvas = SingleTreeProgeny(self.figure, self.ax_for_tree_graph)
        
        # Initialize napari highlight color to match canvas selection color
        _update_napari_highlight_color(self.canvas.color_of_selection_nodes, self.viewer)
        
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
        self.tooltip = TooltipButton(txt)
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
        self.pop_win = Setup(self.canvas, self.viewer)
        self.config_settings.clicked.connect(lambda x: self.pop_win.exec_())
        self.config_settings.setFixedSize(30, 30)

        self.config_settings.setParent(self)
        self.pop_win.sig.connect(self.canvas.change_attributes)

        if self.lT:
            self.Progeny_diagram_loader()
        self.graph_slider.setToolTip(
            f"Currently {self.range+1} lineages present."
        )
        
        # Create a color box to show the current lineage color
        self.lineage_color_box = QLabel()
        self.lineage_color_box.setFixedSize(40, 20)
        self.lineage_color_box.setToolTip("Current lineage color")
        # Initialize with default color (will be updated when data is loaded)
        self.lineage_color_box.setStyleSheet(
            "QLabel { background-color: rgb(128, 128, 128); "
            "border: 1px solid black; border-radius: 3px; }"
        )
        
        # Update color box if lineage data is already loaded
        if self.lT:
            self.update_lineage_color_box()
        
        self.slider_box = Containerize(
            [
                widgets.Label(value="Lineage slider").native,
                self.graph_slider,
                self.lineage_color_box,
            ]
        )
        self.layout().addWidget(self.slider_box)
        
        # Add cell ID selection spinbox with Go button
        self.cell_id_spinbox = QSpinBox()
        self.cell_id_go_button = QPushButton("Go")
        self.cell_id_go_button.setMaximumWidth(40)  # Keep the button compact
        
        if self.lT:
            # Get all cell IDs in the lineage tree
            all_cell_ids = list(self.lT.nodes)
            min_cell_id = min(all_cell_ids)
            max_cell_id = max(all_cell_ids)
            
            self.cell_id_spinbox.setMinimum(min_cell_id)
            self.cell_id_spinbox.setMaximum(max_cell_id)
            self.cell_id_spinbox.setValue(min_cell_id)
            self.cell_id_spinbox.setToolTip("Enter cell ID, then press Enter or click 'Go' to jump to its lineage")
            
            # Connect the Go button to the selector function
            self.cell_id_go_button.clicked.connect(self.cell_id_selector)
            self.cell_id_go_button.setEnabled(True)
            self.cell_id_go_button.setToolTip("Click to jump to the entered cell ID")
            
            # Also allow Enter key in the spinbox to trigger selection
            self.cell_id_spinbox.editingFinished.connect(self.cell_id_selector)
        else:
            # Create disabled spinbox and button when no lineage tree is loaded
            self.cell_id_spinbox.setEnabled(False)
            self.cell_id_spinbox.setToolTip("Load a lineage tree to enable cell ID selection")
            self.cell_id_go_button.setEnabled(False)
            self.cell_id_go_button.setToolTip("Load a lineage tree to enable cell ID selection")
            
        self.cell_id_box = Containerize(
            [
                widgets.Label(value="Cell ID selector").native,
                self.cell_id_spinbox,
                self.cell_id_go_button,
            ]
        )
        
        self.layout().addWidget(self.cell_id_box)
        self.layout().addWidget(
            Containerize(
                [self.w_lineedit, show_labels.native, remove_label.native]
            )
        )
        self.layout().addWidget(w2.native)
        self.layout().addWidget(Containerize([cutoff2.native, cutoff3.native]))
        self.layout().addWidget(w.native)

        show_all = QPushButton("Show all")
        show_all.clicked.connect(self.show_all)
        hide_all = QPushButton("Hide all")
        hide_all.clicked.connect(self.hide_all)
        hide_lin = QPushButton("Hide Lineage")
        hide_lin.clicked.connect(self.hide_lineage)
        show_lin = QPushButton("Show Lineage")
        show_lin.clicked.connect(self.show_lineage)

        shown_cont = Containerize([hide_lin, show_lin, hide_all, show_all])
        self.layout().addWidget(shown_cont)

        self.viewer.mouse_drag_callbacks.append(self.point_click)
        self.viewer.layers.selection.events.connect(self.layer_change)
        self.canvas.node_signal.connect(self._click_on_tree_graph)
        self.canvas.setFocusPolicy(Qt.WheelFocus)
        self.canvas.setFocus()
        self.viewer.dims.events.emitters["current_step"].connect(
            self.canvas.time_line
        )
