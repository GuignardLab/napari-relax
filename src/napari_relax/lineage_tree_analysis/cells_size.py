"""
This module is an example of a barebones QWidget plugin for napari

It implements the Widget specification.
see: https://napari.org/stable/plugins/guides.html?#widgets

Replace code below according to your needs.
"""

from typing import TYPE_CHECKING

import numpy as np
from magicgui import widgets
from napari.layers import Points
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QSlider, QVBoxLayout

from .._util_classes import (
    Layer_corrector_Tree_Producer,
    containerize,
    delayedtooltipeventfilter,
)
from .._utils import (
    _select_correct_layer,
    _transform_float_value_to_slider_int,
    _transform_slider_int_value_to_float,
    _infer_point_size
)
    
DEFAULT_MIN_POINT_SIZE = 1
DEFAULT_MAX_POINT_SIZE = 2000
DEFAULT_OPTIMAL_POINT_SIZE = 200

class CellSize(Layer_corrector_Tree_Producer):
    """
    Changes the size of the Points in Point layer.
    It's added on to all widgets.
    """

    def add_tracks(self, event):
        "Adds the tracks layer of a specific lineageTree points layer."
        active = _select_correct_layer(self, Points)
        if active:
            data = active.metadata["graph_to_create_tracks"]
            data["metadata"] = {"link": active}
            data["blending"] = "translucent"
            self.viewer.add_tracks(
                np.array(active.metadata["data"]),
                **data,
            )
    
    def _get_lT_from_layer(self):
        point_layer = _select_correct_layer(self, Points)
        if point_layer and hasattr(point_layer, "metadata") and "lineageTree" in point_layer.metadata:
            return point_layer.metadata["lineageTree"]
        return None
    
    def update_slider(self):
        """Update the slider values after the update button has been pushed.
        The Points layer holding the lineageTree is used to infer the values.
        """
        lT = self._get_lT_from_layer()
        if lT:
            min_size, optimal_size, max_size = _infer_point_size(lT)
            self.slider_float_range = (min_size, max_size)
        else: # reset to default values
            self.slider_float_range = (
                DEFAULT_MIN_POINT_SIZE,
                DEFAULT_MAX_POINT_SIZE,
            )
            optimal_size = _transform_slider_int_value_to_float(
                self.slider.value(), *self.slider_float_range
            )
        self._changes(None, value=optimal_size)

    def _changes(self, event, value=None):
        """
        Changes the size of one or more Points layer.
        """
        # Determine the new size using a more pythonic approach
        new_size = value or _transform_slider_int_value_to_float(
            self.slider.value(), *self.slider_float_range
        )

        # Apply size changes based on toggle state
        if self.toggle_all.value:
            for layer in self.viewer.layers:
                if isinstance(layer, Points):
                    layer.size = new_size
        else:
            # Update only the active layer
            active_layer = _select_correct_layer(self, Points)
            if active_layer is None:
                return
            active_layer.size = new_size
        
        # Update slider position if value was provided externally
        if value is not None:
            self.slider.setValue(
                _transform_float_value_to_slider_int(
                    new_size, *self.slider_float_range
                )
            )
        
        # Update tooltip with current size
        self.slider.setToolTip(
            f"Change the size of the spheres on the viewer. Current size {new_size}"
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

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)
        event_filt = delayedtooltipeventfilter()
        self.installEventFilter(event_filt)
        self.viewer = napari_viewer
        layout = QVBoxLayout()
        layout.addStretch(1)
        self.setLayout(layout)
        
        # Slider: Change size of spheres
        self.count = widgets.Label(value="Size of spheres.")
        self.slider = QSlider()
        self.slider.setOrientation(Qt.Orientation.Horizontal)
        self.slider.setTickInterval(1)
        self.slider.setMinimum(1)
        self.slider.setMaximum(100)
        self.slider.setValue(20)
        self.slider_float_range = (
            DEFAULT_MIN_POINT_SIZE,
            DEFAULT_MAX_POINT_SIZE,
        )
        self.slider.valueChanged.connect(self._changes)

        # Button: update slider values according to current layer
        update_button = widgets.PushButton(text="Update slider")
        update_button.clicked.connect(self.update_slider)

        # Checkbox: Change size of all layers or only one
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

        # Button: Toggle visibility of other layers
        self.vis_button = widgets.CheckBox(value=False)
        vis_container = widgets.Container(
            widgets=[
                widgets.Label(value="Toggle visibility of other layers"),
                self.vis_button,
            ],
            layout="horizontal",
            labels=False,
        )
        self.vis_button.clicked.connect(self.layer_change)

        # Button: Add tracks layer
        track_button = widgets.PushButton(text="Add Tracks")

        # Assembly
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().addWidget(
            containerize(
                [self.count.native, self.slider, update_button.native, all_container.native]
            )
        )

        self.tracks_and_vis_cont = containerize(
            [vis_container.native, track_button.native]
        )

        self.layout().addWidget(self.tracks_and_vis_cont)
        track_button.clicked.connect(self.add_tracks)
        self.viewer.layers.selection.events.connect(self.layer_change)

        self.update_slider()

