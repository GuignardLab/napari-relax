"""Widgets of the Cross Lineagetree comparison dock widget.

``__all_widgets__`` lists the entries of the widget combobox.
"""

from .cross_comparisons_handler import CrossHandler
from .manager_widget import CrossEmbryo

__all__ = ("CrossEmbryo", "CrossHandler")

# All new widget should be listed here to be displayed in napari
__all_widgets__ = (CrossEmbryo, CrossHandler)
__overall_widget__ = ()
