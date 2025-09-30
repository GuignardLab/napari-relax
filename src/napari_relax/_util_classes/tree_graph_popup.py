from typing import TYPE_CHECKING

from napari.qt import get_current_stylesheet
from napari.settings import get_settings
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

from .._layout_utils import SimpleContainer

if TYPE_CHECKING:
    from ..lineage_tree_analysis.lineage_viewer_widget.lineage_tree_canvas import (
        LineageCanvas,
    )


# Default values for canvas properties - can be referenced by other components
DEFAULT_CANVAS_SETTINGS = {
    "color_of_edges": "black",
    "node_size": 10,
    "lw": 0.3,
    "fontsize": 6,
    "color_of_selection": "magenta",
}


def _get_user_canvas_settings():
    """Get user's preferred canvas settings from napari settings."""
    settings = get_settings()
    if hasattr(settings, 'plugins') and hasattr(settings.plugins, 'napari_relax'):
        plugin_settings = settings.plugins.napari_relax
        return {
            "color_of_edges": getattr(plugin_settings, 'canvas_edge_color', DEFAULT_CANVAS_SETTINGS["color_of_edges"]),
            "node_size": getattr(plugin_settings, 'canvas_node_size', DEFAULT_CANVAS_SETTINGS["node_size"]),
            "lw": getattr(plugin_settings, 'canvas_edge_width', DEFAULT_CANVAS_SETTINGS["lw"]),
            "fontsize": getattr(plugin_settings, 'canvas_fontsize', DEFAULT_CANVAS_SETTINGS["fontsize"]),
            "color_of_selection": getattr(plugin_settings, 'canvas_selection_color', DEFAULT_CANVAS_SETTINGS["color_of_selection"]),
        }
    return DEFAULT_CANVAS_SETTINGS.copy()


def _save_user_canvas_settings(settings_dict):
    """Save user's preferred canvas settings to napari settings."""
    settings = get_settings()
    try:
        if hasattr(settings, 'plugins'):
            if not hasattr(settings.plugins, 'napari_relax'):
                # Create the plugin settings section if it doesn't exist
                settings.plugins.napari_relax = {}
            
            plugin_settings = settings.plugins.napari_relax
            plugin_settings.canvas_edge_color = settings_dict.get("color_of_edges", DEFAULT_CANVAS_SETTINGS["color_of_edges"])
            plugin_settings.canvas_node_size = settings_dict.get("node_size", DEFAULT_CANVAS_SETTINGS["node_size"])
            plugin_settings.canvas_edge_width = settings_dict.get("lw", DEFAULT_CANVAS_SETTINGS["lw"])
            plugin_settings.canvas_fontsize = settings_dict.get("fontsize", DEFAULT_CANVAS_SETTINGS["fontsize"])
            plugin_settings.canvas_selection_color = settings_dict.get("color_of_selection", DEFAULT_CANVAS_SETTINGS["color_of_selection"])
    except Exception as e:
        print(f"Warning: Could not save canvas settings: {e}")


def _update_napari_highlight_color(color_name: str, viewer=None):
    """Update napari's highlight color setting and refresh layers."""
    settings = get_settings()
    # QColor can handle both hex strings (#ff0000) and named colors (magenta)
    color = QColor(color_name)
    if color.isValid():
        rgba = (
            color.red() / 255.0,
            color.green() / 255.0,
            color.blue() / 255.0,
            color.alpha() / 255.0,
        )
        settings.appearance.highlight.highlight_color = rgba
        settings.appearance.highlight.highlight_thickness = 3

        # Refresh Points layers if viewer is available
        if viewer is not None:
            for layer in viewer.layers:
                layer.refresh()
    else:
        # Fallback to magenta if invalid color
        settings.appearance.highlight.highlight_color = (1.0, 0.0, 1.0, 1.0)


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


class LineageCanvasSetup(QDialog):
    sig = Signal(dict)

    def __init__(self, canvas: "LineageCanvas", viewer=None):
        super().__init__()
        self.canvas = canvas
        self.viewer = viewer
        self.setStyleSheet(get_current_stylesheet())
        self.setWindowTitle("Config Tree graph")
        layout = QVBoxLayout()
        double_validator = QDoubleValidator()
        
        # Initialize with current user preferences rather than current canvas state
        # This ensures the dialog shows what the user last configured, not temporary values
        user_prefs = _get_user_canvas_settings()
        self.color_of_edges = str(user_prefs["color_of_edges"])
        self.node_size = str(user_prefs["node_size"])
        self.lw = str(user_prefs["lw"])
        self.fontsize = str(user_prefs["fontsize"])
        self.color_of_selection = str(user_prefs["color_of_selection"])

        reset_but = QPushButton(text="Reset Settings")
        reset_but.pressed.connect(self.reset)
        apply_but = QPushButton(text="Apply")
        apply_but.pressed.connect(self.apply)

        label_node_size = QLabel("Node Size:")
        self.edit_node_size = QLineEdit(
            placeholderText=self.node_size,
            clearButtonEnabled=True,
        )  # type: ignore
        self.edit_node_size.setText(self.node_size)
        self.edit_node_size.setValidator(double_validator)
        nod_size_cont = SimpleContainer([label_node_size, self.edit_node_size])

        label_edge_color = QLabel("Edge Color:")
        edit_col_edg = ColoredPushButton(color=self.color_of_edges)
        edit_col_edg.color_change.connect(
            lambda event: setattr(self, "color_of_edges", event)
        )
        edge_color_cont = SimpleContainer([label_edge_color, edit_col_edg])

        label_edge_size = QLabel("Edge Size:")
        self.edit_edge_size = QLineEdit(
            placeholderText=self.lw,
            clearButtonEnabled=True,
        )  # type: ignore
        self.edit_edge_size.setText(self.lw)
        self.edit_edge_size.setValidator(double_validator)

        edge_size_cont = SimpleContainer(
            [label_edge_size, self.edit_edge_size]
        )

        label_fontsize_size = QLabel("Fontsize for labels:")
        self.edit_fontsize_size = QLineEdit(
            placeholderText=self.node_size,
            clearButtonEnabled=True,
        )  # type: ignore
        self.edit_fontsize_size.setText(self.fontsize)
        self.edit_fontsize_size.setValidator(double_validator)

        fontsize_cont = SimpleContainer(
            [label_fontsize_size, self.edit_fontsize_size]
        )

        label_color_selection = QLabel("Selected Subtrees Color:")
        self.edit_color_sel = ColoredPushButton(color=self.color_of_selection)
        # edit_color_sel.color_change.connect(self._update_selection_color)
        color_of_sel_cont = SimpleContainer(
            [label_color_selection, self.edit_color_sel]
        )
        self.setLayout(layout)
        self.layout().addWidget(nod_size_cont)
        self.layout().addWidget(edge_color_cont)
        self.layout().addWidget(edge_size_cont)
        self.layout().addWidget(fontsize_cont)
        self.layout().addWidget(color_of_sel_cont)
        self.layout().addWidget(SimpleContainer([reset_but, apply_but]))

    # def _update_selection_color(self, color_name: str):
    #     """Update both internal setting and napari highlight color."""
    #     self.color_of_selection = color_name
    #     _update_napari_highlight_color(color_name, self.viewer)

    def reset(self):
        """Resets the colors of the tree graph to default values."""
        # Update napari highlight color to default
        _update_napari_highlight_color(DEFAULT_CANVAS_SETTINGS["color_of_selection"], self.viewer)

        # Use default settings
        settings_to_emit = DEFAULT_CANVAS_SETTINGS.copy()
        self.sig.emit(settings_to_emit)
        self.accept()

    def apply(self):
        """Sets the colors of the tree graph."""
        # Update napari highlight color with the current selection color
        color_name = self.edit_color_sel.color
        self.color_of_selection = color_name
        _update_napari_highlight_color(self.color_of_selection, self.viewer)

        settings_to_emit = {
            "color_of_edges": self.color_of_edges,
            "node_size": self.edit_node_size.text(),
            "lw": self.edit_edge_size.text(),
            "fontsize": self.edit_fontsize_size.text(),
            "color_of_selection": self.color_of_selection,
        }
        
        # Save user preferences
        _save_user_canvas_settings(settings_to_emit)
        
        self.sig.emit(settings_to_emit)
        self.accept()
