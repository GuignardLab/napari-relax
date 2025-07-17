import matplotlib.pyplot as plt
import numpy as np
from LineageTree import lineageTree
from LineageTree.utils import hierarchical_pos
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from qtpy.QtCore import Signal
from scipy.spatial import KDTree


class single_tree(FigureCanvas):
    dict_signal = Signal(dict)

    def __init__(self, figure, ax, root, lT: lineageTree, lnks_tms):
        super().__init__(figure)
        self.ax = ax
        self.selected_node = []
        self.root = root
        self.lnks_tms = lnks_tms
        self.graph = self.lnks_tms
        self.lT = lT
        self.pos = hierarchical_pos(self.graph, self.root)
        self.lT.draw_tree_graph(self.pos, self.graph, ax=self.ax)
        self.draw()
        self.xlim = self.ax.get_xlim()
        self.ylim = self.ax.get_ylim()
        self.xlim_min = (self.xlim[1] - self.xlim[0]) / 50
        self.xlim_max = self.xlim[1] - self.xlim[0]
        self.mpl_connect("button_press_event", self.pan_start)
        self.mpl_connect("button_release_event", self.pan_stop)
        self.mpl_connect("motion_notify_event", self.panning)
        self.mpl_connect("scroll_event", self.scroll)
        self.mpl_connect("key_press_event", self.reset)
        self.pan = False
        self.labels = False
        self.selected_subtree = set()
        self.figure.subplots_adjust(
            wspace=0,
            hspace=0,
            top=1,
            bottom=0,
            right=1,
            left=0,
        )

    def default_values(self):
        leaves = self.lT.find_leaves(self.root)
        self.dict_signal.emit(
            {
                "Number of leaves": len(leaves),
                "Number of nodes": sum(
                    self.lnks_tms[self.root]["times"].values()
                ),
                "Number of divisions": len(leaves) - 1,
                "Depth of tree": max(self.lT.time[t] for t in leaves)
                - self.lT.time[self.root],
                "Average life-cycle": round(
                    np.mean(list(self.lnks_tms[self.root]["times"].values()))
                ),
            }
        )

    def get_new_lT(self, new_lT):
        self.lT = new_lT
        self.graph = self.lT._create_dict_of_plots(self.root)[0]
        self.pos = hierarchical_pos(self.graph, self.lT, self.root)

    def get_new_ax(self):
        self.xlim = self.ax.get_xlim()
        self.ylim = self.ax.get_ylim()
        self.xlim_min = (self.xlim[1] - self.xlim[0]) / 13
        self.xlim_max = self.xlim[1] - self.xlim[0]

    def reset(self, event):
        if event.key == "z":
            self.draw_graph(reset=True)

    def _alt_click(self, event):
        if "alt" in str(event.key) and event.button == 3 and event.inaxes:
            self.selected_subtree = set()
            kdtree = KDTree(list(self.pos.values()))
            dist, ind = kdtree.query([event.xdata, event.ydata])
            if dist > 25:
                self.selected_node.clear()
                plt.close("all")
                self.default_values()
                self.draw_graph()
                return
            cell = list(self.pos.keys())[ind]
            if "shift" in event.key:
                self.selected_node.append(cell)
            else:
                self.selected_node = [cell]
            self.dict_signal.emit(
                {
                    "Start Time": min(
                        self.lT.time[n] for n in self.selected_node
                    ),
                    "Stop Time": max(
                        self.lT.time[self.lT.get_node_chain(n)[-1]]
                        for n in self.selected_node
                    ),
                    "Average Length": np.mean(
                        [
                            len(self.lT.get_node_chain(n))
                            for n in self.selected_node
                        ]
                    ),
                    "-": "-",
                    "~": "-",
                }
            )
            plt.close("all")
            self.draw_graph()

    def click(self, event):
        if event.button == 3 and event.inaxes and "alt" not in str(event.key):
            plt.close("all")
            self.selected_node = []
            kdtree = KDTree(list(self.pos.values()))
            dist, ind = kdtree.query([event.xdata, event.ydata])
            if dist > 25:
                self.selected_subtree.clear()
                plt.close("all")
                self.draw_graph()
                self.default_values()
                return
            cell = list(self.pos.keys())[ind]
            if event.key == "shift":
                cell_sub = set(self.lT.get_subtree_nodes(cell))
                common_cells = self.selected_subtree.intersection(cell_sub)
                if common_cells:
                    if len(common_cells) < len(cell_sub):
                        self.selected_subtree.update(cell_sub)
                    else:
                        self.selected_subtree.difference_update(common_cells)
                else:
                    self.selected_subtree.update(cell_sub)
            else:
                self.selected_subtree = set(self.lT.get_subtree_nodes(cell))
            self.draw_graph()
            leaves = self.lT.leaves.intersection(self.selected_subtree)
            dividing_nodes = {
                node
                for node, succs in self.lT.successor.items()
                if len(succs) == 2
            }
            selected_nodes = self.selected_subtree.intersection(
                self.lnks_tms[self.root]["links"].keys()
            )
            self.dict_signal.emit(
                {
                    "Number of leaves": len(leaves),
                    "Number of nodes": len(self.selected_subtree),
                    "Number of divisions": len(
                        dividing_nodes.intersection(self.selected_subtree)
                    ),
                    "Depth of tree": max(self.lT.time[t] for t in leaves)
                    - min(self.lT.time[t] for t in self.selected_subtree),
                    "Average life-cycle": round(
                        np.mean(
                            [
                                self.lnks_tms[self.root]["times"][node]
                                for node in selected_nodes
                                if node in self.lnks_tms[self.root]["times"]
                            ]
                        ),
                        2,
                    ),
                }
            )

    def pan_start(self, event):
        if event.button == 1 and event.inaxes:
            self.pan = True
            self.starting_pos = (event.xdata, event.ydata)
            self.xlims_on_click = self.ax.get_xlim()
            self.ylims_on_click = self.ax.get_ylim()

    def pan_stop(self, event):
        if event.button == 1 and self.pan:
            self.draw_graph()
            self.pan = False

    def panning(self, event):
        if self.pan and event.button == 1 and event.inaxes:
            dx = event.xdata - self.starting_pos[0]
            dy = event.ydata - self.starting_pos[1]
            self.xlims_on_click -= dx
            self.ylims_on_click -= dy
            if (
                self.xlim[0] <= self.xlims_on_click[0]
                and self.xlims_on_click[1] <= self.xlim[1]
            ):
                self.ax.set_xlim(self.xlims_on_click)
                self.ax.set_ylim(self.ylims_on_click)
                self.draw_idle()
                self.flush_events()
                self.starting_pos = (event.xdata, event.ydata)
            else:
                self.xlims_on_click += dx
                self.ylims_on_click += dy

    def scroll(self, event):
        scale = 1.2
        scale = scale if event.button == "down" else 1 / scale
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        x, y = event.xdata, event.ydata
        new_width = (xlim[1] - xlim[0]) * scale
        new_height = (ylim[1] - ylim[0]) * scale
        if self.xlim_min <= new_width <= self.xlim_max:
            new_x = (xlim[1] - x) / (xlim[1] - xlim[0])
            new_y = (ylim[1] - y) / (ylim[1] - ylim[0])
            self.ax.set_xlim(
                [x - new_width * (1 - new_x), x + new_width * new_x]
            )
            self.ax.set_ylim(
                [y - new_height * (1 - new_y), y + new_height * new_y]
            )
            self.draw_idle()
            if new_width <= self.xlim_min + 70 and not self.labels:
                for node, pos in self.pos.items():
                    if (
                        xlim[0] < pos[0] < xlim[1]
                        and ylim[0] < pos[1] < ylim[1]
                    ):
                        self.ax.text(
                            *pos,
                            "Label: "
                            + str(self.lT.labels.get(node, node))
                            + "\n"
                            + "ID: "
                            + str(node),
                            fontsize=6,
                            rotation=34,
                        )
                self.labels = True
            elif new_width > self.xlim_min + 70 and self.labels:
                for text in self.ax.texts:
                    text.remove()
                self.labels = False
            self.draw()

    def draw_graph(self, reset=False):
        plt.close("all")
        if not reset:
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
        else:
            xlim = self.xlim
            ylim = self.ylim
        with_labels = (xlim[1] - xlim[0]) <= self.xlim_min + 70
        self.labels = with_labels
        self.ax.clear()
        self.lT.draw_tree_graph(
            self.pos,
            self.lnks_tms,
            ax=self.ax,
        )
        if with_labels:
            for node, pos in self.pos.items():
                if xlim[0] < pos[0] < xlim[1] and ylim[0] < pos[1] < ylim[1]:
                    self.ax.text(
                        *pos,
                        "Label: "
                        + str(self.lT.labels.get(node, node))
                        + "\n"
                        + "ID: "
                        + str(node),
                        fontsize=6,
                        rotation=34,
                    )
            self.labels = True
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        self.draw()
