from qtpy.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)


class containerize(QWidget):
    """
    Places a list of widgets on horizontal/vertical containers.
    """

    def __init__(self, widget_list, horizontal=True, **kwargs):
        super().__init__(**kwargs)
        layout = QHBoxLayout() if horizontal else QVBoxLayout()
        for widget in widget_list:
            layout.addWidget(widget)
        self.setLayout(layout)
