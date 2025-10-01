"""
This module is an example of a barebones QWidget plugin for napari

It implements the Widget specification.
see: https://napari.org/stable/plugins/guides.html?#widgets

Replace code below according to your needs.
"""

from pathlib import Path

import numpy as np
from magicgui import widgets
from napari.layers import Points
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QPushButton, QSlider, QVBoxLayout

from .._util_classes import (
    Containerize,
    DelayedTooltipEventFilter,
    LayerCorrectorTreeProducer,
)
from .._interaction_bridge import InteractionBridge
from .._utils import (
    _infer_point_size,
    _select_active_lt_layer,
    _transform_float_value_to_slider_int,
    _transform_slider_int_value_to_float,
)

DEFAULT_MIN_POINT_SIZE = 1
DEFAULT_MAX_POINT_SIZE = 2000
DEFAULT_OPTIMAL_POINT_SIZE = 200


class CellSize(LayerCorrectorTreeProducer):
    """
    Changes the size of the Points in Point layer.
    It's added on to all widgets.
    """

    def add_tracks(self, event):
        "Adds the tracks layer of a specific LineageTree points layer."
        active = _select_active_lt_layer(self.viewer)
        if active:
            data = active.metadata["graph_to_create_tracks"]
            data["metadata"] = {"link": active}
            data["blending"] = "translucent"
            self.viewer.add_tracks(
                np.array(active.metadata["data"]),
                **data,
            )

    def reset_slider(self, value=None):
        """Update the slider values after the update button has been pushed.
        The Points layer holding the lineageTree is used to infer the values.
        """
        points_layer = _select_active_lt_layer(self.viewer)
        if points_layer:
            lT = points_layer.metadata["LineageTree"]
            if lT:
                if value is None:
                    _, optimal_size, _ = _infer_point_size(lT)
                else:
                    optimal_size = value
                self._changes(None, value=optimal_size)

    def _changes(self, event, value=None):
        """
        Changes the size of one or more Points layer.
        Note that value must be given in Points layer unit.
        """

        new_size = None
        active_layer = _select_active_lt_layer(self.viewer)

        if value is None:
            layers_to_update = []

            if self.toggle_all.value:
                for layer in self.viewer.layers:
                    if self.is_lt_layer(layer):
                        layers_to_update.append(layer)
            else:
                # Update only the active layer
                if active_layer and self.is_lt_layer(active_layer):
                    layers_to_update.append(active_layer)

            for layer in layers_to_update:
                if (
                    hasattr(layer, "metadata")
                    and "slider_float_range" in layer.metadata
                ):
                    slider_float_range = layer.metadata["slider_float_range"]
                    value = _transform_slider_int_value_to_float(
                        self.slider.value(), *slider_float_range
                    )
                    layer.size = value

                    # Update the original size in the InteractionBridge
                    bridge = InteractionBridge.get_bridge_for_layer(layer)
                    if bridge:
                        bridge.update_original_size(value)

                    if layer is active_layer:
                        new_size = value

        else:
            new_size = value
            # Update only the active layer
            if active_layer:
                active_layer.size = new_size

                # Update the original size in the InteractionBridge
                bridge = InteractionBridge.get_bridge_for_layer(active_layer)
                if bridge:
                    bridge.update_original_size(new_size)

            self.slider.blockSignals(True)
            # Update the slider position according to the new size
            self.slider.setValue(
                _transform_float_value_to_slider_int(
                    new_size, *active_layer.metadata["slider_float_range"]
                )
            )
            self.slider.blockSignals(False)

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
        currently_selected_layer_names = [
            layer.name for layer in self.viewer.layers.selection
        ]
        if (
            len(currently_selected_layer_names) == 1
            and currently_selected_layer_names
            != self.currently_selected_layer_names
        ):
            self.currently_selected_layer_names = (
                currently_selected_layer_names
            )
            if self.vis_button.value:
                self.see_one_layer()

            # I don't think the lines below are useful, because
            # if vis_button is not pressed in the first place,
            # there is no reason to make invisible layers visible again.
            # else:
            #     self.see_all_layers()

            # Update the slider values according to the new active layer
            active_layer = _select_active_lt_layer(self.viewer)
            if (
                active_layer
                and len(active_layer.size) > 0
            ):
                # Currently assuming all sizes are the same
                # TODO: discuss this
                self.reset_slider(value=active_layer.size[0])

    def write_embryo(self):
        lT = self.get_lT()
        if lT:
            txt = Path(self.save_widget.value)
            lT.write(str(txt))

    def is_lt_layer(self, layer):
        return (
            isinstance(layer, Points)
            and hasattr(layer, "metadata")
            and "LineageTree" in layer.metadata
        )

    def _update_layer_slider_range(self, layer: Points):
        lT = layer.metadata["LineageTree"]
        min_size, _, max_size = _infer_point_size(lT)
        layer.metadata["slider_float_range"] = (min_size, max_size)

    def force_viewer_select_if_lt_layer(self, event):
        layer = event.value
        if self.is_lt_layer(layer):
            self._update_layer_slider_range(layer)
            self.viewer.layers.selection.active = layer

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)

        event_filt = DelayedTooltipEventFilter()
        self.installEventFilter(event_filt)
        self.viewer = napari_viewer
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        ### Slider: Change size of spheres
        self.count = widgets.Label(value="Size of spheres.")
        self.slider = QSlider()
        self.slider.setOrientation(Qt.Orientation.Horizontal)
        self.slider.setTickInterval(1)
        self.slider.setContentsMargins(0, 0, 0, 0)

        # The slider always has values between 1 and 100, but these values
        # are mapped to a float range that can be changed according to the
        # heuristics on the nearest neighbor distances of the lineageTree
        self.slider.setMinimum(1)
        self.slider.setMaximum(100)
        self.slider.setValue(20)
        # slider_float_range is used to store the actual float range
        self.slider_float_range = (
            DEFAULT_MIN_POINT_SIZE,
            DEFAULT_MAX_POINT_SIZE,
        )
        self.slider.valueChanged.connect(self._changes)

        ### Button: reset slider values according to current layer
        reset_slider_button = widgets.PushButton(text="Reset slider")
        reset_slider_button.clicked.connect(lambda event: self.reset_slider())

        ### Checkbox: Change size of all layers or only one
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

        ### Button: Toggle visibility of other layers
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
        self.vis_button.clicked.connect(self.layer_change)

        ### Button: Add tracks layer
        track_button = widgets.PushButton(text="Add Tracks")
        track_button.clicked.connect(self.add_tracks)

        ### Save LineageTree widget
        self.save_widget = widgets.FileEdit(
            mode="w", value=Path(".").absolute(), filter="*.lT"
        )
        self.save_button = QPushButton("Save LineageTree")
        self.save_button.native = self.save_button
        self.save_button.clicked.connect(self.write_embryo)

        # Final assembly
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        cont = Containerize(
            [
                self.count.native,
                self.slider,
                reset_slider_button.native,
                all_container.native,
            ]
        )
        cont.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(cont)

        self.tracks_and_vis_cont = Containerize(
            [vis_container.native, track_button.native]
        )
        self.tracks_and_vis_cont.layout().setContentsMargins(0, 0, 0, 0)
        self.tracks_and_vis_cont.layout().setSpacing(0)
        self.layout().addWidget(self.tracks_and_vis_cont)

        self.save_container = Containerize(
            [self.save_widget.native, self.save_button.native]
        )
        self.save_container.layout().setContentsMargins(0, 15, 0, 0)
        self.save_container.layout().setSpacing(0)
        self.layout().addWidget(self.save_container)

        self.currently_selected_layer_names = [
            layer.name for layer in self.viewer.layers.selection
        ]

        self.viewer.layers.selection.events.active.connect(self.layer_change)

        for layer in self.viewer.layers:
            if self.is_lt_layer(layer):
                self._update_layer_slider_range(layer)

        self.viewer.layers.events.inserted.connect(
            self.force_viewer_select_if_lt_layer
        )

        self.reset_slider()
