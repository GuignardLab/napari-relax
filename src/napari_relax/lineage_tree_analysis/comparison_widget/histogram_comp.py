import os
import pickle
from itertools import combinations
from pathlib import Path
from time import sleep

import matplotlib.pyplot as plt
import mplcursors
import numpy as np
import seaborn as sns
from LineageTree.tree_approximation import tree_style
from magicgui import widgets
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from matplotlib.figure import Figure
from napari._qt.qthreading import thread_worker
from napari.layers import Points
from napari.utils import progress
from qtpy.QtCore import QRegExp
from qtpy.QtGui import QIntValidator, QRegExpValidator
from psygnal import Signal
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QScrollArea,
    QSpacerItem,
    QSizePolicy,
)
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

from ..._util_classes import (
    Layer_corrector_Tree_Producer,
    containerize,
    delayedtooltipeventfilter,
    tooltip_button,
)
from ..._utils import _select_correct_layer


class HistTemplate(QWidget):

    kill_signal = Signal(object)

    def __init__(self, comparisons=..., norms=..., labels=[]):
        super().__init__()
        if labels:

            self.title = widgets.Label(
                value=f"Roots: {','.join(str(l) for l in labels[0])}"
            )
        else:
            self.title = widgets.Label(value="")

        self.kill_button = QPushButton("X")
        self.kill_button.setFixedSize(20, 20)
        self.figure = Figure(figsize=(3, 2), constrained_layout=True)
        self.canvas = FigureCanvas(figure=self.figure)
        self.range = 1  # for now
        self.norm_combo = widgets.ComboBox(
            value="max",
            choices=["max", "sum", "None"],
        )
        self.norm_dict = {"max": max, "sum": sum, "None": lambda x: 1}
        self.norm_combo.changed.connect(self.plot_hist)
        self.slider = widgets.Slider(min=0, max=self.range)
        self.comparisons = comparisons
        self.norms = norms
        self.hist_ax = self.figure.add_subplot(111)
        head_widget = QWidget()
        header = QHBoxLayout()
        header.addWidget(self.norm_combo.native)
        header.addWidget(self.title.native)
        header.addWidget(self.kill_button, alignment=Qt.AlignRight)
        head_widget.setLayout(header)
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.setLayout(layout)
        self.layout().addWidget(head_widget)
        self.layout().addWidget(self.canvas)
        self.layout().addWidget(self.slider.native)
        self.slider.changed.connect(self.plot_hist)
        self.kill_button.clicked.connect(self.kill_widget)

    def kill_widget(self):
        self.kill_signal.emit(self)

    def plot_hist(self):
        self.hist_ax.clear()
        time = int(self.slider.value)
        hist_values = []
        for keys, values in self.comparisons[time]:
            hist_values.append(
                self.comparisons[time][keys, values]
                / self.norm_dict[str(self.norm_combo.value)](
                    self.norms[time][keys, values]
                )
            )
        self.hist_ax.hist(hist_values)
        self.canvas.draw()

    def update_values(self, product):
        self.comparisons, *_, self.norms = product


class HistogramWidget(QScrollArea):

    def receive_values(self, data_from_clustermap: tuple[dict, dict, dict]):
        self.comparisons, self.naming, self.norms = data_from_clustermap
        self.layer_change()
        self.main_hist.slider.max = len(self.comparisons) - 1
        self.main_hist.update_values(data_from_clustermap)
        self.main_hist.title.value = (
            f"Roots: {','.join(str(l) for l in self.naming[0])}"
        )
        self.main_hist.plot_hist()

    def select_values(self): ...

    def add_hist(self, roots=...):
        hist = HistTemplate()
        self.all_histograms.add(hist)

        hist.kill_signal.connect(self.remove_hist)
        self.layout.insertWidget(self.layout.count() - 2, hist)

    def remove_hist(self, obj: QWidget):
        self.layout.removeWidget(obj)
        obj.setParent(None)
        obj.deleteLater()

    def layer_change(self):
        for hist in self.all_histograms:
            self.remove_hist(hist)
        self.main_hist.hist_ax.clear()

    def __init__(self):
        super().__init__()
        self.range = 0
        self.comparisons = {}
        self.norms = {}
        self.all_histograms = set()
        self.main_hist = HistTemplate()
        self.main_hist.layout().removeWidget(self.main_hist.kill_button)
        self.main_hist.kill_button.setParent(None)
        self.add_button = QPushButton("+")
        self.add_button.setFixedSize(20, 20)
        self.container = QWidget()
        self.container.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.layout = QVBoxLayout(self.container)
        self.setWidget(self.container)
        self.spacer = QSpacerItem(
            20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding
        )

        self.setWidget(self.container)
        self.setWidgetResizable(True)
        self.layout.addWidget(self.main_hist)
        self.layout.addWidget(self.add_button)
        self.layout.addItem(self.spacer)
        self.add_button.clicked.connect(self.add_hist)
