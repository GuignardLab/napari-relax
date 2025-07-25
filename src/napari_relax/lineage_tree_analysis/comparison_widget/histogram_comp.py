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
from qtpy.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
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


class Histogram(QWidget):

    def receive_values(self): ...

    def add_hist(self, roots): ...

    def remove_hist(self): ...

    def plot_hist(self): ...

    def __init__(self, parent=..., flags=...):
        super().__init__(parent, flags)
        self.figure = Figure(figsize=(3, 3), constrained_layout=True)
        self.canvas = FigureCanvas
        self.hist_ax = self.figure.add_subplot(111)
