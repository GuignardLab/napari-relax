This component is mainly focused on showcasing quantitative and qualitative features of the dataset by recoloring the dataset or its lineages.
There are 2 sections:

- One is for recoloring any dataset according to the number of sublineages in a specific timepoint
- The other is about using precomputed features to recolor both viewers.

These two components:
<!-- 
![distance_image](./distance_display_componentn.png)

- Using the slider, the user can select a timepoint where ```n``` clones exist. By pressing ```Recolor Clones``` each clone will be colored with a color specified in the colormap. In this specific example the image was recolored according to the clones that existed on timepoint 7.

![jacquard_image](./jacqard.png)

- The user can select any quantitaive attribute and recolor it according to its value.***On the left*** the configuration screen and the colored viewer are shown. ***On the right*** one lineage on the lineage viewer, which is also recolored is shown. The important settings the user may manipulate are how to propagate the coloring. The options are:
    1. ***Black***: If a node has no value no color it will be shown in black color.
    - ***Propagate from Ancestor***: Each node with no value will inherit its value from its ancestor and colored the same color.
    - ***Propagate from Sibling***: Each node with no value will get the same valu as their sibling if they do have a color.
    - ***Default Value***: More settings are available here, as the user can select a value to color each node that has no color.
        1. ***Custom  Value***: The user can just input any value, so these nodes will get this value
        2. ***Mean***: Each node will be colored with just the mean value.
        3. ***Median***:  Each node will be colored with just the median value.
        4. ***Min***: Each node will be colored with just the mean value. -->

## Clone based recoloring
<div class="split-container1">
  <div class = "scrollable-left1" >
<p>
  Using the slider, the user can select a timepoint where <code>n</code> clones exist. 
  By pressing <code>Recolor Clones</code>, each clone will be colored with a color specified in the colormap. 
  In this specific example, the image was recolored according to the clones that existed on timepoint 7.
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
      <li><strong>Black</strong>: If a node has no value, no color, it will be shown in black color.</li>
      <li><strong>Propagate from Ancestor</strong>: Each node with no value will inherit its value from its ancestor and be colored the same color.</li>
      <li><strong>Propagate from Sibling</strong>: Each node with no value will get the same value as their sibling if they do have a color.</li>
      <li><strong>Default Value</strong>: More settings are available here, as the user can select a value to color each node that has no color.
        <ol>
          <li><strong>Custom Value</strong>: The user can input any value, so these nodes will get this value.</li>
          <li><strong>Mean</strong>: Each node will be colored with the mean value.</li>
          <li><strong>Median</strong>: Each node will be colored with the median value.</li>
          <li><strong>Min</strong>: Each node will be colored with the minimum value.</li>
        </ol>
      </li>
    </ol>



  </div>
  <div class="fixed-right1">
    <img src="../jacqard.png" alt="My Image"> 
  </div>
</div>
