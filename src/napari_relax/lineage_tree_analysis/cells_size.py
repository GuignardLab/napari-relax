"""
This module is an example of a barebones QWidget plugin for napari

It implements the Widget specification.
see: https://napari.org/stable/plugins/guides.html?#widgets

Replace code below according to your needs.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from magicgui import widgets
from napari.layers import Points
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QPushButton, QSlider, QVBoxLayout

from .._util_classes import (
    LayerCorrectorTreeProducer,
    Containerize,
    DelayedTooltipEventFilter,
)
from .._utils import _select_correct_layer

if TYPE_CHECKING:
    pass


class CellSize(LayerCorrectorTreeProducer):
    """
    Changes the size of the Points in Point layer.
    It's added on to all widgets.
    """

    def add_tracks(self, event):
        "Adds the tracks layer of a specific LineageTree points layer."
        active = _select_correct_layer(self, Points)
        if active:
            data = active.metadata["graph_to_create_tracks"]
            data["metadata"] = {"link": active}
            data["blending"] = "translucent"
            self.viewer.add_tracks(
                np.array(active.metadata["data"]),
                **data,
            )

    def _changes(self, event):
        """
        Changes the size of one or more Points layer.
        """
        if self.toggle_all.value:
            for layer in self.viewer.layers:
                if isinstance(layer, Points):
                    new_size = self.slider.value()  # type: ignore
                    layer.size = new_size
        else:
            active_layer = _select_correct_layer(self, Points)
            if active_layer is None:
                return
            new_size = self.slider.value()  # type: ignore
            active_layer.size = new_size
        self.slider.setToolTip(
            f"Change the size of the spheres on the viewer. Current size {self.slider.value()}"
        )

    def see_one_layer(self):
        """Button that turns all other layers invisible in the napari viewer"""
        not_selected = self.viewer.layers - self.viewer.layers.selection
        for layer in not_selected:
            layer.visible = False
        self.viewer.layers.selection.active.visible = True

    def see_all_layers(self):
        """Button to see all layers, reverse of see_one_layer"""
        for layer in self.viewer.layers:
            layer.visible = True

    def layer_change(self):
        """Activated when the user changes layers, it updates the ui"""
        if len(self.viewer.layers.selection) == 1:
            if self.vis_button.value:
                self.see_one_layer()
            else:
                self.see_all_layers()

    def write_embryo(self):
        lT = self.get_lT()
        if lT:
            txt = Path(self.save_widget.value)
            lT.write(str(txt))

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)
        event_filt = DelayedTooltipEventFilter()
        self.installEventFilter(event_filt)
        self.viewer = napari_viewer
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        self.vis_button = widgets.CheckBox(value=False)
        vis_container = widgets.Container(
            widgets=[
                widgets.Label(value="Toggle visibility of other layers"),
                self.vis_button,
            ],
            layout="horizontal",
            labels=False,
        )
        vis_container.native.layout().setContentsMargins(0, 0, 0, 0)
        self.toggle_all = widgets.Checkbox(value=False)

        all_container = widgets.Container(
            widgets=[
                widgets.Label(value="All layers"),
                self.toggle_all,
            ],
            layout="horizontal",
            labels=False,
        )
        all_container.tooltip = "Change the size of all layers instead of only changing the size of only one layer."
        self.save_widget = widgets.FileEdit(
            mode="w", value=Path(".").absolute(), filter="*.lT"
        )
        self.save_button = QPushButton("Save LineageTree")
        self.save_button.native = self.save_button
        self.save_container = Containerize(
            [self.save_widget.native, self.save_button.native]
        )
        self.slider = QSlider()
        self.slider.setOrientation(Qt.Orientation.Horizontal)
        self.slider.setTickInterval(1)
        self.slider.setMinimum(0)
        self.slider.setMaximum(1000)
        self.slider.setValue(200)
        self.slider.setContentsMargins(0, 0, 0, 0)
        track_button = widgets.PushButton(text="Add Tracks")
        self.count = widgets.Label(value="Size of spheres.")
        self.slider.setToolTip(
            f"Change the size of the spheres on the viewer. Current size {self.slider.value()}"
        )
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        cont = Containerize(
            [self.count.native, self.slider, all_container.native]
        )

        self.tracks_and_vis_cont = Containerize(
            [vis_container.native, track_button.native]
        )

        cont.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(cont)
        self.tracks_and_vis_cont.layout().setContentsMargins(0, 0, 0, 0)
        self.tracks_and_vis_cont.layout().setSpacing(0)
        self.layout().addWidget(self.tracks_and_vis_cont)
        self.save_container.layout().setContentsMargins(0, 15, 0, 0)
        self.save_container.layout().setSpacing(0)
        self.layout().addWidget(self.save_container)

        track_button.clicked.connect(self.add_tracks)
        self.vis_button.clicked.connect(self.layer_change)
        self.viewer.layers.selection.events.connect(self.layer_change)
        self.save_button.clicked.connect(self.write_embryo)
        self.slider.valueChanged.connect(self._changes)
