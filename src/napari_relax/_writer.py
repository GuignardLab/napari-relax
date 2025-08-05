from lineagetree import LineageTree
from napari.layers import Points
from typing import TYPE_CHECKING, Any, Union
from napari.utils.notifications import show_error

import os


def write_single_image(path: str, data: Any, meta: dict) -> list[str]:
    if "LineageTree" in meta["metadata"]:
        if not path.endswith(("lT", "lt", "LT")):
            path = os.path.splitext(path)[0] + ".lT"
        meta["metadata"]["LineageTree"].write(path)
    else:
        show_error("Please use a layer that contains a LineageTree")
    return [path]
