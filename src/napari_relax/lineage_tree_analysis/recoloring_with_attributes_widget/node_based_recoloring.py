import os
from numbers import Number
from warnings import warn

import numpy as np
from napari.utils.notifications import show_warning
from psygnal import Signal
from qtpy.QtCore import Qt
from qtpy.QtGui import QDoubleValidator
from qtpy.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..._util_classes import (
    Containerize,
    LayerCorrectorTreeProducer,
    TooltipButton,
)
from ..._util_classes.custom_colorboxes import ColorBoxLabel
from ..._utils import _select_active_lt_layer


def filter_dicts_of_objects_by_values(
    obj: object, type_of_object: type
) -> list[str]:
    """Finds all attributes of a class if they are of one type.

    Parameters
    ----------
    obj : object
        Any class
    type_of_object : type
        The type that is to be pinponted

    Returns
    -------
    list[str]
        list of all the attributes
    """
    attributes = []
    for attr in obj.__dict__:
        if (
            isinstance(obj.__getattribute__(attr), dict)
            and attr
            not in (
                "successor",
                "predecessor",
                "_successor",
                "_predecessor",
                "_time",
                "_comparisons",
            )
            and all(
                isinstance(i, type_of_object)
                for i in obj.__getattribute__(attr).values()
            )
            and obj.__getattribute__(attr)
        ):
            attributes.append(attr)
    return attributes


class LineeditCheckbox(QCheckBox):
    """Custom lineedit box that only accepts floats"""

    def __init__(self, parent=None):
        super().__init__("Custom value", parent)
        self.lineedit = QLineEdit()
        self.lineedit.setValidator(QDoubleValidator())
        self.lineedit.setPlaceholderText("Enter number here")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addSpacerItem(
            QSpacerItem(140, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)
        )
        layout.addWidget(self.lineedit)

    def text(self):
        return int(self.lineedit.text())

    def setText(self, value: float):
        self.lineedit.setText(str(value))


class MissingData(QWidget):
    """How to handle missing data, it has 3 shown checkboxes and 4 hidden ones shown upon clicking on the last checkbox.

    Parameters
    ----------
    QWidget : _type_
        _description_
    """

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.check_black = QCheckBox("Black", self)
        self.check_black.setChecked(True)
        self.check_propagate = QCheckBox("Propagate from Ancestor", self)
        self.sibling = QCheckBox("Propagate from Sibling", self)
        self.check_default_value = QCheckBox("Default Value", self)
        self.buttongroup = QButtonGroup()
        self.buttongroup.addButton(self.check_black)
        self.buttongroup.addButton(self.sibling)
        self.buttongroup.addButton(self.check_propagate)
        self.buttongroup.addButton(self.check_default_value)
        self.buttongroup.setExclusive(True)
        self.buttongroup.buttonClicked.connect(self._select_checkbox)

        self.buttongroup_default = QButtonGroup()
        self.buttongroup_default.setExclusive(True)
        self.custom = LineeditCheckbox(self)
        self.mean = QCheckBox("Mean", self)
        self.median = QCheckBox("Median", self)
        self.min = QCheckBox("Min", self)
        self.buttongroup_default.addButton(self.mean)
        self.buttongroup_default.addButton(self.median)
        self.buttongroup_default.addButton(self.min)
        self.buttongroup_default.addButton(self.custom)

        subselection_layout = QVBoxLayout()
        subselection_layout.addWidget(self.custom)
        subselection_layout.addWidget(self.mean)
        subselection_layout.addWidget(self.median)
        subselection_layout.addWidget(self.min)

        for but in self.buttongroup_default.buttons():
            but.hide()

        default_selection_layout = QHBoxLayout()
        default_selection_layout.addSpacerItem(
            QSpacerItem(40, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)
        )
        default_selection_layout.addLayout(subselection_layout)

        layout = QVBoxLayout()
        layout.addWidget(self.check_black)
        layout.addWidget(self.check_propagate)
        layout.addWidget(self.sibling)
        layout.addWidget(self.check_default_value)
        layout.addLayout(default_selection_layout)

        self.setLayout(layout)

    def _select_checkbox(self, button):
        if button.isChecked():
            if button == self.check_default_value:
                for but in self.buttongroup_default.buttons():
                    but.show()
                self.custom.setChecked(True)

            else:
                for but in self.buttongroup_default.buttons():
                    but.hide()

    def selected(self) -> str | None:
        if self.buttongroup.checkedButton():
            if self.check_default_value.isChecked():
                return self.buttongroup_default.checkedButton().text()
            return self.buttongroup.checkedButton().text()
        else:
            warn("Please select a method.", stacklevel=2)
            return None


class Quantitative(LayerCorrectorTreeProducer):
    """The widget to handle the different attributes."""

    color_signal = Signal(dict)

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)
        self.colorbox = ColorBoxLabel(self)
        self.combobox_continuous = self.colorbox.combobox_continuous
        self.lT = self.get_lT()
        self.selected_attribute = QComboBox()
        if self.lT:
            self.selected_attribute.addItems(
                [str(None)]
                + filter_dicts_of_objects_by_values(self.lT, Number)
            )
        else:
            self.selected_attribute.addItem("None")
        layout = QVBoxLayout()
        self.colorbox.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        layout.addWidget(
            Containerize(
                [QLabel("Selected attribute"), self.selected_attribute]
            )
        )
        self.miss_data = MissingData()
        color_button = QPushButton("Recolor Dataset")
        color_button.pressed.connect(self.generate_colors)
        reset_color_button = QPushButton("Reset Color of Dataset")
        reset_color_button.pressed.connect(self.reset_button_pr)
        cont = Containerize([color_button, reset_color_button])
        layout.addWidget(
            Containerize([QLabel("Select Colormap"), self.colorbox])
        )
        layout.addWidget(self.miss_data)
        layout.addWidget(cont)
        self.setLayout(layout)
        self.viewer.layers.selection.events.active.connect(self.layer_change)

    def generate_colors(self):
        cell_color = {}
        selected_method = self.miss_data.selected()
        _cmap = self.colorbox.get_cmap()

        def cmap(x):
            return _cmap.map(x)[0]

        attr = self.selected_attribute.currentText()
        if attr == "None":
            warn("Please select a valid attribute", stacklevel=2)
            return
        min_val = min(self.lT.__getattribute__(attr).values())
        max_val = max(self.lT.__getattribute__(attr).values())
        active_layer = _select_active_lt_layer(self.viewer)
        if active_layer is None:
            return

        existing_nodes = set(self.lT.__getattribute__(attr).values())
        nonexistingnodes = (
            set(active_layer.metadata["napari2lT"].values()) - existing_nodes
        )

        for node, value in self.lT.__getattribute__(attr).items():
            cell_color[node] = cmap((value - min_val) / (max_val - min_val))

        match selected_method:
            case "Black":
                ...
            case "Propagate from Ancestor":
                for node in nonexistingnodes:
                    if node not in self.lT.__getattribute__(attr):
                        prev_node = self.lT.get_ancestor_with_attribute(
                            node, attr
                        )
                        if prev_node != -1:
                            cell_color[node] = cell_color[prev_node]
                        else:
                            cell_color[node] = [0, 0, 0, 1]

            case "Propagate from Sibling":
                show_warning("Not implemented yet!")
                return
            case "Mean":
                mean_val = (
                    np.nanmean(list(self.lT.__getattribute__(attr).values()))
                    - min_val
                ) / (max_val - min_val)
                for node in nonexistingnodes:
                    cell_color[node] = cmap(mean_val)
            case "Min":
                for node in nonexistingnodes:
                    cell_color[node] = cmap(0)
            case "Median":
                median = (
                    np.nanmedian(list(self.lT.__getattribute__(attr).values()))
                    - min_val
                ) / (max_val - min_val)
                for node in nonexistingnodes:
                    cell_color[node] = cmap(median)
            case val if isinstance(val, float | int):
                for node in nonexistingnodes:
                    cell_color[node] = cmap(
                        (val - min_val) / (max_val - min_val)
                    )

        face_colors = [
            cell_color.get(node, [0, 0, 0, 1])
            for point, node in active_layer.metadata["napari2lT"].items()
        ]
        active_layer.face_color = face_colors

        self.color_signal.emit(
            {
                "color_of_nodes": "black",
                "selected_nodes": cell_color.keys(),
                "all_selected": True,
                "quantitative_coloring": True,
                "face_colors": face_colors,
                "node_colors": cell_color,  # Individual colors per node ID
            }
        )

    def reset_button_pr(self):
        # First reset the face colors
        active_layer = _select_active_lt_layer(self.viewer)
        if active_layer is not None:
            original_colors = active_layer.metadata["clone2"]
            active_layer.face_color = original_colors

            # Emit signal with the original face colors
            self.color_signal.emit(
                {
                    "color_of_nodes": "black",
                    "color_of_edges": "black",
                    "node_size": 10,
                    "lw": 0.3,
                    "fontsize": 6,
                    "quantitative_coloring": False,
                    "face_colors": original_colors,
                }
            )
        else:
            # Emit signal without face colors if no active layer
            self.color_signal.emit(
                {
                    "color_of_nodes": "black",
                    "color_of_edges": "black",
                    "node_size": 10,
                    "lw": 0.3,
                    "fontsize": 6,
                    "quantitative_coloring": False,
                }
            )

    def layer_change(self):
        self.lT = self.get_lT()
        if self.lT:
            # Only emit essential settings, preserve visual customizations
            self.color_signal.emit(
                {
                    "color_of_nodes": "black",
                    "color_of_edges": "black",
                    "node_size": 10,
                    "lw": 0.3,
                    "fontsize": 6,
                }
            )
            self.selected_attribute.clear()
            self.selected_attribute.addItems(
                [str(None)]
                + filter_dicts_of_objects_by_values(self.lT, Number)
            )
        else:
            self.selected_attribute.clear()
            self.selected_attribute.addItems([str(None)])


class Qualitative(QWidget): ...


class Coloring(LayerCorrectorTreeProducer):
    name = "coloring"

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)

        self.combobox = QComboBox()
        self.combobox.addItems(["Quantitative", "Qualitative"])
        stack = QStackedWidget()
        self.quant = Quantitative(napari_viewer)
        qual = Qualitative()
        stack.addWidget(self.quant)
        self.combobox.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.combobox.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        stack.addWidget(qual)
        self.combobox.currentIndexChanged.connect(stack.setCurrentIndex)
        layout = QVBoxLayout()
        layout.addWidget(self.combobox, alignment=Qt.AlignLeft)
        layout.addWidget(stack)
        layout.addStretch(1)
        self.setLayout(layout)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(
            os.path.join(current_dir, "node_recolor.html"),
            encoding="utf-8",
        ) as f:
            txt = f.read()
        self.node_tooltip = TooltipButton(txt)
        self.node_tooltip.setParent(self)
        self.node_tooltip.move(self.width() - self.node_tooltip.width(), 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.node_tooltip.move(self.width() - self.node_tooltip.width(), 0)
