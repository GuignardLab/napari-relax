from napari_relax.lineage_tree_analysis.calculate_properties.props import (
    PropertyVisualization,
)

from .cells_size import (
    CellSize,
)
from .comparison_widget.comparisons_handler import ComparisonsHandler
from .lineage_viewer_widget.progeny_selection import ProgenySelection
from .recoloring_with_attributes_widget.recoloring_widget import (
    RecoloringWidget,
)

__all__ = (
    "ProgenySelection",
    "ComparisonsHandler",
    "RecoloringWidget",
    "PropertyVisualization",
)

# All new widget should be listed here to be displayed in napari
__all_widgets__ = (
    ProgenySelection,
    ComparisonsHandler,
    RecoloringWidget,
    PropertyVisualization,
)

__overall_widget__ = CellSize
