from magicgui import widgets
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from ..._util_classes import containerize
from .histogramtemplate import HistTemplate
from .popup_for_hist import pop_up


class HistogramWidget(QWidget):
    def receive_values(self, data_from_clustermap: tuple[dict, dict, dict]):
        if data_from_clustermap is not None:
            self.comparisons, self.naming, self.norms = data_from_clustermap
            self.layer_change()
            self.main_hist.slider.max = len(self.comparisons) - 1
            self.master_slider.max = len(self.comparisons) - 1
            self.main_hist.update_values(
                data_from_clustermap, self.labels, self.times
            )
            self.main_hist.bins = self.master_binsizer.value
            self.main_hist.title.value = f"Roots: {','.join(str(self.labels.get(self.lT.get_labelled_ancestor(label[0]),label[0])) for label in self.naming[0].values())}"
            self.main_hist.plot_hist()

    def add_hist(self):
        if not self.naming:
            return
        popup = pop_up(self.naming, self.labels, self.lT)
        popup.exec_()
        if hasattr(popup, "hist"):
            hist = popup.hist
            self.all_histograms.add(hist)
            hist.update_values(
                (self.comparisons, self.naming, self.norms),
                self.labels,
                self.times,
            )
            hist.lT = self.lT
            if self.master_binsizer.value in ["auto", "fd"]:
                hist.bins = self.main_hist.bin_length
            else:
                hist.bins = self.master_binsizer.value
            hist.plot_hist()
            hist.kill_signal.connect(self.remove_hist)
            hist.title.value = f"Roots: {','.join(str(self.labels.get(self.lT.get_labelled_ancestor(r),r)) for r in hist.specific_roots)}"
            self.container.layout().insertWidget(
                self.container.layout().count() - 2, hist
            )

    def control_sliders(self):
        self.main_hist.slider.value = self.master_slider.value
        self.main_hist.plot_hist()
        for hist in self.all_histograms:
            if self.master_binsizer.value in ["auto", "fd"]:
                hist.bins = self.main_hist.bin_length
            else:
                hist.bins = self.master_binsizer.value
            hist.slider.value = self.master_slider.value
            hist.plot_hist()

    def control_bins(self):
        self.main_hist.bins = self.master_binsizer.value
        self.main_hist.plot_hist()
        for hist in self.all_histograms:
            if self.master_binsizer.value in ["auto", "fd"]:
                hist.bins = self.main_hist.bin_length
            else:
                hist.bins = self.master_binsizer.value
            hist.plot_hist()

    def remove_hist(self, obj: QWidget):
        self.container.layout().removeWidget(obj)
        obj.setParent(None)
        self.all_histograms.remove(obj)
        obj.deleteLater()
        self.container.update()

    def layer_change(self):
        for hist in self.all_histograms:
            self.remove_hist(hist)
        self.all_histograms.clear()
        self.main_hist.hist_ax.clear()

    def receive_labels_and_times(self, labels, times):
        self.labels = labels
        self.times = times

    def __init__(self, lT):
        super().__init__()
        self.lT = lT
        self.range = 0
        self.comparisons = {}
        self.norms = {}
        self.labels = {}
        self.all_histograms = set()
        self.scroll_area = QScrollArea()
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.scroll_area.setWidgetResizable(True)
        self.main_hist = HistTemplate()
        self.main_hist.layout().removeWidget(self.main_hist.kill_button)
        self.main_hist.kill_button.setParent(None)
        self.add_button = QPushButton("Add new Histogram")
        self.container = QWidget()
        self.container.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.container.setLayout(QVBoxLayout(self.container))
        self.scroll_area.setWidget(self.container)
        self.spacer = QSpacerItem(
            20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        self.master_binsizer = widgets.ComboBox(
            value="auto", choices=["auto", "fd"] + list(range(2, 41))[::3]
        )
        self.master_binsizer.changed.connect(self.control_bins)
        bins_cont = containerize(
            [
                widgets.Label(value="Master bins").native,
                self.master_binsizer.native,
            ]
        )

        self.master_slider = widgets.Slider(value=0, min=0, max=0)
        self.master_slider.changed.connect(self.control_sliders)
        m_slid_label = widgets.Label(value="Master Control")
        slid_cont = containerize(
            [m_slid_label.native, self.master_slider.native]
        )
        self.container.setContentsMargins(0, 0, 0, 0)

        self.container.layout().addWidget(self.main_hist)
        self.container.layout().addWidget(
            self.add_button, alignment=Qt.AlignCenter
        )
        self.container.layout().addItem(self.spacer)

        outer_layout = QVBoxLayout(self)
        slid_cont.setContentsMargins(0, 0, 0, 0)
        bins_cont.setContentsMargins(0, 0, 0, 0)

        outer_layout.layout().addWidget(slid_cont)
        outer_layout.layout().addWidget(bins_cont)
        outer_layout.setSpacing(0)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.scroll_area)
        self.setLayout(outer_layout)
        self.add_button.clicked.connect(self.add_hist)


######TODO######
# Merge Graphs(maybe easy)
# cross (easy)
