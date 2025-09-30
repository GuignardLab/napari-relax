"""
This module contains napari widgets for the ReLAX plugin.
Updated to use the new composition-based architecture while maintaining
separate plugin entries for different analysis types.
"""

from typing import TYPE_CHECKING

from magicgui import widgets
from qtpy.QtWidgets import QComboBox, QStackedWidget, QVBoxLayout, QWidget

from . import lineage_tree_analysis, relax_multipledatasets
from ._data_management import LineageTreeDataManager
from ._signal_hub import PluginSignalHub

if TYPE_CHECKING:
    pass


class PluginWidgetBase(QWidget):
    """
    Base class for all ReLAX widgets, updated to use new architecture.
    Uses composition with signal hub and data manager.
    """

    # Module to parse (here None because it is the abstract class)
    module = None

    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer

        # Initialize new architecture components
        self.signal_hub = PluginSignalHub()
        self.data_manager = LineageTreeDataManager(napari_viewer)

        # Setup UI
        main_control = self.__make_widget_combobox()
        layout = QVBoxLayout()
        layout.addStretch(1)
        layout.setSpacing(0)
        self.setLayout(layout)
        self.layout().addWidget(main_control.native)

        if self.module.__overall_widget__:
            # Pass signal hub to overall widget
            overall_widget = self.module.__overall_widget__(
                self.viewer, self.signal_hub
            )
            self.layout().addWidget(overall_widget)

    def __make_widget_combobox(self) -> QComboBox:
        """
        Function to generate a combo box of
        a list of widgets from a module
        """
        if self.module is None:
            return

        main_combobox = QComboBox()
        main_combobox._explicitly_hidden = False
        main_combobox.native = main_combobox

        main_stack = QStackedWidget()
        main_stack.native = main_stack
        self.widget_dictionary = {}

        for im_info_class in self.module.__all_widgets__:
            # Check if widget accepts signal_hub parameter
            try:
                w_created = im_info_class(self.viewer, self.signal_hub)
            except TypeError:
                # Fallback for widgets that don't support signal_hub yet
                w_created = im_info_class(self.viewer)
                # Add signal_hub as attribute for backward compatibility
                if hasattr(w_created, "__dict__"):
                    w_created.signal_hub = self.signal_hub

            main_combobox.addItem(w_created.name)
            main_stack.addWidget(w_created)
            self.widget_dictionary[w_created.name] = w_created

        main_combobox.currentIndexChanged.connect(main_stack.setCurrentIndex)
        main_combobox.name = "main_combobox"
        main_stack.name = "main_stack"

        main_control = widgets.Container(
            widgets=[
                main_combobox,
                main_stack,
            ],
            labels=False,
        )
        return main_control


class LineageTreeAnalysisWidget(PluginWidgetBase):
    """Lineage tree analysis widget with updated architecture."""

    module = lineage_tree_analysis

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)

        # Setup signal connections using the signal hub
        self._setup_signal_connections()

    def _setup_signal_connections(self):
        """Setup signal connections between widgets using the signal hub."""
        # Connect "Explore and Relabel" line edit to "Distance Calculation"
        if (
            "Explore and Relabel" in self.widget_dictionary
            and "Distance Calculation" in self.widget_dictionary
        ):

            explore_widget = self.widget_dictionary["Explore and Relabel"]
            distance_widget = self.widget_dictionary["Distance Calculation"]

            # Connect line edit return pressed to label update
            explore_widget.w_lineedit.returnPressed.connect(
                lambda: self.signal_hub.emit_label_update(
                    explore_widget.w_lineedit.text()
                )
            )

            # Connect signal hub to distance widget label update
            self.signal_hub.label_update_requested.connect(
                distance_widget.label_update
            )

        # Connect "Attribute Based Recoloring" to "Explore and Relabel" for color updates
        if (
            "Attribute Based Recoloring" in self.widget_dictionary
            and "Explore and Relabel" in self.widget_dictionary
        ):

            coloring_widget = self.widget_dictionary[
                "Attribute Based Recoloring"
            ]
            explore_widget = self.widget_dictionary["Explore and Relabel"]

            # Connect color signal through signal hub
            coloring_widget.coloring_widget.quant.color_signal.connect(
                lambda color_map: self.signal_hub.emit_color_change(color_map)
            )

            # Connect signal hub to explore widget canvas
            self.signal_hub.colors_changed.connect(
                explore_widget.canvas.change_attributes
            )

            # Also update lineage color box
            self.signal_hub.colors_changed.connect(
                explore_widget.update_lineage_color_box
            )


class CrossEmbryoManagerComparisonWidget(PluginWidgetBase):
    """Cross-embryo comparison widget with updated architecture."""

    module = relax_multipledatasets

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)

        # Setup signal connections using the signal hub
        self._setup_signal_connections()

    def _setup_signal_connections(self):
        """Setup signal connections between widgets using the signal hub."""
        # Connect "Manager Manipulation" to "Embryo comparisons"
        if (
            "Manager Manipulation" in self.widget_dictionary
            and "Embryo comparisons" in self.widget_dictionary
        ):

            manager_widget = self.widget_dictionary["Manager Manipulation"]
            comparison_widget = self.widget_dictionary["Embryo comparisons"]

            # Connect manager signal through signal hub
            manager_widget.send_manager_to_classes.connect(
                lambda manager: self.signal_hub.emit_manager_ready(manager)
            )

            # Connect signal hub to comparison widget
            self.signal_hub.manager_ready.connect(
                comparison_widget.get_lt_manager
            )
