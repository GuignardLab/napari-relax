import matplotlib.pyplot as plt
import numpy as np
from lineagetree import LineageTree
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from psygnal import Signal
from scipy.spatial import KDTree


class SingleTreeProgeny(FigureCanvas):
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
        lT: LineageTree = None,
        lnks_tms=None,
        hier: dict | None = None,
        do_super=True,
        previous_state=False,
        old_nodes=None,
        points_layer_metadata=None,
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
            self.points_layer_metadata = points_layer_metadata
            
            # Extract colors from the reader metadata if available
            reader_color = self._extract_node_colors_from_reader()
            
            # Use reader color as default color if available
            default_color = reader_color if reader_color is not None else self.color_of_nodes
            
            self.lT.draw_tree_graph(
                self.pos,
                self.graph,
                ax=self.ax,
                color_of_nodes=self.color_of_selection_nodes,
                color_of_edges=self.color_of_selection_edges,
                default_color=default_color,
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
            
            # Initialize marked cell for circle highlighting
            self.marked_cell_id = None
            self.figure.subplots_adjust(
                wspace=0,
                hspace=0,
                top=1,
                bottom=0,
                right=1,
                left=0,
            )
            self.draw_graph()

    def _extract_node_colors_from_reader(self):
        """Extract node colors from the Points layer metadata created by the reader.
        
        This method finds the root lineage color for the currently displayed lineage
        and applies it to all nodes and edges in the graph.
        
        Returns:
            color: Single color as tuple/list for the current lineage root,
                   or None if metadata is not available.
        """
        if not self.points_layer_metadata:
            return None
            
        # Get the color mapping from the reader metadata
        clone2 = self.points_layer_metadata.get("clone2")
        lT2napari = self.points_layer_metadata.get("lT2napari")
        
        if clone2 is None or lT2napari is None:
            return None
            
        # Get the actual root node ID from the graph structure
        # The root is stored in the lnks_tms structure
        actual_root = None
        if hasattr(self, 'lnks_tms') and self.lnks_tms and 'root' in self.lnks_tms:
            actual_root = self.lnks_tms['root']
        elif hasattr(self, 'root') and self.root is not None:
            actual_root = self.root
            
        if actual_root is None:
            return None
            
        # Get the color for this root from clone2
        if actual_root in lT2napari:
            napari_idx = lT2napari[actual_root]
            if napari_idx < len(clone2):
                # Convert numpy array to tuple to avoid LineageTree issues
                color = clone2[napari_idx]
                if hasattr(color, 'tolist'):
                    return color.tolist()
                else:
                    return list(color)
        
        return None

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
        lT: LineageTree = None,
        lnks_tms=None,
        hier=None,
        change=False,
        points_layer_metadata=None,
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
            points_layer_metadata=points_layer_metadata,
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
                # Background click - clear selections and marked cell
                self.selected_subtree.clear()
                if hasattr(self, 'marked_cell_id'):
                    self.marked_cell_id = None
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
                        fontsize=self.fontsize,
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
            
        # Extract colors from reader metadata
        reader_color = self._extract_node_colors_from_reader()
        
        # Use reader color as default color if available
        default_color = reader_color if reader_color is not None else self.color_of_nodes
        
        self.lT.draw_tree_graph(
            self.pos,
            self.lnks_tms,
            lw=float(self.lw),
            size=float(self.node_size),
            color_of_nodes=self.color_of_selection_nodes,
            color_of_edges=self.color_of_selection_edges,
            default_color=default_color,
            selected_nodes=self.selected_subtree,
            selected_edges=self.selected_subtree,
            ax=self.ax,
        )
        
        # Draw circle marker for marked cell if specified
        if hasattr(self, 'marked_cell_id') and self.marked_cell_id is not None:
            self._draw_cell_marker(self.marked_cell_id)
        
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

    def _draw_cell_marker(self, cell_id):
        """Draw a circle marker for the specified cell on the lineage graph.
        
        The cell can be positioned anywhere along an edge, not just at nodes.
        """
        if cell_id not in self.lT.nodes:
            return
            
        # Get the time of the cell
        cell_time = self.lT.time[cell_id]
        
        # Find the position for this cell
        if cell_id in self.pos:
            # Cell is at a node position (root, leaf, or division point)
            marker_pos = self.pos[cell_id]
        else:
            # Cell is along an edge - need to calculate its position
            marker_pos = self._calculate_cell_position_on_edge(cell_id, cell_time)
        
        if marker_pos is not None:
            # Use scatter plot to draw a circular marker that won't be distorted
            self.ax.scatter(
                marker_pos[0], 
                marker_pos[1],
                s=self.node_size * 15,  # Size in points^2, adjust as needed
                facecolors='none',  # No fill
                edgecolors=self.color_of_selection_nodes,  # Border color
                linewidths=2.0,
                marker='o',  # Circle marker
                zorder=10  # Draw on top
            )

    def _calculate_cell_position_on_edge(self, cell_id, cell_time):
        """Calculate the position of a cell along an edge based on its time.
        
        This method finds the lineage path the cell belongs to and interpolates
        its position based on time between the nearest positioned nodes.
        """
        # Try to find the nearest ancestor and descendant nodes that have positions
        ancestor_id = None
        ancestor_pos = None
        ancestor_time = None
        
        descendant_id = None
        descendant_pos = None
        descendant_time = None
        
        # Look for ancestor with position
        current = cell_id
        while current is not None:
            predecessors = self.lT.predecessor.get(current, [])
            if not predecessors:
                break
            current = predecessors[0]
            if current in self.pos:
                ancestor_id = current
                ancestor_pos = self.pos[current]
                ancestor_time = self.lT.time[current]
                break
        
        # Look for descendant with position
        current_nodes = [cell_id]
        max_depth = 20  # Prevent infinite loops
        depth = 0
        
        while current_nodes and descendant_pos is None and depth < max_depth:
            next_nodes = []
            for node in current_nodes:
                children = self.lT.successor.get(node, [])
                for child in children:
                    if child in self.pos:
                        descendant_id = child
                        descendant_pos = self.pos[child]
                        descendant_time = self.lT.time[child]
                        break
                    else:
                        next_nodes.append(child)
                if descendant_pos is not None:
                    break
            current_nodes = next_nodes
            depth += 1
        
        # If we found both ancestor and descendant, interpolate
        if (ancestor_pos is not None and descendant_pos is not None and 
            ancestor_time != descendant_time):
            
            # Calculate time ratio
            time_ratio = (cell_time - ancestor_time) / (descendant_time - ancestor_time)
            
            # Clamp ratio to [0, 1] range
            time_ratio = max(0, min(1, time_ratio))
            
            # Interpolate position
            marker_x = ancestor_pos[0] + time_ratio * (descendant_pos[0] - ancestor_pos[0])
            marker_y = ancestor_pos[1] + time_ratio * (descendant_pos[1] - ancestor_pos[1])
            
            return (marker_x, marker_y)
        
        # Fallback: if we only have ancestor, use its position
        elif ancestor_pos is not None:
            return ancestor_pos
            
        # Fallback: if we only have descendant, use its position
        elif descendant_pos is not None:
            return descendant_pos
        
        return None
