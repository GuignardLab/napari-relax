from lineagetree import LineageTree
from magicgui import widgets
from qtpy.QtCore import QRegExp
from qtpy.QtGui import QRegExpValidator
from qtpy.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QLineEdit,
    QListWidget,
    QVBoxLayout,
    QWidget,
)

from .._layout_utils import SimpleContainer


class EmbryoComparisonTab(QWidget):
    """Template to produce specific tabs, these tabs are specifically used by cross embryo
    comparisons.

    Args:
        QWidget (_type_): _description_
    """

    def time_cropping(self) -> None:
        """Croping Handler."""
        text = self.time_cropper.text()
        if not text or text == 0:
            self.crop = None
        else:
            self.crop = int(text)
        self.time_cropper.setPlaceholderText(f"Final Timepoint: {self.crop}")
        self.time_cropper.update()
        self.time_cropper.clear()

    def show_roots(self) -> list:
        """Returns the list of roots selected to proccess.

        Returns:
            list: all roots
        """
        sp_roots = []
        for index in self.root_list.selectedIndexes():
            sp_roots.append(self.roots[index.row()][0])
        return sp_roots

    def times_selector(self) -> None:
        """
        This function reads the input times of the user which can be:
        a range if the number provided are 3 or 2
        a list of nodes if numbers provided by the user > 3 or 1
        """
        if self.times_list_check.isChecked():
            self.times = sorted(
                {int(num.strip()) for num in self.time_list.text().split(",")}
            )
        else:
            start = self.times_slicer.value.start
            stop = self.times_slicer.value.stop
            step = self.times_slicer.value.step
            if step == 0 or start == stop:
                self.times = [start]
            else:
                self.times = list(range(start, stop, step))

    def get_time_points(self) -> list:
        """Returns the times

        Returns:
            list: The times.
        """
        if self.times_list_check.isChecked():
            self.times = sorted(
                {int(num.strip()) for num in self.time_list.text().split(",")}
            )
        else:
            start = self.times_slicer.value.start
            stop = self.times_slicer.value.stop
            step = self.times_slicer.value.step
            if step == 0 or start == stop:
                self.times = [start]
            else:
                self.times = list(range(start, stop, step))

        return self.times

    def __init__(self, lineagetree: LineageTree, name):
        super().__init__()
        self.name = name  # lineagetree.name
        self.time_crop = None
        self.time_cropper = QLineEdit(
            placeholderText=f"Cropping time of the dataset {self.name}.",
            clearButtonEnabled=True,
        )  # type: ignore
        self.time_cropper.returnPressed.connect(self.time_cropping)
        self.times = [0]
        self.root_list = QListWidget()
        self.root_list.setSelectionMode(QListWidget.MultiSelection)
        selected_nodes = []
        already_used_nodes = set()
        for node, label in lineagetree.labels.items():
            node_to_add = node
            chain = lineagetree.get_chain_of_node(node)
            for node2 in chain:
                if node in lineagetree.labels:
                    node_to_add = node2
                    break
            if node not in already_used_nodes:
                selected_nodes.append([node_to_add, label])
            already_used_nodes.update(chain)
        self.roots = [
            (k, f"{v} - {k} starts from {lineagetree.time[k]} timepoint")
            for k, v in sorted(
                selected_nodes,
                key=lambda x: lineagetree.time[x[0]],
            )
        ]

        self.root_list.addItems([s for k, s in self.roots])

        self.times_slicer_check = QCheckBox(
            "Select a range of timepoints for comparison"
        )
        self.times_slicer_check.setChecked(True)
        self.times_slicer = widgets.SliceEdit(0, 100, 5, min=0)
        time_slice = SimpleContainer(
            [self.times_slicer_check, self.times_slicer.native],
            horizontal=False,
        )

        self.times_list_check = QCheckBox(
            "Select the timepoints for comparison"
        )
        self.times_list = QLineEdit()
        regex = QRegExp(r"^\s*-?\d+\s*(,\s*-?\d+\s*)*$")
        validator = QRegExpValidator(regex, self)
        self.times_list.setValidator(validator)
        times_list = SimpleContainer(
            [self.times_list_check, self.times_list], horizontal=False
        )

        self.time_group = QButtonGroup()
        self.time_group.addButton(self.times_slicer_check)
        self.time_group.addButton(self.times_list_check)
        self.time_group.setExclusive(True)

        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(time_slice)
        layout.addWidget(times_list)
        layout.addWidget(
            SimpleContainer(
                [
                    widgets.Label(
                        value="Final timepoint of lineagetree"
                    ).native,
                    self.time_cropper,
                ]
            )
        )
        layout.addWidget(self.root_list)
