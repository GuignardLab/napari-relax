import os
import pickle
from itertools import combinations
from pathlib import Path
from time import sleep

import matplotlib.pyplot as plt
import mplcursors
import numpy as np
import seaborn as sns
from lineagetree.tree_approximation import tree_style
from magicgui import widgets
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from matplotlib.figure import Figure
from napari._qt.qthreading import thread_worker
from napari.layers import Points
from napari.utils import progress
from qtpy.QtCore import QRegExp
from qtpy.QtGui import QIntValidator, QRegExpValidator
from qtpy.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

from ..._util_classes import (
    Layer_corrector_Tree_Producer,
    containerize,
    delayedtooltipeventfilter,
    tooltip_button,
)
from ..._utils import _select_correct_layer
from .histogram_comp import HistogramWidget


class Online_clustermap(Layer_corrector_Tree_Producer):
    """
    Widget to produce and load comparisons between lineages, which are used to
    plot Clustermaps and letting the user select respective Lineages.
    """

    name = "Distance Calculation"

    def add_spot_on_graph(self, cell, val, color, ax):
        """
        Function to add a spot on the networkx graphs, which is in the middle of a
        life cycle of the cell and calculates the correct position of the new cell.

        Args:
        cell (int): id of the cell
        val (int): the index of the list of networkx graphs.
        """
        active_layer = _select_correct_layer(self, Points)
        if not active_layer:
            return
        if cell not in active_layer.metadata["graphs"][1][val]:
            prev = self.lT.get_predecessors(cell)[0]
            prev_cycle = len(self.lT.get_predecessors(cell))
            after = self.lT.get_successors(cell)[-1]
            pos_prev = active_layer.metadata["graphs"][1][val][prev]
            pos_after = active_layer.metadata["graphs"][1][val][after]

            tmp_pos = np.array(pos_prev) - np.array([0, prev_cycle])
            ax.scatter(*tmp_pos, c=color, s=0.2, zorder=1001)
            ax.plot(
                (tmp_pos[0], pos_after[0]),
                (tmp_pos[1], pos_after[1]),
                c=color,
                linewidth=0.4,
                zorder=1000,
            )

    def _click(self, event):
        """
        Handles the left click of the clustermap plot. When clicked the corresponding sublineages will be
        plotted on the tree graph section and the points will be painted with the same colors while the rest
        will be white.
        Has a togglable part where the camera is transported to the timepoint of the division.
        Args:
            event: Button click (Right Click)

        """
        if event.button == 1 and event.inaxes:
            self.figure.canvas.mpl_disconnect(self.click_signal)
            active_layer = _select_correct_layer(self, Points)
            if not active_layer:
                return
            active_layer.face_color = "white"
            lineages = [
                self.names_of_nodes[int(event.xdata + 0.5)],
                self.names_of_nodes[int(event.ydata + 0.5)],
            ]
            label1 = [""] * len(self.labels_of_node_real)
            label1[int(event.xdata + 0.5)] = self.labels_of_node_real[
                int(event.xdata + 0.5)
            ]
            label2 = [""] * len(self.labels_of_node_real)
            label2[int(event.ydata + 0.5)] = self.labels_of_node_real[
                int(event.ydata + 0.5)
            ]
            self.ax_of_clustermap.set_xticks(
                np.arange(len(label1)), labels=label1
            )
            self.ax_of_clustermap.set_yticks(
                np.arange(len(label1)), labels=label2
            )
            self.ax_of_clustermap.tick_params(axis="x", colors="magenta")
            self.ax_of_clustermap.tick_params(axis="y", colors="cyan")
            plt.setp(
                self.ax_of_clustermap.get_xticklabels(),
                rotation=0,
                ha="center",
            )
            self.canvas.draw()
            colors = [[1, 128 / 255, 1, 1], [0, 1, 1, 1]]
            lineages = (
                [lineages[0]] if lineages[0] == lineages[1] else lineages
            )
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
            self.click_signal = self.figure.canvas.mpl_connect(
                "button_press_event", self._click
            )

    def reset_colorer(self):
        """
        Resets colors of points.
        """
        active_layer = _select_correct_layer(self, Points)
        if not active_layer:
            return
        active_layer.face_color = active_layer.metadata["clone2"]
        active_layer.refresh()

    def time_changer(self):
        """
        Called by the time_slider widget, will handle the time change and create the correct clustermap.
        """
        self.time = self.time_slider.value
        self._clustermap_creator()

    def _clustermap_creator(self):
        """
        Plots the clustermap for the timepoint specified by the time slider, where each element is the pairwise comparison of all the sublineages present in
        the timepoint selected.
        """
        plt.close("all")
        if not self.comps:
            return
        time = int(self.time_slider.value)
        comparisons = self.comps
        names = self.naming
        self.range = len(comparisons)
        len_all_trees = len(names[time].keys())
        hierarchy = np.zeros((len_all_trees, len_all_trees))
        labels_of_roots = [
            self.labels[names[time][i][1]] for i in range(len_all_trees)
        ]
        labels_of_nodes = [names[time][i][0] for i in range(len_all_trees)]

        labels_of_node_real = [
            self.lT.labels[names[time][i][2]] for i in range(len_all_trees)
        ]
        for keys, values in comparisons[time]:
            hierarchy[keys, values] = comparisons[time][
                keys, values
            ] / self.norm_dict[str(self.norm_combo.value)](
                self.norms[time][keys, values]
            )
            hierarchy[values, keys] = hierarchy[keys, values]

        condensed_dist_matrix = squareform(hierarchy)

        linkage_data = linkage(condensed_dist_matrix, method="ward")
        clustermap = sns.clustermap(
            hierarchy,
            xticklabels=labels_of_node_real,
            yticklabels=labels_of_node_real,
            cmap="vlag",
            row_linkage=linkage_data,
            col_linkage=linkage_data,
        )
        clustermap1 = clustermap.data2d
        self.plot = np.array(clustermap1)
        order = dendrogram(linkage_data, no_plot=True)["leaves"]
        labels_of_roots = [labels_of_roots[i] for i in order]
        labels_of_nodes = [labels_of_nodes[i] for i in order]
        labels_of_node_real = [labels_of_node_real[i] for i in order]
        self.names_of_nodes = labels_of_nodes
        self.names_of_roots = labels_of_roots
        self.labels_of_node_real = labels_of_node_real
        plot = self.ax_of_clustermap.imshow(
            clustermap1, cmap=self.colormap.value
        )
        if self.colorbar:
            self.colorbar.remove()
        self.colorbar = self.figure.colorbar(plot, ax=self.ax_of_clustermap)
        self.ax_of_clustermap.set_xticks(
            np.arange(len(labels_of_node_real)), labels=labels_of_node_real
        )
        self.ax_of_clustermap.set_yticks(
            np.arange(len(labels_of_node_real)), labels=labels_of_node_real
        )
        self.ax_of_clustermap.tick_params(axis="both", labelsize=10)
        plt.setp(
            self.ax_of_clustermap.get_xticklabels(),
            rotation=45,
            ha="right",
            rotation_mode="anchor",
        )
        self.ax_of_clustermap.set_title(
            f"Comparisons for Timepoint: {self.times[time]}"
        )
        self.ax_of_clustermap.set_aspect("auto")
        self.figure.tight_layout()
        self.canvas.draw()
        cursor = mplcursors.cursor(
            self.ax_of_clustermap,
            hover=2,  # Transient
            annotation_kwargs={
                "bbox": {
                    "boxstyle": "square,pad=0.2",
                    "facecolor": "white",
                    "alpha": 0.2,
                    "edgecolor": "#ddd",
                    "linewidth": 0.3,
                },
                "linespacing": 1,
                "arrowprops": None,
            },
        )
        cursor.connect(
            "add",
            lambda sel: sel.annotation.set_text(
                f"Value: {str(np.round(self.plot[[sel.index][0]],2))}\nNodes: {self.labels_of_node_real[[sel.index][0][0]]} ({self.names_of_nodes[[sel.index][0][0]]}) vs {self.labels_of_node_real[[sel.index][0][1]]}({self.names_of_nodes[[sel.index][0][1]]})"
            ),
        )

    def update_dictionary(self, product):
        """
        This function will read the yielded product from the thread_worker and will update the user interface
        Args:
            product [list]: [pairwise comparisons: name for each comparison]
        """
        if product is not None:
            self.comps, self.naming, self.norms = product
            self.time_slider.max = len(self.comps) - 1
            self._clustermap_creator()
            if self.pbr:
                self.pbr.update()

    def thread_handler(self):
        """
        This function will start the thread worker and connect the yielded  product to the update
        dictionary function. Also will set the run comparisons button checked, so it cannot be pressed again.
        """
        self.comps = []
        self.naming = []
        self.norms = []
        self.worker = self.thread_worker()

        self.times_selector()
        if not self.times:
            self.worker.quit()
            return
        self.pbr = progress(self.times)
        self.worker.yielded.connect(self.update_dictionary)
        self.worker.yielded.connect(self.tab3.receive_values)
        self.tab3.receive_labels_and_times(self.lT.labels, self.times)
        self.worker.start()
        self.runbutton.setChecked(True)
        self.stopbutton.setChecked(False)

    @thread_worker
    def thread_worker(self):
        """
        This function will calculate the pairwise comparisons of sublineages for multiple timepoints and yield them.
        """
        all_comps = []
        all_names = []
        all_norms = []
        if self.crop and self.crop != 0:
            times = [i for i in self.times if i < self.crop]
        else:
            times = self.times

        local_lT = self.lT
        for t in times:
            tmp_roots = [
                node
                for node in self.specific_roots
                if local_lT.time[node] <= t
            ]
            print(tmp_roots, "tmp_roots")
            if not tmp_roots:
                self.times.remove(t)
                continue
            tmp_name = {
                (
                    node,
                    local_lT.get_ancestor_at_t(node),
                    local_lT.get_labelled_ancestor(node),
                )
                for node in local_lT.nodes_at_t(r=list(tmp_roots), t=t)
            }
            print(tmp_name, "tmp_name")

            name = dict(enumerate(tmp_name))
            comparison = {}
            norms = {}
            comps = combinations(name.keys(), 2)
            for sleep_timer, (n1, n2) in enumerate(comps):
                (
                    comparison[n1, n2],
                    norms[n1, n2],
                ) = local_lT.unordered_tree_edit_distance(
                    name[n1][0],
                    name[n2][0],
                    end_time=self.crop,
                    style=self.styl,
                    downsample=int(self.downsampling_widget.value),
                    norm=None,
                    return_norms=True,
                )
                if sleep_timer % 5 == 0:
                    sleep(0.01)

            all_comps.append(comparison)
            all_names.append(name)
            all_norms.append(norms)
            yield (all_comps, all_names, all_norms)
            sleep(0.1)
        self.worker.quit()
        self.runbutton.setChecked(False)
        self.stopbutton.setChecked(True)
        self.pbr.close()
        self.pbr = None

    def times_selector(self):
        """
        This function reads the input times of the user which can be:
        a range if the number provided are 3 or 2
        a list of nodes if numbers provided by the user > 3 or 1
        """
        if self.time_list_check.isChecked():
            self.times = sorted(
                {int(num.strip()) for num in self.time_list.text().split(",")}
            )
        else:
            start = self.time_slicer.value.start
            stop = self.time_slicer.value.stop
            step = self.time_slicer.value.step
            if step == 0 or start == stop:
                self.times = [start]
            else:
                self.times = list(range(start, stop, step))

    def kill_thread(self):
        """
        Function to kill the thread if the user decides to.
        """
        self.worker.quit()
        self.stopbutton.setChecked(True)
        self.runbutton.setChecked(False)
        if self.pbr:
            self.pbr.clear()
            self.pbr.close()
            self.pbr = None

    def specific_roots_selector(self):
        """
        Saves the selection of the roots of each tree in a variable to be used by
        thread worker.
        """
        self.specific_roots = []
        for index in self.list_widget.selectedIndexes():
            self.specific_roots.append(
                self.list_of_selected_nodes[index.row()][0]
            )
        if self.specific_roots == []:
            self.specific_roots = self.lT.time_nodes[self.lT.t_b]

    def save_dictionary(self):
        """
        Saves the pairwise comparisons and names locally.
        """
        data = {
            "times": self.times,
            "comparisons": self.comps,
            "norms": self.norms,
            "names": self.names_of_nodes,
            "end_time": self.crop,
        }
        with open(str(self.save_pkl.value), "wb") as f:
            pickle.dump(data, f)

    def time_cropping(self):
        """
        Handles the cropping provided bu the time cropper widget.
        """
        text = self.time_cropper.text()
        if not text or text == 0:
            self.crop = None
        else:
            self.crop = int(text)
        self.time_cropper.setPlaceholderText(f"Final Timepoint: {self.crop}")
        self.time_cropper.update()
        self.time_cropper.clear()

    def label_update(self):
        """Function that is called from Progeny selection to update the labels."""
        self.list_widget.clear()
        selected_nodes = []
        already_used_nodes = set()
        for node, label in self.lT.labels.items():
            node_to_add = node
            chain = self.lT.get_chain_of_node(node)
            for node2 in chain:
                if node in self.lT.labels:
                    node_to_add = node2
                    break
            if node not in already_used_nodes:
                selected_nodes.append([node_to_add, label])
            already_used_nodes.update(chain)

        self.list_of_selected_nodes = [
            (k, f"{v} - {k} starts from {self.lT.time[k]} timepoint")
            for k, v in sorted(
                selected_nodes,
                key=lambda x: self.lT.time[x[0]],
            )
        ]
        self.list_widget.addItems([s for k, s in self.list_of_selected_nodes])
        self.list_widget.update()
        self.tab3.receive_labels_and_times(self.lT.labels, self.times)

    def c_layer_change(self, event):
        """Handles the layer change event.

        Args:
            event : The signal of layer change, it's important to note that you need to have one layer selected.
        """
        if event.value:
            self.lT = self.get_lT()
            self.labels = self.lT.labels
            self.range = 1
            self.names_of_nodes = None
            self.names_of_roots = None
            self.label_update()
            self.tab1.layout().update()
            self.layout().update()
            self.tab3.lT = self.lT
            self.tab3.layer_change()
            self.tab3.receive_labels_and_times(self.lT.labels, self.times)

    def update_tree_style(self):
        self.downsampling_widget.visible = False
        self.styl = self.tree_style_combobox.current_choice
        if self.styl == "downsampled":
            self.downsampling_widget.visible = True

    def __init__(self, napari_viewer):
        """
        Build the containers for the loading widget

        Args:
            napari_viewer (napari.Viewer): the parent napari viewer
        """
        super().__init__(napari_viewer)
        self.comps = []
        event_filt = delayedtooltipeventfilter()
        self.installEventFilter(event_filt)
        self.pbr = None
        self.times = []
        self.viewer = napari_viewer
        self.lT = self.get_lT()
        if self.lT:
            self.specific_roots = self.lT.time_nodes[self.lT.t_b]
            self.labels = self.lT.labels
        self.time = 1
        self.crop = None
        self.styl = "simple"
        self.downsampling_widget = widgets.ComboBox(
            value="2", choices=[f"{i}" for i in range(2, 30)]
        )
        self.possible_styles = tree_style.list_names()
        self.tree_style_combobox = widgets.ComboBox(
            value="simple", choices=self.possible_styles
        )
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(
            os.path.join(current_dir, "edit_distances.html"), encoding="utf-8"
        ) as f:
            txt = f.read()
        self.tree_style_combobox.tooltip = txt
        self.tree_style_combobox.changed.connect(self.update_tree_style)
        self.styl_combobox = containerize(
            [self.tree_style_combobox.native, self.downsampling_widget.native]
        )
        self.downsampling_widget.visible = False
        self.range = 1
        self.names_of_nodes = None
        self.names_of_roots = None
        self.runbutton = QPushButton("Run Comparisons")
        self.runbutton.native = self.runbutton
        self.runbutton.name = "runbutton"
        self.runbutton.setCheckable(True)
        self.stopbutton = QPushButton("Stop Processing")
        self.stopbutton.native = self.stopbutton
        self.stopbutton.name = "stopbutton"
        self.stopbutton.setCheckable(True)
        self.button_container = widgets.Container(
            widgets=[self.runbutton, self.stopbutton],
            layout="horizontal",
            labels=False,
        )
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
        self.reset_colors = QPushButton("Reset Colors")
        self.norm_combo = widgets.ComboBox(
            value="max",
            choices=["max", "sum", "None"],
        )
        self.norm_dict = {"max": max, "sum": sum, "None": lambda x: 1}
        self.colormap = widgets.ComboBox(
            value="viridis",
            choices=[
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
            ],
        )
        self.norm_color_cont = containerize(
            [self.norm_combo.native, self.colormap.native]
        )
        self.colormap.changed.connect(self._clustermap_creator)
        self.norm_combo.changed.connect(self._clustermap_creator)
        self.time_mover = widgets.Checkbox(value=False)
        time_mover_text = widgets.Label(value="Move in time")
        self.time_mover_box = widgets.Container(
            widgets=[time_mover_text, self.time_mover],
            layout="horizontal",
            labels=False,
        )
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        if self.lT:
            self.specific_roots = self.lT.time_nodes[self.lT.t_b]
            selected_nodes = []
            already_used_nodes = set()
            for node, label in self.lT.labels.items():
                node_to_add = node
                chain = self.lT.get_chain_of_node(node)
                for node2 in chain:
                    if node in self.lT.labels:
                        node_to_add = node2
                        break
                if node not in already_used_nodes:
                    selected_nodes.append([node_to_add, label])
                already_used_nodes.update(chain)
            self.list_of_selected_nodes = [
                (k, f"{v} - {k} starts from {self.lT.time[k]} timepoint")
                for k, v in sorted(
                    selected_nodes,
                    key=lambda x: self.lT.time[x[0]],
                )
            ]
            self.list_widget.addItems(
                [s for k, s in self.list_of_selected_nodes]
            )
        self.list_widget.itemSelectionChanged.connect(
            self.specific_roots_selector
        )
        # For plot tab#
        self.figures, self.axes_for_tree_graphs = plt.subplots(
            nrows=1, ncols=2, figsize=(1, 2), sharey=True
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
        time_cropper_validator = QIntValidator()
        self.time_cropper.setValidator(time_cropper_validator)
        self.time_cropper.returnPressed.connect(self.time_cropping)
        label_for_style = widgets.Label(
            value="Select approximation for tree comparison.\n"
        )
        self.time_slicer = widgets.SliceEdit(0, 30, 5, min=0)
        self.time_slicer_check = QCheckBox(
            "Select a range of timepoints for comparison"
        )
        time_slice = containerize(
            [self.time_slicer_check, self.time_slicer.native], horizontal=False
        )
        self.time_slicer_check.setChecked(True)
        self.time_list = QLineEdit()
        self.time_list.setPlaceholderText("")
        self.time_list_check = QCheckBox(
            "Select the timepoints for comparison"
        )
        time_list = containerize(
            [self.time_list_check, self.time_list], horizontal=False
        )
        regex = QRegExp(r"^\s*-?\d+\s*(,\s*-?\d+\s*)*$")
        validator = QRegExpValidator(regex, self)
        self.time_list.setValidator(validator)

        self.time_group = QButtonGroup()
        self.time_group.addButton(self.time_slicer_check)
        self.time_group.addButton(self.time_list_check)
        self.time_group.setExclusive(True)

        # Layout of 1st tab
        self.tab1 = QWidget()
        layout1 = QVBoxLayout()
        self.tab1.setLayout(layout1)
        self.tab1.layout().addWidget(
            widgets.Label(value="Select the desired roots.").native
        )
        self.tab1.layout().addWidget(self.list_widget)

        self.tab1.layout().addWidget(
            widgets.Label(value="\nSelect roots to be compared:").native
        )

        self.tab1.layout().addWidget(time_slice)
        self.tab1.layout().addWidget(time_list)
        self.tab1.layout().addWidget(
            containerize(
                [
                    widgets.Label(
                        value="Final timepoint of lineagetree"
                    ).native,
                    self.time_cropper,
                ]
            )
        )
        self.tab1.layout().addWidget(
            containerize([label_for_style.native, self.styl_combobox])
        )
        self.colorbar = None

        # Layout of 2nd tab
        self.tab2 = QWidget()
        layout2 = QVBoxLayout()
        self.tab2.setLayout(layout2)
        self.figure = Figure(figsize=(3, 3), constrained_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.ax_of_clustermap = self.figure.add_subplot(111)
        self.tab2.layout().setContentsMargins(2, 1, 2, 0)
        self.tab2.layout().addWidget(self.tree_canvas)
        self.tab2.layout().addWidget(
            containerize(
                [
                    self.reset_colors,
                    self.time_mover_box.native,
                ]
            )
        )
        self.tab2.layout().addWidget(self.norm_color_cont)
        self.tab2.layout().addWidget(self.canvas)
        self.tab2.layout().addWidget(self.time_slider.native)
        self.tab2.layout().addWidget(container.native)

        self.tab3 = HistogramWidget(self.lT)
        # Rest Layout
        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        self.tabs.addTab(self.tab1, "Configuration Options")
        self.tabs.addTab(self.tab2, "Tree Plots")
        self.tabs.addTab(self.tab3, "Histograms")

        self.setLayout(layout)
        self.layout().addWidget(self.tabs)
        self.layout().addWidget(self.button_container.native)
        self.figure.tight_layout()
        self.runbutton.released.connect(self.thread_handler)
        self.reset_colors.clicked.connect(self.reset_colorer)
        self.click_signal = self.figure.canvas.mpl_connect(
            "button_press_event", self._click
        )
        self.stopbutton.released.connect(self.kill_thread)
        self.stopbutton.setChecked(True)
        self.viewer.layers.selection.events.active.connect(self.c_layer_change)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(
            os.path.join(current_dir, "clustermap.html"), encoding="utf-8"
        ) as f:
            txt2 = f.read()
        self.tooltip = tooltip_button(txt2)
        self.tooltip.setParent(self)
        self.tooltip.move(int(self.width() - self.tooltip.width()), 0)
        with open(
            os.path.join(current_dir, "normalization.html"), encoding="utf-8"
        ) as f:
            txt3 = f.read()
        self.norm_combo.tooltip = txt3

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.tooltip.move(self.width() - self.tooltip.width(), 0)
