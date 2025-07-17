from .cells_size import (
    CellSize,
)
from .clustermap import Online_clustermap
from .distance_display import DisplayDistances

# Clustermap,
# DisplayDistances,
# Online_clustermap,
# ProgenySelection,
from .progeny_selection import ProgenySelection

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
