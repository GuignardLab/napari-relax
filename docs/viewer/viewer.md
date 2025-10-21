<p style="text-align: justify;">

The <a href="https://napari.org/stable/tutorials/fundamentals/quick_start.html#napari-quick-start" target="_blank">Napari standard viewer</a>  is a crucial part of this plugin, making the visualization of any tracking dataset quick and hassle free. Using the viewer, **multiple datasets** may be loaded simultaneously. These datasets may be interacted with as it is described in the napari documentation.
</p>

<p style="text-align: justify;">

Usually, the datasets loaded overlap with each other, so it's recommended to use the grid mode <b>(Ctrl+G)</b> to remove overlapping or hide all the other layers. The user may manually turn on/off the visibility of layers or use alt+left click on the layer of interest to hide every other layer.
</p>

For this plugin the Points Layer is the most common and important type of layer, so it may be useful to read napari's [documentation](https://napari.org/stable/howtos/layers/points.html) on that. The most important controls will be shown on this page.

![viewer](./viewer.png)

## Important Napari Viewer controls panel:

1. **Napari Terminal**: Open the Napari integrated terminal, extremely useful for quick modifications of the dataset (rotation, translation, scaling), however its not recommended for users with no coding experience.

- **3-D viewer**: Toggle 3-D view, essential for navigating 3-D/4D datasets **(Ctrl+Y)**.
- **Grid view**: The grid view will place datasets in different views that are still contolled with the same controls, it is only important if multiple datasets are shown simultaneously on viewer, which overlap **(Ctrl+G)**.
- **Napari Viewer**: The datasets imported will be shown on this viewer, and its visualization and navigation capailities are harnessed throughout the whole plugin. Some **important buttons**:
    - Drag Left Click: Rotate the dataset.
    - Shift Left Click: Move the dataset
    - Scroll: Zoom in and out
    - **Shift Right Click**: Select one node. When a node is selected the Lineage Viewer will also show the correspnding lineage on the [Lineage Viewer](../explore_relabel/explore_relabel.md). 

Using the time slider on the Napari Viewer will also show the corresponding timepoint on the [Lineage Viewer](../explore_relabel/explore_relabel.md). 
