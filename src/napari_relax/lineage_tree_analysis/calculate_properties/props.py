from collections.abc import Callable
from numbers import Number

import matplotlib.pyplot as plt
from lineagetree import LineageTree
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from napari.settings import get_settings
from psygnal import Signal
from qtpy.QtCore import QEvent, Qt
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


class NonInteractiveCanvas(FigureCanvas):
    def wheelEvent(self, event):
        event.ignore()

    def mousePressEvent(self, event):
        event.ignore()


class GeneralPlot(QWidget):
    kill_signal = Signal(QWidget)
    selected_widget = Signal(QWidget | None)

    default_options_for_plot = {}

    @property
    def highlight(self) -> str:
        highlight_color = list(
            get_settings().appearance.highlight.highlight_color
        )

        highlight_color[-1] = 0.2

        r, g, b, a = highlight_color

        return f"""
            background-color: rgba(
                {int(r * 255)},
                {int(g * 255)},
                {int(b * 255)},
                {int(a * 255)}
            );
        """

    def __init__(self, data) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.data = data
        self.setFixedSize(600, 400)
        self.setAttribute(Qt.WA_StyledBackground, True)

        button_layout = QHBoxLayout()

        self.close_button = QPushButton("X")
        self.close_button.setFixedSize(30, 30)
        self.close_button.clicked.connect(lambda: self.kill_signal.emit(self))

        self.settings_button = QPushButton("⚙")
        self.settings_button.setFixedSize(30, 30)

        button_layout.addStretch()
        button_layout.addWidget(self.settings_button)
        button_layout.addSpacing(10)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

        self.dialog = GeneralOptionsPlot(self)

        self.settings_button.clicked.connect(self.open_dialog)
        fig, self.ax = plt.subplots()
        self.canvas = NonInteractiveCanvas(fig)
        self.layout().addWidget(self.canvas)
        self.plot()
        self.installEventFilter(self)

    def plot(self): ...

    def open_dialog(self):
        self.dialog.setWindowTitle("Plot settings")
        self.dialog.resize(400, 300)
        self.dialog.exec()

    def paintBorder(self):
        self.setStyleSheet(self.highlight)

    def resetBorder(self):
        self.setStyleSheet("")

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if not hasattr(self, "selected") or self.selected is False:
                self.paintBorder()
                self.selected = True
                self.selected_widget.emit(self)
            else:
                self.resetBorder()
                self.selected = False
                self.selected_widget.emit(None)

            self.update()
        return super().eventFilter(obj, event)


class Histogram(GeneralPlot):
    def plot(self):
        self.ax.clear()
        for _name, value in self.data.items():
            self.ax.hist(list(value.values()))
        self.canvas.flush_events()
        self.canvas.draw_idle()


class ScatterPlot(GeneralPlot):
    def __init__(
        self, data: dict[str, dict[int, dict]], lT: LineageTree
    ) -> None:
        self.lT = lT
        super().__init__(data)

    def plot(self):
        self.ax.clear()
        for _name, value in self.data.items():
            x, y = [], []
            for node, val in value.items():
                x.append(self.lT.time[node])
                y.append(val)
            self.ax.scatter(x, y)
        self.canvas.draw_idle()


class PropertyVisualization(LayerCorrectorTreeProducer):
    name = "Property Visualization"
    selected_plot: GeneralPlot | None = None

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
        create_scatter_plot.clicked.connect(self.create_scatter)
        create_hist = QPushButton("Create Histogram")
        create_hist.clicked.connect(self.create_histogram)
        add_2_plot = QPushButton("Add to Plot")
        add_2_plot.clicked.connect(self.add_data_to_plot)
        push_layout.addWidget(create_scatter_plot)
        push_layout.addWidget(create_hist)
        push_layout.addWidget(add_2_plot)

        list_layout.addLayout(push_layout)
        total_layout.addLayout(list_layout)

        self.plot_widget = QWidget()
        self.plot_layout = QVBoxLayout(self.plot_widget)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.plot_widget)

        total_layout.addWidget(self.scroll_area)
        self.viewer.layers.selection.events.active.connect(self.layer_change)
        self.populate_tabs(self.tab_widget)

    def populate_tabs(self, tab_wdg: QTabWidget):
        active_layer = _select_active_lt_layer(self.viewer)
        if not active_layer:
            return
        methods = find_all_viable_methods(LineageTree)

        for method in methods:
            widget = self.generate_tab_widget(method)
            tab_wdg.addTab(widget, convert_to_title(method.__name__))

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
        self.populate_list_widget()

    def populate_list_widget(self):
        active_layer = _select_active_lt_layer(self.viewer)
        if not active_layer:
            return
        lt = active_layer.metadata["LineageTree"]
        attributes = filter_dicts_of_objects_by_values(
            lt, Number
        )  ### Change this to whatever .properties will be used

        self.list.addItems(attributes)
        self.list.repaint()

    def add_data_to_plot(self):
        active_layer = _select_active_lt_layer(self.viewer)
        print(self.selected_plot)
        if not active_layer or not self.selected_plot:
            return
        selected_attrs = [
            selected.text() for selected in self.list.selectedItems()
        ]
        data_2_use = {
            selected_attr: getattr(self.get_lT(), selected_attr)
            for selected_attr in selected_attrs
        }
        print(data_2_use)
        self.selected_plot.data.update(data_2_use)
        self.selected_plot.plot()

    def create_histogram(self):
        active_layer = _select_active_lt_layer(self.viewer)
        if not active_layer:
            return
        selected_attrs = [
            selected.text() for selected in self.list.selectedItems()
        ]
        data_2_use = {
            selected_attr: getattr(self.get_lT(), selected_attr)
            for selected_attr in selected_attrs
        }
        hist = Histogram(data_2_use)
        hist.kill_signal.connect(self.onKill)
        hist.selected_widget.connect(self.onPlotSelect)
        self.plot_layout.addWidget(hist)

    def create_scatter(self):
        active_layer = _select_active_lt_layer(self.viewer)
        if not active_layer:
            return
        selected_attrs = [
            selected.text() for selected in self.list.selectedItems()
        ]
        lT = self.get_lT()
        if not lT:
            return
        data_2_use = {
            selected_attr: getattr(lT, selected_attr)
            for selected_attr in selected_attrs
        }
        scatter = ScatterPlot(data_2_use, lT)
        scatter.kill_signal.connect(self.onKill)
        scatter.selected_widget.connect(self.onPlotSelect)
        self.plot_layout.addWidget(scatter)

    def onKill(self, hist):
        if self.selected_plot is hist:
            self.selected_plot = None
        hist.deleteLater()

    def onPlotSelect(self, event):
        if self.selected_plot is not None:
            self.selected_plot.resetBorder()
            self.selected_plot.selected = False
        self.selected_plot = event

    def layer_change(self):
        while self.tab_widget.count() > 0:
            self.tab_widget.removeTab(0)
        self.populate_tabs(self.tab_widget)
        self.list.clear()
        self.populate_list_widget()
