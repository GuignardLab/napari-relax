from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

try:
    from napari._qt.layer_controls.widgets.qt_colormap_control import (
        QtColormapComboBox,
    )
except ModuleNotFoundError:
    from napari._qt.layer_controls.qt_colormap_combobox import (
        QtColormapComboBox,
    )
from napari.utils.colormaps import ALL_COLORMAPS
from qtpy.QtGui import QIcon, QImage, QPixmap
from qtpy.QtWidgets import (
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..._util_classes import (
    Containerize,
)

if TYPE_CHECKING:
    from matplotlib.colors import Colormap


class ColorBoxLabel(QWidget):
    """A colorbox label that uses the naparis colormaps.
    If matplotlib is being used, or any other library that works like matplotlib
    use MatplotlibCompatibleCombobox.
    """

    name = "ColorBoxLabel"

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.combobox_continuous = QtColormapComboBox(self)
        self.combobox_continuous.setObjectName("colormapcombobox")
        for name, cm in ALL_COLORMAPS.items():
            self.combobox_continuous.addItem(cm._display_name, name)
        self.color_label = QPushButton(self)
        self.combobox_continuous.currentTextChanged.connect(
            self.change_color_label
        )
        self.color_label.clicked.connect(self.combobox_continuous.showPopup)
        self.color_label.setStyleSheet(
            "border-top-right-radius: 0; border-bottom-right-radius: 0;"
        )
        self.combobox_continuous.setStyleSheet(
            "border-top-left-radius: 0; border-bottom-left-radius: 0; margin-left: -1px;"
        )
        color_cont = Containerize([self.color_label, self.combobox_continuous])
        self.setLayout(QVBoxLayout())
        self.change_color_label()
        self.layout().addWidget(color_cont)
        self.layout().setSpacing(0)

    def change_color_label(self):
        n_samples = 256
        height = self.combobox_continuous.height()
        gradient = np.tile(np.linspace(0, 1, n_samples), (height, 1))
        cmap = ALL_COLORMAPS[self.combobox_continuous.currentData()]
        colors = (cmap.map(gradient) * 255).astype(np.uint8)
        h, w, ch = colors.shape
        qimage = QImage(colors.data, w, height, ch * w, QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        icon = QIcon(pixmap)
        self.color_label.setIcon(icon)
        self.color_label.setIconSize(pixmap.size())

    def get_cmap(self) -> Colormap:
        return ALL_COLORMAPS[self.combobox_continuous.currentData()]

    def value(self):
        return self.combobox_continuous.currentText()
