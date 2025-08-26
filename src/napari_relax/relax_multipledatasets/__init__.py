from .cross_embryo_comparison import Embryo_comparisons
from .manager_widget import CrossEmbryo

__all__ = ("CrossEmbryo", "Embryo_comparisons")

# All new widget should be listed here to be displayed in napari
__all_widgets__ = (CrossEmbryo, Embryo_comparisons)
__overall_widget__ = ()
