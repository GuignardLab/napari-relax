"""Widgets of the Lineage tree analysis dock widget (single dataset).

``__all_widgets__`` lists the entries of the widget combobox and
``__overall_widget__`` the panel shown under all of them.
"""

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
)

# All new widget should be listed here to be displayed in napari
__all_widgets__ = (
    ProgenySelection,
    ComparisonsHandler,
    RecoloringWidget,
)

__overall_widget__ = CellSize
