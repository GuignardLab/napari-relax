from lineagetree import LineageTree
from napari.layers import Points
import os


def napari_get_writer(path: str, layer_type: Points):
    if "LineageTree" in layer_type.metadata:
        if not path.endswith(("lT", "lt", "LT")):
            path = os.path.splitext(path)[0] + ".lT"
        layer_type.metadata["LineageTree"].write(path)
        return path
    else:
        return None
