"""Shared panel shown at the bottom of the Lineage tree analysis widget."""

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
from .._utils import (
    _infer_point_size,
    _select_active_lt_layer,
    _transform_float_value_to_slider_int,
    _transform_slider_int_value_to_float,
)


class CellSize(LayerCorrectorTreeProducer):
    """Point size, layer visibility, tracks and saving tools.

    It is shown under every entry of the Lineage tree analysis widget.

    Parameters
    ----------
    napari_viewer : napari.Viewer
        The napari viewer.
    """

    def add_tracks(self, event):
        """Add a Tracks layer for the LineageTree of the active layer.

        Parameters
        ----------
        event : object
            The button click event, unused.
        """
        active = _select_active_lt_layer(self.viewer)
        if active:
            data = active.metadata["graph_to_create_tracks"]
            data["metadata"] = {"link": active}
            data["blending"] = "translucent"
            data["name"] = active.name + " Tracks"
            self.viewer.add_tracks(
                np.array(active.metadata["data"]),
                **data,
            )

    def reset_slider(self, value=None):
        """Set the point size and move the slider to match it.

        Parameters
        ----------
        value : float, optional
            Size in Points layer units. If None, the size estimated from
            the distances between neighboring cells is used.
        """
        points_layer = _select_active_lt_layer(self.viewer)

        optimal_size = value

        if value is None and points_layer:
            if "size_display_bounds" in points_layer.metadata:
                _, optimal_size, _ = points_layer.metadata[
                    "size_display_bounds"
                ]

            elif "LineageTree" in points_layer.metadata:
                lT = points_layer.metadata["LineageTree"]
                min_size, optimal_size, max_size = _infer_point_size(lT)
                points_layer.metadata["size_display_bounds"] = (
                    min_size,
                    optimal_size,
                    max_size,
                )

        self._changes(None, value=optimal_size)

    def _changes(self, event, value=None):
        """Change the size of one or all LineageTree Points layers.

        Parameters
        ----------
        event : object
            The slider event, unused.
        value : float, optional
            Size in Points layer units. If None, the slider value is
            converted to a size and applied to the active layer, or to all
            layers when "All layers" is ticked.
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
                    and "size_display_bounds" in layer.metadata
                ):
                    min_size, _, max_size = layer.metadata[
                        "size_display_bounds"
                    ]
                    value = _transform_slider_int_value_to_float(
                        self.slider.value(), min_size, max_size
                    )
                    layer.size = value

                    if layer is active_layer:
                        new_size = value

        else:
            new_size = value
            # Update only the active layer
            if active_layer:
                active_layer.size = new_size

            self.slider.blockSignals(True)
            # Update the slider position according to the new size
            min_size, _, max_size = active_layer.metadata[
                "size_display_bounds"
            ]
            self.slider.setValue(
                _transform_float_value_to_slider_int(
                    new_size, min_size, max_size
                )
            )
            self.slider.blockSignals(False)

        # Update tooltip with current size
        self.slider.setToolTip(
            f"Change the size of the spheres on the viewer. Current size {new_size}"
        )

    def see_one_layer(self):
        """Hide every layer except the active one."""
        not_selected = self.viewer.layers - self.viewer.layers.selection
        for layer in not_selected:
            layer.visible = False
        self.viewer.layers.selection.active.visible = True

    def see_all_layers(self):
        """Show every layer."""
        for layer in self.viewer.layers:
            layer.visible = True

    def layer_change(self):
        """Update the panel when the selected layer changes.

        Hides the other layers if "Toggle visibility of other layers" is
        ticked, and moves the size slider to the size of the new layer.
        """
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
            if active_layer and len(active_layer.size) > 0:
                # Currently assuming all sizes are the same
                # TODO: discuss this
                self.reset_slider(value=active_layer.size[0])

    def write_embryo(self):
        """Save the LineageTree of the active layer to the selected file."""
        lT = self.get_lT()
        if lT:
            txt = Path(self.save_widget.value)
            lT.write(str(txt))

    def is_lt_layer(self, layer):
        """Check whether a layer is a Points layer holding a LineageTree.

        Parameters
        ----------
        layer : napari.layers.Layer
            The layer to check.

        Returns
        -------
        bool
            True if the layer holds a LineageTree.
        """
        return (
            isinstance(layer, Points)
            and hasattr(layer, "metadata")
            and "LineageTree" in layer.metadata
        )

    def _update_layer_slider_range(self, layer: Points):
        if "size_display_bounds" not in layer.metadata:
            lT = layer.metadata["LineageTree"]
            min_size, optimal_size, max_size = _infer_point_size(lT)
            layer.metadata["size_display_bounds"] = (
                min_size,
                optimal_size,
                max_size,
            )

    def force_viewer_select_if_lt_layer(self, event):
        """Select a newly added LineageTree layer and set its size range.

        Parameters
        ----------
        event : napari.utils.events.Event
            The layer insertion event.
        """
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
