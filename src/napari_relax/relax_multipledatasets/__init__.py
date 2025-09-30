from .cross_embryo_comparison import EmbryoComparisonsWidget
from .cross_embryo_manager import CrossEmbryoManager

__all__ = ("CrossEmbryoManager", "EmbryoComparisonsWidget")

# All new widget should be listed here to be displayed in napari
__all_widgets__ = (CrossEmbryoManager, EmbryoComparisonsWidget)
__overall_widget__ = ()
