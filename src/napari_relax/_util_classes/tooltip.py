from qtpy.QtWidgets import QPushButton


class TooltipButton(QPushButton):
    def __init__(self, tooltip=""):
        super().__init__()
        self.setText("?")
        self.setFixedSize(30, 30)
        self.setCheckable(False)
        self.setToolTip(tooltip)
        self.toolTip
        self.setChecked(True)
