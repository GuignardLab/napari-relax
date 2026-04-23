"""
This module is an example of a barebones numpy reader plugin for napari.

It implements the Reader specification, but your plugin may choose to
implement multiple readers or even other plugin contributions. see:
https://napari.org/stable/plugins/guides.html?#readers
"""

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from lineagetree import (
    LOADERS,
    LineageTree,
)
from lineagetree._core import utils
from napari.utils import colormaps

from ._util_classes import LoadingDialog, SetupDialog
from ._utils import _infer_point_size, find_longest_axis

if TYPE_CHECKING:
    from napari.utils import CyclicLabelColormap


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

    # if we know we can read the file, we return the *function* that can read ``path``
    if path.lower().endswith(".lt") or path.lower().split(".")[-1] in LOADERS:
        return reader_function

    # otherwise we return None
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
            loader = next(iter(options.values()))

        lT = loader(path)

    setup = SetupDialog(lT)  # always appears
    setup.exec_()
    print(setup.parameters)
    if not setup.parameters:
        return

    lT.time_resolution = setup.parameters["time_r"]
    if setup.parameters["resave"]:
        lT.write(path)

    return layer_preparation(lT, path, parameters=setup.parameters)


def _extract_napari_surface_from_lT(lT: LineageTree):
    # First pass: count total vertices and faces to pre-allocate arrays
    total_vertices = 0
    total_faces = 0

    for node in lT.nodes:
        if node in lT.mesh:
            mesh = lT.mesh[node]
            total_vertices += mesh["vertices"].shape[0]
            total_faces += mesh["faces"].shape[0]

    # Pre-allocate arrays
    all_vertices = np.zeros((total_vertices, 4))
    all_faces = np.zeros((total_faces, 3), dtype=int)

    vertex_offset = 0
    face_offset = 0

    for node in lT.nodes:
        if node not in lT.mesh:
            continue

        mesh = lT.mesh[node]
        points = mesh["vertices"][
            :, ::-1
        ]  # reverse coordinates for napari convention
        triangles = mesh["faces"]
        node_time = lT.time[node]

        num_vertices = points.shape[0]
        num_faces = triangles.shape[0]

        # Add time dimension and fill points
        all_vertices[vertex_offset : vertex_offset + num_vertices, 0] = (
            node_time
        )
        all_vertices[vertex_offset : vertex_offset + num_vertices, 1:] = points

        # Adjust triangle indices and fill triangles
        all_faces[face_offset : face_offset + num_faces] = (
            triangles + vertex_offset
        )

        vertex_offset += num_vertices
        face_offset += num_faces

    return all_vertices, all_faces


@dataclass(frozen=True)
class SpatialData:
    """Contains allspatial information a new Points layers may need.

     Attributes
    ----------
    data : np.ndarray
        Array containing the positions of the points.
    lT_to_here : dict
        Mapping from lineage tree IDs to napari IDs.
    here_to_lT : dict
        Mapping from napari IDs to lineage tree IDs.
    clone : np.ndarray
        Original colors of the dataset.
    clone2 : np.ndarray
        Updated colors of the dataset.
    cmap : CyclicLabelColormap
        Colormap used to assign colors to nodes.
    roots : set
        Root nodes of the dataset.
    barycenter : float
        Center of the dataset (should be 0 if centered).
    last_c_of_track : list
        Leaf nodes of the dataset (used for graph loading).
    first_c_to_track : list
        Root nodes of tracks (used for graph loading).
    rescaling_factor : float
        Scaling factor applied to the data.
    """

    data: np.ndarray
    lT_to_here: dict
    here_to_lT: dict
    clone: np.ndarray
    clone2: np.ndarray
    cmap: "CyclicLabelColormap"
    barycenter: float
    last_c_of_track: list
    first_c_to_track: list
    rescaling_factor: float


def initial_loading(lT: LineageTree, scaling=False) -> SpatialData:
    """Calculates the bare minimum to load a LineageTree and returns a dict that contains the data the colors of the nodes and other things that are usefull for other funcs

    Parameters
    ----------
    lT : LineageTree
        The lineageTree

    Returns
    -------
    SpatialData
    """
    tracks = lT.all_chains
    first_c_to_track = {}
    last_c_of_track = {}
    if scaling:
        scale = find_longest_axis(lT)
        print("long_path", scale)
    else:
        scale = 1
    lT.spatial_resolution = 1 / scale
    # Pre-calculate total number of cells
    total_cells = sum(len(track) for track in tracks)

    # Pre-allocate arrays
    data = np.zeros((total_cells, 5), dtype=float)  # track_id, time, z, y, x
    lT_to_here = {}

    c_id = 0

    for i, track in enumerate(tracks):
        first_c_to_track[track[0]] = i
        last_c_of_track[i] = track[-1]

        for cell in track:
            # Get position once and reverse coordinates
            pos = lT.pos[cell]
            data[c_id] = [
                i,
                lT.time[cell],
                *(pos[::-1]),
            ]  # Reverse z,y,x order
            lT_to_here[cell] = c_id
            c_id += 1

    here_to_lT = {v: k for k, v in lT_to_here.items()}
    barycenter = data[:, 2:].mean(axis=0)
    data[:, 2:] -= barycenter
    data[:, 2:] = data[:, 2:] / scale

    clone = np.zeros(len(data))
    roots = lT.roots
    clone2 = np.zeros((len(data), 4))
    cmap = colormaps.label_colormap(len(roots))

    for i, root in enumerate(roots, start=1):
        color = cmap.map(i)
        # Get all cells in subtree at once for vectorized assignment
        subtree_cells = lT.get_subtree_nodes(root)
        # Convert to indices and assign vectorized
        cell_indices = [
            lT_to_here[cell] for cell in subtree_cells if cell in lT_to_here
        ]
        if cell_indices:
            clone[cell_indices] = i
            clone2[cell_indices, :] = color
    return SpatialData(
        data=data,
        lT_to_here=lT_to_here,
        here_to_lT=here_to_lT,
        clone=clone,
        clone2=clone2,
        cmap=cmap,
        barycenter=barycenter,
        last_c_of_track=last_c_of_track,
        first_c_to_track=first_c_to_track,
        rescaling_factor=scale,
    )


def graph_loading(
    lT: LineageTree,
    last_c_of_track: dict,
    first_c_to_track: dict,
    divisor: int,
) -> tuple[dict, dict, dict]:
    """Generates the graphs for the loaded lineagetree.

    Parameters
    ----------
    lT : LineageTree
        The lineagetree object
    last_c_of_track : dict
        a dict created during initial loading
    first_c_to_track : dict
        a dict created during initial loading
    divisor : int
        Handles the minimum size of the trees

    Returns
    -------
    tuple[dict,dict,dict]
        The threee graphs that are gonna be used for the plugin lineage viewers.
    """
    if divisor == 0:
        graphs = lT._create_dict_of_plots({root for root in lT.roots})

        pos = {
            i: utils.hierarchical_pos(
                g, g["root"], ycenter=-int(lT.time[g["root"]]), vert_gap=1
            )
            for i, g in graphs.items()
        }
    else:
        graphs = lT._create_dict_of_plots(
            {
                root
                for root in lT.roots
                if len(lT.get_subtree_nodes(root))
                >= (lT.t_e - lT.t_b) / divisor
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
    return graphs, pos, graph


def layer_preparation(
    lT: LineageTree,
    points_layer_name: str | Path,
    no_graph=False,
    parameters=None,
):

    spatial_data = initial_loading(lT, parameters.get("rescale", False))

    if Path(points_layer_name).exists():
        points_layer_name = Path(points_layer_name).stem
    else:
        points_layer_name = points_layer_name

    # Create a unique identifier for this lineage tree to link Points and Surface layers
    lineage_tree_id = str(uuid.uuid4())
    if not no_graph:
        graphs, pos, graph = graph_loading(
            lT,
            spatial_data.last_c_of_track,
            spatial_data.first_c_to_track,
            parameters.get("divisor", 0),
        )
    else:
        graphs, pos, graph = (), (), ()

    # optimal point size infered from heuristics on nearest neighbor distances
    min_size, optimal_size, max_size = _infer_point_size(lT)

    add_kwargs_point = {
        "size": optimal_size,
        "properties": {
            "clone": spatial_data.clone,
            "Selection": np.zeros_like(spatial_data.clone),
        },
        "metadata": {
            "LineageTree": lT,
            "lT2napari": spatial_data.lT_to_here,
            "napari2lT": spatial_data.here_to_lT,
            "clone2": spatial_data.clone2,
            "graphs": (graphs, pos),
            "name_for_manager": points_layer_name,
            "data": spatial_data.data,
            "lineage_tree_id": lineage_tree_id,  # Unique identifier for linking companion layers
            "graph_to_create_tracks": {
                "graph": graph,
                "properties": {
                    "Lineage": spatial_data.clone,
                    "Selection": np.ones_like(spatial_data.clone),
                },
            },
            "size_display_bounds": (min_size, optimal_size, max_size),
            "rescaling_dactor": spatial_data.rescaling_factor,
        },
        "name": points_layer_name,
        "face_color": spatial_data.clone2,
        "shading": "spherical",
    }

    napari_layers = [
        (spatial_data.data[:, 1:], add_kwargs_point, "points"),
    ]

    if hasattr(lT, "mesh"):

        root_nodes_ids = lT.roots
        dict_roots_to_successors = {
            root: sum(lT.get_all_chains_of_subtree(root), [])
            for root in root_nodes_ids
        }

        dict_successors_to_roots = {
            successor: root
            for root, successors in dict_roots_to_successors.items()
            for successor in successors
        }

        # Pre-calculate total vertices for efficient vertex_colors allocation
        total_vertices = sum(
            mesh["vertices"].shape[0] for mesh in lT.mesh.values()
        )
        vertex_colors = np.zeros(
            (total_vertices, 4)
        )  # Pre-allocate RGBA array
        node_to_vertex_range = {}  # Track vertex ranges for each node
        vertex_offset = 0

        for node_id, mesh in lT.mesh.items():
            root_node_id = dict_successors_to_roots.get(node_id, node_id)
            root_index = list(spatial_data.roots).index(root_node_id) + 1
            num_vertices = mesh["vertices"].shape[0]

            # Store vertex range for this node
            node_to_vertex_range[node_id] = (
                vertex_offset,
                vertex_offset + num_vertices,
            )

            # Efficiently assign colors to the pre-allocated array
            color = spatial_data.cmap.map(root_index)  # Get color once
            vertex_colors[vertex_offset : vertex_offset + num_vertices] = color

            vertex_offset += num_vertices

        all_vertices, all_faces = _extract_napari_surface_from_lT(lT)

        # Barycenter is removed here to match points layer centering.
        # This is debatable if several meshes of the same objects are loaded,
        # as barycenters are inferred from meshes centroids, which won't
        # necessarily coincide for different mesh files from the same embryo.
        all_vertices[:, 1:] -= spatial_data.barycenter

        napari_surface = (all_vertices, all_faces)

        add_kwargs_surface = {
            "name": f"{points_layer_name}_mesh",
            "vertex_colors": vertex_colors,  # Already a numpy array, no conversion needed
            "opacity": 0.25,
            "shading": "smooth",
            "metadata": {
                "node_to_vertex_range": node_to_vertex_range,
                "lineage_tree_id": lineage_tree_id,  # Unique identifier for linking to Points layer
            },
        }

        napari_layers.append((napari_surface, add_kwargs_surface, "surface"))

    return napari_layers
