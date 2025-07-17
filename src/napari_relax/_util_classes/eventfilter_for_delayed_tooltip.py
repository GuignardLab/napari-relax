from qtpy.QtCore import QEvent, QObject, QTimer
from qtpy.QtWidgets import QToolTip


class delayedtooltipeventfilter(QObject):
    """Event filter for showing a tooltip with a delay
    Easily installable in any QObject by QObject.installEventFilter(delayedtooltipeventfilter)

    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.delay = 500
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.tooltip_text = ""
        self.widget = None
        self.pos = None
        self.timer.timeout.connect(self.show_tooltip)

    def show_tooltip(self):
        if self.tooltip_text:
            QToolTip.showText(self.pos, self.tooltip_text, self.widget)

    def eventFilter(self, a0: QObject, a1: QEvent) -> bool:
        if a1.type() == QEvent.ToolTip:
            self.widget = a0
            self.tooltip_text = a0.toolTip()
            self.pos = a1.globalPos()
            self.timer.start(self.delay)
            return True
        elif a1.type() == QEvent.Leave:
            self.timer.stop()
            QToolTip.hideText()
            self.tooltip_text = ""
            self.widget = None
            self.pos = None
        return super().eventFilter(a0, a1)
