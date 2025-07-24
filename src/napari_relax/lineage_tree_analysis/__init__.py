from .cells_size import (
    CellSize,
)
from .comparison_widget.clustermap import Online_clustermap

# Clustermap,
# DisplayDistances,
# Online_clustermap,
# ProgenySelection,
from .lineage_viewer_widget.progeny_selection import ProgenySelection
from .recoloring_with_attributes_widget.distance_display import (
    DisplayDistances,
)

__all__ = (
    "ProgenySelection",
    "DisplayDistances",
    "Online_clustermap",
)

# All new widget should be listed here to be displayed in napari
__all_widgets__ = (
    ProgenySelection,
    DisplayDistances,
    Online_clustermap,
)

__overall_widget__ = CellSize
