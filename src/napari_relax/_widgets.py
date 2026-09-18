"""The two dock widgets registered in ``napari.yaml``.

Each widget stacks the widgets listed in ``__all_widgets__`` of
its module behind a combobox, and adds the module's
``__overall_widget__`` under them:

- `LineageTreeAnalysisWidget` uses `lineage_tree_analysis`;
- `CrossEmbryoComparisonWidget` uses `relax_multipledatasets`.
"""

from typing import TYPE_CHECKING

from magicgui import widgets
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import lineage_tree_analysis, relax_multipledatasets

if TYPE_CHECKING:
    pass


class ReLAXWidget(QWidget):
    """Base class of the ReLAX dock widgets.

    Subclasses set ``module`` to the package whose ``__all_widgets__``
    are shown.

    Parameters
    ----------
    napari_viewer : napari.Viewer
        The napari viewer.
    """

    # Module to parse (here None because it is the abstract class)
    module = None

    def __make_widget_combobox(self) -> QComboBox:
        """Build a combobox that switches between the widgets of the module.

        Returns
        -------
        magicgui.widgets.Container
            The combobox and the stack of widgets.
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
            w_created = im_info_class(self.viewer)
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

    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        main_control = self.__make_widget_combobox()
        layout = QVBoxLayout()
        layout.setSpacing(0)
        self.setLayout(layout)
        self.layout().addWidget(main_control.native)
        if self.module.__overall_widget__:
            self.layout().addWidget(
                self.module.__overall_widget__(self.viewer)
            )
        screen = QApplication.primaryScreen()
        dpi = screen.logicalDotsPerInch()
        scale = dpi / 96
        font = self.font()
        font.setPointSizeF(font.pointSizeF() * scale)
        self.setFont(font)
        layout.addStretch(1)


class LineageTreeAnalysisWidget(ReLAXWidget):
    """Single-dataset widget: explore, recolor and compare lineages.

    Parameters
    ----------
    napari_viewer : napari.Viewer
        The napari viewer.
    """

    module = lineage_tree_analysis  # for the time being

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)
        explore_and_relabel = self.widget_dictionary["Explore and Relabel"]
        explore_and_relabel.w_lineedit.returnPressed.connect(
            self.widget_dictionary["Distance Calculation"].config.label_update
        )
        explore_and_relabel.w_lineedit.returnPressed.connect(
            self.widget_dictionary[
                "Distance Calculation"
            ].clustermap.receive_new_labels
        )
        self.widget_dictionary[
            "Attribute Based Recoloring"
        ].coloring_widget.quant.color_signal.connect(
            explore_and_relabel.progeny_diagram_loader
        )


class CrossEmbryoComparisonWidget(ReLAXWidget):
    """Multiple-dataset widget: manage datasets and compare them.

    Parameters
    ----------
    napari_viewer : napari.Viewer
        The napari viewer.
    """

    module = relax_multipledatasets

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)
        self.widget_dictionary[
            "Manager Manipulation"
        ].send_manager_to_classes.connect(
            self.widget_dictionary["Cross Distance Calculation"].get_lt_manager
        )
