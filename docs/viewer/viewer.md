<p style="text-align: justify;">

The <a href="https://napari.org/stable/tutorials/fundamentals/quick_start.html#napari-quick-start" target="_blank">Napari Viewer</a>  is a crucial part of this plugin, making the visualization of any tracking dataset quick and easy. Using the viewer, <b>multiple datasets</b> may be loaded simultaneously and can be interacted with using the viewer.
</p>

<p style="text-align: justify;">

If multiple datasets are imported into napari they will usually overlap with each other, thus it's recommended to use the grid mode <b>(Ctrl+G)</b> to place all existing layers in a grid. The user may manually turn on/off the visibility of layers or use alt+left click on the layer of interest to hide every other layer.
</p>

---

## Napari Viewer controls

For this plugin the ```Points Layer``` is the most common and important type of layer, so it may be useful to read napari's [documentation](https://napari.org/stable/howtos/layers/points.html) on that. The most important controls will be shown on this page.

<div class="split-container">
  <div class="scrollable-left1">

<ol>
<li><strong>Napari Terminal</strong>: Open the Napari integrated terminal.</li>
<li><strong>3-D viewer</strong>: Toggle 3-D view, essential for navigating 3-D/4D datasets <strong>(Ctrl+Y)</strong>.</li>
<li><strong>Grid view</strong>: The grid view will place datasets in different views that are still controlled with the same controls, it is only important if multiple datasets are shown simultaneously on viewer, which overlap <strong>(Ctrl+G)</strong>.</li>
<li><strong>Napari Viewer</strong>: The datasets imported will be shown on this viewer, and its visualization and navigation capabilities are harnessed throughout the whole plugin. Some <strong>important buttons</strong>:
    <ul>
    <li>Drag Left Click: Rotate the dataset.</li>
    <li>Shift Left Click: Move the dataset.</li>
    <li>Scroll: Zoom in and out.</li>
    <li><strong>Shift Right Click</strong>: Select one node. When a node is selected the Lineage Viewer will also show the corresponding lineage on the <a href="../../explore_relabel/explore_relabel/">Lineage Viewer</a>.</li>
    </ul>
</li>
</ol>

<p>Using the time slider on the Napari Viewer will also show the corresponding timepoint, as a grey line, on the <a href="../../explore_relabel/explore_relabel/">Lineage Viewer</a>.</p>

  </div>
  <div class="fixed-right">
    <img src="../viewer.png" alt="My Image"> 
  </div>
</div>

---

Go to [Starting page](../index.md)                                           
Go to [Tutorials](../guides/guides.md)