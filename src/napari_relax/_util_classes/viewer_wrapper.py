from napari.qt import QtViewer


class QtViewerWrap(QtViewer):
    """QtViewer embedded in a widget, forwarding file drops to napari."""

    def __init__(self, main_viewer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_viewer = main_viewer

    def _qt_open(
        self,
        filenames: list,
        stack: bool,
        plugin: str = None,
        layer_type: str = None,
        **kwargs,
    ):
        """Open dropped files in the main napari viewer."""
        self.main_viewer.window._qt_viewer._qt_open(
            filenames, stack, plugin, layer_type, **kwargs
        )
