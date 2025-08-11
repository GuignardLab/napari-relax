from numbers import Number
from typing import TYPE_CHECKING
from warnings import warn
from PyQt5.QtCore import Qt
from napari._qt.layer_controls.qt_colormap_combobox import QtColormapComboBox
from napari.utils.colormaps import AVAILABLE_COLORMAPS
import numpy as np
from qtpy.QtGui import QPixmap, QIcon, QImage
from qtpy.QtWidgets import QApplication, QLabel
from magicgui import widgets
from matplotlib.pyplot import colormaps
from napari.layers import Points
from psygnal import Signal
from qtpy.QtGui import QDoubleValidator
from qtpy.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
import matplotlib.pyplot as plt
from ..._util_classes import (
    Layer_corrector_Tree_Producer,
    containerize,
)
from ..._utils import _select_correct_layer

if TYPE_CHECKING:
    pass


class ColorBoxLabel(QWidget):

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.combobox_continuous = QtColormapComboBox(self)
        self.combobox_continuous.setObjectName("colormapcombobox")
        for name, cm in AVAILABLE_COLORMAPS.items():
            self.combobox_continuous.addItem(cm._display_name, name)
        self.color_label = QPushButton(self)
        self.combobox_continuous.currentTextChanged.connect(
            self.change_color_label
        )
        self.color_label.clicked.connect(self.combobox_continuous.showPopup)
        color_cont = containerize([self.color_label, self.combobox_continuous])
        self.setLayout(QVBoxLayout())
        self.change_color_label()
        self.layout().addWidget(color_cont)
        self.layout().setSpacing(0)

    def change_color_label(self):
        n_samples = 256
        height = self.combobox_continuous.height()
        gradient = np.tile(np.linspace(0, 1, n_samples), (height, 1))
        cmap = AVAILABLE_COLORMAPS[self.combobox_continuous.currentData()]
        colors = (cmap.map(gradient) * 255).astype(np.uint8)
        h, w, ch = colors.shape
        qimage = QImage(colors.data, w, height, ch * w, QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        icon = QIcon(pixmap)
        self.color_label.setIcon(icon)
        self.color_label.setIconSize(pixmap.size())
