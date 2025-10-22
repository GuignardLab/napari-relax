from magicgui import widgets
from napari.components.viewer_model import ViewerModel
from napari.utils import progress
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .._util_classes import (
    BigDatasetNamesDialog,
    LayerCorrectorTreeProducer,
    QtViewerWrap,
)
from .cell_size import MinimalCellSize
from .cross_config import CrossConfig
from .cross_embryo_comparison import CrossClustermap


class CrossHandler(LayerCorrectorTreeProducer):
    """Class to laod the widgets for comparing lineages across datasets."""

    name = "Cross Distance Calculation"

    def get_lt_manager(self, signal):
        """
        Gets the lineagetree manager object every time is
        changed Manager class.
        """
        self.manager = signal
        self.comparisonswidget.manager = signal
        self.config.manager = signal
        self.config.lineagetree_list.clear()
        self.config.lineagetree_list.addItems(
            [f"{key}" for key in self.manager.lineagetrees]
        )
        self.config.lineagetree_list.update()
        self.comparisonswidget.layers = {
            layer.metadata.get("name_for_manager", ""): layer
            for layer in self.viewer.layers
        }

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

    def thread_handler(self):
        continue_comps = True
        self.comparisons = []
        self.names = []
        self.norms = []
        for lineagetree in self.manager.lineagetrees:
            if len(lineagetree) > 6:
                continue_comps = BigDatasetNamesDialog()
                continue_comps.exec_()
                continue_comps = continue_comps.continue_proccess
                break
        if continue_comps:
            self.config.times = {}
            for tab in self.config.tab_dictionary:
                self.config.times[tab] = self.config.tab_dictionary[
                    tab
                ].ret_times()
            minimum_length = 1_000
            for tab in self.config.times:
                minimum_length = min(
                    len(self.config.times[tab]), minimum_length
                )
            self.pbr = progress(range(minimum_length))
            self.worker = self.config.roots_selector()
            self.worker.aborted.connect(self.kill_thread)
            self.worker.returned.connect(self.kill_thread)
            self.worker.errored.connect(self.kill_thread)
            self.worker.yielded.connect(self.update_comparisons)
            self.worker.start()
            self.runbutton.setChecked(True)
            self.stopbutton.setChecked(False)

    def update_comparisons(self, product):
        (
            self.comparisonswidget.comparisons,
            self.comparisonswidget.names,
            self.comparisonswidget.norms,
        ) = product
        self.comparisonswidget.time_slider.max = len(product[0]) - 1
        self.comparisonswidget.clustermap_creator()
        if self.pbr:
            self.pbr.update()

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)
        self.tabs = QTabWidget()
        self.pbr = None
        self.viewer = napari_viewer
        all_splitter = QSplitter()
        self.viewer_model1 = ViewerModel(title="SPC 1")
        self.viewer_model2 = ViewerModel(title="SPC 2")
        viewers = [self.viewer_model1, self.viewer_model2]
        self.qt_viewer1 = QtViewerWrap(napari_viewer, self.viewer_model1)
        self.qt_viewer2 = QtViewerWrap(napari_viewer, self.viewer_model2)
        viewer_splitter = QSplitter()
        viewer_splitter.setOrientation(Qt.Vertical)
        viewer_splitter.addWidget(self.qt_viewer1)
        sliders = MinimalCellSize(
            napari_viewer, self.viewer_model1, self.viewer_model2
        )
        viewer_splitter.addWidget(sliders)
        viewer_splitter.addWidget(self.qt_viewer2)
        viewer_splitter.setContentsMargins(0, 0, 0, 0)
        self.runbutton = QPushButton("Run Comparisons")
        self.runbutton.native = self.runbutton
        self.runbutton.name = "runbutton"
        self.runbutton.clicked.connect(self.thread_handler)
        self.runbutton.setCheckable(True)
        self.stopbutton = QPushButton("Stop Processing")
        self.stopbutton.native = self.stopbutton
        self.stopbutton.name = "stopbutton"
        self.stopbutton.setCheckable(True)
        self.button_container = widgets.Container(
            widgets=[self.runbutton, self.stopbutton],
            layout="horizontal",
            labels=False,
        )
        self.config = CrossConfig(self.viewer)

        self.comparisonswidget = CrossClustermap(
            self.viewer, dataset_viewers=viewers
        )

        whole_layout = QVBoxLayout()
        whole_layout.addStretch(1)
        self.widget = QWidget()
        self.widget.setLayout(whole_layout)
        self.tabs.addTab(self.config, "Configuration")
        self.tabs.addTab(self.comparisonswidget, "Plots")

        self.widget.layout().addWidget(self.tabs)
        self.widget.layout().addWidget(self.button_container.native)
        all_splitter.addWidget(viewer_splitter)
        all_splitter.addWidget(self.widget)
        all_layout = QVBoxLayout()
        self.setLayout(all_layout)
        all_layout.addWidget(all_splitter)
        self.stopbutton.released.connect(self.kill_thread)
        self.stopbutton.setChecked(True)
