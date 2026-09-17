This component is mainly focused on showcasing quantitative and qualitative features of the dataset by recoloring the dataset's nodes according to their attributes or their progeny.

It is the **Attribute Based Recoloring** entry of the **Lineage tree analysis** widget, with 2 tabs:

- **Clone based Recoloring** recolors any dataset according to the sublineages existing at a specific timepoint.
- **Node based Recoloring** uses precomputed features to recolor both viewers at the node level.

---

## Clone based recoloring
<div class="split-container1">
  <div class = "scrollable-left1" >
<p>
  The <strong>Population Graph</strong> shows the number of cells over time. Using the slider, the user can select a timepoint (red dashed line, with its number of cells in the title) and press <strong>Recolor Clones</strong> to recolor the whole dataset according to the clones existing on this timepoint. For example if the user selects timepoint 2 in the <code>C. elegans</code> demo dataset, two colors will be shown, one for each sublineage in timepoint 2. </p>
  <p>The user can also change the colormap, by interacting with the <strong>Color map</strong> combobox, if they prefer another array of colors. <strong>Reset Coloring</strong> restores the original colors.
</p>

  </div>
  <div class="fixed-right1">
    <img src="../distance_display_componentn.png" alt="My Image"> 
  </div>
</div>

---
## Node based recoloring
<div class="split-container">
  <div class="scrollable-left1">
<p>
    With <strong>Quantitative</strong> selected (qualitative attributes are not supported yet), the user can pick any numeric node attribute of the LineageTree in <strong>Selected attribute</strong>, choose a colormap in <strong>Select Colormap</strong>, and press <strong>Recolor Dataset</strong> to color each node according to its value. <strong>Reset Color of Dataset</strong> restores the original colors.
    <strong>Top</strong>: The configuration screen and the colored Napari viewer. 
    <strong>Bottom</strong>: One lineage that has been recolored is shown on the Lineage Viewer.
    </p>
    <p>
    The user may select how to handle nodes that have no value:
    </p>
    <ol>
      <li><code>Black</code>: If a node has no value, no color, it will be shown in black color.</li>
      <li><code>Propagate from Ancestor</code>: Each node with no value will inherit its value from its ancestor and be colored the same color.</li>
      <li><code>Propagate from Sibling</code>: Each node with no value will get the same value as their sibling if they do have a color. <em>Not implemented yet: selecting it shows a warning.</em></li>
      <li><code>Default Value</code>: More settings are available here, as the user can select a value to color each node that has no color.
        <ol>
          <li><code>Custom Value</code>: The user can input any value in the text field, so these nodes will get this value.</li>
          <li><code>Mean</code>: Each node will be colored with the mean value.</li>
          <li><code>Median</code>: Each node will be colored with the median value.</li>
          <li><code>Min</code>: Each node will be colored with the minimum value.</li>
        </ol>
      </li>
    </ol>



  </div>
  <div class="fixed-right1">
    <img src="../jacqard.png" alt="My Image"> 
  </div>
</div>

---

Go to [Starting page](../index.md)                                           
Go to [Tutorials](../guides/guides.md)