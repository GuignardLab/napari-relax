from .cell_size_control import (
    CellSizeControlWidget,
)
from .comparison_widget.distance_clustering_widget import InteractiveClusterMapWidget

# Clustermap,
# DisplayDistances,
# InteractiveClusterMapWidget,
# LineageExplorationWidget,
from .lineage_viewer_widget.lineage_explorer import LineageExplorationWidget
from .recoloring_with_attributes_widget.distance_display import (
    DisplayDistances,
)

__all__ = (
    "LineageExplorationWidget",
    "DisplayDistances",
    "InteractiveClusterMapWidget",
)

# All new widget should be listed here to be displayed in napari
__all_widgets__ = (
    LineageExplorationWidget,
    DisplayDistances,
    InteractiveClusterMapWidget,
)

__overall_widget__ = CellSizeControlWidget
