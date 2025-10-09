import os
import pickle
from itertools import combinations
from pathlib import Path
from time import sleep

import matplotlib.pyplot as plt
import mplcursors
import numpy as np
import seaborn as sns
from lineagetree.tree_approximation import tree_style
from magicgui import widgets
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from matplotlib.figure import Figure
from napari._qt.qthreading import thread_worker
from napari.layers import Points
from napari.utils import notifications, progress
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

from napari_relax._util_classes import containerize

from ..._util_classes import (
    Containerize,
    DelayedTooltipEventFilter,
    LayerCorrectorTreeProducer,
    TooltipButton,
)
from ..._utils import _select_correct_layer

from .config import ConfigurationPanel
from .clustermap import OnlineClustermap


class ComparisonsHandler(LayerCorrectorTreeProducer):
    """
    Widget to produce and load comparisons between lineages, which are used to
    plot Clustermaps and letting the user select respective Lineages.
    """

    name = "ComparisonsHandler"

    def update_dictionary(self, product):
        """
        This function will read the yielded product from the thread_worker and will update the user interface
        Args:
            product [list]: [pairwise comparisons: name for each comparison]
        """
        (
            self.clustermap.comps,
            self.clustermap.naming,
            self.clustermap.norms,
            self.clustermap.times,
        ) = product
        self.clustermap.time_slider.max = len(self.comps) - 1
        self.clustermap._clustermap_creator()
        if self.pbr:
            self.pbr.update()

    def thread_handler(self):
        """
        This function will start the thread worker and connect the yielded  product to the update
        dictionary function. Also will set the run comparisons button checked, so it cannot be pressed again.
        """
        self.comps = []
        self.naming = []
        self.norms = []
        self.worker = self.config.thread_worker()
        self.config.times_selector()
        # if (
        #     max([self.lT.time[root] for root in self.specific_roots])
        #     > self.times[0]
        # ):
        #     self.kill_thread()
        #     self.runbutton.setChecked(False)
        #     notifications.show_error(
        #         "Do not use a starting point before the roots"
        #     )
        #     return
        if not self.config.times:
            self.worker.quit()
            return
        self.pbr = progress(self.clustermap.times)
        self.worker.yielded.connect(self.update_dictionary)
        self.worker.start()
        self.runbutton.setChecked(True)
        self.stopbutton.setChecked(False)
        self.worker.returned.connect(self.kill_thread)

    def kill_thread(self, dummy_event=None):
        """
        Function to kill the thread if the user decides to.
        """
        self.worker.quit()
        self.stopbutton.setChecked(True)
        self.runbutton.setChecked(False)
        if self.pbr:
            self.pbr.clear()
            self.pbr.close()
            self.pbr = None

    def __init__(self, napari_viewer):
        """
        Build the containers for the loading widget

        Args:
            napari_viewer (napari.Viewer): the parent napari viewer
        """
        super().__init__(napari_viewer)
        self.pbr = None
        self.runbutton = QPushButton("Run Comparisons")
        self.runbutton.native = self.runbutton
        self.runbutton.name = "runbutton"
        self.runbutton.setCheckable(True)
        self.stopbutton = QPushButton("Stop Processing")
        self.stopbutton.native = self.stopbutton
        self.stopbutton.name = "stopbutton"
        self.stopbutton.setCheckable(True)
        layout = QVBoxLayout()
        tabs = QTabWidget()
        self.config = ConfigurationPanel(self.viewer)

        self.clustermap = OnlineClustermap(self.viewer, self.config)
        tabs.addTab(self.config, "Configuration Panel")
        tabs.addTab(self.clustermap, "Clustermap")
        self.setLayout(layout)
        self.layout().addWidget(tabs)
        self.layout().addWidget(
            Containerize([self.runbutton, self.stopbutton])
        )

        self.setLayout(layout)
        self.runbutton.released.connect(self.thread_handler)
        self.stopbutton.released.connect(self.kill_thread)
        self.stopbutton.setChecked(True)
