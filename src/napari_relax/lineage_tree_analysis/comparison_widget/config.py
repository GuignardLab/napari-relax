import os
from itertools import combinations
from time import sleep

from lineagetree.tree_approximation import tree_style
from magicgui import widgets
from napari._qt.qthreading import thread_worker
from napari.utils import notifications
from qtpy.QtCore import QRegExp
from qtpy.QtGui import QIntValidator, QRegExpValidator
from qtpy.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QLineEdit,
    QListWidget,
    QVBoxLayout,
)

from ..._util_classes import (
    Containerize,
    LayerCorrectorTreeProducer,
)
from ..._util_classes.tooltip import TooltipButton


class ConfigurationPanel(LayerCorrectorTreeProducer):
    """Widget to calculate the pairwise comparisons of any configuration selected."""

    name = "ConfigurationPanel"

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
                    sleep(0.1)

            all_comps.append(comparison)
            all_names.append(name)
            all_norms.append(norms)
            yield (all_comps, all_names, all_norms, self.times)

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
            if start < self.lT.t_b:
                notifications.show_error(
                    "Starting timepoint cannot be smaller than the first timepoint of the dataset."
                )
                return
            if step == 0 or start == stop:
                self.times = [start]
            else:
                self.times = list(range(start, stop, step))

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
        if self.lT:
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
            self.list_widget.update()

    def layer_change(self, event):
        """Handles the layer change event.

        Args:
            event : The signal of layer change, it's important to note that you need to have one layer selected.
        """
        if event.value:
            self.lT = self.get_lT()
            if self.lT:
                start = self.lT.t_b
                stop = self.lT.t_b + 30
                self.labels = self.lT.labels
            else:
                start = 0
                stop = 30
            self.time_slicer.start.value = start
            self.time_slicer.stop.value = stop
            self.range = 1
            self.names_of_nodes = None
            self.names_of_roots = None
            self.label_update()
            self.layout().update()

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
        self.styl_combobox = Containerize(
            [self.tree_style_combobox.native, self.downsampling_widget.native]
        )
        self.downsampling_widget.visible = False
        self.range = 1
        self.names_of_nodes = None
        self.names_of_roots = None
        self.norm_combo = widgets.ComboBox(
            value="max",
            choices=["max", "sum", "None"],
        )
        self.norm_dict = {"max": max, "sum": sum, "None": lambda x: 1}
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
        if self.lT:
            start = self.lT.t_b
            stop = self.lT.t_b + 30
        else:
            start = 0
            stop = 30
        self.time_slicer = widgets.SliceEdit(start, stop, 5, min=0)
        self.time_slicer_check = QCheckBox(
            "Select a range of timepoints for comparison"
        )
        time_slice = Containerize(
            [self.time_slicer_check, self.time_slicer.native], horizontal=False
        )
        self.time_slicer_check.setChecked(True)
        self.time_list = QLineEdit()
        self.time_list.setPlaceholderText("")
        self.time_list_check = QCheckBox(
            "Select the timepoints for comparison"
        )
        time_list = Containerize(
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
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.layout().addWidget(time_slice)
        self.layout().addWidget(time_list)
        self.layout().addWidget(
            Containerize(
                [
                    widgets.Label(
                        value="Final timepoint of lineagetree"
                    ).native,
                    self.time_cropper,
                ]
            )
        )
        self.layout().addWidget(label_for_style.native)
        self.layout().addWidget(self.styl_combobox)
        self.layout().addWidget(
            widgets.Label(value="\nSelect roots to be compared:").native
        )
        self.layout().addWidget(self.list_widget)
        self.viewer.layers.selection.events.active.connect(self.layer_change)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(
            os.path.join(current_dir, "config.html"),
            encoding="utf-8",
        ) as f:
            txt = f.read()
        self.node_tooltip = TooltipButton(txt)
        self.node_tooltip.setParent(self)
        self.node_tooltip.move(self.width() - self.node_tooltip.width(), 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.node_tooltip.move(self.width() - self.node_tooltip.width(), 0)
