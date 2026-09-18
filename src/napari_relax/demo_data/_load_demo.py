import os

from lineagetree import LineageTree

from .._reader import layer_preparation
from ._download_utils import ensure_demo_data

directory = os.path.dirname(__file__)


def load_demo():
    """Load the Parhyale hawaiensis demo dataset.

    The file ships with the plugin.

    Returns
    -------
    list of tuple
        LayerData tuples for napari.
    """
    # Ensure demo data is available (will download if needed)
    demo_file_path = ensure_demo_data("demo")
    demo_data = LineageTree.load(str(demo_file_path))
    demo_data.time_resolution = 1
    data = layer_preparation(demo_data, "Demo", parameters={})
    return data


def load_celegans():
    # Ensure demo data is available (will download if needed)
    """Load the C. elegans demo dataset.

    The dataset is downloaded from Zenodo on first use and cached.

    Returns
    -------
    list of tuple
        LayerData tuples for napari.
    """
    demo_file_path = ensure_demo_data("C.elegans")
    demo_data = LineageTree.load(str(demo_file_path))
    demo_data.time_resolution = 1
    data = layer_preparation(demo_data, "C.elegans", parameters={})
    return data
