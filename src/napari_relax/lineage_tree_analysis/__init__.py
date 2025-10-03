from .cells_size import (
    CellSize,
)
from .comparison_widget.clustermap import OnlineClustermap

# Clustermap,
# DisplayDistances,
# OnlineClustermap,
# ProgenySelection,
from .lineage_viewer_widget.progeny_selection import ProgenySelection
from .recoloring_with_attributes_widget.recoloring_widget import (
    RecoloringWidget,
)


__all__ = (
    "ProgenySelection",
    "RecoloringWidget",
    "OnlineClustermap",
)

# All new widget should be listed here to be displayed in napari
__all_widgets__ = (
    ProgenySelection,
    RecoloringWidget,
    OnlineClustermap,
)

__overall_widget__ = CellSize
