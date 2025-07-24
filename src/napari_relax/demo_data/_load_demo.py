import os

from LineageTree import lineageTree

from .._reader import layer_preparation

directory = os.path.dirname(__file__)


def load_demo():
    """Adds the lineatree to the viewer"""
    demo_data = lineageTree.load(os.path.join(directory, "demo.lT"))
    demo_data.time_resolution = 10
    data = layer_preparation(demo_data, "Demo")
    return data
