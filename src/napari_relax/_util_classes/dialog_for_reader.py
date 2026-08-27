from magicgui import widgets
from napari.qt import get_current_stylesheet
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .._util_classes import Containerize


class LoadingDialog(QDialog):
    def __init__(self, options):
        super().__init__()
        layout = QVBoxLayout()
        self.setWindowTitle("lineagetree data type selection.")
        self.value_selected = ""
        label = QLabel("Please select the method used to produce the dataset.")

        checkboxes = [QCheckBox(opt, self) for opt in options]
        self.match = dict(zip(checkboxes, options, strict=False))
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
        main_layout = QVBoxLayout()
        self.form_widget = QWidget()
        self.form_layout = QFormLayout()
        self.form_widget.setLayout(self.form_layout)
        self.setWindowTitle("Loading Parameters")

        if current is None:
            self.tr_edit = widgets.LineEdit(value="0")
        else:
            self.tr_edit = widgets.LineEdit(value=str(current))

        self.tr_edit.tooltip = ""
        self.value_selected = 0
        self.check_resave = QCheckBox()
        self.ok_but = widgets.PushButton(text="Ok")
        self.ok_but.clicked.connect(self._ok_pressed)
        self.setLayout(main_layout)
        row = QHBoxLayout()
        row.addWidget(self.tr_edit.native)
        row.addWidget(QLabel("mins"))

        self.form_layout.addRow("Time resolution:", row)
        self.form_layout.addRow(
            "Resave dataset with\nnew time resolution", self.check_resave
        )
        self.layout().addWidget(self.form_widget)
        self.layout().addWidget(self.ok_but.native)
        self.setStyleSheet(get_current_stylesheet())

    def _ok_pressed(self, event):
        try:
            float(self.tr_edit.value)
        except ValueError:
            pass
        else:
            self.value_selected = float(self.tr_edit.value)
            self.accept()


class SetupDialog(TimeResDialog):
    def __init__(self, lT, current=None):
        super().__init__(current)
        self.lT = lT
        form_layout: QFormLayout = self.form_widget.layout()

        self.layout().removeWidget(self.ok_but.native)
        self.ok_but.native.setParent(None)

        self.rescaler = QCheckBox("")
        form_layout.addRow("Rescale Dataset", self.rescaler)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setMinimumWidth(150)

        self.value_shown = QPushButton(str(self.slider.value()))
        self.value_shown.setFixedSize(40, 20)
        self.value_shown.setStyleSheet(
            """
                                        QPushButton {
                                            background-color: transparent;
                                            border: none;
                                        }
                                        """
        )

        self.slider.valueChanged.connect(
            lambda x: self.value_shown.setText(str(x))
        )
        row = QHBoxLayout()
        row.addWidget(self.slider)
        row.addWidget(self.value_shown)

        form_layout.addRow("Filter Dataset:", row)

        cancel_but = QPushButton("Cancel")
        cancel_but.pressed.connect(self._cancel_pressed)

        self.layout().addWidget(Containerize([cancel_but, self.ok_but.native]))

    def _ok_pressed(self, event):
        try:
            float(self.tr_edit.value)
        except ValueError:
            pass
        else:
            self.parameters = {
                "divisor": self.slider.value(),
                "time_r": float(self.tr_edit.value),
                "rescale": self.rescaler.isChecked(),
                "resave": self.check_resave.isChecked(),
            }
            self.accept()

    def _cancel_pressed(self):
        self.parameters = {}
        self.accept()
