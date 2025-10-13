import copy
import pickle
from functools import partial
from itertools import combinations
from pathlib import Path
from time import sleep

import matplotlib.pyplot as plt
import mplcursors
import numpy as np
import seaborn as sns
from lineagetree.tree_approximation import tree_style
from magicgui import widgets
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from matplotlib.figure import Figure
from napari._qt.qthreading import thread_worker
from napari.components.viewer_model import ViewerModel
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

from .._reader import layer_preparation
from .._util_classes import (
    BigDatasetNamesDialog,
    Containerize,
    DelayedTooltipEventFilter,
    LayerCorrectorTreeProducer,
    QtViewerWrap,
    TabTemplate,
)


class MinimalCellSize(LayerCorrectorTreeProducer):
    def change(
        self,
        viewer: QtViewerWrap,
        slider,
        other_viewer,
        other_slider,
        event,
    ):
        if active_layer := viewer.layers.selection.active:
            if not self.toggle_all.value:
                new_size = slider.value()  # type: ignore
                active_layer.size = new_size
                slider.setToolTip(
                    f"Change the size of the spheres on the viewer. Current size {slider.value()}"
                )
            else:
                new_size = slider.value()  # type: ignore
                active_layer.size = new_size
                other_viewer.layers.selection.active.size = new_size
                other_slider.setValue(new_size)
                slider.setToolTip(
                    f"Change the size of the spheres on the viewer. Current size {slider.value()}"
                )
                other_slider.setToolTip(
                    f"Change the size of the spheres on the viewer. Current size {slider.value()}"
                )

    def __init__(self, napari_viewer, napari_viewer_1, napari_viewer_2):
        super().__init__(napari_viewer)
        event_filt = DelayedTooltipEventFilter()
        self.installEventFilter(event_filt)
        self.viewer_1 = napari_viewer_1
        self.viewer_2 = napari_viewer_2
        self.toggle_all = widgets.CheckBox(value=False)
        toggle_container = widgets.Container(
            widgets=[
                widgets.Label(value="Both viewers"),
                self.toggle_all,
            ],
            layout="vertical",
            labels=False,
        )
        layout = QHBoxLayout()
        layout.addStretch(1)
        self.setLayout(layout)
        self.slider_1 = QSlider()
        self.slider_1.setOrientation(Qt.Orientation.Horizontal)
        self.slider_1.setTickInterval(1)
        self.slider_1.setMinimum(0)
        self.slider_1.setMaximum(2000)
        self.slider_1.setValue(200)
        self.slider_1.setToolTip(
            f"Change the size of the spheres on the viewer. Current size {self.slider_1.value()}"
        )
        self.slider_2 = QSlider()
        self.slider_2.setOrientation(Qt.Orientation.Horizontal)
        self.slider_2.setTickInterval(1)
        self.slider_2.setMinimum(0)
        self.slider_2.setMaximum(2000)
        self.slider_2.setValue(200)
        self.slider_2.setToolTip(
            f"Change the size of the spheres on the viewer. Current size {self.slider_2.value()}"
        )

        self.change_size_2 = partial(
            self.change,
            self.viewer_2,
            self.slider_2,
            self.viewer_1,
            self.slider_1,
        )
        self.slider_2.valueChanged.connect(self.change_size_2)
        self.change_size_1 = partial(
            self.change,
            self.viewer_1,
            self.slider_1,
            self.viewer_2,
            self.slider_2,
        )
        self.slider_1.valueChanged.connect(self.change_size_1)

        slid_container = Containerize(
            [self.slider_1, self.slider_2], horizontal=False
        )
        slid_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.slider_1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.slider_2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.layout().addWidget(widgets.Label(value="Size of spheres").native)
        self.layout().addWidget(slid_container)
        self.layout().addWidget(toggle_container.native)
