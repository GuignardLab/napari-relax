import os

from lineagetree import LineageTree

from .._reader import layer_preparation

directory = os.path.dirname(__file__)


def load_demo():
    """Adds the lineatree to the viewer"""
    demo_data = LineageTree.load(os.path.join(directory, "demo.lT"))
    demo_data.time_resolution = 10
    data = layer_preparation(demo_data, "Demo")
    return data


def load_c_elegans():
    """Adds the lineatree to the viewer"""
    demo_data = LineageTree.load(
        os.path.join(directory, "c.elegans.smoothed.lT")
    )
    demo_data.time_resolution = 1
    data = layer_preparation(demo_data, "C.elegans")
    return data
