from itertools import combinations

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

from ..._util_classes import containerize


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
        self.separate_check = QCheckBox("Separate labels")
        self.separate_check.setChecked(False)
        self.in_group_check = QCheckBox("In-group comparisons")
        self.in_group_check.setChecked(True)
        self.out_group_check = QCheckBox("Out-group comparisons")
        self.out_group_check.setChecked(True)
        self.accept_button = QPushButton("Accept")
        layout.addWidget(self.list_widget)
        layout.addWidget(self.in_group_check)
        layout.addWidget(self.out_group_check)
        layout.addWidget(self.separate_check)
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
                separate=self.separate_check.isChecked(),
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
        specific_roots: set | None = None,
        in_group=True,
        out_group=True,
        separate=False,
    ):
        super().__init__()
        self.lT = None
        self.bins = "auto"
        self.specific_roots = specific_roots
        self.in_group = in_group
        self.out_group = out_group
        self.separate = separate
        self.title = widgets.Label(value="")
        self.kill_button = QPushButton("X")
        self.kill_button.setFixedSize(20, 20)
        self.figure = Figure(figsize=(3, 2), constrained_layout=True)
        self.canvas = FigureCanvas(figure=self.figure)
        self.range = 0
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
        hist_values = []
        labels = []
        match (self.out_group, self.in_group):
            case (True, True):
                for key in list_of_comparisons:
                    if (
                        self.naming[time][key[0]][1] in self.specific_roots
                        and self.naming[time][key[1]][1] in self.specific_roots
                    ):
                        hist_values.append(
                            comparisons[key]
                            / self.norm_dict[str(self.norm_combo.value)](
                                self.norms[time][key]
                            )
                        )
                        self.hist_ax.set_title(
                            f"Time: {self.times[int(self.slider.value)]}"
                        )

            case (True, False):
                combs = list(combinations(self.specific_roots, 2))
                specific_combs = {(i, j): [] for i, j in combs}
                for key in list_of_comparisons:
                    root1 = get_all_ancestors_of_node(
                        self.lT, self.naming[time][key[0]][0]
                    ).intersection(self.specific_roots)
                    root2 = get_all_ancestors_of_node(
                        self.lT, self.naming[time][key[1]][0]
                    ).intersection(self.specific_roots)

                    if (
                        self.naming[time][key[0]][1] in self.specific_roots
                        and self.naming[time][key[1]][1] in self.specific_roots
                        and (root1 != root2)
                    ):
                        if self.separate:
                            if (
                                next(iter(root1)),
                                next(iter(root2)),
                            ) in specific_combs:
                                specific_combs[
                                    next(iter(root1)), next(iter(root2))
                                ].append(
                                    comparisons[key]
                                    / self.norm_dict[
                                        str(self.norm_combo.value)
                                    ](self.norms[time][key])
                                )
                            else:
                                specific_combs[
                                    next(iter(root2)), next(iter(root1))
                                ].append(
                                    comparisons[key]
                                    / self.norm_dict[
                                        str(self.norm_combo.value)
                                    ](self.norms[time][key])
                                )
                            self.hist_ax.set_title(
                                f"Time: {self.times[int(self.slider.value)]} only outgroup"
                            )
                            hist_values = [
                                list(li) for li in specific_combs.values()
                            ]
                            labels = [
                                f"{self.lT.labels.get(root1, root1)} - {self.lT.labels.get(root2,root2)}"
                                for root1, root2 in combs
                            ]
                        else:
                            hist_values.append(
                                comparisons[key]
                                / self.norm_dict[str(self.norm_combo.value)](
                                    self.norms[time][key]
                                )
                            )

            case (False, True):
                sp_root_dict = {root: [] for root in self.specific_roots}
                for key in list_of_comparisons:
                    root1 = get_all_ancestors_of_node(
                        self.lT, self.naming[time][key[0]][0]
                    ).intersection(self.specific_roots)
                    root2 = get_all_ancestors_of_node(
                        self.lT, self.naming[time][key[1]][0]
                    ).intersection(self.specific_roots)
                    if (
                        self.naming[time][key[0]][1] in self.specific_roots
                        and self.naming[time][key[1]][1] in self.specific_roots
                        and (root1 == root2)
                        and root1
                    ):
                        if self.separate:
                            sp_root_dict[next(iter(root1))].append(
                                comparisons[key]
                                / self.norm_dict[str(self.norm_combo.value)](
                                    self.norms[time][key]
                                )
                            )
                            hist_values = [
                                list(val) for val in sp_root_dict.values()
                            ]
                            self.hist_ax.set_title(
                                f"Time: {self.times[int(self.slider.value)]} only ingroup"
                            )
                            labels = [
                                self.lT.labels.get(root, root)
                                for root in self.specific_roots
                            ]
                        else:
                            hist_values.append(
                                comparisons[key]
                                / self.norm_dict[str(self.norm_combo.value)](
                                    self.norms[time][key]
                                )
                            )
                            self.hist_ax.set_title(
                                f"Time: {self.times[int(self.slider.value)]} only ingroup"
                            )
        return hist_values, labels

    def plot_hist(self):
        self.hist_ax.clear()
        time = int(self.slider.value)
        if self.lT is None:
            self.hist_ax.set_title(
                f"Time: {self.times[int(self.slider.value)]}"
            )
            comparisons = self.comparisons[time]
            hist_values = []
            if len(comparisons) > 0:
                for keys, values in comparisons:
                    hist_values.append(
                        comparisons[keys, values]
                        / self.norm_dict[str(self.norm_combo.value)](
                            self.norms[time][keys, values]
                        )
                    )
                _, leng, _ = self.hist_ax.hist(
                    hist_values, bins=self.bins, range=(0, 1)
                )
                self.bin_length = len(leng) - 1
                # self.hist_ax.set_xlim(0, 1)
                self.hist_ax.set_ylabel("# pairwise comparisons")
                self.hist_ax.set_xlabel("Tree edit distance")
        else:
            hist_values, labels = self.filter_roots()
            if labels == []:
                _, leng, _ = self.hist_ax.hist(
                    hist_values, bins=self.bins, range=(0, 1)
                )
            else:
                if hist_values and isinstance(hist_values[0], list):
                    for hist_val, lab in zip(hist_values, labels, strict=False):
                        _, leng, _ = self.hist_ax.hist(
                            hist_val,
                            bins=self.bins,
                            range=(0, 1),
                            label=lab,
                            alpha=0.7,
                        )
                else:
                    _, leng, _ = self.hist_ax.hist(
                        hist_values,
                        bins=self.bins,
                        range=(0, 1),
                        label=labels,
                        alpha=0.7,
                    )
                self.hist_ax.legend()
            self.bin_length = len(leng) - 1
            # self.hist_ax.set_xlim(0, 1)
            self.hist_ax.set_ylabel("# pairwise comparisons")
            self.hist_ax.set_xlabel("Tree edit distance")
        self.canvas.draw()

    def update_values(
        self, product: tuple[dict, dict, dict], labels: dict, times: list
    ):
        self.comparisons, self.naming, self.norms = product
        self.labels = labels
        self.slider.max = len(self.comparisons) - 1
        self.times = times


class HistogramWidget(QWidget):
    def receive_values(self, data_from_clustermap: tuple[dict, dict, dict]):
        self.comparisons, self.naming, self.norms = data_from_clustermap
        self.layer_change()
        self.main_hist.slider.max = len(self.comparisons) - 1
        self.master_slider.max = len(self.comparisons) - 1
        self.main_hist.update_values(
            data_from_clustermap, self.labels, self.times
        )
        self.main_hist.bins = self.master_binsizer.value
        self.main_hist.title.value = f"Roots: {','.join(str(self.labels.get(label[1],label[1])) for label in self.naming[0].values())}"
        self.main_hist.plot_hist()

    def add_hist(self):
        popup = pop_up(self.naming, self.labels)
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
            hist.title.value = f"Roots: {','.join(str(self.labels.get(r,r)) for r in hist.specific_roots)}"
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
                print(self.main_hist.bin_length)
                hist.bins = self.main_hist.bin_length
            else:
                hist.bins = self.master_binsizer.value
            hist.plot_hist()

    def remove_hist(self, obj: QWidget):
        self.container.layout().removeWidget(obj)
        obj.setParent(None)
        obj.deleteLater()
        self.all_histograms.remove(obj)

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
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.main_hist = HistTemplate()
        self.main_hist.layout().removeWidget(self.main_hist.kill_button)
        self.main_hist.kill_button.setParent(None)
        self.add_button = QPushButton("+")
        # self.add_button.setFixedSize(20, 20)
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
