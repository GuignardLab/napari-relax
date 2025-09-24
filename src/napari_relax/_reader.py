"""
This module is an example of a barebones numpy reader plugin for napari.

It implements the Reader specification, but your plugin may choose to
implement multiple readers or even other plugin contributions. see:
https://napari.org/stable/plugins/guides.html?#readers
"""

from pathlib import Path

import numpy as np
from lineagetree import (
    LOADERS,
    LineageTree,
)
from lineagetree._core import utils
from napari.utils import colormaps
from napari.utils.notifications import show_warning

from ._util_classes import LoadingDialog, TimeResDialog
from ._utils import _infer_point_size


def napari_get_reader(path):
    """A basic implementation of a Reader contribution.

    Parameters
    ----------
    path : str or list of str
        Path to file, or list of paths.

    Returns
    -------
    function or None
        If the path is a recognized format, return a function that accepts the
        same path or list of paths, and returns a list of layer data tuples.
    """
    if isinstance(path, list):
        # reader plugins may be handed single path, or a list of paths.
        # if it is a list, it is assumed to be an image stack...
        # so we are only going to look at the first file.
        path = path[0]

    # if we know we cannot read the file, we immediately return None.

    if (
        path.lower().endswith(".lt")
        or path.lower().split(".")[-1] in LOADERS
    ):
        return reader_function

    # otherwise we return the *function* that can read ``path``.
    return None


def reader_function(path: str):
    """Take a path or list of paths and return a list of LayerData tuples.

    Readers are expected to return data as a list of tuples, where each tuple
    is (data, [add_kwargs, [layer_type]]), "add_kwargs" and "layer_type" are
    both optional.

    Parameters
    ----------
    path : str or list of str
        Path to file, or list of paths.

    Returns
    -------
    layer_data : list of tuples
        A list of LayerData tuples where each tuple in the list contains
        (data, metadata, layer_type), where data is a numpy array, metadata is
        a dict of keyword arguments for the corresponding viewer.add_* method
        in napari, and layer_type is a lower-case string naming the type of
        layer. Both "meta", and "layer_type" are optional. napari will
        default to layer_type=="image" if not provided
    """
    if path.lower().endswith(".lt"):
        lT = LineageTree.load(path)
    else:
        extension = path.lower().split(".")[-1]
        options = LOADERS[extension]

        if len(options) > 1:
            selector = LoadingDialog(options.keys())
            selector.exec_()
            value_selected = selector.value_selected
            if value_selected:
                loader = options[selector.value_selected]
            else:
                raise Warning("Please select one reader function.")
        else:
            loader = options.values[0]

        lT = loader(path)

    if not hasattr(lT, "time_resolution") or lT.time_resolution == 0:
        t_res = TimeResDialog()
        t_res.exec_()
        lT.time_resolution = t_res.value_selected
        if t_res.check_resave.isChecked():
            lT.write(path)

    return layer_preparation(lT, path)


def layer_preparation(lT: LineageTree, path: str = ""):
    tracks = lT.all_chains
    first_c_to_track = {}
    last_c_of_track = {}
    data = []
    c_id = 0
    lT_to_here = {}
    for i, t in enumerate(tracks):
        first_c_to_track[t[0]] = i
        last_c_of_track[i] = t[-1]
        for cell in t:
            data.append(
                (
                    i,
                    lT.time[cell],
                )
                + tuple(p for p in np.array(lT.pos[cell])[::-1])
            )

            lT_to_here[cell] = c_id
            c_id += 1
    here_to_lT = {v: k for k, v in lT_to_here.items()}
    data = np.array(data, dtype=float)
    data[:, 2:] -= data[:, 2:].mean(axis=0)

    clone = np.zeros(len(data))
    roots = lT.roots

    clone2 = np.zeros((len(data), 4))
    cmap = colormaps.label_colormap(len(roots))
    for i, root in enumerate(roots, start=1):
        color = cmap.map(i)
        for cell in lT.get_subtree_nodes(root):
            clone[lT_to_here[cell]] = i
            clone2[lT_to_here[cell], :] = color

    if Path(path).stem:
        path = Path(path).stem
    graphs = lT._create_dict_of_plots(
        {
            root
            for root in lT.roots
            if len(lT.get_subtree_nodes(root)) > (lT.t_e - lT.t_b) / 4
        }
    )
    show_warning(
        "Only lineages with height larger than 1/4 of the total timepoints will be shown on the lineage Viewer."
    )
    pos = {
        i: utils.hierarchical_pos(
            g, g["root"], ycenter=-int(lT.time[g["root"]]), vert_gap=1
        )
        for i, g in graphs.items()
    }
    graph = {}
    for t, c in last_c_of_track.items():
        for di in lT.successor.get(c, []):
            graph.setdefault(first_c_to_track[di], []).append(t)

    # optimal point size infered from heuristics on nearest neighbor distances
    _, optimal_size, _ = _infer_point_size(lT)

    add_kwargs_point = {
        "size": optimal_size,
        "properties": {
            "clone": clone,
            "Selection": np.zeros_like(clone),
        },
        "metadata": {
            "LineageTree": lT,
            "lT2napari": lT_to_here,
            "napari2lT": here_to_lT,
            "clone2": clone2,
            "graphs": (graphs, pos),
            "name_for_manager": path,
            "data": data,
            "graph_to_create_tracks": {
                "graph": graph,
                "properties": {
                    "Lineage": clone,
                    "Selection": np.ones_like(clone),
                },
            },
        },
        "name": path,
        "face_color": clone2,
        "shading": "spherical",
    }

    return [
        (data[:, 1:], add_kwargs_point, "points"),
    ]
