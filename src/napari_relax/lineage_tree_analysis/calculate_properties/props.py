from lineagetree import LineageTree

from napari_relax._utils import _select_active_lt_layer
from napari_relax._util_classes import LayerCorrectorTreeProducer
from qtpy.QtWidgets import QPushButton, QTabWidget, QVBoxLayout, QWidget
from napari_relax.lineage_tree_analysis.calculate_properties.props_utils import find_all_viable_methods,get_parameters_of_function
from napari_relax.lineage_tree_analysis.calculate_properties.widget_generator import LineEditGenerator
import re
from napari_relax._util_classes import DelayedTooltipEventFilter
from collections.abc import Callable

import inspect
import re


# def get_parameter_doc(func, parameter: str) -> str | None:
#     """Get the documentation for one parameter from a function's docstring."""
#     doc = func.__doc__

#     if not doc:
#         return None

#     pattern = rf"^\s*{re.escape(parameter)}\s*:\s*(.*?)(?=^\s*\w[\w\s]*\s*:|\Z)"

#     match = re.search(pattern, doc, re.MULTILINE | re.DOTALL)

#     if not match:
#         return None

#     return match.group(0).strip()

def get_parameter_doc(func, parameter: str) -> str | None:
    """Get the documentation for one parameter from a function's docstring.
    No idea how it works it's chatgpt code and I don't speak regex
    Practically it returns only the part of the docsting that is related to the parameter given"""
    doc = func.__doc__

    if not doc:
        return None

    pattern = rf"""
        ^\s*{re.escape(parameter)}\s*:\s*
        (.*?)
        (?=
            ^\s*\w[\w\s]*\s*:      # next parameter
            |^\s*Returns?\s*:      # Returns / Return
            |^\s*Returns?\s*$      # Returns / Return without :
            |\Z
        )
    """

    match = re.search(
        pattern,
        doc,
        re.MULTILINE | re.DOTALL | re.VERBOSE,
    )

    if not match:
        return None

    return match.group(1).strip()

def convert_to_title(name):
    return re.sub(r"_+", " ", name).title()

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTabWidget,
    QSizePolicy,
)


class PropertyVisualization(LayerCorrectorTreeProducer):
    name = "Property Visualization"

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)

        self.viewer = napari_viewer
        self.tab_widget = QTabWidget()

        self.tab_widget.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Maximum,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        layout.addWidget(self.tab_widget, alignment=Qt.AlignTop)

        self.populate_tabs()

    def populate_tabs(self):
        methods = find_all_viable_methods(LineageTree)

        for method in methods:
            widget = self.generate_tab_widget(method)
            self.tab_widget.addTab(
                widget,
                convert_to_title(method.__name__)
            )

    def generate_tab_widget(self, method: Callable) -> QWidget:
        widget = QWidget()

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        pars = get_parameters_of_function(method)

        event_filt = DelayedTooltipEventFilter()
        widget.installEventFilter(event_filt)

        widget_dict = {}

        for name, typ in pars.items():
            wdg = LineEditGenerator(name, typ)

            if prm := get_parameter_doc(method, name):
                wdg.setToolTip(prm)

            widget_dict[name] = wdg
            layout.addWidget(wdg)

        widget.widget_dict = widget_dict

        widget.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Maximum,
        )
        widget.method = method
        run =QPushButton("Run")
        run.clicked.connect(lambda x: method(**{par:val.get_value() for par,val in widget_dict.items()}))
        widget.layout().addWidget(run)
        return widget




