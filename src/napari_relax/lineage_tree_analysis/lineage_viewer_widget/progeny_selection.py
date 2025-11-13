import contextlib
import os
from pathlib import Path
from typing import TYPE_CHECKING

from magicgui import widgets
from matplotlib.figure import Figure
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

from ..._interaction_bridge import InteractionBridge
from ..._util_classes import (
    Containerize,
    DelayedTooltipEventFilter,
    LayerCorrectorTreeProducer,
    TooltipButton,
)
from ..._util_classes.popable_window_for_tree_graph import Setup
from ..._utils import _select_active_lt_layer
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

        cell = active_layer.selected_data.pop()
        active_layer.selected_data = {cell}
        scores = self.get_sublineage(
            active_layer.metadata["napari2lT"][cell], self.lT
        )

        # Get node IDs for the selected lineage
        selected_node_ids = list(scores.keys())

        # Use interaction bridge for coordinated multi-layer selection
        self.bridge.highlight_lineages(selected_node_ids)
        val = self.val_finder(
            active_layer.metadata["napari2lT"][cell],
            self.lT,
            active_layer.metadata["graphs"][0],
        )
        if val is not None:
            self.graph_slider.setValue(int(val))

            # Save state to bridge
            self.bridge.update_state(graph_slider_value=int(val))

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

            # Save updated state to bridge
            self.bridge.update_state(
                selected_subtree=set(selected_cells), selected_lineage=val
            )
            self.canvas.draw_graph()
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
                layer, node_id = result
                node_id_napari = layer.metadata["lT2napari"][node_id]
                active_layer.selected_data = {node_id_napari}

                # Clear selections in all layers
                for viewer_layer in viewer.layers:
                    with contextlib.suppress(Exception):
                        viewer_layer.selected_data.clear()

                # Find the graph value for this node
                val = self.val_finder(
                    node_id_napari,
                    self.lT,
                    layer.metadata["graphs"][0],
                )

                if val is not None:
                    self.graph_slider.setValue(int(val))
                    self.canvas.change_lineage(
                        self.figure,
                        self.ax_for_tree_graph,
                        val,
                        self.lT,
                        layer.metadata["graphs"][0][val],
                        layer.metadata["graphs"][1][val],
                    )
                    self.canvas.draw_graph()
                else:
                    self.canvas.ax.clear()
                    self.canvas.draw()

                # # Update the progeny diagram
                # self.progeny_diagram_loader()

    def progeny_diagram_loader(self):
        """
        Program to load the diagrams in black or magenta. Reads the attributes to load different graphs.
        """
        active_layer = _select_active_lt_layer(self.viewer)
        if not active_layer:
            return
        self.ax_for_tree_graph.clear()
        val = int(self.graph_slider.value())

        # Save slider state to bridge
        self.bridge.update_state(graph_slider_value=val, selected_lineage=val)

        # Preserve selected_subtree during lineage change if it exists
        preserve_subtree = getattr(self.canvas, "selected_subtree", set())

        self.canvas.change_lineage(
            self.figure,
            self.ax_for_tree_graph,
            val,
            self.lT,
            active_layer.metadata["graphs"][0][val],
            active_layer.metadata["graphs"][1][val],
            False,
        )

        # Ensure selected_subtree is properly set and draw
        if preserve_subtree:
            self.canvas.selected_subtree = preserve_subtree
            self.canvas.draw_graph()

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

    def _click_on_tree_graph(self, event):
        """This functions handle the left-click interaction with the tree graph. Finds the node clicked
        and colors is subtree.

        Args:
            event : The signal that contains the spatial information of the graph click.
        """
        # Get the Points layer through the bridge for consistent behavior
        if "points" not in self.bridge.adapters:
            return
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
        if event["dblclick"]:
            self.update_time_slider_for_cell(cell_id)

    def sub_point_painter(self):
        """Paints specific part of the lineagetree when a sublineage is selected"""
        active_layer = _select_active_lt_layer(self.viewer)
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

            # Save state to bridge
            self.bridge.update_state(
                selected_subtree=set(selected_cells),
                selected_lineage=val,
                graph_slider_value=val,
            )

            # Use interaction bridge for coordinated selection of the subtree
            self.bridge.highlight_lineages(selected_cells)

            lT_cell = self.lT.get_chain_of_node(
                active_layer.metadata["napari2lT"][cell]
            )[0]
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
                self.canvas.draw_graph()

                # Also restore highlighting on companion layers
                selected_node_ids = list(bridge_selected_subtree)
                self.bridge.highlight_lineages(selected_node_ids)

                # Restore other state
                if self.bridge:
                    self.bridge.restore_state(self)

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

        # set the time slider to show when this cell appears
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
        self.figure = Figure(figsize=(1, 3), frameon=False)
        self.ax_for_tree_graph = self.figure.add_subplot(111)
        self.canvas = SingleTreeProgeny(self.figure, self.ax_for_tree_graph)
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
        self.pop_win = Setup(self.canvas)
        self.config_settings.clicked.connect(lambda x: self.pop_win.exec_())
        self.config_settings.setFixedSize(30, 30)

        self.config_settings.setParent(self)
        self.pop_win.sig.connect(self.canvas.change_attributes)

        if self.lT:
            self.progeny_diagram_loader()
        self.graph_slider.setToolTip(
            f"Currently {self.range+1} lineages present."
        )
        self.slider_box = Containerize(
            [
                widgets.Label(value="Lineage slider").native,
                self.graph_slider,
            ]
        )
        self.layout().addWidget(self.slider_box)
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
