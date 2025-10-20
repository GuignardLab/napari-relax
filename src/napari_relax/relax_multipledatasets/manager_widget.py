import os
from pathlib import Path

from lineagetree import LineageTree, LineageTreeManager
from magicgui import widgets
from psygnal import Signal
from qtpy import QtCore, QtWidgets
from qtpy.QtWidgets import (
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from .._reader import layer_preparation
from .._util_classes import (
    Containerize,
    LayerCorrectorTreeProducer,
    TimeResDialog,
    TooltipButton,
)


class CrossEmbryo(LayerCorrectorTreeProducer):
    name = "Manager Manipulation"

    send_manager_to_classes = Signal(LineageTreeManager)

    def update_layer_list(self):
        self.layers = {
            layer.metadata.get("name_for_manager"): layer
            for layer in self.viewer.layers
        }

    def save_manager(self):
        file = self.save_manager_widget.value
        self.manager.write(str(file))

    def add_a_new_embryo(self):
        """Adds a new embryo to the manager."""
        for file in self.add_lT_to_manager.line_edit.value.split(", "):
            lT = LineageTree.load(fname=file)
            self.manager.add(lT, name=Path(file).stem)
        self.update_Qlistwidget()
        self.send_manager_to_classes.emit(self.manager)

    def add_a_new_embryo_from_viewer(self):
        pass

    def remove_embryo(self, source, pos):
        """Removes an embryo from the manager"""
        self.manager.remove_embryo(source.itemAt(pos).text())
        self.update_Qlistwidget()
        self.send_manager_to_classes.emit(self.manager)

    def load_a_manager(self):
        """Loads a LineageTreeManager object to the app, so it can be used by napari"""
        file = self.load_ltm_file.line_edit.value
        lTm = LineageTreeManager.load(file)
        self.manager = lTm
        self.update_Qlistwidget()
        self.send_manager_to_classes.emit(self.manager)

    def add_new_layer(self, name=None):
        """Adds the lineatree to the viewer."""
        existing = [
            layer.metadata.get("name_for_manager", "")
            for layer in self.viewer.layers
            if layer.metadata["LineageTree"]
        ]
        if not name:
            for lT_item in self.lineagetree_list.selectedItems():
                if lT_item.text() not in existing:
                    data = layer_preparation(
                        self.manager.lineagetrees[lT_item.text()],
                        path=lT_item.text(),
                    )[0]
                    data[1]["metadata"]["name_for_manager"] = lT_item.text()
                    self.viewer.add_points(data[0], **data[1])
        else:
            for lT_item in name:
                if lT_item.text() not in existing:
                    data = layer_preparation(
                        self.manager.lineagetrees[lT_item.text()],
                        path=lT_item.text(),
                    )[0]
                    data[1]["metadata"]["name_for_manager"] = lT_item.text()
                    self.viewer.add_points(data[0], **data[1])
        self.update_layer_list()

    def create_a_manager(self):
        """Creates a new LineageTreeManager from all existing layers."""
        self.manager = LineageTreeManager()
        layers = [
            layer
            for layer in self.viewer.layers
            if layer.metadata.get("LineageTree")
        ]
        for layer in layers:
            self.manager.add(layer.metadata["LineageTree"], name=layer.name)
            layer.metadata["name_for_manager"] = layer.name
        self.update_Qlistwidget()
        self.send_manager_to_classes.emit(self.manager)
        self.update_layer_list()

    def update_Qlistwidget(self):
        """Function that is called when the lineagetrees in the manager
        object are changed. It replaces the Qlistwidget with a new one
        that has the correct LineageTrees.
        """
        self.lineagetree_list.clear()
        self.lineagetree_list.addItems(
            [f"{key}" for key in self.manager.lineagetrees]
        )
        self.lineagetree_list.update()

    def eventFilter(self, source, event):
        """eventFilter to create context menu for the QListwidget.
        This filter connect the right click to produce a context menu that has 2 actions
        change the time resolution and remove an embryo.

        Args:
            source (_type_): _description_
            event (_type_): _description_

        Returns:
            _type_: _description_
        """
        if (
            isinstance(source, QListWidget)
            and event.type() == QtCore.QEvent.ContextMenu
            and source.itemAt(event.pos())
        ):
            context_menu = QtWidgets.QMenu(self)
            change_tr = QtWidgets.QAction(
                "Change Time Resolution", self.lineagetree_list
            )
            remove_action = QtWidgets.QAction(
                "Remove Embryo", self.lineagetree_list
            )
            context_menu.addAction(change_tr)
            context_menu.addAction(remove_action)

            change_tr.triggered.connect(
                lambda: self.change_time_resolution(source, event.pos())
            )
            remove_action.triggered.connect(
                lambda: self.remove_embryo(source, event.pos())
            )
            context_menu.exec_(event.globalPos())
            return True

        return super().eventFilter(source, event)

    def change_time_resolution(self, source, pos: QtCore.QPoint):
        lt = self.manager.lineagetrees[source.itemAt(pos).text()]
        t_res = TimeResDialog(lt.time_resolution)
        t_res.exec_()
        lt.time_resolution = t_res.value_selected

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)

        self.viewer = napari_viewer
        self.manager = LineageTreeManager()
        self.lineagetree_list = QListWidget()
        self.lineagetree_list.setSelectionMode(QListWidget.MultiSelection)
        self.lineagetree_list.installEventFilter(self)
        self.save_manager_widget = widgets.FileEdit(
            mode="w", value=Path(".").absolute(), filter="*.ltm"
        )
        self.save_manager_button = QPushButton("Save Manager")
        self.save_manager_button.native = self.save_manager_button
        self.save_ltm_container = Containerize(
            [self.save_manager_widget.native, self.save_manager_button.native]
        )
        self.load_ltm_file = widgets.FileEdit(
            value=Path(".").absolute(), filter="*.ltM"
        )
        self.load_manager = QPushButton("Load a Manager")
        self.load_manager.native = self.load_manager
        self.loading_cont = Containerize(
            [self.load_ltm_file.native, self.load_manager.native]
        )
        self.create_manager = QPushButton(
            "Create a Manager from existing layers"
        )

        self.add_lT_to_manager = widgets.FileEdit(
            mode="rm", value=Path(".").absolute(), filter="*.lT"
        )
        self.add_emb = QPushButton("Add LineageTrees")
        self.add_emb.native = self.add_emb
        self.add_emb_container = Containerize(
            [self.add_lT_to_manager.native, self.add_emb.native]
        )
        self.add_layer = QPushButton("Add selected lineageTrees to viewer")
        layout = QVBoxLayout()
        layout.addStretch(1)
        self.setLayout(layout)
        self.layout().addWidget(self.create_manager)
        self.layout().addWidget(QLabel(text="Load a Manager"))
        self.layout().addWidget(self.loading_cont)
        self.layout().addWidget(
            QLabel(text="List of all LineageTrees loaded to the Manager")
        )
        self.layout().addWidget(self.lineagetree_list)
        self.layout().addWidget(
            QLabel(text="Add one or more Embryos to the layers")
        )
        self.layout().addWidget(self.add_layer)
        self.layout().addWidget(
            QLabel(text="Add a new Embryo to an existing Manager")
        )
        self.layout().addWidget(self.add_emb_container)
        self.layout().addWidget(QLabel(text="Save a Manager"))
        self.layout().addWidget(self.save_ltm_container)
        self.save_manager_button.pressed.connect(self.save_manager)
        self.add_layer.pressed.connect(self.add_new_layer)
        self.add_emb.pressed.connect(self.add_a_new_embryo)
        self.load_manager.pressed.connect(self.load_a_manager)
        self.create_manager.pressed.connect(self.create_a_manager)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(
            os.path.join(current_dir, "manager.html"),
            encoding="utf-8",
        ) as f:
            txt = f.read()
        self.node_tooltip = TooltipButton(txt)
        self.node_tooltip.setParent(self)
        self.node_tooltip.move(self.width() - self.node_tooltip.width(), 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.node_tooltip.move(self.width() - self.node_tooltip.width(), 0)
