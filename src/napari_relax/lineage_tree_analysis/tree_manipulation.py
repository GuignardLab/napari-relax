from collections import deque

import matplotlib.pyplot as plt
import numpy as np
from LineageTree.utils import hierarchical_pos
from magicgui import widgets
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from napari.layers import Points
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QKeyEvent
from qtpy.QtWidgets import (
    QHeaderView,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .._reader import layer_preparation
from .._util_classes import (
    Layer_corrector_Tree_Producer,
    containerize,
    single_tree,
)
from .._utils import (
    _select_correct_layer,
    custom_error,
    extract_lineage,
    inject_lineage,
    plot_lineages_for_tree_manip,
)


class tree_manipulation(Layer_corrector_Tree_Producer):
    """Class to manipulate Lineagetrees."""

    name = "tree_manip"
    pressed_key = Signal(QKeyEvent)
    table_values = Signal(dict)

    def keyPressEvent(self, event):
        self.pressed_key.emit(event)

    def undo_z(self, event):
        if (
            event.key() == Qt.Key.Key_Z
            and (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            and not (Qt.KeyboardModifier.ShiftModifier & event.modifiers())
            and self.live_ctrl_z
            and self.lT
        ):
            to_redo = self.live_ctrl_z.pop()
            self.lT.remove_nodes(
                {
                    node
                    for s_lt in to_redo[1]
                    for node in self.lT.get_subtree_nodes(s_lt)
                }
            )
            if to_redo[0]:
                inject_lineage(self.lT, to_redo[0])
            tree_graph = self.split.widget(0)
            if isinstance(self.split.widget(0), single_tree):
                self.refresh_graphs_without_changing_plot(tree_graph)
            else:
                self.refresh_graphs_without_changing_plot(None)
            self.split.refresh()

    def redo_z(self, event):
        return
        if (
            event.key() == Qt.Key.Key_Z
            and (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            and (Qt.KeyboardModifier.ShiftModifier & event.modifiers())
            and self.ctrl_shift_z_deq
            and self.lT
        ):
            to_undo = self.ctrl_shift_z_deq.pop()
            self.ctrl_shift_z_deq.append(to_undo[::-1])
            self.lT.remove_nodes(self.lT.get_subtree_nodes(to_undo[1]))
            inject_lineage(self.lT, to_undo[0])
            tree_graph = self.split.widget(0)
            if isinstance(self.split.widget(0), single_tree):
                self.refresh_graphs_without_changing_plot(tree_graph)
            else:
                self.refresh_graphs_without_changing_plot(None)
            self.split.refresh()

    def complete_lineage(self):
        if self.lT:
            tree_graph = self.split.widget(0)
            self.ctrl_shift_z_deq.clear()
            if isinstance(tree_graph, single_tree):
                to_append = (
                    extract_lineage(self.lT, tree_graph.root),
                    [tree_graph.root],
                )
                self.live_ctrl_z.append(to_append)
                self.lT.complete_lineage(tree_graph.root)
                self.refresh_graphs_without_changing_plot(tree_graph)
            elif self.selected_trees:
                to_append = (
                    extract_lineage(self.lT, self.selected_trees),
                    list(self.selected_trees),
                )
                self.live_ctrl_z.append(to_append)

                self.lT.complete_lineage(self.selected_trees)
                self.selected_trees.clear()
                self.refresh_graphs_without_changing_plot(None)
            else:
                to_append = (
                    extract_lineage(self.lT, self.lT.roots),
                    list(self.lT.roots),
                )
                self.lT.complete_lineage()
                self.refresh_graphs_without_changing_plot(None)
                self.live_ctrl_z.append(to_append)
            self.split.refresh()

    def modify_branch(self):
        tree_graph = self.split.widget(0)
        if (
            isinstance(tree_graph, single_tree)
            and self.lT
            and len(tree_graph.selected_node) == 1
        ):
            node = tree_graph.selected_node.pop()
            to_append = extract_lineage(
                self.lT, self.lT.get_ancestor_at_t(node)
            )
            self.ctrl_shift_z_deq.clear()
            self.lT.modify_branch(node, int(self.change_length.value))
            self.live_ctrl_z.append(
                (to_append, [self.lT.get_ancestor_at_t(node)])
            )
            self.refresh_graphs_without_changing_plot(tree_graph)

    def add_branch(self):
        tree_graph = self.split.widget(0)
        if (
            isinstance(tree_graph, single_tree)
            and self.lT
            and len(tree_graph.selected_node) == 1
        ):
            self.ctrl_shift_z_deq.clear()
            cycle = self.lT.get_node_chain(tree_graph.selected_node.pop())
            root = self.lT.get_ancestor_at_t(cycle[0])
            to_append = extract_lineage(self.lT, root)
            mid_cycle = cycle[len(cycle) // 2]
            self.lT.add_branch(
                pred=mid_cycle,
                length=int(self.set_length.value),
                move_timepoints=False,
                reverse=True,
            )
            self.live_ctrl_z.append([to_append, [root]])
            self.refresh_graphs_without_changing_plot(tree_graph)

    def copy_lineage(self):
        if len(self.selected_trees) == 1 and self.lT:
            self.ctrl_shift_z_deq.clear()
            new_t = self.lT.copy_lineage(self.selected_trees.pop())
            self.live_ctrl_z.append([None, [new_t]])
            self.refresh_graphs_without_changing_plot(None)

    def fuse_lineages(self):
        """Fuses 2 lineages together, according the lengths received from self.left, self.right boxes...."""
        if len(self.selected_trees) == 2 and self.lT:
            self.ctrl_shift_z_deq.clear()
            to_append = extract_lineage(
                self.lT, [self.selected_trees[0], self.selected_trees[1]]
            )
            new_t = self.lT.fuse_lineage_tree(
                self.selected_trees[0],
                self.selected_trees[1],
                int(self.left.text()),
                int(self.right.text()),
                int(self.central.text()),
            )
            self.live_ctrl_z.append((to_append, [new_t]))
            self.refresh_graphs_without_changing_plot(None)
            self.selected_trees.clear()
        else:
            custom_error(
                "Fuse Error", "select 2 lineages", "Please select 2 lineages"
            )

    def split_tree(self):
        if len(self.selected_trees) == 1 and self.lT:
            self.ctrl_shift_z_deq.clear()
            first_t = self.selected_trees.pop()
            to_append = extract_lineage(self.lT, first_t)
            second_t = self.lT.cut_tree(first_t)
            self.live_ctrl_z.append((to_append, [first_t, second_t]))
            self.refresh_graphs_without_changing_plot(None)
        else:
            custom_error("Split Error", "", "Please select 1 lineage")

    def remove_nodes(self):
        tree_graph = self.split.widget(0)
        if isinstance(tree_graph, single_tree) and self.lT:
            self.ctrl_shift_z_deq.clear()
            if tree_graph.selected_subtree:
                self.live_ctrl_z.append(
                    (extract_lineage(self.lT, tree_graph.selected_subtree), [])
                )
                self.lT.remove_nodes(tree_graph.selected_subtree)
                tree_graph.selected_subtree.clear()
            else:
                self.live_ctrl_z.append(
                    (
                        self.lT.get_ancestor_at_t(
                            extract_lineage(
                                self.lT, tree_graph.selected_node[0]
                            )
                        ),
                        [],
                    )
                )
                nodes_to_remove = {
                    node
                    for n in tree_graph.selected_node
                    for node in self.lT.get_node_chain(n)
                }
                self.lT.remove_nodes(nodes_to_remove)
                tree_graph.selected_node.clear()
            self.refresh_graphs_without_changing_plot(tree_graph)

    def add_new_tree_to_viewer(self):
        data = layer_preparation(
            self.lT,
            path="Manipulated_tree",
        )[0]
        self.viewer.add_points(data[0], **data[1])

    def refresh_graphs_without_changing_plot(
        self, single_tree_to_refresh: single_tree | None
    ):
        if self.lT:
            if single_tree_to_refresh:
                single_tree_to_refresh.get_new_lT(self.lT)
                single_tree_to_refresh.get_new_ax()
                single_tree_to_refresh.draw_graph(reset=True)
            nrows = np.round(np.sqrt(self.roots))
            (
                self.figure,
                self.ax,
                self.ax2root,
                self.root2ax,
            ) = self.lT.plot_all_lineages(
                self.roots,
                nrows=nrows,
                figsize=(10, 15),
            )
        self.figure.subplots_adjust(
            wspace=0,
            hspace=0,
            top=1,
            bottom=0,
            right=1,
            left=0,
        )
        self.canvas_new = FigureCanvas(self.figure)
        self.canvas = self.canvas_new
        if not single_tree_to_refresh:
            self.split.widget(
                0
            ).deleteLater()  ### Only works like that for some reason replace widget works only if its called from this app, and not a parent
            self.canvas = self.canvas_new
            self.split.insertWidget(0, self.canvas)
        self.canvas.mpl_connect("button_press_event", self._click_select)
        self.split.refresh()
        self.canvas.mpl_connect("button_press_event", self._zoom)
        self.canvas.draw()

    def _click_select(self, event):
        """Selects multiple trees. The selected trees are saved on a list called self.selected trees and each element of the list is the id of the root node.

        Args:
            event (_type_): _description_
        """
        if event.button == 1 and event.inaxes and not event.dblclick:
            ax = event.inaxes
            root = self.ax2root[event.inaxes]
            if root in self.selected_trees:
                self.selected_trees.remove(root)
                ax.set_facecolor("white")
            else:
                self.selected_trees.append(root)
                ax.patch.set_facecolor("yellow")
            self.canvas.draw()

    def change_value_of_change_length(self, sig):
        self.change_length.value = int(sig)

    def _zoom(self, event):
        """Handles the zooming and unzooming into one of the graph.The zoom works by double clicking left mouse button.

        Args:
            event (_type_): _description_
        """
        if event.button == 1 and event.inaxes and event.dblclick and self.lT:
            self.selected_trees.clear()
            if self.split.isAncestorOf(self.canvas):
                for f_ax in self.ax.flatten():
                    f_ax.patch.set_facecolor("white")
                root = self.ax2root[event.inaxes]

                graph = self.lnks_tms[
                    self.val_finder(root, self.lT, self.lnks_tms)
                ]
                pos = hierarchical_pos(graph, root)
                fig, ax = self.lT.draw_tree_graph(pos, graph)
                self.selected_trees.clear()

                self.single_tree_canvas = single_tree(
                    fig,
                    ax,
                    root,
                    self.lT,
                    graph,
                )
                self.split.replaceWidget(0, self.single_tree_canvas)
                self.single_tree_canvas.mpl_connect(
                    "button_press_event", self._zoom
                )
                self.single_tree_canvas.setFocusPolicy(Qt.ClickFocus)
                self.single_tree_canvas.setFocus()
            else:
                self.split.replaceWidget(0, self.canvas)
                self.canvas.setFocusPolicy(Qt.ClickFocus)
                self.canvas.setFocus()
                self.single_tree_canvas.selected_node.clear()
                self.single_tree_canvas.selected_subtree.clear()

    def set_dict_values_to_table(self, val: dict):
        for i, (k, v) in enumerate(val.items()):
            self.table.setItem(i, 0, QTableWidgetItem(str(k)))
            self.table.setItem(i, 1, QTableWidgetItem(str(v)))
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

    def default_table_values(self):
        return
        self.table_values.emit(
            {
                "Number of leaves": len(self.lT.leaves),
                "Number of nodes": len(self.lT.nodes),
                "Number of divisions": len(self.lT.leaves)
                - len(self.lT.time_nodes[0]),
                "Depth of tree": max(self.lT.time_nodes)
                - min(self.lT.time_nodes),
                "Average life-cycle": round(
                    np.mean(
                        [
                            v
                            for r in self.lT.roots
                            for v in self.lnks_tms[r]["times"].values()
                        ]
                    ),
                    2,
                ),
            }
        )

    def label_layer_change(self, event=None):
        """Function that handles changing the layer on napari viewer, updating a label or changing a tree.

        Args:
            event (_type_, optional): _description_. Defaults to None.
        """
        if len(self.viewer.layers.selection) == 1:
            lintr = self.get_lT()
            if lintr:
                self.lT = lintr
                self.roots = {
                    root for root in self.lT.roots if self.lT.labels.get(root)
                }
                self.lnks_tms = self.lT.to_simple_graph(
                    {
                        root
                        for root in self.lT.roots
                        if self.lT.labels.get(root, None)
                    }
                )
                self.hiers = {
                    i: hierarchical_pos(
                        g, g["root"], ycenter=-int(self.lT.time[g["root"]])
                    )
                    for i, g in self.lnks_tms.items()
                }
                nrows = np.round(np.sqrt(len(self.roots)))
                (
                    self.figure,
                    self.ax,
                    self.ax2root,
                    self.root2ax,
                ) = plot_lineages_for_tree_manip(
                    self.lT,
                    self.lnks_tms,
                    self.hiers,
                    nrows=nrows,
                    figsize=(10, 15),
                )
                self.figure.subplots_adjust(
                    wspace=0.01,
                    hspace=0.01,
                    top=0.98,
                    bottom=0.0,
                    right=0.98,
                    left=0.02,
                )
                self.canvas_new = FigureCanvas(self.figure)
                self.split.widget(
                    0
                ).deleteLater()  ### Only works like that for some reason replace widget works only if its called from this app, and not a parent
                self.canvas = self.canvas_new
                self.split.insertWidget(0, self.canvas)
                self.canvas.mpl_connect(
                    "button_press_event", self._click_select
                )
                self.split.refresh()
                self.canvas.mpl_connect("button_press_event", self._zoom)
                self.canvas.draw()

    def get_lT(self):
        """Overload of get_lT to get the copy from the metadata, so the deeepcopying
        takes place while loading and not during runtime
        """
        active_layer = _select_correct_layer(self, Points)
        if active_layer is None:
            return None
        return active_layer.metadata.get("lineageTree", None)

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)
        self.selected_trees = []
        lintr = self.get_lT()
        self.split = QSplitter()
        if lintr:
            self.lT = lintr  # extract_lineage(lintr, set(lintr.successor).difference(lintr.predecessor))
            self.roots = {
                root for root in self.lT.roots if self.lT.labels.get(root)
            }
            self.lnks_tms = self.lT.to_simple_graph(
                {
                    root
                    for root in self.lT.roots
                    if self.lT.labels.get(root, None)
                }
            )
            self.hiers = {
                i: hierarchical_pos(
                    g, g["root"], ycenter=-int(self.lT.time[g["root"]])
                )
                for i, g in self.lnks_tms.items()
            }
            nrows = np.round(np.sqrt(len(self.roots)))
            (
                self.figure,
                self.ax,
                self.ax2root,
                self.root2ax,
            ) = plot_lineages_for_tree_manip(
                self.lT,
                self.lnks_tms,
                self.hiers,
                nrows=nrows,
                figsize=(10, 15),
            )
            self.figure.subplots_adjust(
                wspace=0.01,
                hspace=0.01,
                top=0.98,
                bottom=0.0,
                right=0.98,
                left=0.02,
            )
            self.canvas = FigureCanvas(self.figure)
        else:
            self.lT = None
            self.figure, self.ax = plt.subplots(nrows=1, ncols=1)
            self.canvas = FigureCanvas(self.figure)
        self.canvas.mpl_connect("button_press_event", self._click_select)
        self.canvas.mpl_connect("button_press_event", self._zoom)
        self.viewer.layers.selection.events.active.connect(
            self.label_layer_change
        )
        control_layout = QVBoxLayout()
        control_layout.addStretch(1)
        self.control_screen = QWidget()
        self.control_screen.setLayout(control_layout)
        self.table = QTableWidget()
        self.table.setRowCount(5)
        self.table.setColumnCount(2)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setVisible(False)
        for i in range(5):
            self.table.setItem(i, 0, QTableWidgetItem("Item " + str(i)))
        self.control_screen.layout().addWidget(self.table)
        self.control_screen.layout().addWidget(
            widgets.Label(
                value="Click to select a tree.\nDouble Click to zoom in.\nScroll to un/-zoom\nLeft Click to pan\n Shift/- Right click to select\nZ to reset view\nDouble click to go to previous screen"
            ).native
        )
        fuse_button = QPushButton(text="Fuse trees")
        self.central = widgets.LineEdit(value="1").native
        self.left = widgets.LineEdit(value="1").native
        self.right = widgets.LineEdit(value="1").native
        fuse_container = containerize(
            [
                containerize(
                    [widgets.Label(value="Central Node").native, self.central]
                ),
                containerize(
                    [
                        widgets.Label(value="Left branch Length").native,
                        self.left,
                        widgets.Label(value="Right branch Length").native,
                        self.right,
                    ]
                ),
            ],
            horizontal=False,
        )
        fuse_button.pressed.connect(self.fuse_lineages)
        split_button = QPushButton(text="Split tree")
        split_button.pressed.connect(self.split_tree)
        delete_button = QPushButton(text="Delete branch")
        delete_button.pressed.connect(self.remove_nodes)
        add_button = QPushButton(text="Add a Sibling")
        self.set_length = widgets.LineEdit(value="10")
        add_button.pressed.connect(self.add_branch)
        modify_button = QPushButton(text="Modify Branch")
        self.change_length = widgets.LineEdit(value="10")
        modify_button.pressed.connect(self.modify_branch)
        copy_button = QPushButton(text="Create Copy of Sublineage")
        copy_button.pressed.connect(self.copy_lineage)
        complete_button = QPushButton(text="Complete Lineages")
        complete_button.pressed.connect(self.complete_lineage)
        save_new_lt_button = QPushButton(text="Make new layer of current tree")
        save_new_lt_button.pressed.connect(self.add_new_tree_to_viewer)
        self.control_screen.layout().addWidget(fuse_button)
        self.control_screen.layout().addWidget(fuse_container)
        self.control_screen.layout().addWidget(split_button)
        self.control_screen.layout().addWidget(delete_button)
        self.control_screen.layout().addWidget(
            containerize([self.set_length.native, add_button])
        )
        self.control_screen.layout().addWidget(
            containerize([self.change_length.native, modify_button])
        )
        self.control_screen.layout().addWidget(copy_button)
        self.control_screen.layout().addWidget(complete_button)
        self.control_screen.layout().addWidget(save_new_lt_button)
        self.live_ctrl_z = deque([], maxlen=15)
        self.ctrlz_deq = deque([], maxlen=15)
        self.ctrl_shift_z_deq = deque([], maxlen=5)
        self.pressed_key.connect(self.redo_z)
        self.pressed_key.connect(self.undo_z)
        self.setFocusPolicy(Qt.ClickFocus)
        self.destroyed.connect(lambda x: print("peos"))
        self.split.addWidget(self.canvas)
        self.split.addWidget(self.control_screen)
        all_layout = QVBoxLayout()
        all_layout.addStretch(1)
        self.setLayout(all_layout)
        self.layout().addWidget(self.split)
