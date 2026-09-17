# Adding a Widget

New features usually become a new entry of one of the two dock widgets. See [Architecture](architecture.md) for how entries are loaded.

---

### 1. Create the Widget Class

Subclass `LayerCorrectorTreeProducer` in `lineage_tree_analysis` (single dataset) or `relax_multipledatasets` (several datasets). For example, `src/napari_relax/lineage_tree_analysis/my_widget.py`:

```python
"""My Widget entry of the Lineage tree analysis widget."""

from qtpy.QtWidgets import QVBoxLayout

from .._util_classes import LayerCorrectorTreeProducer


class MyWidget(LayerCorrectorTreeProducer):
    """One-line summary of what the widget does.

    Parameters
    ----------
    napari_viewer : napari.Viewer
        The napari viewer.
    """

    name = "My Widget"  # label in the combobox

    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)
        self.setLayout(QVBoxLayout())
        self.viewer.layers.selection.events.active.connect(self.layer_change)

    def layer_change(self, event):
        """Update the widget for the LineageTree of the new active layer."""
        lT = self.get_lT()
        if lT is None:
            return
        ...
```

Use `self.get_lT()` to read the LineageTree of the selected dataset, and the layer metadata described in [Architecture](architecture.md#where-the-data-lives) to map nodes to points.

---

### 2. Register It

Add the class to `__all_widgets__` in the package `__init__.py`. The order of the tuple is the order of the combobox.

To react to another entry, connect signals in the matching `ReLAXWidget` subclass in `_widgets.py`, using `self.widget_dictionary["<name>"]`.

---

### 3. Add In-App Help (Optional)

Write a short HTML file next to the module and show it with a `TooltipButton`, as the existing entries do. HTML files are included in the package automatically.

---

### 4. Document It

- Write numpy-style docstrings. `ruff` checks them (rule set `D`) when `pre-commit` runs.
- Add a user page under `docs/` and list it in the `nav` of `mkdocs.yml`.
- Add the module to the matching page of the [API reference](api/io.md) if it is not already covered.
- Preview with `mkdocs serve`; pull requests fail if `mkdocs build --strict` reports a warning.

---

### 5. Test It

Tests live in `src/napari_relax/_tests` and run with `pytest` (or `tox` for all Python versions). napari provides the `make_napari_viewer` fixture to create a viewer in tests.
