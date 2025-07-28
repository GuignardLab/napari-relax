from magicgui import widgets
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from matplotlib.figure import Figure
from psygnal import Signal
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


class pop_up(QDialog):

    def __init__(self, roots, labels):
        super().__init__()

        layout = QVBoxLayout()
        self.setWindowTitle("Create new Histogram")
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        self.list_items = [
            f"{root[1]} - {labels[root[1]]}" for root in roots[0].values()
        ]
        self.list_widget.addItems(self.list_items)
        self.in_group_check = QCheckBox("In-group comparisons")
        self.in_group_check.setChecked(True)
        self.out_group_check = QCheckBox("Out-group comparisons")
        self.out_group_check.setChecked(True)
        self.accept_button = QPushButton("Accept")
        layout.addWidget(self.list_widget)
        layout.addWidget(self.in_group_check)
        layout.addWidget(self.out_group_check)
        layout.addWidget(self.accept_button)
        self.setLayout(layout)
        self.accept_button.clicked.connect(self.accept_parameters)

    def accept_parameters(self):
        if len(self.list_widget.selectedItems()) > 0 and (
            self.in_group_check.isChecked() or self.out_group_check.isChecked()
        ):
            lista = [
                int(self.list_items[i.row()].split(" ")[0])
                for i in self.list_widget.selectedIndexes()
            ]
            self.hist = HistTemplate(
                specific_roots=lista,
                in_group=self.in_group_check.isChecked(),
                out_group=self.out_group_check.isChecked(),
            )
            self.accept()


def get_all_ancestors_of_node(lT, n: int) -> set:
    ancestor = n
    ancestor_list = {n}
    while lT._predecessor[ancestor]:
        ancestor = lT._predecessor[ancestor][0]
        if ancestor:
            ancestor_list.add(ancestor)

    return ancestor_list


class HistTemplate(QWidget):

    kill_signal = Signal(object)

    def __init__(
        self,
        specific_roots=...,
        in_group=True,
        out_group=True,
    ):
        super().__init__()
        self.lT = None
        self.specific_roots = specific_roots
        self.in_group = in_group
        self.out_group = out_group
        self.title = widgets.Label(value="")
        self.kill_button = QPushButton("X")
        self.kill_button.setFixedSize(20, 20)
        self.figure = Figure(figsize=(3, 2), constrained_layout=True)
        self.canvas = FigureCanvas(figure=self.figure)
        self.range = 1  # for now
        self.norm_combo = widgets.ComboBox(
            value="max",
            choices=["max", "sum", "None"],
        )
        self.norm_combo.native.setSizePolicy(
            QSizePolicy.Minimum, QSizePolicy.Minimum
        )
        self.norm_dict = {"max": max, "sum": sum, "None": lambda x: 1}
        self.norm_combo.changed.connect(self.plot_hist)
        self.slider = widgets.Slider(min=0, max=self.range)
        self.hist_ax = self.figure.add_subplot(111)
        head_widget = QWidget()
        header = QHBoxLayout()
        header.addWidget(self.norm_combo.native)
        header.addWidget(self.title.native)
        header.addWidget(self.kill_button, alignment=Qt.AlignRight)
        head_widget.setLayout(header)
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.setLayout(layout)
        self.layout().addWidget(head_widget)
        self.layout().addWidget(self.canvas)
        self.layout().addWidget(self.slider.native)
        self.slider.changed.connect(self.plot_hist)
        self.kill_button.clicked.connect(self.kill_widget)

    def kill_widget(self):
        self.kill_signal.emit(self)

    def filter_roots(self):
        time = int(self.slider.value)
        comparisons = self.comparisons[time]
        list_of_comparisons = list(comparisons.keys())
        new_c = {}
        match (self.out_group, self.in_group):
            case (True, True):
                for key in list_of_comparisons:
                    if (
                        self.naming[time][key[0]][1] in self.specific_roots
                        and self.naming[time][key[1]][1] in self.specific_roots
                    ):
                        new_c[key] = comparisons[key]
                        self.hist_ax.set_title(
                            f"Time: {self.times[int(self.slider.value)]}"
                        )

            case (True, False):
                for key in list_of_comparisons:
                    print(
                        get_all_ancestors_of_node(
                            self.lT, self.naming[time][key[0]][0]
                        ).intersection(self.specific_roots),
                        get_all_ancestors_of_node(
                            self.lT, self.naming[time][key[1]][1]
                        ).intersection(self.specific_roots),
                    )

                    if (
                        self.naming[time][key[0]][1] in self.specific_roots
                        and self.naming[time][key[1]][1] in self.specific_roots
                        and (
                            get_all_ancestors_of_node(
                                self.lT, self.naming[time][key[0]][0]
                            ).intersection(self.specific_roots)
                            != (
                                get_all_ancestors_of_node(
                                    self.lT, self.naming[time][key[1]][0]
                                ).intersection(self.specific_roots)
                            )
                        )
                    ):
                        print("ftanw edw")
                        new_c[key] = comparisons[key]
                        self.hist_ax.set_title(
                            f"Time: {self.times[int(self.slider.value)]} only outgroup"
                        )

            case (False, True):
                for key in list_of_comparisons:
                    if (
                        self.naming[time][key[0]][1] in self.specific_roots
                        and self.naming[time][key[1]][1] in self.specific_roots
                        and (
                            get_all_ancestors_of_node(
                                self.lT, self.naming[time][key[0]][0]
                            ).intersection(self.specific_roots)
                            == (
                                get_all_ancestors_of_node(
                                    self.lT, self.naming[time][key[1]][0]
                                ).intersection(self.specific_roots)
                            )
                        )
                    ):
                        new_c[key] = comparisons[key]
                        self.hist_ax.set_title(
                            f"Time: {self.times[int(self.slider.value)]} only ingroup"
                        )

        return new_c

    def plot_hist(self):
        self.hist_ax.clear()
        time = int(self.slider.value)
        if self.lT is None:
            comparisons = self.comparisons[time]
        else:
            comparisons = self.filter_roots()
        hist_values = []
        if len(comparisons) > 0:
            for keys, values in comparisons:
                hist_values.append(
                    comparisons[keys, values]
                    / self.norm_dict[str(self.norm_combo.value)](
                        self.norms[time][keys, values]
                    )
                )
            self.hist_ax.hist(hist_values)
        self.canvas.draw()

    def update_values(self, product, labels={}, times=...):
        self.comparisons, self.naming, self.norms = product
        self.labels = labels
        self.slider.max = len(self.comparisons) - 1
        self.times = times


class HistogramWidget(QScrollArea):

    def receive_values(self, data_from_clustermap: tuple[dict, dict, dict]):
        self.comparisons, self.naming, self.norms = data_from_clustermap
        self.layer_change()
        self.main_hist.slider.max = len(self.comparisons) - 1
        self.main_hist.update_values(
            data_from_clustermap, self.labels, self.times
        )
        self.main_hist.title.value = f"Roots: {','.join(str(self.labels.get(label[1],label[1])) for label in self.naming[0].values())}"
        self.main_hist.plot_hist()

    def add_hist(self):
        popup = pop_up(self.naming, self.labels)
        popup.exec_()
        hist = popup.hist
        self.all_histograms.add(hist)
        hist.update_values(
            (self.comparisons, self.naming, self.norms),
            self.labels,
            self.times,
        )
        hist.lT = self.lT
        hist.plot_hist()
        hist.kill_signal.connect(self.remove_hist)
        hist.title.value = f"Roots: {','.join(str(self.labels.get(r,r)) for r in hist.specific_roots)}"
        self.layout.insertWidget(self.layout.count() - 2, hist)

    def remove_hist(self, obj: QWidget):
        self.layout.removeWidget(obj)
        obj.setParent(None)
        obj.deleteLater()

    def layer_change(self):
        for hist in self.all_histograms:
            self.remove_hist(hist)
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
        self.main_hist = HistTemplate()
        self.main_hist.layout().removeWidget(self.main_hist.kill_button)
        self.main_hist.kill_button.setParent(None)
        self.add_button = QPushButton("+")
        self.add_button.setFixedSize(20, 20)
        self.container = QWidget()
        self.container.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.layout = QVBoxLayout(self.container)
        self.setWidget(self.container)
        self.spacer = QSpacerItem(
            20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding
        )

        self.setWidget(self.container)
        self.setWidgetResizable(True)
        self.layout.addWidget(self.main_hist)
        self.layout.addWidget(self.add_button)
        self.layout.addItem(self.spacer)
        self.add_button.clicked.connect(self.add_hist)


######TODO######
# Synchronous sliders (EAsy)
# Merge Graphs(maybe easy)
# cross (easy)
