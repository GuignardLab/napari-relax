"""napari writer saving a LineageTree as a ``.lT`` file."""

import os
from typing import Any

from napari.utils.notifications import show_error


def write_single_image(path: str, data: Any, meta: dict) -> list[str]:
    """Save the LineageTree of a layer as a ``.lT`` file.

    Parameters
    ----------
    path : str
        Destination path. ``.lT`` is used if it has another extension.
    data : Any
        Layer data, unused.
    meta : dict
        Layer attributes; the LineageTree is read from its metadata or
        from the metadata of the linked layer.

    Returns
    -------
    list of str
        The path that was written.
    """
    lineage_tree = None

    # Try to get LineageTree directly from metadata
    if "LineageTree" in meta["metadata"]:
        lineage_tree = meta["metadata"]["LineageTree"]
    # If not found, try to get it from linked layer
    elif "link" in meta["metadata"] and hasattr(
        meta["metadata"]["link"], "metadata"
    ):
        linked_metadata = meta["metadata"]["link"].metadata
        if "LineageTree" in linked_metadata:
            lineage_tree = linked_metadata["LineageTree"]

    if lineage_tree:
        if not path.endswith(("lT", "lt", "LT")):
            path = os.path.splitext(path)[0] + ".lT"
        lineage_tree.write(path)
    else:
        show_error(
            "Please use a layer that contains a LineageTree or is linked to one"
        )
    return [path]
