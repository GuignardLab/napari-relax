from magicgui import widgets
from napari.qt import get_current_stylesheet
from qtpy.QtWidgets import QCheckBox, QDialog, QLabel, QPushButton, QVBoxLayout

from .._util_classes import Containerize


class LoadingDialog(QDialog):
    def __init__(self, options):
        super().__init__()
        layout = QVBoxLayout()
        self.setWindowTitle("lineagetree data type selection.")
        self.value_selected = ""
        label = QLabel("Please select the method used to produce the dataset.")

        checkboxes = [QCheckBox(opt, self) for opt in options]
        self.match = {
            cb: opt for cb, opt in zip(checkboxes, options, strict=False)
        }
        layout.addWidget(label)
        for cb in checkboxes:
            layout.addWidget(cb)
            cb.stateChanged.connect(self.on_type_selection)
        self.setLayout(layout)
        self.setStyleSheet(get_current_stylesheet())

    def on_type_selection(self, event):
        self.value_selected = self.match[self.sender()]
        self.accept()


class BigDatasetNamesDialog(QDialog):
    """Dialog box to ask the user if they want to continue using big names."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.setWindowTitle("LineageTree names too big!")
        self.layout().addWidget(
            QLabel(
                "One or more names of the datasets are longer than 5 characters\nthis may make the reslting clustermap misbehave.\n Do you want to continue?"
            )
        )
        self.continue_proccess = False
        self.yes_but = QPushButton("Yes")
        self.no_but = QPushButton("No")
        self.yes_but.pressed.connect(self.continue_comps)
        self.no_but.pressed.connect(self.stop_comps)
        self.layout().addWidget(Containerize([self.no_but, self.yes_but]))
        self.setStyleSheet(get_current_stylesheet())

    def stop_comps(self):
        self.continue_proccess = False
        self.accept()

    def continue_comps(self):
        self.continue_proccess = True
        self.accept()


class TimeResDialog(QDialog):
    def __init__(self, current=None):
        super().__init__()
        layout = QVBoxLayout()
        self.setWindowTitle("Set time resolution")
        if current is None:
            self.tr_edit = widgets.LineEdit(value="0")
        else:
            self.tr_edit = widgets.LineEdit(value=str(current))
        self.tr_edit.tooltip = "Set time resolution in mins"
        self.value_selected = 0
        self.check_resave = QCheckBox(
            "Resave dataset with new time resolution"
        )
        ok_but = widgets.PushButton(text="Ok")
        self.setLayout(layout)
        self.layout().addWidget(
            Containerize([self.tr_edit.native, QLabel("mins")])
        )
        self.layout().addWidget(ok_but.native)
        self.layout().addWidget(self.check_resave)
        ok_but.clicked.connect(self.selected_value)
        self.setStyleSheet(get_current_stylesheet())

    def selected_value(self, event):
        try:
            float(self.tr_edit.value)
        except ValueError:
            pass
        else:
            self.value_selected = float(self.tr_edit.value)
            self.accept()
