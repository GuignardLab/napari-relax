from itertools import combinations

from magicgui import widgets
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from matplotlib.figure import Figure
from psygnal import Signal
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..._utils import get_all_ancestors_of_node


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
                    root1 = get_all_ancestors_of_node(
                        self.lT, self.naming[time][key[0]][0]
                    ).intersection(self.specific_roots)
                    root2 = get_all_ancestors_of_node(
                        self.lT, self.naming[time][key[1]][0]
                    ).intersection(self.specific_roots)

                    if root1 and root2:
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

                    if root1 and root2 and (root1 != root2):
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
                    if root2 and root1 and (root1 == root2):
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
                    for hist_val, lab in zip(
                        hist_values, labels, strict=False
                    ):
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
