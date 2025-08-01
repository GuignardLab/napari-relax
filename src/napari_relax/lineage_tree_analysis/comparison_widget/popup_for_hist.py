from qtpy.QtWidgets import (
    QCheckBox,
    QDialog,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from .histogramtemplate import HistTemplate
from napari.qt import get_current_stylesheet
from napari.settings import get_settings


class pop_up(QDialog):
    def __init__(self, roots, labels):
        super().__init__()
        self.setStyleSheet(get_current_stylesheet())

        layout = QVBoxLayout()
        self.setWindowTitle("Create new Histogram")
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        self.list_items = [
            f"{root[0]} - {labels.get(root[0], root[0])}"
            for root in roots[0].values()
        ]
        self.list_widget.addItems(self.list_items)
        self.separate_check = QCheckBox("Separate labels")
        self.separate_check.setChecked(False)
        self.in_group_check = QCheckBox("In-group comparisons")
        self.in_group_check.setChecked(True)
        self.out_group_check = QCheckBox("Out-group comparisons")
        self.out_group_check.setChecked(True)
        self.accept_button = QPushButton("Accept")
        layout.addWidget(self.list_widget)
        layout.addWidget(self.in_group_check)
        layout.addWidget(self.out_group_check)
        layout.addWidget(self.separate_check)
        layout.addWidget(self.accept_button)
        self.setLayout(layout)
        self.accept_button.clicked.connect(self.accept_parameters)

    def accept_parameters(self):
        if len(self.list_widget.selectedItems()) > 0 and (
            self.in_group_check.isChecked() or self.out_group_check.isChecked()
        ):
            lista = [
                int(self.list_items[i.row()].split(" ")[0])
                for i in self.list_widget.selectedIndexes()
            ]
            self.hist = HistTemplate(
                specific_roots=lista,
                in_group=self.in_group_check.isChecked(),
                out_group=self.out_group_check.isChecked(),
                separate=self.separate_check.isChecked(),
            )
            self.accept()
