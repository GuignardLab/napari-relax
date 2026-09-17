"""ReLAX: a napari plugin to explore and compare cell lineage trees.

The plugin contributions (reader, writer, widgets and sample data)
are declared in ``napari.yaml``.
"""

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

from ._reader import napari_get_reader
from ._widgets import (
    CrossEmbryoComparisonWidget,
    LineageTreeAnalysisWidget,
)

__all__ = (
    "CrossEmbryoComparisonWidget",
    "LineageTreeAnalysisWidget",
    "napari_get_reader",
)
