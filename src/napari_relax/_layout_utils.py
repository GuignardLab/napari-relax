"""
Simplified layout utilities to replace Containerize.
Uses standard Qt layouts with helper functions.
"""

from qtpy.QtWidgets import QHBoxLayout, QLayout, QVBoxLayout, QWidget


def create_horizontal_container(
    widgets: list[QWidget], parent: QWidget = None
) -> QWidget:
    """
    Create a widget with horizontal layout containing the given widgets.

    Args:
        widgets: list of widgets to add to the container
        parent: Optional parent widget

    Returns:
        Container widget with horizontal layout
    """
    container = QWidget(parent)
    layout = QHBoxLayout()
    container.setLayout(layout)

    for widget in widgets:
        layout.addWidget(widget)

    return container


def create_vertical_container(
    widgets: list[QWidget], parent: QWidget = None
) -> QWidget:
    """
    Create a widget with vertical layout containing the given widgets.

    Args:
        widgets: list of widgets to add to the container
        parent: Optional parent widget

    Returns:
        Container widget with vertical layout
    """
    container = QWidget(parent)
    layout = QVBoxLayout()
    container.setLayout(layout)

    for widget in widgets:
        layout.addWidget(widget)

    return container


def add_widgets_to_layout(layout: QLayout, widgets: list[QWidget]) -> None:
    """
    Add multiple widgets to an existing layout.

    Args:
        layout: Layout to add widgets to
        widgets: list of widgets to add
    """
    for widget in widgets:
        layout.addWidget(widget)


class SimpleContainer(QWidget):
    """
    Simplified replacement for Containerize class.
    Provides same functionality with cleaner interface.
    """

    def __init__(
        self,
        widgets: list[QWidget],
        horizontal: bool = True,
        parent: QWidget = None,
    ):
        """
        Create a container with the specified layout.

        Args:
            widgets: list of widgets to add
            horizontal: If True, use horizontal layout; if False, use vertical
            parent: Optional parent widget
        """
        super().__init__(parent)

        # Create appropriate layout
        layout = QHBoxLayout() if horizontal else QVBoxLayout()
        self.setLayout(layout)

        # Add all widgets
        for widget in widgets:
            layout.addWidget(widget)
