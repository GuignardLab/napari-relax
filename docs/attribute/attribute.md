This component is mainly focused on showcasing quantitative and qualitative features of the dataset by recoloring the dataset's nodes according to their attributes or their progeny.

There are 2 sections:

- One is for recoloring any dataset according to the number of sublineages existing in a specific timepoint
- The other is about using precomputed features to recolor both viewers on n node level.

---

These two components:

## Clone based recoloring
<div class="split-container1">
  <div class = "scrollable-left1" >
<p>
  Using the slider, the user can select a timepoint in the dataset and recolor the whole dataset according to the number of clones existing on this timepoint. For example if the user selects timepoint 2 in the <code>demo C. Elegans</code> dataset, two colors will be shown, one for each sublineage in timepoint 2. </p>
  <p>The user can also change the colormap, by interactring with the combobox, if they prefer an other array of colors.
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
    The user can select any quantitative attribute and recolor it according to its value.
    <strong>Top</strong>: The configuration screen and the colored Napari viewer. 
    <strong>Bottom</strong>: One lineage that has been recolored is shown on the Lineage Viewer.
    </p>
    <p>
    The user may select how to handle nodes that have no value:
    </p>
    <ol>
      <li><code>Black</code>: If a node has no value, no color, it will be shown in black color.</li>
      <li><code>Propagate from Ancestor</code>: Each node with no value will inherit its value from its ancestor and be colored the same color.</li>
      <li><code>Propagate from Sibling</code>: Each node with no value will get the same value as their sibling if they do have a color.</li>
      <li><code>Default Value</code>: More settings are available here, as the user can select a value to color each node that has no color.
        <ol>
          <li><code>Custom Value</code>: The user can input any value, so these nodes will get this value.</li>
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