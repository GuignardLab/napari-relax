from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLineEdit,QWidget, QLabel, QHBoxLayout, QPushButton
from qtpy.QtGui import QIntValidator, QDoubleValidator
from typing import get_args




def get_base_type(annotation: str) -> tuple[type | None, bool]:
    annotation = eval(annotation, {
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "None": type(None),
    })

    types = get_args(annotation)

    if not types:
        return annotation, False

    allows_none = type(None) in types

    types = [t for t in types if t is not type(None)]

    if not types:
        return None, True

    if float in types:
        return float, allows_none

    return types[0], allows_none

class LineEditGenerator(QWidget):
    def __init__(
        self,
        name: str,
        typ_of_widget: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.typ_of_widget, allows_none = get_base_type(typ_of_widget)

        lbl = QLabel(name)
        self.line_edit = QLineEdit()
        validator = Type2Validation.get(self.typ_of_widget)

        if validator:
            self.line_edit.setValidator(validator())

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(lbl)
        self.layout().addWidget(self.line_edit)

        if allows_none:
            self.none_button = QPushButton("None")
            self.none_button.setCheckable(True)
            self.none_button.clicked.connect(self.line_edit.clear)
            self.line_edit.textChanged.connect(lambda x: self.none_button.setChecked(False))
            self.layout().addWidget(self.none_button)


    def get_value(self):
        if hasattr(self, "none_button") and self.none_button.isChecked():
            return None
        text = self.line_edit.text()
        if not text:
            return None

        return self.typ_of_widget(text)




Type2Validation = {int:QIntValidator,float:QDoubleValidator}