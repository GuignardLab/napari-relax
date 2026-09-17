# Architecture

This page gives contributors an overview of how ReLAX is organized. The [API reference](api/io.md) is generated from the docstrings.

---

## Plugin Contributions

Everything napari loads from ReLAX is declared in `src/napari_relax/napari.yaml`:

| Contribution | Python object | Notes |
| --- | --- | --- |
| Reader | `napari_relax._reader:napari_get_reader` | `.lT`, `.lt`, `.LT`, `.mastodon`, `.xml`, `.bmf` |
| Writer | `napari_relax._writer:write_single_image` | Points layers, saved as `.lT` |
| Widget *Lineage tree analysis* | `napari_relax._widgets:LineageTreeAnalysisWidget` | Single dataset |
| Widget *Cross Lineagetree comparison* | `napari_relax._widgets:CrossEmbryoComparisonWidget` | Several datasets |
| Sample data | `napari_relax.demo_data:load_demo`, `load_celegans` | Listed in `demo_data/datasets.json` |
| Settings | `configurations.progeny_canvas` | Node size, edge size and font size of the Lineage Viewer, read with `napari.settings.get_plugin_settings` (napari 0.9 or newer) |

---

## Where the Data Lives

The reader turns a file into a LineageTree, then `layer_preparation` builds a **Points** layer. Everything the widgets need is stored in the layer's `metadata`:

| Key | Content |
| --- | --- |
| `LineageTree` | The LineageTree object, including its labels and cached comparisons |
| `lT2napari`, `napari2lT` | Mapping between LineageTree node IDs and point indices |
| `default_colors` | Original point colors, used by every *Reset* button |
| `graphs` | Graph and node positions of each lineage, for the Lineage Viewer |
| `graph_to_create_tracks` | Data used by *Add Tracks* |
| `size_display_bounds` | Minimal, optimal and maximal point sizes |
| `lineage_tree_id` | Identifier shared with the companion layers |
| `name_for_manager` | Name of the dataset in a cross-dataset manager |

Companion layers (the `<name>_mesh` Surface layer and Tracks layers) point back to their Points layer with `metadata["link"]`. Widgets call `_select_active_lt_layer` to get the Points layer of whatever layer is selected.

---

## Dock Widgets

Both dock widgets subclass `ReLAXWidget`, which stacks the entries of a package behind a combobox:

```
ReLAXWidget
├── combobox + stack of <package>.__all_widgets__
└── <package>.__overall_widget__, shown under every entry
```

| Dock widget | Package | Entries (`name`) | Shared panel |
| --- | --- | --- | --- |
| `LineageTreeAnalysisWidget` | `lineage_tree_analysis` | `ProgenySelection` (*Explore and Relabel*), `ComparisonsHandler` (*Distance Calculation*), `RecoloringWidget` (*Attribute Based Recoloring*) | `CellSize` |
| `CrossEmbryoComparisonWidget` | `relax_multipledatasets` | `CrossEmbryo` (*Manager Manipulation*), `CrossHandler` (*Cross Distance Calculation*) | none |

Every entry subclasses `LayerCorrectorTreeProducer`, which provides `get_lT()`, `val_finder()` and `sub_points_selector()`. The class attribute `name` is the label shown in the combobox; `_widgets.py` also uses it to connect entries to each other:

- a label change in *Explore and Relabel* refreshes the root list and clustermap of *Distance Calculation*;
- recoloring in *Attribute Based Recoloring* redraws the Lineage Viewer;
- *Manager Manipulation* sends the manager to *Cross Distance Calculation* whenever it changes.

---

## Interaction Bridge

`InteractionBridge` (in `_interaction_bridge.py`) exists once per Points layer. Through one adapter per layer type (Points, Surface, Tracks), it applies selections and visibility changes to all the layers of a dataset at once, and stores the state of the widgets for that dataset (slider position, selected subtree, visibility) so it can be restored when the user switches layers.

---

## Long Computations

Comparisons run in napari `thread_worker`s (`ConfigurationPanel.thread_worker` and `CrossConfig.roots_selector`) that yield their results after each timepoint. `ComparisonsHandler` and `CrossHandler` start the workers, update the clustermap as results arrive, and drive the progress bar.

---

## In-App Help

Each entry has a **?** button (`TooltipButton`) showing an HTML file stored next to its module, for example `comparison_widget/config.html`. When a user-facing page of this documentation changes, update the matching HTML file too.
