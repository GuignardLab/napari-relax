# Opening a Dataset

Importing data is one of the most important aspects of this plugin. All the supported formats can be easily opened using **Drag and Drop** onto the napari window, or with **File>Open File(s)...**.
If there is no available data, the user may use one of the sample datasets the plugin comes with: **File>Open Sample>ReLAX>demo lineageTree dataset** or **C. elegans dataset** (see [Quick Start](../quick_start/q_start.md)).

---

### 1. Check the Format

| Format | Extension | Notes |
| --- | --- | --- |
| LineageTree | `.lT` | Native format. Also stores the labels and comparisons made in ReLAX. |
| MaMuT or ASTEC | `.xml` | ReLAX asks which of the two tools produced the file. |
| Mastodon | `.mastodon` | Mastodon project file. |
| BMF | `.bmf` | |

LineageTree can read more formats, for example CSV, TGMM XML or SWC files. To open one of them in ReLAX, convert it to `.lT` first:

```python
from lineagetree import read_from_csv

lT = read_from_csv("tracks.csv")
lT.write("tracks.lT")
```

The [LineageTree loaders](https://guignardlab.github.io/LineageTree/loaders/) documentation lists all readers and their options.

---

### 2. Choose the Loader (`.xml` only)

When several loaders can read the file, a **lineagetree data type selection** window asks the user to *select the method used to produce the dataset*.
Tick the tool that produced the file: **MaMuT XML loader** or **ASTEC XML loader**. Closing the window without choosing stops the import.

---

### 3. Set the Loading Parameters

Every file then opens a **Loading Parameters** window:

- **Time resolution** (mins): the time between two consecutive timepoints, pre-filled with the value stored in the dataset. The [Manager](../cross+comparison/manager.md) uses it to align datasets acquired at different rates.
- **Resave dataset with new time resolution**: writes the dataset with the new time resolution as a `.lT` file. An opened `.lT` file is overwritten; for other formats, `.lT` is added to the file name (`embryo.xml` becomes `embryo.xml.lT`).
- **Rescale Dataset**: divides all positions by the largest distance between two cells of the dataset, so that datasets with different spatial units appear at a similar scale.
- **Filter Dataset**: hides small lineages from the [Lineage Viewer](../explore_relabel/explore_relabel.md). With a value *n* above 0, only lineages with at least *(number of timepoints) / n* nodes are listed; 0 keeps every lineage. All cells are still shown in the napari viewer.

Press **Ok** to load the dataset or **Cancel** to abort.

---

### 4. Start Exploring

Loading a dataset adds:

- a **Points** layer named after the file, with one point per cell and timepoint, colored by lineage;
- a **Surface** layer named `<file name>_mesh` if the dataset contains cell meshes. It is linked to the Points layer.

Select the Points layer and open **Plugins>Lineage tree analysis** to explore it with the [Lineage Viewer](../explore_relabel/explore_relabel.md).

---

### Troubleshooting

- **The file is not offered to ReLAX**: check that its extension is one of the supported ones above, or convert it to `.lT`.
- **"Please select one reader function."**: the loader window was closed without choosing a loader. Open the file again and tick one.
- **Ok does nothing in the Loading Parameters window**: the time resolution must be a number.
