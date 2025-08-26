from typing import TYPE_CHECKING

from napari.qt import get_current_stylesheet
from psygnal import Signal
from qtpy.QtGui import QColor, QDoubleValidator
from qtpy.QtWidgets import (
    QColorDialog,
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from .._util_classes import Containerize
from ..lineage_tree_analysis.lineage_viewer_widget.canvas_for_progeny import (
    SingleTreeProgeny,
)

class ColoredPushButton(QPushButton):
    color_change = Signal(str)

    def __init__(self, text="", parent=None, color="magenta"):
        super().__init__(text, parent)
        self.color = color
        self.setStyleSheet(f"background-color: {self.color};")
        self.clicked.connect(self.choose_color)

    def choose_color(self):
        color = QColorDialog().getColor(initial=QColor(self.color))

        if color.isValid():
            self.setStyleSheet(f"background-color: {color.name()};")
            self.color_change.emit(color.name())
            self.color = color.name()


class Setup(QDialog):
    sig = Signal(dict)

    def __init__(self, canvas: SingleTreeProgeny):
        super().__init__()
        self.setStyleSheet(get_current_stylesheet())
        self.setWindowTitle("Config Tree graph")
        layout = QVBoxLayout()
        double_validator = QDoubleValidator()
        self.color_of_nodes = str(canvas.color_of_nodes)
        self.color_of_edges = str(canvas.color_of_edges)
        self.node_size = str(canvas.node_size)
        self.lw = str(canvas.lw)
        self.fontsize = str(canvas.fontsize)
        self.color_of_selection = str(canvas.color_of_selection_nodes)

        reset_but = QPushButton(text="Reset Settings")
        reset_but.pressed.connect(self.reset)
        apply_but = QPushButton(text="Apply")
        apply_but.pressed.connect(self.apply)

        label_col_nod = QLabel("Node Color:")
        edit_col_nod = ColoredPushButton(
            color=self.color_of_nodes,
        )
        edit_col_nod.color_change.connect(
            lambda event: setattr(self, "color_of_nodes", event)
        )
        col_nod_cont = Containerize([label_col_nod, edit_col_nod])

        label_node_size = QLabel("Node Size:")
        self.edit_node_size = QLineEdit(
            placeholderText=self.node_size,
            clearButtonEnabled=True,
        )  # type: ignore
        self.edit_node_size.setText(self.node_size)
        self.edit_node_size.setValidator(double_validator)
        nod_size_cont = Containerize([label_node_size, self.edit_node_size])

        edit_col_edg = ColoredPushButton(color=self.color_of_edges)
        edit_col_edg.color_change.connect(
            lambda event: setattr(self, "color_of_nodes", event)
        )

        label_edge_size = QLabel("Edge Size:")
        self.edit_edge_size = QLineEdit(
            placeholderText=self.lw,
            clearButtonEnabled=True,
        )  # type: ignore
        self.edit_edge_size.setText(self.lw)
        self.edit_edge_size.setValidator(double_validator)

        edge_size_cont = Containerize([label_edge_size, self.edit_edge_size])

        label_fontsize_size = QLabel("Fontsize for labels:")
        self.edit_fontsize_size = QLineEdit(
            placeholderText=self.node_size,
            clearButtonEnabled=True,
        )  # type: ignore
        self.edit_fontsize_size.setText(self.fontsize)
        self.edit_fontsize_size.setValidator(double_validator)

        fontsize_cont = Containerize(
            [label_fontsize_size, self.edit_fontsize_size]
        )

        label_color_selection = QLabel("Selected Subtrees Color:")
        edit_color_sel = ColoredPushButton(color=self.color_of_selection)
        edit_color_sel.color_change.connect(
            lambda event: setattr(self, "color_of_selection", event)
        )
        color_of_sel_cont = Containerize(
            [label_color_selection, edit_color_sel]
        )
        self.setLayout(layout)
        self.layout().addWidget(col_nod_cont)
        self.layout().addWidget(nod_size_cont)
        self.layout().addWidget(edge_size_cont)
        self.layout().addWidget(fontsize_cont)
        self.layout().addWidget(color_of_sel_cont)
        self.layout().addWidget(Containerize([reset_but, apply_but]))

    def reset(self):
        """Resets the colors of the tree graph."""
        self.sig.emit(
            {
                "color_of_nodes": "black",
                "color_of_edges": "black",
                "node_size": 10,
                "lw": 0.3,
                "fontsize": 6,
                "color_of_selection": "magenta",
            }
        )
        self.accept()

    def apply(self):
        """Sets the colors of the tree graph."""
        self.sig.emit(
            {
                "color_of_nodes": self.color_of_nodes,
                "color_of_edges": self.color_of_edges,
                "node_size": self.edit_node_size.text(),
                "lw": self.edit_edge_size.text(),
                "fontsize": self.edit_fontsize_size.text(),
                "color_of_selection": self.color_of_selection,
                "all_selected": False,
            }
        )
        self.accept()
