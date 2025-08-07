import copy
from functools import partial
from itertools import combinations
from pathlib import Path
from time import sleep

import matplotlib.pyplot as plt
import mplcursors
import pickle
import numpy as np
import seaborn as sns
from lineagetree.tree_approximation import tree_style
from magicgui import widgets
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from matplotlib.figure import Figure
from matplotlib.patheffects import withSimplePatchShadow
from napari._qt.qthreading import thread_worker
from napari.components.viewer_model import ViewerModel
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

from .._reader import layer_preparation
from .._util_classes import (
    Layer_corrector_Tree_Producer,
    QtViewerWrap,
    big_dataset_names_dialog,
    containerize,
    delayedtooltipeventfilter,
    tab_template,
)


class minimal_cell_size(Layer_corrector_Tree_Producer):
    def change(
        self,
        viewer: QtViewerWrap,
        slider,
        other_viewer,
        other_slider,
        event,
    ):
        if active_layer := viewer.layers.selection.active:
            if not self.toggle_all.value:
                new_size = slider.value()  # type: ignore
                active_layer.size = new_size
                slider.setToolTip(
                    f"Change the size of the spheres on the viewer. Current size {slider.value()}"
                )
            else:
                new_size = slider.value()  # type: ignore
                active_layer.size = new_size
                other_viewer.layers.selection.active.size = new_size
                other_slider.setValue(new_size)
                slider.setToolTip(
                    f"Change the size of the spheres on the viewer. Current size {slider.value()}"
                )
                other_slider.setToolTip(
                    f"Change the size of the spheres on the viewer. Current size {slider.value()}"
                )

    def __init__(self, napari_viewer, napari_viewer_1, napari_viewer_2):
        super().__init__(napari_viewer)
        event_filt = delayedtooltipeventfilter()
        self.installEventFilter(event_filt)
        self.viewer_1 = napari_viewer_1
        self.viewer_2 = napari_viewer_2
        self.toggle_all = widgets.CheckBox(value=False)
        toggle_container = widgets.Container(
            widgets=[
                widgets.Label(value="Both viewers"),
                self.toggle_all,
            ],
            layout="vertical",
            labels=False,
        )
        layout = QHBoxLayout()
        layout.addStretch(1)
        self.setLayout(layout)
        self.slider_1 = QSlider()
        self.slider_1.setOrientation(Qt.Orientation.Horizontal)
        self.slider_1.setTickInterval(1)
        self.slider_1.setMinimum(0)
        self.slider_1.setMaximum(2000)
        self.slider_1.setValue(200)
        self.slider_1.setToolTip(
            f"Change the size of the spheres on the viewer. Current size {self.slider_1.value()}"
        )
        self.slider_2 = QSlider()
        self.slider_2.setOrientation(Qt.Orientation.Horizontal)
        self.slider_2.setTickInterval(1)
        self.slider_2.setMinimum(0)
        self.slider_2.setMaximum(2000)
        self.slider_2.setValue(200)
        self.slider_2.setToolTip(
            f"Change the size of the spheres on the viewer. Current size {self.slider_2.value()}"
        )

        self.change_size_2 = partial(
            self.change,
            self.viewer_2,
            self.slider_2,
            self.viewer_1,
            self.slider_1,
        )
        self.slider_2.valueChanged.connect(self.change_size_2)
        self.change_size_1 = partial(
            self.change,
            self.viewer_1,
            self.slider_1,
            self.viewer_2,
            self.slider_2,
        )
        self.slider_1.valueChanged.connect(self.change_size_1)

        slid_container = containerize(
            [self.slider_1, self.slider_2], horizontal=False
        )
        slid_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.slider_1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.slider_2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.layout().addWidget(widgets.Label(value="Size of spheres").native)
        self.layout().addWidget(slid_container)
        self.layout().addWidget(toggle_container.native)


class Embryo_comparisons(Layer_corrector_Tree_Producer):
    name = "Embryo comparisons"

    def get_lt_manager(self, signal):
        """
        Gets the lineagetree manager object every time is
        changed Manager class.
        """
        self.manager = signal
        self.lineagetree_list.clear()
        self.lineagetree_list.addItems(
            [f"{key}" for key in self.manager.lineagetrees]
        )
        self.lineagetree_list.update()
        self.layers = {
            layer.metadata.get("name_for_manager", ""): layer
            for layer in self.viewer.layers
        }

    def tab_maker(self):
        selected_items = self.lineagetree_list.selectedItems()
        self.tab_dictionary = {}
        for _ in range(self.root_tabs.count()):
            self.root_tabs.removeTab(0)
        if len(selected_items) < 1:
            default_tab = QWidget()
            default_layout = QVBoxLayout()
            default_layout.addStretch(1)
            default_tab.setLayout(default_layout)
            self.root_tabs.addTab(default_tab, "Empty Layout")
        else:
            for item in selected_items:
                self.tab_dictionary[item.text()] = tab_template(
                    self.manager.lineagetrees[item.text()], item.text()
                )
                self.root_tabs.addTab(
                    self.tab_dictionary[item.text()], item.text()
                )

        self.root_tabs.update()
        self.tab1.layout().update()

    def add_spot_on_graph(self, cell, index, lineagetree_name):
        """Adds a spot on the graph on the correct place if it does not exist on the graph.

        Args:
            cell (int): The if of the cell
            index (int): Index of the list of networkx graphs
            lineagetree_name (str): The name of the lineagetree on the layers and self.manager
        """
        lt = self.manager.lineagetrees[lineagetree_name]
        graph = self.layers[lineagetree_name].metadata["graphs"][0][index]
        pos = self.layers[lineagetree_name].metadata["graphs"][1][index]

        if cell not in graph:
            prev = lt.get_predecessors(cell)[0]
            after = lt.get_successors(cell)[-1]
            graph.remove_edge(prev, after)
            graph.add_node(cell)
            graph.add_edge(prev, cell)
            graph.add_edge(cell, after)
            vector = np.array(pos[list(graph.pred[cell])[0]])
            pos[cell] = vector - [0, len(lt.get_predecessors(cell))]

    def paint_sublineage(self, cell, index, color, lineagetree_name):
        if isinstance(color, int):
            color = "magenta" if color == 0 else "cyan"
        color_map = []
        active_layer = self.layers[lineagetree_name]
        lT = self.manager.lineagetrees[lineagetree_name]
        sub_tree = set(lT.get_subtree_nodes(cell))
        for cell1 in active_layer.metadata["graphs"][0][index]:
            if cell1 in sub_tree:
                color_map.append(color)
            else:
                color_map.append("black")
        return color_map

    def reset_graph(self, cell, index, lineagetree_name):
        layer = self.layers[lineagetree_name]
        lt = layer.metadata["LineageTree"]
        if cell in layer.metadata["graphs"][0][index]:
            prev, after = (
                lt.get_node_chain(cell)[0],
                lt.get_node_chain(cell)[-1],
            )
            layer.metadata["graphs"][0][index].remove_node(cell)
            layer.metadata["graphs"][0][index].add_edge(prev, after)

    def tree_painter(self, node, lineagetree_name, color, ax):
        """Paints the correct sublineage on the tree graph

        Args:
            node (int): The name of the first node of the sub/-lineage
            lineagetree_name (str): The name of the lineagetree saved in the manager and the layers.
            color (list|color): The color the tree has to be painted.
            ax (ax object): Matplotlib object where the tree will be graphed.
        """
        lT = self.manager.lineagetrees[lineagetree_name]
        index = Layer_corrector_Tree_Producer(self.viewer).val_finder(
            node, lT, self.layers[lineagetree_name].metadata["graphs"][0]
        )
        ax.clear()
        lT.draw_tree_graph(
            self.layers[lineagetree_name].metadata["graphs"][1][index],
            self.layers[lineagetree_name].metadata["graphs"][0][index],
            selected_nodes=lT.get_subtree_nodes(node),
            selected_edges=lT.get_subtree_nodes(node),
            color_of_nodes=color,
            color_of_edges=color,
            ax=ax,
        )
        self.tree_canvas.draw()

    def sub_points_painter(self, node, lineagetree_name, viewer, color):
        """
        Adds all descendants of a cell to selected_data.
        Reads the selected data from napari.layer and it will select all the cells that are ancestors of this point.
        """
        existing = [
            layer.metadata.get("name_for_manager")
            for layer in self.viewer.layers
        ]
        if lineagetree_name not in existing:
            data = layer_preparation(
                self.manager.lineagetrees[lineagetree_name],
                path=lineagetree_name + ".lT",
            )[0]
            data[1]["metadata"]["name_for_manager"] = lineagetree_name
            self.viewer.add_points(data[0], **data[1])
        viewer.layers.clear()
        viewer.dims.ndisplay = 3
        data = layer_preparation(
            self.manager.lineagetrees[lineagetree_name],
            path=lineagetree_name + ".lT",
        )[0]
        data[1]["metadata"]["name_for_manager"] = lineagetree_name
        viewer.add_points(data[0], **data[1])
        for layer in viewer.layers:
            layer.face_color = "white"
        self.layers = {
            layer.metadata.get("name_for_manager", ""): layer
            for layer in self.viewer.layers
        }
        self.viewer.layers.selection.active = self.layers[lineagetree_name]
        active_layer = viewer.layers.selection.active
        lT = active_layer.metadata["LineageTree"]
        active_layer.selected_data.add(
            active_layer.metadata["lT2napari"][node]
        )
        scores = lT.get_subtree_nodes(node)
        for val in scores:
            active_layer.selected_data.add(
                active_layer.metadata["lT2napari"][val]
            )
        active_layer.face_color[list(active_layer.selected_data)] = color
        active_layer.refresh()
        active_layer.selected_data.clear()

    def _click(self, event):
        if event.button == 1:
            layers = [
                self.labels_lT[int(event.xdata + 0.5)],
                self.labels_lT[int(event.ydata + 0.5)],
            ]
            nodes = [
                self.labels_node[int(event.xdata + 0.5)],
                self.labels_node[int(event.ydata + 0.5)],
            ]
            colors = [[1, 128 / 255, 1, 1], [0, 1, 1, 1]]
            for i, (node, lT) in enumerate(zip(nodes, layers, strict=False)):
                self.sub_points_painter(node, lT, self.viewers[i], colors[i])
                self.tree_painter(node, lT, colors[i], self.axes[i])
            label1 = [""] * len(self.labels_of_clustermap)
            label1[int(event.xdata + 0.5)] = self.labels_of_clustermap[
                int(event.xdata + 0.5)
            ]
            label2 = [""] * len(self.labels_of_clustermap)
            label2[int(event.ydata + 0.5)] = self.labels_of_clustermap[
                int(event.ydata + 0.5)
            ]
            self.ax1.set_xticks(np.arange(len(label1)), labels=label1)
            self.ax1.set_yticks(np.arange(len(label1)), labels=label2)
            self.ax1.tick_params(axis="x", colors="magenta")
            self.ax1.tick_params(axis="y", colors="cyan")
            plt.setp(
                self.ax1.get_xticklabels(),
                rotation=45,
                ha="center",
            )
            self.canvas.draw()

    def clustermap_creator(self):
        plt.close("all")
        time = int(self.time_slider.value)

        self.range = len(self.comparisons)

        len_all_trees = len(self.names[time].keys())
        hierarchy = np.zeros((len_all_trees, len_all_trees))
        self.labels_lT = [self.names[time][n][0] for n in self.names[time]]
        self.labels_root = [self.names[time][n][2] for n in self.names[time]]
        self.labels_node = [self.names[time][n][1] for n in self.names[time]]
        self.labels = [
            self.manager.lineagetrees[self.names[time][n][0]].labels[
                self.manager.lineagetrees[
                    self.names[time][n][0]
                ].get_labelled_ancestor(self.names[time][n][1])
            ]
            for n in self.names[time]
        ]
        self.labels_of_clustermap = [
            self.names[time][n][0] + "_" + str(self.labels[n])
            for n in self.names[time]
        ]
        for keys, values in self.comparisons[time]:
            hierarchy[keys, values] = self.comparisons[time][
                keys, values
            ] / self.norm_dict[str(self.norm_combo.value)](
                self.norms[time][keys, values]
            )
            hierarchy[values, keys] = hierarchy[keys, values]

        condensed_dist_matrix = squareform(hierarchy)

        linkage_data = linkage(condensed_dist_matrix, method="ward")
        order = dendrogram(linkage_data, no_plot=True)["leaves"]
        self.labels_of_clustermap = [
            self.labels_of_clustermap[i] for i in order
        ]
        self.labels_lT = [self.labels_lT[i] for i in order]
        self.labels_node = [self.labels_node[i] for i in order]
        self.labels_root = [self.labels_root[i] for i in order]

        clustermap = sns.clustermap(
            hierarchy,
            xticklabels=self.labels_of_clustermap,
            yticklabels=self.labels_of_clustermap,
            cmap="vlag",
            row_linkage=linkage_data,
            col_linkage=linkage_data,
        )
        clustermap1 = clustermap.data2d
        self.plot = np.array(clustermap1)
        plot = self.ax1.imshow(clustermap1, cmap=self.colormap.value)
        if self.colorbar:
            self.colorbar.remove()
        self.colorbar = self.figure.colorbar(plot, ax=self.ax1)
        self.ax1.set_xticks(
            np.arange(len(self.labels_of_clustermap)),
            labels=self.labels_of_clustermap,
        )
        self.ax1.set_yticks(
            np.arange(len(self.labels_of_clustermap)),
            labels=self.labels_of_clustermap,
        )
        plt.setp(
            self.ax1.get_xticklabels(),
            rotation=45,
            ha="right",
        )
        self.ax1.set_aspect("auto")
        cursor = mplcursors.cursor(
            self.ax1,
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
                f"Value: {str(np.round(self.plot[[sel.index][0]],2))}\nNodes: {self.labels_of_clustermap[[sel.index][0][0]]} ,({self.labels_node[[sel.index][0][0]]}, Time: {self.manager.lineagetrees[self.labels_lT[[sel.index][0][0]]].time[self.labels_node[[sel.index][0][0]]]}) \nvs\n{self.labels_of_clustermap[[sel.index][0][1]]}({self.labels_node[[sel.index][0][1]]}, Time: {self.manager.lineagetrees[self.labels_lT[[sel.index][0][1]]].time[self.labels_node[[sel.index][0][1]]]})"
            ),
        )
        self.canvas.draw()

    def save_dictionary(self):
        roots = {}
        times = {}
        end_times = {}
        for tab in self.tab_dictionary:
            roots[tab] = self.tab_dictionary[tab].show_roots()
            times[tab] = self.tab_dictionary[tab].ret_times()
            end_times[tab] = self.tab_dictionary[tab].time_crop

        data = {
            "roots": roots,
            "times": times,
            "end_times": end_times,
            "comparisons": self.comparisons,
            "norms": self.norms,
            "names": self.names,
        }
        with open(str(self.save_pkl.value), "wb") as f:
            pickle.dump(data, f)

    @thread_worker
    def roots_selector(self):
        roots = {}
        times = {}
        end_times = {}
        all_comparisons = []
        all_names = []
        all_norms = []
        local_manager = copy.copy(self.manager)
        for tab in self.tab_dictionary:
            roots[tab] = self.tab_dictionary[tab].show_roots()
            times[tab] = self.tab_dictionary[tab].ret_times()
            end_times[tab] = self.tab_dictionary[tab].time_crop
        minimum_length = 1_000
        for tab in times:
            minimum_length = min(len(times[tab]), minimum_length)
        for t in range(int(minimum_length)):
            comparisons = {}
            self.all_roots = [
                (
                    lt,
                    selected_root,
                    int(node),
                )
                for lt in roots
                for node in roots[lt]
                for selected_root in local_manager.lineagetrees[lt].nodes_at_t(
                    times[lt][t], int(node)
                )
            ]
            names = dict(enumerate(self.all_roots))
            norms = {}
            combs = combinations(names.keys(), 2)
            for sleep_timer, (n1, n2) in enumerate(combs):
                (
                    comparisons[n1, n2],
                    norms[n1, n2],
                ) = local_manager.cross_lineage_edit_distance(
                    names[n1][1],
                    names[n1][0],
                    names[n2][1],
                    names[n2][0],
                    end_times[names[n1][0]],
                    end_times[names[n2][0]],
                    style=self.comp_style,
                    downsample=int(
                        self.downsampling_widget.currentText().split(" ")[0]
                    ),
                    return_norms=True,
                )

                if sleep_timer % 5 == 0:
                    sleep(0.1)
            all_comparisons.append(comparisons)
            all_names.append(names)
            all_norms.append(norms)
            yield all_comparisons, all_names, all_norms
        self.worker.quit()
        self.runbutton.setChecked(False)
        self.stopbutton.setChecked(True)

    @property
    def lcm(self):
        tmp_tr = []
        for item in self.lineagetree_list.selectedItems():
            tmp_tr.append(
                int(self.manager.lineagetrees[item.text()]._time_resolution)
            )
        if len(tmp_tr) == 1:
            return tmp_tr.pop()
        elif tmp_tr:
            return np.lcm.reduce(tmp_tr)
        return 1

    def kill_thread(self):
        """
        Function to kill the thread if the user decides to.
        """
        self.worker.quit()
        self.stopbutton.setChecked(True)
        self.runbutton.setChecked(False)

    def thread_handler(self):
        continue_comps = True
        self.comparisons = []
        self.names = []
        self.norms = []
        for lineagetree in self.manager.lineagetrees:
            if len(lineagetree) > 6:
                continue_comps = big_dataset_names_dialog()
                continue_comps.exec_()
                continue_comps = continue_comps.continue_proccess
                break
        if continue_comps:
            self.worker = self.roots_selector()
            self.worker.yielded.connect(self.update_comparisons)
            self.worker.start()
            self.runbutton.setChecked(True)
            self.stopbutton.setChecked(False)

    def update_comparisons(self, product):
        self.comparisons, self.names, self.norms = product
        self.time_slider.max = len(product[0]) - 1
        self.clustermap_creator()

    def time_changer(self):
        self.time = self.time_slider.value
        self.clustermap_creator()

    def update_tree_style(self):
        self.downsampling_widget.setVisible(False)
        self.comp_style = self.tree_style_combobox.current_choice
        if self.comp_style == "downsampled":
            self.downsampling_widget.setVisible(True)

    def change_downsampling_rates(self):
        self.downsampling_widget.clear()
        for i in [f"{i} downsampling rate" for i in range(1, 30)]:
            self.downsampling_widget.addItem(i)

    def change_tooltip_for_downsample(self):
        cur_text = self.downsampling_widget.currentText().split(" ")
        if cur_text[0]:
            down_factor = int(cur_text[0])
            list_of_selected_emryos = [
                f"{lt.text()} with downsampling: {down_factor*self.lcm/self.manager.lineagetrees[lt.text()]._time_resolution}"
                for lt in self.lineagetree_list.selectedItems()
            ]

            self.downsampling_widget.setToolTip(
                "\n".join(
                    ["Real downsampling rates:\n", *list_of_selected_emryos]
                )
            )
        else:
            self.downsampling_widget.setToolTip("")

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)
        self.tabs = QTabWidget()
        self.tab_dictionary = {}
        self.viewer = napari_viewer
        all_splitter = QSplitter()
        self.viewer_model1 = ViewerModel(title="SPC 1")
        self.viewer_model2 = ViewerModel(title="SPC 2")
        self.viewers = [self.viewer_model1, self.viewer_model2]
        self.qt_viewer1 = QtViewerWrap(napari_viewer, self.viewer_model1)
        self.qt_viewer2 = QtViewerWrap(napari_viewer, self.viewer_model2)
        viewer_splitter = QSplitter()
        viewer_splitter.setOrientation(Qt.Vertical)
        viewer_splitter.addWidget(self.qt_viewer1)
        sliders = minimal_cell_size(
            napari_viewer, self.viewer_model1, self.viewer_model2
        )
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
        self.colormap.changed.connect(self.clustermap_creator)
        self.norm_combo.changed.connect(self.clustermap_creator)
        viewer_splitter.addWidget(sliders)
        viewer_splitter.addWidget(self.qt_viewer2)
        viewer_splitter.setContentsMargins(0, 0, 0, 0)
        self.comp_style = "simple"
        self.possible_styles = tree_style.list_names()
        self.lineagetree_list = QListWidget()
        self.lineagetree_list.setSelectionMode(QListWidget.MultiSelection)
        self.lineagetree_list.itemSelectionChanged.connect(self.tab_maker)
        self.downsampling_widget = QComboBox()
        self.downsampling_widget.addItems(
            [
                f"{i} downsampling rate"
                for i in range(1, self.lcm * 30, self.lcm)
            ]
        )
        self.downsampling_widget.setVisible(False)
        self.downsampling_widget.currentIndexChanged.connect(
            self.change_tooltip_for_downsample
        )
        self.lineagetree_list.itemSelectionChanged.connect(
            self.change_downsampling_rates
        )
        self.tree_style_combobox = widgets.ComboBox(
            value="simple", choices=self.possible_styles
        )
        self.styl_combobox = containerize(
            [self.tree_style_combobox.native, self.downsampling_widget]
        )
        self.tree_style_combobox.changed.connect(self.update_tree_style)
        self.downsampling_widget.visible = False
        label_for_style = widgets.Label(
            value="Select approximation for tree comparison.\n"
        )
        self.runbutton = QPushButton("Run Comparisons")
        self.runbutton.native = self.runbutton
        self.runbutton.name = "runbutton"
        self.runbutton.clicked.connect(self.thread_handler)
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
        self.figures, self.axes = plt.subplots(
            nrows=1, ncols=2, figsize=(4, 3)
        )
        for ax in self.axes:
            ax.axis("off")
        self.tree_canvas = FigureCanvas(self.figures)
        self.time_mover = widgets.Checkbox(value=False)
        time_mover_text = widgets.Label(value="Move in time")
        self.time_mover_box = widgets.Container(
            widgets=[time_mover_text, self.time_mover],
            layout="horizontal",
            labels=False,
        )
        self.range = 0
        self.time_slider = widgets.IntSlider(min=0, max=self.range)
        self.time_slider.changed.connect(self.time_changer)
        self.tab1 = QWidget()
        self.root_tabs = QTabWidget()
        layout_1 = QVBoxLayout()
        layout_1.addStretch(1)
        self.tab1.setLayout(layout_1)
        self.tab1.layout().addWidget(label_for_style.native)
        self.tab1.layout().addWidget(self.styl_combobox)
        self.tab1.layout().addWidget(self.lineagetree_list)
        self.tab1.layout().addWidget(self.root_tabs)
        self.tab_maker()

        self.tab2 = QWidget()
        layout_2 = QVBoxLayout()
        layout_2.addStretch(1)
        self.tab2.setLayout(layout_2)
        self.figure = Figure(figsize=(3, 3), constrained_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.colorbar = None
        self.ax1 = self.figure.add_subplot(111)
        self.tab2.layout().addWidget(self.tree_canvas)

        self.tab2.layout().addWidget(
            containerize([self.norm_combo.native, self.colormap.native])
        )
        self.tab2.layout().addWidget(self.time_mover_box.native)
        self.tab2.layout().addWidget(self.time_mover_box.native)
        self.tab2.layout().addWidget(self.canvas)
        self.tab2.layout().addWidget(self.time_slider.native)

        whole_layout = QVBoxLayout()
        whole_layout.addStretch(1)
        self.widget = QWidget()
        self.widget.setLayout(whole_layout)
        self.tabs.addTab(self.tab1, "Configuration")
        self.tabs.addTab(self.tab2, "Plots")

        self.widget.layout().addWidget(self.tabs)
        self.widget.layout().addWidget(self.button_container.native)
        all_splitter.addWidget(viewer_splitter)
        all_splitter.addWidget(self.widget)
        all_layout = QVBoxLayout()
        self.setLayout(all_layout)
        all_layout.addWidget(all_splitter)
        self.stopbutton.released.connect(self.kill_thread)
        self.stopbutton.setChecked(True)
        self.figure.canvas.mpl_connect("button_press_event", self._click)
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
        self.tab2.layout().addWidget(container.native)
