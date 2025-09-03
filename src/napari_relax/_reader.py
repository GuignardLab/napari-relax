"""
This module is an example of a barebones numpy reader plugin for napari.

It implements the Reader specification, but your plugin may choose to
implement multiple readers or even other plugin contributions. see:
https://napari.org/stable/plugins/guides.html?#readers
"""

from pathlib import Path
import uuid

import numpy as np
from lineagetree import (
    LineageTree,
    read_from_ASTEC,
    read_from_mamut_xml,
    read_from_mastodon,
    read_from_tgmm_xml,
    read_from_bmf,
)
from lineagetree._core import utils
from napari.utils import colormaps
from napari.utils.notifications import show_warning

from ._util_classes import LoadingDialog, TimeResDialog


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
        lT = LineageTree(file_format=path, file_type="mastodon")
    elif path.lower().endswith(".lt"):
        lT = LineageTree.load(path)
    elif path.lower().endswith(".mastodon"):
        lT = read_from_mastodon(path)
    elif path.lower().endswith(".xml"):
        selector = LoadingDialog()
        selector.exec_()
        file_type = selector.value_selected
        if file_type is None:
            raise Warning("Please select one type.")
        lT = loaders[file_type](
            path
        )  # LineageTree(file_format=path, file_type=file_type)
    elif path.lower().endswith(".bmf"):
        lT = read_from_bmf(path, store_meshes=True)
    if not hasattr(lT, "time_resolution") or lT.time_resolution == 0:
        t_res = TimeResDialog()
        t_res.exec_()
        lT.time_resolution = t_res.value_selected
        if t_res.check_resave.isChecked():
            lT.write(path)
    return layer_preparation(lT, path)


def _extract_napari_surface_from_lT(lT: LineageTree, dict_successors_to_roots: dict):
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
    

def _infer_point_size(lT: LineageTree):
    """
    Infer a point size based on nearest neighbor distances.
    Current heuristic is to return the minimum median nearest neighbor distance
    across all time points in the lineage tree.
    If no points are found, return a default size of 100.
    """
    #TODO: remove before merging
    min_dist = float("inf")

    for t in lT.time_nodes:
        nodes = lT.time_nodes[t]
        if 1 < len(nodes):
            idx3d, nodes = lT.get_idx3d(t)
            min_dist = min(
                min_dist,
                np.median(idx3d.query(idx3d.data, k=2)[0][:, 1])
            )

    if min_dist == float("inf"):
        return 100
    else:
        return min_dist


def layer_preparation(lT: LineageTree, points_layer_name: str = ""):
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
    barycenter = data[:, 2:].mean(axis=0)
    data[:, 2:] -= barycenter

    clone = np.zeros(len(data))
    roots = lT.roots

    clone2 = np.zeros((len(data), 4))
    cmap = colormaps.label_colormap(len(roots))
    for i, root in enumerate(roots, start=1):
        color = cmap.map(i)
        for cell in lT.get_subtree_nodes(root):
            clone[lT_to_here[cell]] = i
            clone2[lT_to_here[cell], :] = color

    if Path(points_layer_name).stem:
        points_layer_name = Path(points_layer_name).stem
    
    # Create a unique identifier for this lineage tree to link Points and Surface layers
    lineage_tree_id = str(uuid.uuid4())
    
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
            "LineageTree": lT,
            "lT2napari": lT_to_here,
            "napari2lT": here_to_lT,
            "clone2": clone2,
            "graphs": (graphs, pos),
            "name_for_manager": points_layer_name,
            "data": data,
            "lineage_tree_id": lineage_tree_id,  # Unique identifier for linking companion layers
            "graph_to_create_tracks": {
                "graph": graph,
                "properties": {
                    "Lineage": clone,
                    "Selection": np.ones_like(clone),
                },
            },
        },
        "name": points_layer_name,
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

        vertex_colors = []
        node_to_vertex_range = {}  # Track vertex ranges for each node
        vertex_offset = 0

        for node_id, mesh in lT.mesh.items():
            root_node_id = dict_successors_to_roots.get(node_id, node_id)
            root_index = list(roots).index(root_node_id) + 1
            num_vertices = mesh.vertices.shape[0]
            
            # Store vertex range for this node
            node_to_vertex_range[node_id] = (vertex_offset, vertex_offset + num_vertices)
            vertex_offset += num_vertices
            
            vertex_colors.extend(
                [cmap.map(root_index)] * num_vertices
            )

        all_points, all_triangles, values = _extract_napari_surface_from_lT(lT, dict_successors_to_roots)
        
        all_points[:, 1:] -= barycenter #TODO think about barycenter

        napari_surface = (
            all_points,
            all_triangles
        )

        add_kwargs_surface = {
            "name": f"{points_layer_name}_mesh",
            "vertex_colors": np.array(vertex_colors),
            "opacity": 0.25,
            "shading": "smooth",
            "metadata": {
                "node_to_vertex_range": node_to_vertex_range,
                "lineage_tree_id": lineage_tree_id,  # Unique identifier for linking to Points layer
            },
        }

        return [
            (data[:, 1:], add_kwargs_point, "points"),
            (napari_surface, add_kwargs_surface, "surface"),
        ]