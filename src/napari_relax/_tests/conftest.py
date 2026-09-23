"""Shared fixtures for the napari-relax test suite.

Most tests run on a small synthetic LineageTree (see
`make_lineage_tree`) so that expected values can be computed by hand.
"""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
from lineagetree import LineageTree  # noqa: E402
from matplotlib.backend_bases import KeyEvent, MouseEvent  # noqa: E402
from qtpy.QtWidgets import QDialog, QMenu, QMessageBox  # noqa: E402

from napari_relax._reader import layer_preparation  # noqa: E402

# Lineage A: root 1 at t=0, divides at t=2 (node 3) into 4 and 5.
# Lineage B: root 10 at t=0, a single chain without division.
# Lineage C: root 20 appears late (t=2) and divides at t=3 (node 21).
SUCCESSOR = {
    1: [2],
    2: [3],
    3: [4, 5],
    4: [6],
    5: [7],
    6: [8],
    7: [9],
    8: [],
    9: [],
    10: [11],
    11: [12],
    12: [13],
    13: [14],
    14: [15],
    15: [],
    20: [21],
    21: [22, 23],
    22: [24],
    23: [25],
    24: [],
    25: [],
}
TIME = {
    1: 0,
    2: 1,
    3: 2,
    4: 3,
    5: 3,
    6: 4,
    7: 4,
    8: 5,
    9: 5,
    **{10 + t: t for t in range(6)},
    20: 2,
    21: 3,
    22: 4,
    23: 4,
    24: 5,
    25: 5,
}
POS = {
    1: (0, 0, 0),
    2: (0, 0, 1),
    3: (0, 0, 2),
    4: (-5, 0, 3),
    5: (5, 0, 3),
    6: (-5, 0, 4),
    7: (5, 0, 4),
    8: (-5, 0, 5),
    9: (5, 0, 5),
    **{10 + t: (50, 0, t) for t in range(6)},
    20: (100, 0, 2),
    21: (100, 0, 3),
    22: (95, 0, 4),
    23: (105, 0, 4),
    24: (95, 0, 5),
    25: (105, 0, 5),
}
LINEAGE_A = {1, 2, 3, 4, 5, 6, 7, 8, 9}
LINEAGE_B = {10, 11, 12, 13, 14, 15}
LINEAGE_C = {20, 21, 22, 23, 24, 25}
LABELS = {1: "A", 10: "B", 20: "C"}


def make_lineage_tree(
    name="embryo", labels=None, time_offset=0, node_offset=0
):
    """Build the synthetic LineageTree described above.

    Parameters
    ----------
    name : str
        Name of the LineageTree.
    labels : dict, optional
        Labels of the nodes, `LABELS` by default.
    time_offset : int
        Added to every timepoint, to test datasets not starting at 0.
    node_offset : int
        Added to every node ID. A LineageTreeManager refuses trees equal
        to one it already holds, so datasets added to the same manager
        need different IDs or times.
    """
    labels = LABELS if labels is None else labels
    lT = LineageTree(
        successor={
            n + node_offset: [s + node_offset for s in succ]
            for n, succ in SUCCESSOR.items()
        },
        time={n + node_offset: t + time_offset for n, t in TIME.items()},
        starting_time=None,
        pos={n + node_offset: p for n, p in POS.items()},
        name=name,
        labels={n + node_offset: label for n, label in labels.items()},
    )
    lT.time_resolution = 5
    return lT


def add_lt_layer(viewer, lT, name="embryo", **parameters):
    """Add the ReLAX Points layer of a LineageTree to a viewer."""
    data, kwargs, _ = layer_preparation(lT, name, parameters=parameters)[0]
    return viewer.add_points(data, **kwargs)


def points_of(layer, nodes):
    """Return the napari indices of LineageTree nodes."""
    return sorted(layer.metadata["lT2napari"][n] for n in nodes)


def mouse_event(
    canvas,
    ax,
    xdata,
    ydata,
    name="button_press_event",
    button=1,
    dblclick=False,
):
    """Create a matplotlib mouse event at data coordinates of an axes."""
    canvas.draw()
    x, y = ax.transData.transform((xdata, ydata))
    return MouseEvent(name, canvas, x, y, button=button, dblclick=dblclick)


def key_event(canvas, key):
    """Create a matplotlib key press event."""
    return KeyEvent("key_press_event", canvas, key)


@pytest.fixture
def lt():
    return make_lineage_tree()


@pytest.fixture
def viewer(make_napari_viewer):
    return make_napari_viewer()


@pytest.fixture
def lt_layer(viewer, lt):
    return add_lt_layer(viewer, lt)


@pytest.fixture(autouse=True)
def modal_calls(qapp, monkeypatch):
    """Stop modal dialogs and menus from blocking, and record them.

    Tests that need a dialog to return a specific result patch ``exec_``
    of that dialog class themselves, which takes precedence. Depending
    on ``qapp`` also guarantees a QApplication for widgets created
    without ``qtbot``.
    """
    calls = []

    def fake_exec(self, *args, **kwargs):
        calls.append(self)
        return 0

    for cls in (QDialog, QMessageBox, QMenu):
        monkeypatch.setattr(cls, "exec_", fake_exec, raising=False)
        monkeypatch.setattr(cls, "exec", fake_exec, raising=False)
    return calls


@pytest.fixture(autouse=True)
def isolated_plugin_settings(tmp_path, monkeypatch):
    """Keep napari plugin settings (auto-saved on change) in tmp_path.

    Same mechanism as napari's ``plugin_settings`` fixture, without
    blocking plugin discovery.
    """
    from napari import settings

    settings._clear_plugin_settings_cache()
    monkeypatch.setattr(
        settings, "_CFG_PATH", str(tmp_path / "settings" / "settings.yaml")
    )
    yield
    settings._clear_plugin_settings_cache()


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


@pytest.fixture
def rng():
    return np.random.default_rng(0)
