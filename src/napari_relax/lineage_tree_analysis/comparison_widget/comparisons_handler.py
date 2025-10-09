
from napari.utils import progress
from qtpy.QtWidgets import (
    QPushButton,
    QTabWidget,
    QVBoxLayout,
)

from ..._util_classes import (
    Containerize,
    LayerCorrectorTreeProducer,
)
from .clustermap import OnlineClustermap
from .config import ConfigurationPanel


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
        self.clustermap.time_slider.max = len(self.clustermap.comps) - 1
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
        self.worker.aborted.connect(self.kill_thread)

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
