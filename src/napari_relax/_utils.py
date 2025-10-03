from collections.abc import Iterable

import matplotlib.pyplot as plt
import numpy as np
from lineagetree import LineageTree
from napari.layers import Points
from napari.qt import get_current_stylesheet
from qtpy.QtWidgets import (
    QMessageBox,
)


def _convert_color_to_list(color):
    """Normalize color to a list format.

    Args:
        color: Color in various formats (numpy array, list, tuple)

    Returns:
        list: Normalized color as list
    """
    if hasattr(color, "tolist"):
        return color.tolist()
    else:
        return list(color)

def _convert_color_to_hex(color):
    """Convert RGB color values to hex string format.

    Args:
        color: Color in various formats (numpy array, list, tuple)
                Values should be in 0-1 range (matplotlib format)

    Returns:
        str: Hex color string (e.g., "#ff0000")
    """
    color = _convert_color_to_list(color)

    # Ensure we have at least 3 values
    if len(color) < 3:
        return "#000000"  # Default to black

    # Convert to 0-255 range and then to hex
    r = int(min(255, max(0, color[0] * 255)))
    g = int(min(255, max(0, color[1] * 255)))
    b = int(min(255, max(0, color[2] * 255)))
    
    return f"#{r:02x}{g:02x}{b:02x}"

def _convert_hex_color_to_rgba(color, alpha=1.0):
    """Convert hex color string to RGBA list format.

    Args:
        color: Hex color string (e.g., "#ff0000")
        alpha: Alpha value (0-1 range)
    Returns:
        list: RGBA color as list (e.g., [255, 0,
                0, 255] for red with full opacity)
    """
    if isinstance(color, str) and color.startswith("#") and len(color) == 7:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        a = int(min(255, max(0, alpha * 255)))
        return [r, g, b, a]
    else:
        raise ValueError("Invalid hex color format. Expected format: #RRGGBB")


def _infer_point_size(lT: "LineageTree"):
    """
    Infer a point size based on nearest neighbor distances.

    Heuristics:
    - minimal size: 0.01 * optimal size
    - optimal size: half of minimum median nearest neighbor distance
                    across all time points
    - maximal size: half of maximum nearest neighbor distance across
                    all time points
    """

    optimal_dist = float("inf")
    maximal_dist = 0

    timepoints = list(lT.time_nodes.keys())
    if len(timepoints) > 100:
        # Sample evenly across the timeline
        step = len(timepoints) // 10
        sampled_timepoints = timepoints[::step]
    else:
        sampled_timepoints = timepoints

    for t in sampled_timepoints:
        nodes = lT.time_nodes[t]
        if len(nodes) > 1:
            idx3d, nodes = lT.get_idx3d(t)

            nn_dists = idx3d.query(idx3d.data, k=2)[0][:, 1]

            optimal_dist = np.nanmin(
                [optimal_dist, np.nanmedian(nn_dists) / 2]
            )

            maximal_dist = np.nanmax([maximal_dist, np.nanmax(nn_dists) / 2])

    if optimal_dist == float("inf"):
        optimal_dist = 100
    if maximal_dist <= optimal_dist:
        maximal_dist = 10 * optimal_dist

    minimal_dist = 0.01 * optimal_dist

    return minimal_dist, optimal_dist, maximal_dist


def _transform_slider_int_value_to_float(
    int_value, min_float_value, max_float_value
):
    if min_float_value and max_float_value:
        return min_float_value + (max_float_value - min_float_value) * (
            int_value / 100
        )
    else:
        return float(int_value)


def _transform_float_value_to_slider_int(
    float_value, min_float_value, max_float_value
):
    if min_float_value and max_float_value:
        return int(
            100
            * (float_value - min_float_value)
            / (max_float_value - min_float_value)
        )
    else:
        return int(float_value)


def _select_active_lt_layer(viewer):
    """
    Finds the correct layer of the specified type that corresponds to the currently active layer.
    If the active layer is already of the correct type, returns it.
    Otherwise, looks for a 'link' metadata in the active layer pointing to the correct layer.
    """
    if len(viewer.layers.selection) == 1:
        active_layer = viewer.layers.selection.active
        if (
            isinstance(active_layer, Points)
            and hasattr(active_layer, "metadata")
            and "LineageTree" in active_layer.metadata
        ):
            return active_layer
        else:
            # Look for a 'link' metadata in the active layer
            if (
                hasattr(active_layer, "metadata")
                and "link" in active_layer.metadata
                and isinstance(active_layer.metadata["link"], Points)
            ):
                return active_layer.metadata["link"]

    # Fallback: return None if no matching layer found
    return None


def error_image_selection():
    """
    Print a message error in a box
    """
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setText("Image selection error")
    msg.setInformativeText(
        "Please select an adequate image\n"
        "You can select point images on the left hand side of the viewer"
    )
    msg.setWindowTitle("Image selection error")
    msg.setStyleSheet(get_current_stylesheet())
    msg.exec_()


def custom_error(title, message, informative=None):
    """
    Print a message error in a box
    """
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setText(title)
    if informative:
        msg.setInformativeText(informative)
    msg.setWindowTitle("message")
    msg.setStyleSheet(get_current_stylesheet())
    msg.exec_()


def clear_layout(self):
    layout = self.layout()
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


def error_cell_selection():
    """
    Print a message error in a box
    """
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setText("Cell selection error")
    msg.setInformativeText(
        "The cell you chose cannot be processed\nPlease chose another one"
    )
    msg.setWindowTitle("Cell selection error")
    msg.exec_()


def extract_lineage(main_lT: LineageTree, roots: int | list | set):
    new_lT = LineageTree()
    if not isinstance(roots, Iterable):
        roots = [roots]
    for r in roots:
        pred_root = main_lT.predecessor.get(r)
        if pred_root:
            new_lT.successor[pred_root[0]] = list(
                main_lT.successor[pred_root[0]]
            )
        old_nodes = main_lT.get_subtree_nodes(r)
        new_lT.nodes.update(old_nodes)
        for new_node in old_nodes:
            new_lT.time[new_node] = main_lT.time[new_node]
            succ = main_lT.successor.get(new_node)
            if succ:
                new_lT.successor[new_node] = list(succ)
            pred = main_lT.predecessor.get(new_node)
            if pred:
                new_lT.predecessor[new_node] = list(pred)
            new_lT.pos[new_node] = main_lT.pos[new_node]
            new_lT.time_nodes.setdefault(new_lT.time[new_node], set()).add(
                new_node
            )
            if main_lT.labels.get(new_node):
                new_lT.labels[new_node] = main_lT.labels[new_node]
        new_root = r
        if r in main_lT.roots:
            new_lT.roots.add(new_root)
        new_lT.t_e, new_lT.t_b = int(main_lT.t_e), int(main_lT.t_b)
    return new_lT


def inject_lineage(
    main_lineageTree: LineageTree, extracted_lineageTree: LineageTree
):
    main_lineageTree.nodes.update(extracted_lineageTree.nodes)
    main_lineageTree.predecessor.update(extracted_lineageTree.predecessor)
    main_lineageTree.successor.update(extracted_lineageTree.successor)
    main_lineageTree.pos.update(extracted_lineageTree.pos)
    main_lineageTree.time.update(extracted_lineageTree.time)
    main_lineageTree.roots.update(extracted_lineageTree.roots)
    main_lineageTree.labels.update(extracted_lineageTree.labels)
    for t in range(
        int(min(extracted_lineageTree.t_b, main_lineageTree.t_b)),
        int(max(extracted_lineageTree.t_e, main_lineageTree.t_e)),
    ):
        main_lineageTree.time_nodes.setdefault(t, set).update(
            extracted_lineageTree.time_nodes.get(t, set())
        )


def rotate_3d(
    axes,
    target=(
        [0, 1, 0],
        [1, 0, 0],
        [0, 0, 1],
    ),
):
    H = (
        np.array(axes - np.mean(axes, axis=0))
        @ np.array(target - np.mean(target, axis=0)).T
    )
    U, _, Vt = np.linalg.svd(H)
    R = Vt @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        return Vt.T @ U.T
    return R


def create_links_and_chains(lT: LineageTree, roots: list | set | int):
    """Generates a dictionary containing the links and the lengths of each chain.
    Similar to simple tree, mainly used for tree manip app.

    Args:
        roots (Union[list,set,int]): The roots from which the tree will be generated.

    Returns:
        dict: A dictionary with keys "links" and "times" which contains the connections all cells and their chain
        length.
    """

    if not roots:
        to_do = set(lT.roots)
    elif isinstance(roots, Iterable):
        to_do = set(roots)
    else:
        to_do = {roots}
    times = {}
    links = {}
    while to_do:
        curr = to_do.pop()
        cyc = lT.get_successors(curr)
        last = cyc.pop()
        times[curr] = len(cyc)
        links[curr] = last
        succ = lT.successor.get(last)
        if succ:
            for s in succ:
                times[s] = 1
            to_do.update(succ)
            links[last] = succ
    return {"links": links, "times": times}


def plot_lineages_for_tree_manip(
    lT,
    lnks_tms,
    hiers,
    nrows=2,
    figsize=(10, 15),
    dpi=100,
    fontsize=40,
    figure=None,
    axes=None,
    **kwargs,
):
    """Plots all lineages.

    Args:
        last_time_point_to_consider (int, optional): Which timepoints and upwards are the graphs to be calculated.
                                                    For example if start_time is 10, then all trees that begin
                                                    on tp 10 or before are calculated. Defaults to None.
        nrows (int):  How many rows of plots should be printed.
        kwargs: args accepted by networkx
    """

    nrows = int(nrows)
    if nrows < 1 or not nrows:
        nrows = 1
        raise Warning("Number of rows has to be at least 1")
    graphs = lnks_tms
    pos = hiers
    ncols = int(len(graphs) // nrows) + (+np.sign(len(graphs) % nrows))
    figure, axes = plt.subplots(
        figsize=figsize,
        nrows=nrows,
        ncols=ncols,
        dpi=dpi,
        sharey=True,
    )
    flat_axes = axes.flatten() if isinstance(axes, list) else [axes]
    ax2root = {}
    root2ax = {}
    min_width, min_height = float("inf"), float("inf")

    for ax in flat_axes:
        bbox = ax.get_window_extent().transformed(
            figure.dpi_scale_trans.inverted()
        )
        min_width = min(min_width, bbox.width)
        min_height = min(min_height, bbox.height)

    adjusted_fontsize = fontsize * min(min_width, min_height) / 5
    for i, graph in graphs.items():
        # Extract parameters for the new function
        node_size = kwargs.get("size", kwargs.get("node_size", 10))
        line_width = kwargs.get("lw", 0.3)
        edge_color = kwargs.get("color_of_edges", "black")
        node_color = kwargs.get("color_of_nodes", kwargs.get("default_color", "black"))
        selection_color = kwargs.get("color_of_selection", "magenta")
        selected_nodes = kwargs.get("selected_nodes", set())
        
        lT.draw_tree_graph_relax(
            hier=pos[i],
            lnks_tms=graph,
            color_of_nodes=node_color,
            color_of_edges=edge_color,
            selected_nodes=selected_nodes,
            color_of_selection=selection_color,
            size=node_size,
            lw=line_width,
            ax=flat_axes[i],
        )
        root = graph["root"]
        ax2root[flat_axes[i]] = root
        root2ax[root] = flat_axes[i]
        label = lT.labels.get(int(root), "Unlabeled")
        xlim = flat_axes[i].get_xlim()
        ylim = flat_axes[i].get_ylim()
        x_pos = (xlim[0] + xlim[1]) / 2
        y_pos = ylim[1] * 0.8
        flat_axes[i].text(
            x_pos,
            y_pos,
            label,
            fontsize=adjusted_fontsize,
            color="black",
            ha="center",
            va="center",
            bbox={"facecolor": "white", "alpha": 0.5, "edgecolor": "green"},
        )
    if isinstance(axes, list):
        [figure.delaxes(ax) for ax in axes.flatten() if not ax.has_data()]
        for ax in axes.flatten():
            ax.get_yaxis().set_visible(False)
            ax.get_xaxis().set_visible(False)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["bottom"].set_visible(False)
            ax.spines["left"].set_visible(False)
    else:
        axes.get_yaxis().set_visible(False)
        axes.get_xaxis().set_visible(False)
        axes.spines["top"].set_visible(False)
        axes.spines["right"].set_visible(False)
        axes.spines["bottom"].set_visible(False)
        axes.spines["left"].set_visible(False)

    return figure, axes, ax2root, root2ax
