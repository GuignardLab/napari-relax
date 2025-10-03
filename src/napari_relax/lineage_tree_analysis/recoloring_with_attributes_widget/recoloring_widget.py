import matplotlib.pyplot as plt
import numpy as np
from magicgui import widgets
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from napari.layers import Points
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget

from ..._util_classes import LayerCorrectorTreeProducer
from ..._utils import _select_correct_layer
from .node_based_recoloring import Coloring
from .clone_based_recoloring import CloneRecoloring
from .custom_colorboxes.mpl_compatible_combobox import (
    QUANTITATIVE_CMAPS,
    MplCompatibleColorCombobox,
)


class RecoloringWidget(LayerCorrectorTreeProducer):
    name = "Attribute Based Recoloring"

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)
        layout = QVBoxLayout()
        tabs = QTabWidget()
        self.clone_based_recoloring = CloneRecoloring(self.viewer)
        self.coloring_widget = Coloring(self.viewer)
        tabs.addTab(self.clone_based_recoloring, "Clone based Recoloring")
        tabs.addTab(self.coloring_widget, "Node based Recoloring")
        layout.addWidget(tabs)
        self.setLayout(layout)
