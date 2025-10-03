from numbers import Number
from typing import TYPE_CHECKING
from warnings import warn

import numpy as np
from napari.utils.colormaps import AVAILABLE_COLORMAPS
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

from ..._layout_utils import SimpleContainer
from ..._util_classes import (
    LineageTreeWidgetBase,
)
from ..._utils import _select_active_lt_layer
from .colorboxlabel import ColorBoxLabel

if TYPE_CHECKING:
    pass


def filter_dicts_of_objects_by_values(
    obj: object, type_of_object: type
) -> list[str]:
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


class QuantitativeColoringWidget(LineageTreeWidgetBase):
    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)
        # self.combobox_continuous = QtColormapComboBox(self)
        # self.combobox_continuous.setObjectName("colormapcombobox")
        # for name, cm in AVAILABLE_COLORMAPS.items():
        #     self.combobox_continuous.addItem(cm._display_name, name)
        # self.color_label = QPushButton(self)
        # self.combobox_continuous.currentTextChanged.connect(
        #     self.change_color_label
        # )
        # self.color_label.clicked.connect(self.combobox_continuous.showPopup)
        # color_cont = SimpleContainer([self.color_label, self.combobox_continuous])
        self.colorbox = ColorBoxLabel(self)
        self.combobox_continuous = self.colorbox.combobox_continuous

        # Get lineage tree from active layer
        active_layer = _select_active_lt_layer(self.viewer)
        if active_layer is not None:
            self.lT = active_layer.metadata.get("LineageTree", None)
        else:
            self.lT = None

        self.selected_attribute = QComboBox()
        if self.lT:
            self.selected_attribute.addItems(
                [str(None)]
                + filter_dicts_of_objects_by_values(self.lT, Number)
            )
        else:
            self.selected_attribute.addItem("None")
        layout = QVBoxLayout()
        layout.addWidget(self.selected_attribute)
        self.miss_data = MissingData()
        color_button = QPushButton("Recolor Dataset")
        color_button.pressed.connect(self.generate_colors)
        reset_color_button = QPushButton("Reset Color of Dataset")
        reset_color_button.pressed.connect(self.reset_button_pr)
        cont = SimpleContainer([color_button, reset_color_button])
        layout.addWidget(
            SimpleContainer([QLabel("Select Colormap"), self.colorbox])
        )
        layout.addWidget(self.miss_data)
        layout.addWidget(cont)
        self.setLayout(layout)
        self.viewer.layers.selection.events.active.connect(self.layer_change)

    def generate_colors(self):
        cell_color = {}
        selected_method = self.miss_data.selected()
        _cmap = AVAILABLE_COLORMAPS[self.combobox_continuous.currentData()]

        def cmap(x):
            return _cmap.map(x)[0]

        attr = self.selected_attribute.currentText()
        if attr == "None":
            warn("Please select a valid attribute", stacklevel=2)
            return
        min_val = min(self.lT.__getattribute__(attr).values())
        max_val = max(self.lT.__getattribute__(attr).values())
        active_layer = _select_active_lt_layer(self.viewer)
        match selected_method:
            case "Black":
                for node, value in self.lT.__getattribute__(attr).items():
                    cell_color[node] = cmap(
                        (value - min_val) / (max_val - min_val)
                    )
            case "Propagate from Ancestor":
                for node, value in self.lT.__getattribute__(attr).items():
                    cell_color[node] = cmap(
                        (value - min_val) / (max_val - min_val)
                    )
                for node in active_layer.metadata["napari2lT"].values():
                    if node not in self.lT.__getattribute__(attr):
                        prev_node = self.lT.get_ancestor_with_attribute(
                            node, attr
                        )
                        if prev_node != -1:
                            cell_color[node] = cell_color[prev_node]
                        else:
                            cell_color[node] = [0, 0, 0, 1]

            case "Propagate from Sibling":
                ...
            case "Mean":
                for node, value in self.lT.__getattribute__(attr).items():
                    cell_color[node] = cmap(
                        (value - min_val) / (max_val - min_val)
                    )
                mean_val = np.mean(
                    list(self.lT.__getattribute__(attr).values())
                )
                for node in active_layer.metadata["napari2lT"].values():
                    if node not in cell_color:
                        cell_color[node] = cmap(
                            (mean_val - min_val) / (max_val - min_val)
                        )
            case "Min":
                for node, value in self.lT.__getattribute__(attr).items():
                    cell_color[node] = cmap(
                        (value - min_val) / (max_val - min_val)
                    )
                min_val = np.min(list(self.lT.__getattribute__(attr).values()))
                for node in active_layer.metadata["napari2lT"].values():
                    if node not in cell_color:
                        cell_color[node] = cmap(0)
            case "Median":
                for node, value in self.lT.__getattribute__(attr).items():
                    cell_color[node] = cmap(
                        (value - min_val) / (max_val - min_val)
                    )
                median = np.median(
                    list(self.lT.__getattribute__(attr).values())
                )
                for node in active_layer.metadata["napari2lT"].values():
                    if node not in cell_color:
                        cell_color[node] = cmap(
                            (median - min_val) / (max_val - min_val)
                        )
            case val if isinstance(val, float | int):
                for node, value in self.lT.__getattribute__(attr).items():
                    cell_color[node] = cmap(
                        (value - min_val) / (max_val - min_val)
                    )
                for node in active_layer.metadata["napari2lT"].values():
                    if node not in cell_color:
                        cell_color[node] = cmap(
                            (val - min_val) / (max_val - min_val)
                        )

        face_colors = [
            cell_color.get(node, [0, 0, 0, 1])
            for point, node in active_layer.metadata["napari2lT"].items()
        ]
        active_layer.face_color = face_colors

        # Emit through new structured signals via signal hub
        print(f"🎨 [DEBUG] Emitting color signals for {len(cell_color)} nodes")
        
        # Check if signal hub is available
        if self.signal_hub is None:
            print(f"❌ [DEBUG] signal_hub is None! Cannot emit signals.")
            return
            
        print(f"🎨 [DEBUG] Using signal_hub: {id(self.signal_hub)} with {len(self.signal_hub.get_registered_widgets())} widgets")
        
        # Send a single comprehensive signal with all the data needed
        comprehensive_data = {
            "type": "quantitative",
            "node_colors": cell_color,
            "face_colors": face_colors,
            "selected_nodes": set(cell_color.keys()),
            "colormap": self.combobox_continuous.currentData(),
            "attribute": self.selected_attribute.currentText(),
            "source": "attribute_coloring",
        }
        print(f"🎨 [DEBUG] emit_color_mapping_update: {comprehensive_data['type']} with {len(comprehensive_data['node_colors'])} colors")
        self.signal_hub.emit_color_mapping_update(comprehensive_data)

    def reset_button_pr(self):
        # First reset the face colors
        active_layer = _select_active_lt_layer(self.viewer)
        
        # Check if signal hub is available
        if self.signal_hub is None:
            print(f"❌ [DEBUG] signal_hub is None in reset_button_pr! Cannot emit signals.")
            return
            
        if active_layer is not None:
            original_colors = active_layer.metadata["clone2"]
            active_layer.face_color = original_colors
            
            # CRITICAL: Also update the current_face_colors metadata that the canvas uses
            if "current_face_colors" in active_layer.metadata:
                active_layer.metadata["current_face_colors"] = original_colors
                print(f"🔄 [DEBUG] Updated current_face_colors metadata to original colors")

        # Emit reset signal to clear quantitative mode from canvas
        self.signal_hub.emit_coloring_reset()

    def layer_change(self):
        active_layer = _select_active_lt_layer(self.viewer)
        if active_layer is not None:
            self.lT = active_layer.metadata.get("LineageTree", None)
        else:
            self.lT = None

        if self.lT:
            # DO NOT emit visual settings on layer change
            # The LineageCanvas should use its own user preferences
            # Only emit coloring reset to clear any quantitative state
            if self.signal_hub is not None:
                self.signal_hub.emit_coloring_reset()
            
            # Update the attribute selection
            self.selected_attribute.clear()
            self.selected_attribute.addItems(
                [str(None)]
                + filter_dicts_of_objects_by_values(self.lT, Number)
            )
        else:
            self.selected_attribute.clear()
            self.selected_attribute.addItems([str(None)])


class QualitativeColoringWidget(QWidget): ...


class AttributeColoringWidget(LineageTreeWidgetBase):
    name = "coloring"

    def __init__(self, napari_viewer, signal_hub=None):
        super().__init__(napari_viewer)
        
        # Store signal hub for passing to child widgets
        self.signal_hub = signal_hub

        self.combobox = QComboBox()
        self.combobox.addItems(
            [
                "Coloring based on Quantitative Attributes", 
                "Coloring based on Qualitative Attributes"
            ]
        )
        stack = QStackedWidget()
        self.quant = QuantitativeColoringWidget(napari_viewer)
        # Pass signal hub to quantitative widget if available
        if signal_hub is not None:
            self.quant.signal_hub = signal_hub
            print(f"🎨 [DEBUG] AttributeColoringWidget passed signal_hub {id(signal_hub)} to QuantitativeColoringWidget")
        else:
            print(f"❌ [DEBUG] AttributeColoringWidget received None signal_hub!")
            
        qual = QualitativeColoringWidget()
        stack.addWidget(self.quant)
        stack.addWidget(qual)
        self.combobox.currentIndexChanged.connect(stack.setCurrentIndex)
        layout = QVBoxLayout()
        layout.addWidget(self.combobox)
        layout.addWidget(stack)
        layout.addStretch(1)
        self.setLayout(layout)
