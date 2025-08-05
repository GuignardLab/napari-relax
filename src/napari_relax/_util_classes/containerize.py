from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)


class containerize(QWidget):
    """
    Places a list of widgets on horizontal/vertical containers.
    """

    def __init__(self, widget_list, horizontal=True, align=False, **kwargs):
        super().__init__(**kwargs)
        layout = QHBoxLayout() if horizontal else QVBoxLayout()
        alignment = Qt.AlignVCenter if horizontal else Qt.AlignHCenter
        for widget in widget_list:
            if align:
                layout.addWidget(widget, alignment=alignment)
            else:
                layout.addWidget(widget)

        self.setLayout(layout)
