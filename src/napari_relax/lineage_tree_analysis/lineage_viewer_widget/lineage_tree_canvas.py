import matplotlib.pyplot as plt
import numpy as np
from lineagetree import LineageTree
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from psygnal import Signal
from scipy.spatial import KDTree

from ..._utils import _convert_color_to_hex, _convert_color_to_list


def _get_user_canvas_preferences():
    """Get user's preferred canvas settings."""
    # Import here to avoid circular imports
    from ..._util_classes.tree_graph_popup import _get_user_canvas_settings
    return _get_user_canvas_settings()


class LineageCanvas(FigureCanvas):
    node_signal = Signal(dict)
    colors_updated = Signal()

    def change_attributes(self, signal):
        """
        Receives a signal to change the attributes of the plot.
        """
        # CRITICAL: Edge color should ONLY be changed by LineageCanvasSetup dialog
        # Never update edge colors from other signals to prevent contamination
        # self.color_of_edges = signal.get("color_of_edges", self.color_of_edges)  # REMOVED!
        
        # Only update visual settings that don't interfere with user preferences
        self.node_size = signal.get("node_size", self.node_size)
        self.lw = signal.get("lw", self.lw)
        self.fontsize = signal.get("fontsize", self.fontsize)

        # Only update selection colors if it's a valid single color (not a dictionary)
        color_of_selection = signal.get("color_of_selection")
        if color_of_selection is not None and not isinstance(
            color_of_selection, dict
        ):
            self.color_of_selection_nodes = color_of_selection
            self.color_of_selection_edges = color_of_selection

        self.fontsize = signal.get("fontsize", self.fontsize)
        
        # Special handling for LineageCanvasSetup signals (identified by presence of color_of_edges)
        # These are the ONLY signals allowed to update edge colors
        if "color_of_edges" in signal:
            self.color_of_edges = signal["color_of_edges"]
            # This is a visual settings update from LineageCanvasSetup - update all visual properties
            self.node_size = signal.get("node_size", self.node_size)
            self.lw = signal.get("lw", self.lw)
            self.fontsize = signal.get("fontsize", self.fontsize)
        
        # CRITICAL: Only change quantitative state if signal explicitly addresses it
        # Don't reset quantitative mode for unrelated signals (visual settings, etc.)
        if "quantitative_coloring" in signal:
            # This signal is about quantitative coloring - process normally
            is_quantitative = signal.get("quantitative_coloring", False)
            
            # Store individual node colors if provided (for quantitative coloring)
            if "node_colors" in signal:
                self.node_colors = signal["node_colors"]

            # Update face colors metadata if provided (for quantitative coloring)
            if "face_colors" in signal:
                self.update_face_colors(signal["face_colors"])
            
            # Set quantitative mode and handle selection
            self.is_quantitative_mode = is_quantitative
            
            if is_quantitative:
                # Entering quantitative mode - preserve any existing selection
                if "selected_nodes" in signal:
                    self.selected_subtree = signal["selected_nodes"]
                # If no selection specified, keep existing selection if any
            else:
                # Exiting quantitative mode - clear selection and individual colors
                # if (
                #     hasattr(self, "selected_subtree")
                #     and self.selected_subtree is not None
                # ):
                #     self.selected_subtree.clear()
                # else:
                #     self.selected_subtree = set()

                # Clear individual node colors when exiting quantitative mode
                if hasattr(self, "node_colors"):
                    delattr(self, "node_colors")
        else:
            # This signal is NOT about quantitative coloring (e.g., visual settings)
            # Preserve current quantitative state
            is_quantitative = getattr(self, "is_quantitative_mode", False)

        # draw_graph now handles its own canvas initialization checks
        self.draw_graph()

        # Note: colors_updated signal is now emitted from draw_graph to cover all cases

    def __init__(
        self,
        figure,
        ax,
        root=None,
        lT: LineageTree = None,
        lnks_tms=None,
        hier: dict | None = None,
        previous_state=False,
        old_nodes=None,
        points_layer_metadata=None,
    ):
        # Initialize as a matplotlib FigureCanvas
        super().__init__(figure)
        
        # Load user preferences and apply them to this instance
        self._load_user_preferences()
        
        # Initialize the lineage data if provided
        if root is not None and (lT or lnks_tms, hier):
            self._initialize_lineage_data(
                ax=ax,
                root=root,
                lT=lT,
                lnks_tms=lnks_tms,
                hier=hier,
                previous_state=previous_state,
                old_nodes=old_nodes,
                points_layer_metadata=points_layer_metadata,
            )
            
    def _load_user_preferences(self):
        """Load and apply user canvas preferences."""
        user_prefs = _get_user_canvas_preferences()
        self.color_of_nodes = user_prefs.get("color_of_edges", "black")  # Use edge color for nodes too in normal mode
        self.color_of_edges = user_prefs["color_of_edges"]
        self.node_size = user_prefs["node_size"]
        self.lw = user_prefs["lw"]
        self.fontsize = user_prefs["fontsize"]
        self.color_of_selection_nodes = user_prefs["color_of_selection"]
        self.color_of_selection_edges = user_prefs["color_of_selection"]

    def _initialize_lineage_data(
        self,
        ax,
        root,
        lT: LineageTree,
        lnks_tms,
        hier,
        previous_state=False,
        old_nodes=None,
        points_layer_metadata=None,
    ):
        """Initialize the canvas with lineage data and setup the graph."""
        self.ax = ax
        self.selected_node = []
        self.root = root
        self.lnks_tms = lnks_tms
        self.graph = lnks_tms
        self.lT = lT
        self.pos = hier
        self.points_layer_metadata = points_layer_metadata

        # Set up initial selection state
        if previous_state and old_nodes:
            # Preserve the previous selection state
            self.selected_subtree = old_nodes
        else:
            self.selected_subtree = set()

        # Initialize marked cell for circle highlighting
        self.marked_cell_id = None
        
        # Set up matplotlib event connections
        self.mpl_connect("button_press_event", self.click)
        self.mpl_connect("button_press_event", self.pan_start)
        self.mpl_connect("button_release_event", self.pan_stop)
        self.mpl_connect("motion_notify_event", self.panning)
        self.mpl_connect("scroll_event", self.scroll)
        self.mpl_connect("key_press_event", self.reset)
        self.pan = False
        self.labels = False

        # Configure figure layout
        self.figure.subplots_adjust(
            wspace=0,
            hspace=0,
            top=1,
            bottom=0,
            right=1,
            left=0,
        )
        
        # Perform initial drawing with basic parameters to establish bounds
        self._draw_initial_graph()
        
        # After initial drawing, store the bounds for pan/zoom constraints and reset
        self._store_initial_bounds()

    def _draw_initial_graph(self):
        """Draw the initial graph with basic parameters to establish axis bounds."""
        if not hasattr(self, "ax") or self.ax is None or not hasattr(self, "lT"):
            return
            
        # Extract colors for the initial drawing
        color_info = self._extract_current_lineage_color()
        reader_color = self._extract_node_colors_from_reader()
        
        if color_info and color_info.get("color"):
            default_color = color_info["color"]
        elif reader_color is not None:
            default_color = reader_color
        else:
            default_color = self.color_of_nodes

        # Draw the graph with basic parameters
        self.lT.draw_tree_graph_relax(
            hier=self.pos,
            lnks_tms=self.lnks_tms,
            color_of_nodes=default_color,
            color_of_edges=self.color_of_edges,
            selected_nodes=self.selected_subtree,
            color_of_selection=self.color_of_selection_nodes,
            size=float(self.node_size),
            lw=float(self.lw),
            ax=self.ax,
        )
        
        # Draw the canvas to establish proper bounds
        self.draw()

    def _store_initial_bounds(self):
        """Store the initial graph bounds for pan/zoom constraints and reset functionality."""
        if hasattr(self, "ax") and self.ax is not None:
            self.initial_xlim = self.ax.get_xlim()
            self.initial_ylim = self.ax.get_ylim()
            # Store tree Y limits for timeline functionality
            if hasattr(self, "pos") and self.pos:
                self.lims_of_tree = np.array(list(self.pos.values()))[:, 1]

    def _get_bounds_info(self):
        """Get current and initial bounds information for interactions.
        
        Returns:
            dict: Contains current and initial xlim/ylim, and computed boundaries
        """
        if not hasattr(self, "ax") or self.ax is None:
            return None
            
        current_xlim = self.ax.get_xlim()
        current_ylim = self.ax.get_ylim()
        
        # Use initial bounds if available, otherwise current bounds
        initial_xlim = getattr(self, "initial_xlim", current_xlim)
        initial_ylim = getattr(self, "initial_ylim", current_ylim)
        
        return {
            "current_xlim": current_xlim,
            "current_ylim": current_ylim,
            "initial_xlim": initial_xlim,
            "initial_ylim": initial_ylim,
            "xmin": initial_xlim[0],
            "xmax": initial_xlim[1],
            "ymin": initial_ylim[0],
            "ymax": initial_ylim[1],
            "full_width": initial_xlim[1] - initial_xlim[0],
            "full_height": initial_ylim[1] - initial_ylim[0],
            "label_threshold": (initial_xlim[1] - initial_xlim[0]) / 50 + 70,
        }

    def _get_actual_root(self):
        """Get the actual root node ID from the graph structure.

        Returns:
            The root node ID, or None if not available.
        """
        if (
            hasattr(self, "lnks_tms")
            and self.lnks_tms
            and "root" in self.lnks_tms
        ):
            return self.lnks_tms["root"]
        elif hasattr(self, "root") and self.root is not None:
            return self.root
        return None

    def _get_metadata_mappings(self):
        """Get the color and node mappings from metadata.

        Returns:
            tuple: (clone2, lT2napari) or (None, None) if not available.
        """
        if not self.points_layer_metadata:
            return None, None

        clone2 = self.points_layer_metadata.get("clone2")
        lT2napari = self.points_layer_metadata.get("lT2napari")

        if clone2 is None or lT2napari is None:
            return None, None

        return clone2, lT2napari

    def _extract_node_colors_from_reader(self):
        """Extract node colors from the Points layer metadata created by the reader.

        This method finds the root lineage color for the currently displayed lineage
        and applies it to all nodes and edges in the graph.

        Returns:
            color: Single color as tuple/list for the current lineage root,
                   or None if metadata is not available.
        """
        clone2, lT2napari = self._get_metadata_mappings()
        if clone2 is None or lT2napari is None:
            return None

        actual_root = self._get_actual_root()
        if actual_root is None:
            return None

        # Get the color for this root from clone2
        if actual_root in lT2napari:
            napari_idx = lT2napari[actual_root]
            if napari_idx < len(clone2):
                # Convert to hex string for the new function
                return _convert_color_to_hex(clone2[napari_idx])

        return None

    def _extract_current_lineage_color(self):
        """Extract the current color for this lineage from the active Points layer.

        This method checks the actual face_color of points in the current lineage,
        which may be different from the original clone2 colors if quantitative
        recoloring has been applied.

        Returns:
            dict: dictionary with 'color' (single color if uniform) and 'is_uniform' (bool)
                  indicating whether all nodes in the lineage have the same color.
                  Returns None if no data is available.
        """
        clone2, lT2napari = self._get_metadata_mappings()
        if clone2 is None or lT2napari is None:
            return None

        actual_root = self._get_actual_root()
        if actual_root is None:
            return None

        # Get all nodes in the current lineage
        if hasattr(self, "lT") and self.lT:
            lineage_nodes = list(self.lT.get_subtree_nodes(actual_root))
        else:
            lineage_nodes = [actual_root]

        # Try to get the active Points layer to access current face colors
        # try:
        # This requires access to the viewer, which we don't have directly in the canvas
        # We'll need to get the face colors from the points layer metadata
        # Let's check if face colors are passed in the metadata
        current_face_colors = self.points_layer_metadata.get(
            "current_face_colors"
        )
        if current_face_colors is None:
            # Fallback to original clone2 colors
            return self._get_original_color_info(actual_root)

        # Collect colors for all nodes in this lineage
        lineage_colors = []
        for node in lineage_nodes:
            if node in lT2napari:
                napari_idx = lT2napari[node]
                if napari_idx < len(current_face_colors):
                    color = current_face_colors[napari_idx]
                    lineage_colors.append(_convert_color_to_list(color))

        if not lineage_colors:
            return None

        # Check if all colors are the same (uniform lineage color)
        first_color = lineage_colors[0][:3]  # Compare only RGB, ignore alpha
        # is_uniform = all(color[:3] == first_color for color in lineage_colors)
        is_uniform = len(set(tuple(color[:3]) for color in lineage_colors)) == 1

        return {
            "color": _convert_color_to_hex(first_color),
            "is_uniform": is_uniform,
        }

    def update_face_colors(self, face_colors):
        """Update the metadata with provided face colors."""
        if self.points_layer_metadata is not None:
            self.points_layer_metadata["current_face_colors"] = face_colors

    def _get_original_color_info(self, actual_root):
        """Get the original color info from clone2 for fallback."""
        clone2, lT2napari = self._get_metadata_mappings()

        if clone2 is None or lT2napari is None or actual_root not in lT2napari:
            return None

        napari_idx = lT2napari[actual_root]
        if napari_idx < len(clone2):
            color = _convert_color_to_list(clone2[napari_idx])

            return {
                "color": _convert_color_to_hex(color[:3]),
                "is_uniform": True,  # Original colors are always uniform per lineage
            }

    def time_line(self, time):
        if hasattr(self, "ax") and self.ax:
            bounds = self._get_bounds_info()
            if bounds is None:
                return
                
            time = time.value[0]
            zorder = max([_.zorder for _ in self.ax.get_children()]) + 1
            
            if not hasattr(self, "line"):
                (self.line,) = self.ax.plot(
                    [
                        bounds["xmin"],
                        bounds["xmax"],
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
                # Check if time is within tree limits
                tree_limits = getattr(self, "lims_of_tree", None)
                if tree_limits is not None and (
                    min(tree_limits)
                    <= -time - self.lT.t_b
                    <= max(tree_limits)
                ):
                    self.line.set_ydata(
                        [
                            -time - self.lT.t_b,
                            -time - self.lT.t_b,
                        ]
                    )
                    self.line.set_xdata(
                        [
                            bounds["xmin"],
                            bounds["xmax"],
                        ]
                    )
                    self.line.set_visible(True)
                    self.line.set_zorder(zorder + 1)
                else:
                    self.line.set_visible(False)
            else:
                (self.line,) = self.ax.plot(
                    [
                        bounds["xmin"],
                        bounds["xmax"],
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
        """Change the lineage displayed in the canvas.
        
        This method updates the canvas to display a new lineage while preserving
        the current selection state if applicable.
        """
        # Preserve selected nodes if they exist
        if (
            hasattr(self, "selected_subtree")
            and self.selected_subtree
        ):
            old_nodes = self.selected_subtree
            preserve_state = True
        else:
            old_nodes = set()
            preserve_state = False
            
        # Re-initialize with new lineage data
        self._initialize_lineage_data(
            ax=ax,
            root=root,
            lT=lT,
            lnks_tms=lnks_tms,
            hier=hier,
            previous_state=preserve_state,
            old_nodes=old_nodes,
            points_layer_metadata=points_layer_metadata,
        )

    def click(self, event):
        if event.button == 1 and event.inaxes and self.lT:
            bounds = self._get_bounds_info()
            if bounds is None:
                return
                
            plt.close("all")
            self.selected_node = []
            kdtree = KDTree(list(self.pos.values()))
            dist, ind = kdtree.query([event.xdata, event.ydata])
            
            # Calculate click tolerance based on current view
            max_x = bounds["xmin"], bounds["xmax"]
            max_y = bounds["ymin"], bounds["ymax"]
            max_dist = (
                np.sqrt(
                    (max_x[1] - max_x[0]) ** 2 + (max_y[1] - max_y[0]) ** 2
                )
                / 97
            )
            if dist > (max_dist):
                # Background click - clear selections and marked cell
                self.selected_subtree.clear()
                self.marked_cell_id = None

                plt.close("all")
                self.draw_graph()
                self.node_signal.emit({})
                return
            cell = list(self.pos.keys())[ind]
            self.node_signal.emit({"value": cell, "dblclick": event.dblclick})
            # Always select the subtree when clicking on a node
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
            bounds = self._get_bounds_info()
            if bounds is None:
                return
                
            dx = event.xdata - self.starting_pos[0]
            dy = event.ydata - self.starting_pos[1]
            self.xlims_on_click -= dx
            self.ylims_on_click -= dy
            
            # Constrain panning to initial bounds
            if (
                bounds["xmin"] <= self.xlims_on_click[0]
                and self.xlims_on_click[1] <= bounds["xmax"]
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
            
        bounds = self._get_bounds_info()
        if bounds is None:
            return
            
        scale = 1.2 if event.button == "down" else 1 / 1.2
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        x, y = event.xdata, event.ydata
        new_width = (xlim[1] - xlim[0]) * scale
        new_height = (ylim[1] - ylim[0]) * scale
        
        # Constrain to initial bounds
        if new_width > bounds["full_width"]:
            new_x_left, new_x_right = bounds["initial_xlim"]
        else:
            new_x_left = x - new_width * (x - xlim[0]) / (xlim[1] - xlim[0])
            new_x_right = x + new_width * (xlim[1] - x) / (xlim[1] - xlim[0])
            new_x_left = max(new_x_left, bounds["xmin"])
            new_x_right = min(new_x_right, bounds["xmax"])
            
        if new_height > bounds["full_height"]:
            new_y_bottom, new_y_top = bounds["initial_ylim"]
        else:
            new_y_bottom = y - new_height * (y - ylim[0]) / (ylim[1] - ylim[0])
            new_y_top = y + new_height * (ylim[1] - y) / (ylim[1] - ylim[0])
            new_y_bottom = max(new_y_bottom, bounds["ymin"])
            new_y_top = min(new_y_top, bounds["ymax"])
            
        self.ax.set_xlim([new_x_left, new_x_right])
        self.ax.set_ylim([new_y_bottom, new_y_top])
        self.draw_idle()
        
        # Handle label display based on zoom level
        if new_width <= bounds["label_threshold"] and not self.labels:
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
        elif new_width > bounds["label_threshold"] and self.labels:
            for text in self.ax.texts:
                text.remove()
            self.labels = False
        self.draw()

    def draw_graph(self, reset=False):
        # Safety check: Don't draw if canvas is not properly initialized
        if not hasattr(self, "ax") or self.ax is None:
            return
            
        # Don't draw if we don't have lineage data
        if not hasattr(self, "lT") or self.lT is None:
            return
            
        # Don't draw if we don't have position data
        if not hasattr(self, "pos") or not self.pos:
            return

        bounds = self._get_bounds_info()
        if bounds is None:
            # Fallback: use current axis limits if bounds not yet established
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            # Use a simple threshold for labels when bounds are not available
            current_width = xlim[1] - xlim[0]
            with_labels = current_width <= 70  # Simple fallback threshold
        else:
            if not reset:
                xlim = bounds["current_xlim"]
                ylim = bounds["current_ylim"]
            else:
                xlim = bounds["initial_xlim"]
                ylim = bounds["initial_ylim"]
                
            # Determine if labels should be shown based on zoom level
            current_width = xlim[1] - xlim[0]
            with_labels = current_width <= bounds["label_threshold"]
            
        self.labels = with_labels

        # Handle selection highlighting for quantitative mode
        if getattr(self, "is_quantitative_mode", False):
            # Quantitative mode - preserve existing selection highlighting
            # Only clear selection if there isn't already a valid selection
            if not hasattr(self, 'selected_subtree') or self.selected_subtree is None:
                self.selected_subtree = set()
            # Otherwise, keep the existing selection for highlighting in quantitative mode

        # Extract current colors from the active layer (handles quantitative coloring)
        color_info = self._extract_current_lineage_color()

        # Use current color as default if available, otherwise fallback to original reader color
        # This allows nodes to get proper colors from points layer in default mode
        default_color = None
        if color_info and color_info.get("color"):
            default_color = color_info["color"]
        else:
            # Fallback to original reader color
            reader_color = self._extract_node_colors_from_reader()
            default_color = (
                reader_color
                if reader_color is not None
                else self.color_of_nodes
            )

        # Determine node colors based on mode
        if getattr(self, "is_quantitative_mode", False) and hasattr(self, "node_colors"):
            # Quantitative mode - use individual node colors from dictionary
            node_colors = self.node_colors
        else:
            # Default mode - use uniform color from points layer or fallback
            color_info = self._extract_current_lineage_color()
            if color_info and color_info.get("color"):
                node_colors = color_info["color"]  # String color from points layer
            else:
                reader_color = self._extract_node_colors_from_reader()
                node_colors = reader_color if reader_color is not None else self.color_of_nodes

        # Call the new function
        self.lT.draw_tree_graph_relax(
            hier=self.pos,
            lnks_tms=self.lnks_tms,
            color_of_nodes=node_colors,  # Dict for quantitative, string for default
            color_of_edges=self.color_of_edges,  # Always user preference
            selected_nodes=self.selected_subtree,  # Highlighted nodes
            color_of_selection=self.color_of_selection_nodes,  # Selection color
            size=float(self.node_size),
            lw=float(self.lw),
            ax=self.ax,
        )

        # Draw circle marker for marked cell if specified
        if self.marked_cell_id is not None:
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
        
        # Always emit signal after drawing to update color box
        # This covers both quantitative and default coloring cases
        self.colors_updated.emit()

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
            marker_pos = self._calculate_cell_position_on_edge(
                cell_id, cell_time
            )

        if marker_pos is not None:
            # Use scatter plot to draw a circular marker
            self.ax.scatter(
                marker_pos[0],
                marker_pos[1],
                s=float(self.node_size)
                * 15,  # Size in points^2, adjust as needed
                facecolors="none",  # No fill
                edgecolors=self.color_of_selection_nodes,  # Border color
                linewidths=2.0,
                marker="o",  # Circle marker
                zorder=10,  # Draw on top
            )

    def _calculate_cell_position_on_edge(self, cell_id, cell_time):
        """Simplified version using direct lineage traversal"""

        chain_of_node = self.lT.get_chain_of_node(cell_id)

        # chain_of_node has at least 3 elements, otherwise the node
        # would be in self.pos
        ancestor_id, descendant_id = chain_of_node[0], chain_of_node[-1]
        ancestor_pos, descendant_pos = (
            self.pos[ancestor_id],
            self.pos[descendant_id],
        )
        ancestor_time, descendant_time = (
            self.lT.time[ancestor_id],
            self.lT.time[descendant_id],
        )

        # Interpolate if we have both endpoints
        if (
            ancestor_pos
            and descendant_pos
            and ancestor_time != descendant_time
        ):
            time_ratio = (cell_time - ancestor_time) / (
                descendant_time - ancestor_time
            )
            time_ratio = np.clip(time_ratio, 0, 1)

            return (
                ancestor_pos[0]
                + time_ratio * (descendant_pos[0] - ancestor_pos[0]),
                ancestor_pos[1]
                + time_ratio * (descendant_pos[1] - ancestor_pos[1]),
            )

        # Fallback to nearest positioned node
        return ancestor_pos or descendant_pos
