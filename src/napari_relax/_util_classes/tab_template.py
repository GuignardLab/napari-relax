from lineagetree import LineageTree
from magicgui import widgets

try:
    from qtpy.QtCore import QRegExp
    from qtpy.QtGui import QRegExpValidator
except:
    from qtpy.QtCore import QRegularExpression as QRegExp
    from qtpy.QtGui import QRegularExpressionValidator as QRegExpValidator

from qtpy.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QLineEdit,
    QListWidget,
    QVBoxLayout,
    QWidget,
)

from .containerize import Containerize


class TabTemplate(QWidget):
    """Per-dataset configuration tab of the cross-dataset comparison.

    Parameters
    ----------
    lineagetree : LineageTree
        The dataset configured by this tab.
    name : str
        Name of the dataset in the manager.
    """

    def time_cropping(self) -> None:
        """Read the crop time typed by the user."""
        text = self.time_cropper.text()
        if not text or text == 0:
            self.crop = None
        else:
            self.crop = int(text)
        self.time_cropper.setPlaceholderText(f"Final Timepoint: {self.crop}")
        self.time_cropper.update()
        self.time_cropper.clear()

    def show_roots(self) -> list:
        """Return the roots selected for the comparison.

        Returns
        -------
        list
            The selected root IDs.
        """
        sp_roots = []
        for index in self.root_list.selectedIndexes():
            sp_roots.append(self.roots[index.row()][0])
        return sp_roots

    def times_selector(self) -> None:
        """Read the timepoints to compare.

        They are either a comma-separated list or a range built from
        start, stop and step.
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

    def ret_times(self) -> list:
        """Read and return the timepoints to compare.

        Returns
        -------
        list
            The timepoints.
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
        time_slice = Containerize(
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
        times_list = Containerize(
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
            Containerize(
                [
                    widgets.Label(
                        value="Final timepoint of lineagetree"
                    ).native,
                    self.time_cropper,
                ]
            )
        )
        layout.addWidget(self.root_list)
