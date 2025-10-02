from typing import TYPE_CHECKING

import numpy as np
from qtpy.QtCore import QSize, QModelIndex, QRect, Qt
from qtpy.QtGui import QIcon, QImage, QPixmap, QPainter
from qtpy.QtWidgets import (
    QPushButton,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QListView,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

import matplotlib.cm as cm

from ...._util_classes import Containerize

COLORMAP_WIDTH = 150
TEXT_WIDTH = 130
ENTRY_HEIGHT = 24
PADDING = 2

if TYPE_CHECKING:
    pass

quant_cmap_names = [
    "Pastel1",
    "Pastel2",
    "Paired",
    "Accent",
    "Dark2",
    "Set1",
    "Set2",
    "Set3",
    "tab10",
    "tab20",
    "tab20b",
    "tab20c",
]

QUANTITATIVE_CMAPS = {name: cm.get_cmap(name) for name in quant_cmap_names}


class DiscreteColorbox(QWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.combobox_continuous = CustomQtColormapComboBox(self)
        self.combobox_continuous.setObjectName("colormapcombobox")

        for name in QUANTITATIVE_CMAPS:
            self.combobox_continuous.addItem(name, name)

        self.color_label = QPushButton(self)
        self.color_label.setFixedHeight(28)
        self.combobox_continuous.currentTextChanged.connect(
            self.change_color_label
        )
        self.color_label.clicked.connect(self.combobox_continuous.showPopup)

        color_cont = Containerize([self.color_label, self.combobox_continuous])
        layout = QVBoxLayout(self)
        layout.addWidget(color_cont)
        layout.setSpacing(0)

        self.change_color_label()

    def change_color_label(self):
        cmap_name = self.combobox_continuous.currentData()
        if not cmap_name:
            return
        cmap = QUANTITATIVE_CMAPS[cmap_name]
        icon = self.make_icon(cmap, width=256, height=20)
        self.color_label.setIcon(icon)
        self.color_label.setIconSize(QSize(256, 20))

    def make_icon(self, cmap, width: int = 64, height: int = 12) -> QIcon:
        gradient = np.tile(np.linspace(0, 1, width), (height, 1))
        h, w, ch = colors.shape
        qimage = QImage(colors.data, w, h, ch * w, QImage.Format_RGBA8888)
        qimage = qimage.copy()
        pixmap = QPixmap.fromImage(qimage)
        return QIcon(pixmap)


class CustomColorStyledDelegate(QStyledItemDelegate):
    def __init__(self, base_height: int, **kwargs):
        super().__init__(**kwargs)
        self.base_height = base_height

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ):
        option_copy = QStyleOptionViewItem(option)

        cbar_rect = QRect(
            option.rect.x() + PADDING,
            option.rect.y() + PADDING,
            COLORMAP_WIDTH,
            option.rect.height() - 2 * PADDING,
        )
        text_rect = QRect(
            cbar_rect.right() + PADDING,
            option.rect.y() + PADDING,
            TEXT_WIDTH,
            option.rect.height() - 2 * PADDING,
        )

        option_copy.rect = text_rect
        super().paint(painter, option_copy, index)

        cmap_name = index.data(Qt.UserRole)
        if cmap_name not in QUANTITATIVE_CMAPS:
            return
        cmap = QUANTITATIVE_CMAPS[cmap_name]

        gradient = np.tile(
            np.linspace(0, 1, cbar_rect.width()), (cbar_rect.height(), 1)
        )
        colors = (cmap(gradient) * 255).astype(np.uint8)
        h, w, ch = colors.shape
        qimage = QImage(colors.data, w, h, ch * w, QImage.Format_RGBA8888)
        qimage = qimage.copy()
        painter.drawImage(cbar_rect, qimage)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex):
        sz = super().sizeHint(option, index)
        sz.setHeight(self.base_height)
        sz.setWidth(COLORMAP_WIDTH + TEXT_WIDTH + 3 * PADDING)
        return sz


class CustomQtColormapComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        view = QListView()
        view.setMinimumWidth(COLORMAP_WIDTH + TEXT_WIDTH)
        view.setItemDelegate(CustomColorStyledDelegate(ENTRY_HEIGHT))
        self.setView(view)
