import copy
import os
from itertools import combinations
from time import sleep

import numpy as np
from lineagetree.tree_approximation import tree_style
from magicgui import widgets
from napari._qt.qthreading import thread_worker
from qtpy.QtWidgets import (
    QComboBox,
    QListWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .._util_classes import (
    Containerize,
    LayerCorrectorTreeProducer,
    TabTemplate,
    TooltipButton,
)


class CrossConfig(LayerCorrectorTreeProducer):
    name = "CrossConfig"

    def get_lt_manager(self, signal):
        """
        Gets the lineagetree manager object every time is
        changed Manager class.
        """
        self.manager = signal
        self.lineagetree_list.clear()
        self.lineagetree_list.addItems(
            [f"{key}" for key in self.manager.lineagetrees]
        )
        self.lineagetree_list.update()
        self.layers = {
            layer.metadata.get("name_for_manager", ""): layer
            for layer in self.viewer.layers
        }

    def tab_maker(self):
        selected_items = self.lineagetree_list.selectedItems()
        self.tab_dictionary = {}
        for _ in range(self.root_tabs.count()):
            self.root_tabs.removeTab(0)
        if len(selected_items) < 1:
            default_tab = QWidget()
            default_layout = QVBoxLayout()
            default_layout.addStretch(1)
            default_tab.setLayout(default_layout)
            self.root_tabs.addTab(default_tab, "Empty Layout")
        else:
            for item in selected_items:
                self.tab_dictionary[item.text()] = TabTemplate(
                    self.manager.lineagetrees[item.text()], item.text()
                )
                self.root_tabs.addTab(
                    self.tab_dictionary[item.text()], item.text()
                )

        self.root_tabs.update()
        self.layout().update()

    @thread_worker
    def roots_selector(self):
        roots = {}
        end_times = {}
        all_comparisons = []
        all_names = []
        all_norms = []
        local_manager = copy.copy(self.manager)
        for tab in self.tab_dictionary:
            roots[tab] = self.tab_dictionary[tab].show_roots()
            # self.times[tab] = self.tab_dictionary[tab].ret_times()
            end_times[tab] = self.tab_dictionary[tab].time_crop
        minimum_length = 1_000
        for tab in self.times:
            minimum_length = min(len(self.times[tab]), minimum_length)
        for t in range(int(minimum_length)):
            comparisons = {}
            self.all_roots = [
                (
                    lt,
                    selected_root,
                    int(node),
                )
                for lt in roots
                for node in roots[lt]
                for selected_root in local_manager.lineagetrees[lt].nodes_at_t(
                    self.times[lt][t], int(node)
                )
            ]
            names = dict(enumerate(self.all_roots))
            norms = {}
            combs = combinations(names.keys(), 2)
            for sleep_timer, (n1, n2) in enumerate(combs):
                (
                    comparisons[n1, n2],
                    norms[n1, n2],
                ) = local_manager.cross_lineage_edit_distance(
                    names[n1][1],
                    names[n1][0],
                    names[n2][1],
                    names[n2][0],
                    end_times[names[n1][0]],
                    end_times[names[n2][0]],
                    style=self.comp_style,
                    downsample=int(
                        self.downsampling_widget.currentText().split(" ")[0]
                    ),
                    return_norms=True,
                )

                if sleep_timer % 5 == 0:
                    sleep(0.1)
            all_comparisons.append(comparisons)
            all_names.append(names)
            all_norms.append(norms)
            yield all_comparisons, all_names, all_norms

    @property
    def lcm(self):
        tmp_tr = []
        for item in self.lineagetree_list.selectedItems():
            tmp_tr.append(
                int(self.manager.lineagetrees[item.text()]._time_resolution)
            )
        if len(tmp_tr) == 1:
            return tmp_tr.pop()
        elif tmp_tr:
            return np.lcm.reduce(tmp_tr)
        return 1

    def kill_thread(self):
        """
        Function to kill the thread if the user decides to.
        """
        self.worker.quit()
        self.stopbutton.setChecked(True)
        self.runbutton.setChecked(False)

    def update_comparisons(self, product):
        self.comparisons, self.names, self.norms = product
        self.time_slider.max = len(product[0]) - 1

    def update_tree_style(self):
        self.downsampling_widget.setVisible(False)
        self.comp_style = self.tree_style_combobox.current_choice
        if self.comp_style == "downsampled":
            self.downsampling_widget.setVisible(True)

    def change_downsampling_rates(self):
        self.downsampling_widget.clear()
        for i in [f"{i} downsampling rate" for i in range(1, 30)]:
            self.downsampling_widget.addItem(i)

    def change_tooltip_for_downsample(self):
        cur_text = self.downsampling_widget.currentText().split(" ")
        if cur_text[0]:
            down_factor = int(cur_text[0])
            list_of_selected_emryos = [
                f"{lt.text()} with downsampling: {down_factor*self.lcm/self.manager.lineagetrees[lt.text()]._time_resolution}"
                for lt in self.lineagetree_list.selectedItems()
            ]

            self.downsampling_widget.setToolTip(
                "\n".join(
                    ["Real downsampling rates:\n", *list_of_selected_emryos]
                )
            )
        else:
            self.downsampling_widget.setToolTip("")

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)
        self.viewer = napari_viewer
        self.tab_dictionary = {}
        self.norm_combo = widgets.ComboBox(
            value="max",
            choices=["max", "sum", "None"],
        )
        self.norm_dict = {"max": max, "sum": sum, "None": lambda x: 1}

        self.colormap = widgets.ComboBox(
            value="viridis",
            choices=[
                "viridis",
                "plasma",
                "inferno",
                "magma",
                "cividis",
                "Greys",
                "Purples",
                "Blues",
                "Greens",
                "Oranges",
                "Reds",
                "YlOrBr",
                "YlOrRd",
                "OrRd",
                "PuRd",
                "RdPu",
                "BuPu",
                "GnBu",
                "PuBu",
                "YlGnBu",
                "PuBuGn",
                "BuGn",
                "YlGn",
            ],
        )
        self.comp_style = "simple"
        self.possible_styles = tree_style.list_names()
        self.lineagetree_list = QListWidget()
        self.lineagetree_list.setSelectionMode(QListWidget.MultiSelection)
        self.lineagetree_list.itemSelectionChanged.connect(self.tab_maker)
        self.downsampling_widget = QComboBox()
        self.downsampling_widget.addItems(
            [
                f"{i} downsampling rate"
                for i in range(1, self.lcm * 30, self.lcm)
            ]
        )
        self.downsampling_widget.setVisible(False)
        self.downsampling_widget.currentIndexChanged.connect(
            self.change_tooltip_for_downsample
        )
        self.lineagetree_list.itemSelectionChanged.connect(
            self.change_downsampling_rates
        )
        self.tree_style_combobox = widgets.ComboBox(
            value="simple", choices=self.possible_styles
        )
        self.styl_combobox = Containerize(
            [self.tree_style_combobox.native, self.downsampling_widget]
        )
        self.tree_style_combobox.changed.connect(self.update_tree_style)
        self.downsampling_widget.visible = False
        label_for_style = widgets.Label(
            value="Select approximation for tree comparison.\n"
        )
        self.root_tabs = QTabWidget()

        layout = QVBoxLayout()
        self.setLayout(layout)
        self.layout().addWidget(label_for_style.native)
        self.layout().addWidget(self.styl_combobox)
        self.layout().addWidget(self.lineagetree_list)
        self.layout().addWidget(self.root_tabs)
        self.tab_maker()
        layout.addStretch(1)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(
            os.path.join(current_dir, "cross_config.html"),
            encoding="utf-8",
        ) as f:
            txt = f.read()
        self.node_tooltip = TooltipButton(txt)
        self.node_tooltip.setParent(self)
        self.node_tooltip.move(self.width() - self.node_tooltip.width(), 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.node_tooltip.move(self.width() - self.node_tooltip.width(), 0)
