import contextlib
import os
from pathlib import Path
from typing import TYPE_CHECKING

from magicgui import widgets
from matplotlib.figure import Figure
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpacerItem,
    QSpinBox,
    QVBoxLayout,
)

from ..._interaction_bridge import InteractionBridge
from ..._util_classes import (
    Containerize,
    DelayedTooltipEventFilter,
    LayerCorrectorTreeProducer,
    TooltipButton,
)
from ..._utils import _select_active_lt_layer
from .lineage_viewer.viewer import SingleTreeProgeny

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

    def select_the_lineage(self):
        """
        If a Point is selected it selects the whole Lineage.
        """
        active_layer = _select_active_lt_layer(self.viewer)
        if not active_layer:
            return
        if not active_layer.selected_data:
            return 0

        # Ensure lineage tree is available
        self.lT = self.get_lT()
        if self.lT is None:
            return

        napari_node_id = next(iter(active_layer.selected_data))
        lt_node_id = active_layer.metadata["napari2lT"][napari_node_id]
        scores = self.get_sublineage(lt_node_id, self.lT)

        # Get node IDs for the selected lineage
        selected_node_ids = list(scores.keys())
        # Use interaction bridge for coordinated multi-layer selection
        self.bridge.highlight_lineages(selected_node_ids)
        val = self.val_finder(
            lt_node_id,
            self.lT,
            active_layer.metadata["graphs"][0],
        )
        if val is not None:
            self.graph_slider.setValue(int(val))

            # Save state to bridge
            self.bridge.update_state(graph_slider_value=int(val))

            selected_cells = self.lT.get_subtree_nodes(
                self.lT.get_ancestor_at_t(lt_node_id)  # type: ignore
            )
            self.canvas.change_lineage(
                self.roots[int(self.graph_slider.value())],
                self.lT,
                active_layer.metadata["graphs"][0][val],
                active_layer.metadata["graphs"][1][val],
                points_layer_metadata=active_layer.metadata,
            )
            self.canvas.selected_subtree = set(selected_cells)

            # Save updated state to bridge
            self.bridge.update_state(
                selected_subtree=set(selected_cells), selected_lineage=val
            )
        else:
            raise Warning(
                "No tree for this node, because it has no progenitor in roots"
            )

    def point_click(self, viewer, event):
        """Function for clicking on the viewer to select a node from any supported layer type.

        Args:
            viewer (napari_viewer): The viewer of napari.
            event : The event signal that contains the spatial information of the action taken.
        """
        if "Shift" in event.modifiers and event.button == 2:
            # Ensure lineage tree is available
            active_layer = _select_active_lt_layer(self.viewer)
            if active_layer is None:
                self.lT = None
            else:
                self.lT = active_layer.metadata.get("LineageTree", None)
            if self.lT is None:
                return

            # Use InteractionBridge to find node in any layer
            result = self.bridge.find_node_at_position(
                event.position, event.view_direction, event.dims_displayed
            )

            if result:
                self.canvas.selected_nodes.clear()
                layer, node_id = result
                node_id_napari = layer.metadata["lT2napari"][node_id]
                self.cell_id_spinbox.setValue(node_id_napari)

                # Update the cell ID spinbox to show the clicked cell
                self.cell_id_spinbox.setValue(node_id)

                # Clear selections in all layers
                for viewer_layer in viewer.layers:
                    with contextlib.suppress(Exception):
                        viewer_layer.selected_data.clear()

                active_layer.selected_data = {node_id_napari}

                # Find the graph value for this node
                val = self.val_finder(
                    node_id,
                    self.lT,
                    layer.metadata["graphs"][0],
                )

                if val is not None:
                    self.graph_slider.setValue(int(val))
                    self.canvas.change_lineage(
                        self.roots[int(self.graph_slider.value())],
                        self.lT,
                        active_layer.metadata["graphs"][0][val],
                        active_layer.metadata["graphs"][1][val],
                        points_layer_metadata=active_layer.metadata,
                    )

                    # Add circle marker for the clicked cell
                    self.canvas.marked_cell_id = active_layer.metadata[
                        "napari2lT"
                    ][node_id_napari]
                    # if not hasattr(self, "face_colors_handler"):
                    self.face_colors_handler = (
                        active_layer._face.events.connect(
                            self.progeny_diagram_loader
                        )
                    )
                    self.canvas._draw_cell_marker(self.canvas.marked_cell_id)
                    self.canvas.draw()
                else:
                    self.canvas.ax.cla()
                    self.canvas.draw()

    def update_lineageviewer_colors(self):
        """Update the color box to show the current lineage color."""

        self._update_canvas_with_current_colors()

        if (
            hasattr(self, "canvas")
            and hasattr(self.canvas, "_extract_current_lineage_color")
            and hasattr(self.canvas, "points_layer_metadata")
            and self.canvas.points_layer_metadata is not None
        ):
            try:
                self.canvas._extract_current_lineage_color()
            except (AttributeError, KeyError):
                ...

    def _update_canvas_with_current_colors(self):
        """Update the canvas metadata with current face colors from the active layer."""
        active_layer = _select_active_lt_layer(self.viewer)
        if active_layer and hasattr(self, "canvas"):
            # Just update the metadata, the canvas handles its own redrawing
            self.canvas.update_face_colors(active_layer.face_color)

    def progeny_diagram_loader(self):
        """
        Program to load the diagrams in black or magenta. Reads the attributes to load different graphs.
        """
        active_layer = _select_active_lt_layer(self.viewer)
        if not active_layer and "lT" not in active_layer.metadata:
            return
        self.ax_for_tree_graph.clear()
        val = int(self.graph_slider.value())

        # Save slider state to bridge
        self.bridge.update_state(graph_slider_value=val, selected_lineage=val)

        # Preserve selected_subtree during lineage change if it exists
        preserve_subtree = getattr(self.canvas, "selected_subtree", set())

        self.canvas.change_lineage(
            self.roots[int(self.graph_slider.value())],
            self.lT,
            active_layer.metadata["graphs"][0][val],
            active_layer.metadata["graphs"][1][val],
            points_layer_metadata=active_layer.metadata,
        )

        # Clear any marked cell from spinbox selection
        self.canvas.marked_cell_id = None
        # Ensure selected_subtree is properly set and draw
        if preserve_subtree:
            self.canvas.selected_subtree = preserve_subtree

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
        self.update_lineageviewer_colors()

    def _click_on_tree_graph(self, event):
        """This functions handle the left-click interaction with the tree graph. Finds the node clicked
        and colors its subtree.

        Args:
            event : The signal that contains the spatial information of the graph click.
        """
        active_layer = _select_active_lt_layer(self.viewer)
        # Get the Points layer through the bridge for consistent behavior
        if "points" not in self.bridge.adapters:
            return
        active_layer.selected_data.clear()

        # Clear any marked cell from spinbox selection
        self.canvas.marked_cell_id = None

        if not event:
            # Background click - clear selections and refresh
            active_layer.refresh()

        points_layer = self.bridge.adapters["points"].layer
        if not points_layer:
            return

        points_layer.selected_data.clear()
        if not event:
            # Background click - unselect everything and reset all companion layer visibility
            self.bridge.reset_visibility()
            points_layer.refresh()
            return

        cell_id = event["value"]
        cell = active_layer.metadata["lT2napari"][cell_id]
        color = active_layer.face_color[cell]
        active_layer._face.current_color = color

        # Update the cell ID spinbox to show the clicked cell
        try:
            self.cell_id_spinbox.setValue(cell_id)
        except:
            pass

        # Get the sublineage for the clicked node
        selected_node_ids = self.lT.get_subtree_nodes(cell_id)
        # Set the selected subtree on the canvas so hide/show lineage buttons work
        self.canvas.selected_subtree = set(selected_node_ids)

        # Use interaction bridge for coordinated multi-layer selection
        self.bridge.highlight_lineages(selected_node_ids)

        normal_label = "Unlabeled"
        self.w_lineedit.setPlaceholderText(
            f"ID of root: {cell_id} - Label: {self.lT.labels.get(cell_id,normal_label)}"
        )

        # Only move time slider on double click (original behavior)
        if event["dblclick"]:
            self.update_time_slider_for_cell(cell_id)
        if not hasattr(self, "face_colors_handler"):
            self.face_colors_handler = active_layer._face.events.connect(
                self.progeny_diagram_loader
            )

    def sub_point_painter(self):
        """Paints specific part of the lineagetree when a sublineage is selected"""
        active_layer = _select_active_lt_layer(self.viewer)
        if not active_layer:
            return
        napari_node_id = next(iter(active_layer.selected_data))
        lt_node_id = active_layer.metadata["napari2lT"][napari_node_id]
        val = self.val_finder(
            lt_node_id,
            self.lT,
            active_layer.metadata["graphs"][0],
        )
        if val is not None:
            selected_node_ids = self.lT.get_subtree_nodes(
                self.lT.get_predecessors(lt_node_id)[0]
            )
            self.graph_slider.setValue(val)
            self.ax_for_tree_graph.clear()
            self.canvas.selected_nodes = set(selected_node_ids)
            self.canvas.change_lineage(
                self.roots[int(self.graph_slider.value())],
                self.lT,
                active_layer.metadata["graphs"][0][val],
                active_layer.metadata["graphs"][1][val],
                points_layer_metadata=active_layer.metadata,
            )

            # Save state to bridge
            self.bridge.update_state(
                selected_subtree=set(selected_node_ids),
                selected_lineage=val,
                graph_slider_value=val,
            )

            # Use interaction bridge for coordinated selection of the subtree
            self.bridge.highlight_lineages(selected_node_ids)

            lT_cell = self.lT.get_chain_of_node(lt_node_id)[0]
            normal_text = "Unlabeled"
            self.w_lineedit.setPlaceholderText(
                f"ID of root: {lT_cell} - Label: {self.lT.labels.get(lT_cell, normal_text)}"
            )
        else:
            raise Warning("Selected cell is not part of an important lineage.")

    def points_selector(self):
        """Select the entire lineage that contains the selected node."""
        self.select_the_lineage()

    def layer_change(self, event):
        """
        Function that handles the layer change event.
        Switches to the InteractionBridge for the selected layer and restores its state.
        """
        active_layer = _select_active_lt_layer(self.viewer)
        if active_layer is None:
            return
        try:
            self.face_colors_handler.disconnect()
            self.face_colors_handler = active_layer._face.events.connect(
                self.progeny_diagram_loader
            )
        except:
            pass

        # Save current state to the previous bridge
        if self.bridge:
            self.bridge.update_state(
                graph_slider_value=self.graph_slider.value(),
                selected_subtree=(
                    getattr(self.canvas, "selected_subtree", set())
                ),
            )

        # Get or create the InteractionBridge for this Points layer
        self.bridge = InteractionBridge.get_bridge_for_layer(active_layer)
        if not self.bridge:
            # Create a new bridge for this Points layer (this will establish links automatically)
            self.bridge = InteractionBridge.create_bridge_for_points_layer(
                self.viewer, active_layer
            )
        else:
            # If bridge already exists, make sure links are established for any new companion layers
            self.bridge._establish_layer_links()
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

                # Restore the saved state for this lineage tree
                saved_slider_value = 0  # default
                if self.bridge and "graph_slider_value" in self.bridge.state:
                    saved_slider_value = self.bridge.state[
                        "graph_slider_value"
                    ]
                    # Ensure the saved value is within valid range
                    saved_slider_value = max(
                        0, min(saved_slider_value, self.range)
                    )

                label = self.lT.labels.get(
                    self.roots[saved_slider_value], "Unlabeled"
                )
                self.w_lineedit.setPlaceholderText(
                    f"ID of root: {self.roots[saved_slider_value]} - Label: {label}"
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
                self.cell_id_spinbox.editingFinished.connect(
                    self.cell_id_selector
                )

                self.w_lineedit.update()

                # Store the selected_subtree from bridge state to restore after slider triggers progeny_diagram_loader
                bridge_selected_subtree = {}
                if (
                    self.bridge
                    and "selected_subtree" in self.bridge.state
                    and self.bridge.state["selected_subtree"]
                ):
                    bridge_selected_subtree = self.bridge.state[
                        "selected_subtree"
                    ]

                # Setting the slider value will trigger progeny_diagram_loader via valueChanged signal
                # However, if the saved value is the same as current value, no signal is emitted
                # So we need to force the diagram loading
                current_slider_value = self.graph_slider.value()
                self.graph_slider.setValue(saved_slider_value)

                # Force diagram loading if slider value didn't change (common case: both are 0)
                if current_slider_value == saved_slider_value:
                    self.progeny_diagram_loader()

                # Now restore the highlighting state after the slider change has completed
                # Set the selected subtree and redraw to show highlighting
                self.canvas.selected_subtree = bridge_selected_subtree

                # Also restore highlighting on companion layers
                selected_node_ids = list(bridge_selected_subtree)
                self.bridge.highlight_lineages(selected_node_ids)

                # Restore other state
                if self.bridge:
                    self.bridge.restore_state(self)
            else:
                # Disable spinbox and button if no lineage tree
                self.cell_id_spinbox.setEnabled(False)
                self.cell_id_go_button.setEnabled(False)
            self.face_colors_handler = active_layer._face.events.connect(
                self.progeny_diagram_loader
            )

    def label_remover(self):
        active_layer = _select_active_lt_layer(self.viewer)
        if active_layer is None:
            return
        to_remove = int(self.w_lineedit.placeholderText().split()[3])
        self.lT.labels.pop(to_remove)
        active_layer.metadata["LineageTree"].labels.pop(to_remove)
        self.progeny_diagram_loader()

    def show_all_labels(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText("Labels")
        msg.setInformativeText(
            "\n".join(f"{k}:{v}" for k, v in self.lT.labels.items())
        )
        msg.exec_()

    def show_all(self):
        """Show all nodes across all layer types."""
        # Store the currently selected lineage before resetting
        selected_subtree = None
        if hasattr(self, "canvas") and hasattr(
            self.canvas, "selected_subtree"
        ):
            selected_subtree = (
                self.canvas.selected_subtree.copy()
                if self.canvas.selected_subtree
                else None
            )

        # # Reset visibility (this will clear the selection)
        self.bridge.restore_visibility()

        # After resetting visibility, restore the selection for the currently selected lineage
        if selected_subtree:
            # Use highlight_lineages to restore selection without hiding other nodes
            selected_node_ids = list(selected_subtree)
            self.bridge.highlight_lineages(selected_node_ids)

        # Save state
        if self.bridge:
            self.bridge.update_state(visibility_state="all_visible")

    def hide_all(self):
        """Hide all nodes across all layer types."""
        self.bridge.show_only_nodes([])
        # Save state
        self.bridge.update_state(visibility_state="all_hidden")

    def hide_lineage(self):
        """Hide the currently selected lineage across all layer types."""
        if (
            hasattr(self.canvas, "selected_subtree")
            and self.canvas.selected_subtree
        ):
            # Use the currently selected subtree from the graph
            selected_node_ids = list(self.canvas.selected_subtree)
            if selected_node_ids:
                self.bridge.hide_lineages(selected_node_ids)
                # Save state
                self.bridge.update_state(
                    visibility_state="lineage_hidden",
                    hidden_lineage=selected_node_ids,
                )
                return
        # Fallback: use Points layer selected data
        active_layer = _select_active_lt_layer(self.viewer)
        if active_layer and active_layer.selected_data:
            # If there's a selected point, get its lineage and hide it
            selected_points = list(active_layer.selected_data)
            if selected_points and self.lT:
                # Get the lineage for the first selected point
                point_id = selected_points[0]
                lT_cell_id = active_layer.metadata["napari2lT"][point_id]
                lineage_node_ids = self.lT.get_subtree_nodes(lT_cell_id)

                # Set the selected subtree for consistency
                self.canvas.selected_subtree = set(lineage_node_ids)

                # Hide the lineage
                self.bridge.hide_lineages(lineage_node_ids)
                self.bridge.update_state(
                    visibility_state="lineage_hidden",
                    hidden_lineage=lineage_node_ids,
                )
            else:
                # Just hide the selected points
                active_layer.shown[selected_points] = False
                active_layer.refresh()

    def show_lineage(self):
        """Show only the currently selected lineage across all layer types."""
        if (
            hasattr(self.canvas, "selected_subtree")
            and self.canvas.selected_subtree
        ):
            # Use the currently selected subtree from the graph
            selected_node_ids = list(self.canvas.selected_subtree)
            if selected_node_ids:
                # Show only the selected lineage across all layers (including hiding other points)
                self.bridge.show_only_lineages(selected_node_ids)
                # Save state
                self.bridge.update_state(
                    visibility_state="lineage_only",
                    visible_lineage=selected_node_ids,
                )
                return

        # Fallback: use Points layer selected data
        active_layer = _select_active_lt_layer(self.viewer)
        if active_layer and active_layer.selected_data:
            # If there's a selected point, get its lineage and show only it
            selected_points = list(active_layer.selected_data)
            if selected_points and self.lT:
                # Get the lineage for the first selected point
                point_id = selected_points[0]
                lT_cell_id = active_layer.metadata["napari2lT"][point_id]
                lineage_node_ids = self.lT.get_subtree_nodes(lT_cell_id)

                # Set the selected subtree for consistency
                self.canvas.selected_subtree = set(lineage_node_ids)

                # Show only the lineage
                self.bridge.show_only_lineages(lineage_node_ids)
                self.bridge.update_state(
                    visibility_state="lineage_only",
                    visible_lineage=lineage_node_ids,
                )
            else:
                # Just show the selected points
                active_layer.shown[selected_points] = True
                active_layer.refresh()

    def cell_id_selector(self):
        """
        Select lineage based on cell ID input from spinbox.
        Moves slider to lineage containing this cell and shows a circle marker on lineage graph.
        """
        active_layer = _select_active_lt_layer(self.viewer)
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
                self.roots[int(self.graph_slider.value())],
                self.lT,
                active_layer.metadata["graphs"][0][val],
                active_layer.metadata["graphs"][1][val],
                points_layer_metadata=active_layer.metadata,
            )

            # Clear any previous subtree selection and draw with circle marker
            self.canvas.selected_subtree = set()
            self.canvas.marked_cell_id = (
                cell_id  # Store the cell to mark with circle
            )

            # Select only the single cell in the 3D view (not sublineage)
            points_to_select = set()
            if cell_id in active_layer.metadata["lT2napari"]:
                points_to_select.add(
                    active_layer.metadata["lT2napari"][cell_id]
                )

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
            self.update_lineageviewer_colors()

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

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)

        # Get the specific Points layer for this widget
        points_layer = _select_active_lt_layer(self.viewer)

        # Get or create the InteractionBridge for this Points layer
        if points_layer:
            # First establish links from companion layers to the Points layer
            # We'll let the bridge handle this during its creation

            # Then get or create the bridge (which will now find the linked layers)
            self.bridge = InteractionBridge.get_bridge_for_layer(points_layer)
            if not self.bridge:
                # Create a new bridge for this Points layer (this will establish links automatically)
                self.bridge = InteractionBridge.create_bridge_for_points_layer(
                    napari_viewer, points_layer
                )
        else:
            # Create a temporary bridge that will be replaced when a layer is selected
            self.bridge = InteractionBridge(napari_viewer, None)

        self.lT: LineageTree = self.get_lT()
        if self.lT:
            self.graph_slider = QSlider()
            self.graph_slider.setOrientation(Qt.Orientation.Horizontal)
            self.graph_slider.setTickInterval(1)
            self.graph_slider.setMinimum(0)
            self.graph_slider.setValue(0)
            self.roots = [
                g["root"]
                for g in _select_active_lt_layer(self.viewer)
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
        self.graph_slider.valueChanged.connect(self.progeny_diagram_loader)
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
        self.figure = Figure(constrained_layout=True, frameon=False)
        self.ax_for_tree_graph = self.figure.add_subplot(111)
        self.ax_for_tree_graph.axis("off")
        self.canvas = SingleTreeProgeny(self.figure, self.ax_for_tree_graph)
        self.canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.canvas.setContentsMargins(0, 0, 0, 0)
 

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
        self.layout().addWidget(self.canvas, stretch=1)
        self.tooltip.move(0, 0)
        self.config_settings = QPushButton(text="")
        self.config_settings.setIcon(
            QIcon(str(Path(__file__).parent / "gear-bold.svg"))
        )
        # self.pop_win = Setup(self.canvas, self.viewer)
        # self.config_settings.clicked.connect(lambda x: self.pop_win.exec_())
        # self.config_settings.setFixedSize(30, 30)

        # self.config_settings.setParent(self)
        # self.pop_win.sig.connect(self.canvas.change_attributes)

        if self.lT:
            self.progeny_diagram_loader()
        self.graph_slider.setToolTip(
            f"Currently {self.range+1} lineages present."
        )

        if self.lT:
            self.update_lineageviewer_colors()

        self.slider_box = Containerize(
            [
                widgets.Label(value="Lineage slider").native,
                self.graph_slider,
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
            self.cell_id_spinbox.setToolTip(
                "Enter cell ID, then press Enter or click 'Go' to jump to its lineage"
            )

            # Connect the Go button to the selector function
            self.cell_id_go_button.clicked.connect(self.cell_id_selector)
            self.cell_id_go_button.setEnabled(True)
            self.cell_id_go_button.setToolTip(
                "Click to jump to the entered cell ID"
            )

            # Also allow Enter key in the spinbox to trigger selection
            self.cell_id_spinbox.editingFinished.connect(self.cell_id_selector)
        else:
            # Create disabled spinbox and button when no lineage tree is loaded
            self.cell_id_spinbox.setEnabled(False)
            self.cell_id_spinbox.setToolTip(
                "Load a lineage tree to enable cell ID selection"
            )
            self.cell_id_go_button.setEnabled(False)
            self.cell_id_go_button.setToolTip(
                "Load a lineage tree to enable cell ID selection"
            )

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
        self.viewer.layers.selection.events.active.connect(self.layer_change)
        self.canvas.node_signal.connect(self._click_on_tree_graph)
        self.canvas.setFocusPolicy(Qt.WheelFocus)
        self.canvas.setFocus()
        self.viewer.dims.events.emitters["current_step"].connect(
            self.canvas.time_line
        )
