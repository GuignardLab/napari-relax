from qtpy.QtWidgets import QTabWidget, QVBoxLayout

from ..._util_classes import LayerCorrectorTreeProducer
from .clone_based_recoloring import CloneRecoloring
from .node_based_recoloring import Coloring


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
