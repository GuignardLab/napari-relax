"""Distance Calculation entry of the Lineage tree analysis widget."""

from napari.utils import progress
from qtpy.QtWidgets import QPushButton, QTabWidget, QVBoxLayout

from ..._util_classes import (
    Containerize,
    LayerCorrectorTreeProducer,
)
from .clustermap import Clustermap
from .config import ConfigurationPanel


class ComparisonsHandler(LayerCorrectorTreeProducer):
    """Tabs to configure, run and inspect pairwise lineage comparisons.

    The Configuration Panel tab (`ConfigurationPanel`) sets up and
    runs the comparisons; the Clustermap tab (`Clustermap`) shows the
    results.

    Parameters
    ----------
    napari_viewer : napari.Viewer
        The napari viewer.
    """

    name = "Distance Calculation"

    def update_dictionary(self, product):
        """Send the results yielded by the comparison thread to the clustermap.

        Parameters
        ----------
        product : tuple
            Comparisons, sublineage names, normalizations and timepoints,
            one entry per timepoint computed so far.
        """
        (
            self.clustermap.comps,
            self.clustermap.naming,
            self.clustermap.norms,
            self.clustermap.times,
        ) = product
        self.clustermap.time_slider.max = len(self.clustermap.comps) - 1
        if self.pbr:
            self.pbr.update()
        self.clustermap.send_data()

    def thread_handler(self):
        """Start the comparisons in a background thread.

        The results are sent to `update_dictionary` as each timepoint is
        computed.
        """
        self.comps = []
        self.naming = []
        self.norms = []
        self.config.times_selector()
        if not self.config.times:
            self.kill_thread()
            return
        self.pbr = progress(range(len(self.config.times)))
        self.worker = self.config.thread_worker()
        self.worker.aborted.connect(self.kill_thread)
        self.worker.returned.connect(self.kill_thread)
        self.worker.errored.connect(self.kill_thread)
        self.worker.yielded.connect(self.update_dictionary)
        self.worker.start()
        self.runbutton.setChecked(True)
        self.stopbutton.setChecked(False)

    def kill_thread(self, dummy_event=None):
        """Stop the comparison thread and close the progress bar.

        Parameters
        ----------
        dummy_event : object, optional
            Event of the signal that triggered the stop, unused.
        """
        if self.pbr:
            self.pbr.close()
            self.pbr.clear()
            self.pbr = None
        self.worker.quit()
        self.stopbutton.setChecked(True)
        self.runbutton.setChecked(False)

    def __init__(self, napari_viewer):
        """Build the tabs and the Run/Stop buttons.

        Parameters
        ----------
        napari_viewer : napari.Viewer
            The napari viewer.
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

        self.clustermap = Clustermap(self.viewer, self.config)
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
