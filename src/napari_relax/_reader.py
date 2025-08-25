"""
This module is an example of a barebones numpy reader plugin for napari.

It implements the Reader specification, but your plugin may choose to
implement multiple readers or even other plugin contributions. see:
https://napari.org/stable/plugins/guides.html?#readers
"""

from pathlib import Path

import numpy as np
from LineageTree import (
    lineageTree,
    read_from_ASTEC,
    read_from_mamut_xml,
    read_from_mastodon,
    read_from_tgmm_xml,
    read_from_bmf,
    utils,
)
from napari.utils import colormaps

from ._util_classes import loading_dialog, time_res_dialog


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
        path.endswith(".lT")
        or path.lower().endswith(".mastodon")
        or path.lower().endswith(".xml")
        or path.lower().endswith(".csv")
        or path.lower().endswith(".bmf")
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
    # handle both a string and a list of strings
    loaders = {
        "mamut": read_from_mamut_xml,
        "ASTEC": read_from_ASTEC,
        "tgmm": read_from_tgmm_xml,
    }
    if isinstance(path, list):
        lT = lineageTree(file_format=path, file_type="mastodon")
    elif path.lower().endswith(".lt"):
        lT = lineageTree.load(path)
    elif path.lower().endswith(".mastodon"):
        lT = read_from_mastodon(path)
    elif path.lower().endswith(".xml"):
        selector = loading_dialog()
        selector.exec_()
        file_type = selector.value_selected
        if file_type is None:
            raise Warning("Please select one type.")
        lT = loaders[file_type](
            path
        )  # lineageTree(file_format=path, file_type=file_type)
    elif path.lower().endswith(".bmf"):
        lT = read_from_bmf(path, store_meshes=True)
    if not hasattr(lT, "time_resolution") or lT.time_resolution == 0:
        t_res = time_res_dialog()
        t_res.exec_()
        lT.time_resolution = t_res.value_selected
        if t_res.check_resave:
            lT.write(path)
    return layer_preparation(lT, path)


def _extract_napari_surface_from_lT(lT: lineageTree, dict_successors_to_roots: dict):
    all_points = np.zeros((0, 4))
    all_triangles = np.zeros((0, 3), dtype=int)

    values = []

    root_nodes_ids = lT.roots

    dict_roots_to_rand = {
        root: np.random.rand() for root in root_nodes_ids
    }

    # iterate over all nodes in the lineage tree
    for node in lT.nodes:
        root_of_node = dict_successors_to_roots.get(node, node)

        points, triangles = lT.mesh[node].vertices, lT.mesh[node].faces
        points = points[:, ::-1]  # reverse the order of coordinates to match napari's convention

        time = lT.time[node]

        points = np.hstack((np.full(points.shape[0], time).reshape(-1, 1), points))

        values.append(dict_roots_to_rand[root_of_node] * np.ones(points.shape[0]))

        all_points = np.vstack((all_points, points))
        all_triangles = np.vstack((all_triangles, triangles + all_points.shape[0] - points.shape[0]))

    values = np.concatenate(values)

    return all_points, all_triangles, values
    

def _infer_point_size(lT: lineageTree):
    """
    Infer a point size based on nearest neighbor distances.
    Current heuristic is to return the minimum median nearest neighbor distance
    across all time points in the lineage tree.
    If no points are found, return a default size of 100.
    """
    from time import time
    from tqdm import tqdm
    t0 = time()
    t1 = 0
    t2 = 0

    min_dist = float("inf")

    for t in tqdm(lT.time_nodes):
        t1_0 = time()
        nodes = lT.time_nodes[t]
        t1 += time() - t1_0
        if 1 < len(nodes):
            t2_0 = time()
            idx3d, nodes = lT.get_idx3d(t)
            t2 += time() - t2_0
            min_dist = min(
                min_dist,
                np.median(idx3d.query(idx3d.data, k=2)[0][:, 1])
            )

    print(f"Time to compute points size: {time() - t0:.2f} seconds")
    print(f"  of which {t1:.2f} seconds in getting nodes at time t")
    print(f"  of which {t2:.2f} seconds in creating/querying idx3d")

    if min_dist == float("inf"):
        return 100
    else:
        return min_dist


def layer_preparation(lT: lineageTree, path: str = ""):
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

    # deduce optimal point size for display based on a heuristic
    # on nearest neighbor distances
    size = _infer_point_size(lT)

    add_kwargs_point = {
        "size": size,
        "properties": {
            "clone": clone,
            "Selection": np.zeros_like(clone),
        },
        "metadata": {
            "lineageTree": lT,
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

    if not hasattr(lT, "mesh"):
        return [
            (data[:, 1:], add_kwargs_point, "points"),
        ]
    else:
        root_nodes_ids = lT.roots
        dict_roots_to_successors = {
            root: sum(lT.get_all_chains_of_subtree(root), []) for root in root_nodes_ids
        }

        dict_successors_to_roots = {
            successor: root for root, successors in dict_roots_to_successors.items()
            for successor in successors
        }
        napari_surface = _extract_napari_surface_from_lT(lT, dict_successors_to_roots)

        vertex_colors = []

        for node_id, mesh in lT.mesh.items():
            root_node_id = dict_successors_to_roots.get(node_id, node_id)
            root_index = list(roots).index(root_node_id) + 1
            vertex_colors.extend(
                [cmap.map(root_index)] * mesh.vertices.shape[0]
            )

        napari_surface = (
            napari_surface[0],
            napari_surface[1],
        )

        add_kwargs_surface = {
            "name": f"{path}_mesh",
            "vertex_colors": np.array(vertex_colors),
            "opacity": 0.25,
            "shading": "smooth",
        }

        return [
            (data[:, 1:], add_kwargs_point, "points"),
            (napari_surface, add_kwargs_surface, "surface"),
        ]