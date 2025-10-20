import os

from lineagetree import LineageTree

from .._reader import layer_preparation
from ._download_utils import ensure_demo_data

directory = os.path.dirname(__file__)


def load_demo():
    """
    Adds the lineage tree to the viewer.

    This function will automatically download demo data if it's not available locally.
    The download is performed only once and the data is cached for future use.
    """
    # Ensure demo data is available (will download if needed)
    demo_file_path = ensure_demo_data("demo")
    demo_data = LineageTree.load(str(demo_file_path))
    demo_data.time_resolution = 1
    data = layer_preparation(demo_data, "Demo")
    return data


def load_celegans():
    # Ensure demo data is available (will download if needed)
    demo_file_path = ensure_demo_data("C.elegans")
    demo_data = LineageTree.load(str(demo_file_path))
    demo_data.time_resolution = 1
    data = layer_preparation(demo_data, "C.elegans")
    return data
