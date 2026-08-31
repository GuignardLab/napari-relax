from collections.abc import Callable
from numbers import Number

import matplotlib.pyplot as plt
from lineagetree import LineageTree
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from psygnal import Signal
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from napari_relax._util_classes import (
    DelayedTooltipEventFilter,
    LayerCorrectorTreeProducer,
)
from napari_relax.lineage_tree_analysis.calculate_properties.props_utils import (
    convert_to_title,
    find_all_viable_methods,
    get_parameter_doc,
    get_parameters_of_function,
)
from napari_relax.lineage_tree_analysis.calculate_properties.widget_generator import (
    LineEditGenerator,
)
from napari_relax.lineage_tree_analysis.recoloring_with_attributes_widget.node_based_recoloring import (
    filter_dicts_of_objects_by_values,  #### Temporary####
)

from ..._utils import _select_active_lt_layer


class TabFactory(QWidget):
    def __init__(self, method: Callable) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        pars = get_parameters_of_function(method)
        event_filt = DelayedTooltipEventFilter()
        self.installEventFilter(event_filt)

        widget_dict = {}

        for name, typ in pars.items():
            wdg = LineEditGenerator(name, typ)

            if prm := get_parameter_doc(method, name):
                wdg.setToolTip(prm)

            widget_dict[name] = wdg
            layout.addWidget(wdg)

        self.widget_dict = widget_dict

        self.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Maximum,
        )
        self.method = method
        self.run = QPushButton("Run")
        self.layout().addWidget(self.run)


class GeneralOptionsPlot(QDialog):
    settings_accepted = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Plot Settings")
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        layout = QVBoxLayout(self)

        # Your settings widgets here...

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )

        buttons.accepted.connect(self.accept_settings)
        buttons.rejected.connect(self.hide)

        layout.addWidget(buttons)

    def accept_settings(self):
        settings = {
            "color": "blue",
            "alpha": 0.5,
            "line_style": "--",
            "line_width": 1.5,
        }

        self.settings_accepted.emit(settings)

        # Don't destroy the dialog
        self.hide()

    def closeEvent(self, event):
        # X button → hide instead of destroy
        event.ignore()
        self.hide()


class GeneralPlot(QWidget):
    kill_signal = Signal()

    default_options_for_plot = {}

    def __init__(self, data) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.data = data
        if self.data and isinstance(self.data[0], list):
            self.number_of_datasets = len(self.data)
        elif self.data:
            self.number_of_datasets = 1
        else:
            self.number_of_datasets = 0
        if self.number_of_datasets == 1:
            self.data = [self.data]

        self.close_button = QPushButton("X")
        self.close_button.resize(400, 400)
        self.close_button.clicked.emit(self.kill_signal)
        layout.addWidget(
            self.close_button, alignment=Qt.AlignTop | Qt.AlignRight
        )
        layout = QVBoxLayout(self)

        self.settings_button = QPushButton("⚙", self)
        self.settings_button.setFixedSize(30, 30)

        self.dialog = GeneralOptionsPlot(self)

        self.settings_button.clicked.connect(self.open_dialog)
        fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(fig)
        self.layout().addWidget(self.canvas)
        self.plot()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        margin = 5
        self.settings_button.move(
            self.width() - self.settings_button.width() - margin, margin
        )

    def plot(self): ...

    def open_dialog(self):
        self.dialog.setWindowTitle("Plot settings")
        self.dialog.resize(400, 300)
        self.dialog.exec()


class Histogram(GeneralPlot):
    def plot(self):
        for _ in self.data:
            self.ax.hist(self.data)


class PropertyVisualization(LayerCorrectorTreeProducer):
    name = "Property Visualization"

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)

        self.viewer = napari_viewer
        self.tab_widget = QTabWidget()

        total_layout = QVBoxLayout(self)
        total_layout.setContentsMargins(0, 0, 0, 0)
        total_layout.setSpacing(4)

        title = QLabel(
            '<span style="font-family: Arial; font-size: 20px; color: white;">'
            "Function Runner"
            "</span>"
        )
        title.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Fixed,
        )

        total_layout.addWidget(
            title,
            alignment=Qt.AlignHCenter | Qt.AlignTop,
        )

        total_layout.addWidget(
            self.tab_widget,
            alignment=Qt.AlignTop,
        )

        self.populate_tabs()

        list_label = QLabel(
            '<span style="font-family: Arial; font-size: 20px; color: white;">'
            "List"
            "</span>"
        )
        list_label.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Fixed,
        )

        total_layout.addWidget(
            list_label,
            alignment=Qt.AlignHCenter | Qt.AlignTop,
        )
        list_layout = QHBoxLayout()

        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.MultiSelection)
        list_layout.addWidget(self.list)
        push_layout = QVBoxLayout()
        create_scatter_plot = QPushButton("Create Scatter Plot")
        create_hist = QPushButton("Create Histogram")
        create_hist.clicked.connect(self.create_histogram)
        push_layout.addWidget(create_scatter_plot)
        push_layout.addWidget(create_hist)
        list_layout.addLayout(push_layout)
        total_layout.addLayout(list_layout)

        self.plot_widget = QWidget(self)
        self.plot_layout = QVBoxLayout(self.plot_widget)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.plot_widget)

        total_layout.addStretch()

    def populate_tabs(self):
        methods = find_all_viable_methods(LineageTree)

        for method in methods:
            widget = self.generate_tab_widget(method)
            self.tab_widget.addTab(widget, convert_to_title(method.__name__))

    def generate_tab_widget(self, method: Callable) -> QWidget:
        widget: TabFactory = TabFactory(method)
        widget.run.clicked.connect(self.run_LineagaeTree_method)
        return widget

    def run_LineagaeTree_method(self):
        wdg: TabFactory = self.tab_widget.currentWidget()

        if wdg is None:
            return
        active_layer = _select_active_lt_layer(self.viewer)
        parameters = {
            str(par): val.get_value() for par, val in wdg.widget_dict.items()
        }
        parameters["self"] = active_layer.metadata["LineageTree"]
        wdg.method(**parameters)
        self.list.clear()
        print("etrexa")
        self.populate_list_widget()

    def populate_list_widget(self):
        active_layer = _select_active_lt_layer(self.viewer)
        lt = active_layer.metadata["LineageTree"]
        attributes = filter_dicts_of_objects_by_values(lt, Number)

        self.list.addItems(attributes)
        self.list.repaint()

    # def create_histogram(self):
    #     data_2_use = [getattr(self.get_lT)]
