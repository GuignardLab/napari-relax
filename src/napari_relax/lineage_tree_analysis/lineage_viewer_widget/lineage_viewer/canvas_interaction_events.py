import numpy as np


class CanvasUtils:

    def reset(self, event):
        if event.key == "z":
            self.draw_graph(reset=True)

    def pan_start(self, event):
        if event.button == 3 and event.inaxes:
            self.pan = True
            # Store in pixel coords — unaffected by axes limit changes
            self.starting_pos = (event.x, event.y)
            self.xlims_on_click = np.array(self.ax.get_xlim())
            self.ylims_on_click = np.array(self.ax.get_ylim())
            self._plot_labels()

    def pan_stop(self, event):
        if event.button == 3 and self.pan:
            self.pan = False
            self._plot_labels()

    def panning(self, event):
        if not (self.pan and event.button == 3 and event.inaxes):
            return

        # Work in pixels, convert delta to data coords
        dx_px = event.x - self.starting_pos[0]
        dy_px = event.y - self.starting_pos[1]

        # Convert pixel delta to data delta
        ax = self.ax
        x0, x1 = self.xlims_on_click
        y0, y1 = self.ylims_on_click
        bbox = ax.get_window_extent()
        dx_data = dx_px * (x1 - x0) / bbox.width
        dy_data = dy_px * (y1 - y0) / bbox.height

        ax.set_xlim(x0 - dx_data, x1 - dx_data)
        ax.set_ylim(y0 - dy_data, y1 - dy_data)
        self._plot_labels()
        self.draw_idle()

    def on_scroll(self, event):
        if not event.inaxes:
            return
        scale = 1.4 if event.button == "down" else 1 / 1.4
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
            for node, pos in self.hier.items():
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

    def time_line(self, time):
        if hasattr(self, "ax") and self.ax and self.lT:
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

    def connect_signals(self):
        """Connects the mpl signals to the canvas"""
        self.mpl_connect("button_press_event", self.click)
        self.mpl_connect("button_press_event", self.pan_start)
        self.mpl_connect("button_release_event", self.pan_stop)
        self.mpl_connect("motion_notify_event", self.panning)
        self.mpl_connect("scroll_event", self.on_scroll)
        self.mpl_connect("key_press_event", self.reset)

    def _draw_cell_marker(self, cell_id):
        """Draw a circle marker for the specified cell on the lineage graph.

        The cell can be positioned anywhere along an edge, not just at nodes.
        """
        if cell_id not in self.lT.nodes:
            return

        # Get the time of the cell
        cell_time = self.lT.time[cell_id]

        # Find the position for this cell
        if cell_id in self.hier:
            # Cell is at a node position (root, leaf, or division point)
            marker_pos = self.hier[cell_id]
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
                edgecolors="magenta",  # self.color_of_selection_nodes,  # Border color
                linewidths=2.0,
                marker="o",  # Circle marker
                zorder=10,  # Draw on top
            )

    def _calculate_cell_position_on_edge(self, cell_id, cell_time):
        """Simplified version using direct lineage traversal"""

        chain_of_node = self.lT.get_chain_of_node(cell_id)

        # chain_of_node has at least 3 elements, otherwise the node
        # would be in self.hier
        ancestor_id, descendant_id = chain_of_node[0], chain_of_node[-1]
        ancestor_pos, descendant_pos = (
            self.hier[ancestor_id],
            self.hier[descendant_id],
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
