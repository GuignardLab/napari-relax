import matplotlib.pyplot as plt
import numpy as np
from LineageTree import lineageTree
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from psygnal import Signal
from scipy.spatial import KDTree


class single_tree_progeny(FigureCanvas):
    node_signal = Signal(dict)
    color_of_nodes = "black"
    color_of_edges = "black"
    node_size = 10
    lw = 0.3
    fontsize = 6
    color_of_selection_nodes = "magenta"
    color_of_selection_edges = "magenta"
    all_selected = False

    def change_attributes(self, signal):
        """
        Receives a signal to change the attributes of the plot.
        """
        self.color_of_nodes = signal.get("color_of_nodes", self.color_of_nodes)
        self.color_of_edges = signal.get("color_of_edges", self.color_of_edges)
        self.node_size = signal.get("node_size", self.node_size)
        self.lw = signal.get("lw", self.lw)
        self.color_of_selection_nodes = signal.get(
            "color_of_selection", self.color_of_selection_nodes
        )
        self.color_of_selection_edges = signal.get(
            "color_of_selection", self.color_of_selection_edges
        )
        self.fontsize = signal.get("fontsize", self.fontsize)
        self.all_selected = signal.get("all_selected", False)
        if self.all_selected is True:
            self.selected_subtree = signal["selected_nodes"]
        else:
            self.selected_subtree.clear()
        self.draw_graph()

    def __init__(
        self,
        figure,
        ax,
        root=None,
        lT: lineageTree = None,
        lnks_tms=None,
        hier: dict | None = None,
        do_super=True,
        previous_state=False,
        old_nodes=None,
    ):
        if do_super:
            super().__init__(figure)
        if root is not None and (lT or lnks_tms, hier):
            self.ax = ax
            self.selected_node = []
            self.root = root
            self.lnks_tms = lnks_tms
            self.graph = lnks_tms
            self.lT = lT
            self.pos = hier
            self.lT.draw_tree_graph(
                self.pos,
                self.graph,
                ax=self.ax,
            )
            self.draw()
            self.xlim = self.ax.get_xlim()
            self.ylim = self.ax.get_ylim()
            self.xmax = self.xlim[1]
            self.xmin = self.xlim[0]
            self.ymax = self.ylim[1]
            self.ymin = self.ylim[0]
            self.lims_of_tree = np.array(list(self.pos.values()))[:, 1]
            self.xlim_min = (self.xlim[1] - self.xlim[0]) / 50
            self.xlim_max = self.xlim[1] - self.xlim[0]
            self.mpl_connect("button_press_event", self.click)
            self.mpl_connect("button_press_event", self.pan_start)
            self.mpl_connect("button_release_event", self.pan_stop)
            self.mpl_connect("motion_notify_event", self.panning)
            self.mpl_connect("scroll_event", self.scroll)
            self.mpl_connect("key_press_event", self.reset)
            self.pan = False
            self.labels = False
            if previous_state and old_nodes:
                self.all_selected = True
                self.selected_subtree = old_nodes
            else:
                self.selected_subtree = set()
            self.figure.subplots_adjust(
                wspace=0,
                hspace=0,
                top=1,
                bottom=0,
                right=1,
                left=0,
            )
            self.draw_graph()

    def time_line(self, time):
        if hasattr(self, "ax") and self.ax:
            time = time.value[0]
            zorder = max([_.zorder for _ in self.ax.get_children()]) + 1
            if not hasattr(self, "line"):
                (self.line,) = self.ax.plot(
                    [
                        self.xmin,
                        self.xmax,
                    ],
                    [
                        -time - self.lT.t_b,
                        -time - self.lT.t_b,
                    ],
                    color="grey",
                    linewidth=2,
                    alpha=0.3,
                    zorder=zorder,
                )
                self.line.set_visible(True)

            if hasattr(self, "line") and self.line in self.ax.lines:
                if (
                    min(self.lims_of_tree)
                    <= -time - self.lT.t_b
                    <= max(self.lims_of_tree)
                ):
                    self.line.set_ydata(
                        [
                            -time - self.lT.t_b,
                            -time - self.lT.t_b,
                        ]
                    )
                    self.line.set_xdata(
                        [
                            self.xmin,
                            self.xmax,
                        ]
                    )
                    self.line.set_visible(True)
                    self.line.set_zorder(zorder + 1)
                else:
                    self.line.set_visible(False)
            else:
                (self.line,) = self.ax.plot(
                    [
                        self.xmin,
                        self.xmax,
                    ],
                    [
                        -time - self.lT.t_b,
                        -time - self.lT.t_b,
                    ],
                    color="grey",
                    linewidth=2,
                    alpha=0.3,
                    zorder=zorder,
                )
                self.line.set_visible(True)
            self.draw_idle()
            self.flush_events()

    def change_lineage(
        self,
        figure,
        ax,
        root=None,
        lT: lineageTree = None,
        lnks_tms=None,
        hier=None,
        change=False,
    ):
        if (
            hasattr(self, "selected_subtree")
            and self.selected_subtree
            and self.all_selected
        ):
            old_nodes = self.selected_subtree
        else:
            old_nodes = set()
        self.__init__(
            figure,
            ax,
            root,
            lT,
            lnks_tms,
            hier,
            change,
            previous_state=self.all_selected,
            old_nodes=old_nodes,
        )

    def click(self, event):
        if event.button == 1 and event.inaxes and self.lT:
            plt.close("all")
            self.selected_node = []
            kdtree = KDTree(list(self.pos.values()))
            dist, ind = kdtree.query([event.xdata, event.ydata])
            max_x = self.xmin, self.xmax
            max_y = self.ymin, self.ymax
            max_dist = (
                np.sqrt(
                    (max_x[1] - max_x[0]) ** 2 + (max_y[1] - max_y[0]) ** 2
                )
                / 97
            )
            if dist > (max_dist):
                self.selected_subtree.clear()
                plt.close("all")
                self.draw_graph()
                self.node_signal.emit({})
                return
            cell = list(self.pos.keys())[ind]
            self.node_signal.emit({"value": cell, "dblclick": event.dblclick})
            if not self.all_selected:
                self.selected_subtree = set(self.lT.get_subtree_nodes(cell))
            self.draw_graph()

    def reset(self, event):
        if event.key == "z":
            self.draw_graph(reset=True)

    def pan_start(self, event):
        if event.button == 3 and event.inaxes:
            self.pan = True
            self.starting_pos = (event.xdata, event.ydata)
            self.xlims_on_click = self.ax.get_xlim()
            self.ylims_on_click = self.ax.get_ylim()

    def pan_stop(self, event):
        if event.button == 3 and self.pan:
            self.draw_graph()
            self.pan = False

    def panning(self, event):
        if self.pan and event.button == 3 and event.inaxes:
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
        if not event.inaxes:
            return
        scale = 1.2 if event.button == "down" else 1 / 1.2
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        x, y = event.xdata, event.ydata
        new_width = (xlim[1] - xlim[0]) * scale
        new_height = (ylim[1] - ylim[0]) * scale
        if new_width > (self.xlim[1] - self.xlim[0]):
            new_x_left, new_x_right = self.xlim
        else:
            new_x_left = x - new_width * (x - xlim[0]) / (xlim[1] - xlim[0])
            new_x_right = x + new_width * (xlim[1] - x) / (xlim[1] - xlim[0])
            new_x_left = max(new_x_left, self.xlim[0])
            new_x_right = min(new_x_right, self.xlim[1])
        if new_height > (self.ylim[1] - self.ylim[0]):
            new_y_bottom, new_y_top = self.ylim
        else:
            new_y_bottom = y - new_height * (y - ylim[0]) / (ylim[1] - ylim[0])
            new_y_top = y + new_height * (ylim[1] - y) / (ylim[1] - ylim[0])
            new_y_bottom = max(new_y_bottom, self.ylim[0])
            new_y_top = min(new_y_top, self.ylim[1])
        self.ax.set_xlim([new_x_left, new_x_right])
        self.ax.set_ylim([new_y_bottom, new_y_top])
        self.draw_idle()
        if new_width <= self.xlim_min + 70 and not self.labels:
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
        elif new_width > self.xlim_min + 70 and self.labels:
            for text in self.ax.texts:
                text.remove()
            self.labels = False
        self.draw()

    def draw_graph(self, reset=False):
        if not reset:
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
        else:
            xlim = self.xlim
            ylim = self.ylim
        with_labels = (xlim[1] - xlim[0]) <= self.xlim_min + 70
        self.labels = with_labels
        if self.all_selected:
            self.selected_subtree = set(self.lT.nodes)
        self.lT.draw_tree_graph(
            self.pos,
            self.lnks_tms,
            lw=float(self.lw),
            size=float(self.node_size),
            color_of_nodes=self.color_of_selection_nodes,
            color_of_edges=self.color_of_selection_edges,
            default_color=self.color_of_nodes,
            selected_nodes=self.selected_subtree,
            selected_edges=self.selected_subtree,
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
                        fontsize=self.fontsize,
                        rotation=34,
                    )
            self.labels = True
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        self.draw()
