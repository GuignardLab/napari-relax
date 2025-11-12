# Lineage-Level Analysis Plugin

This component focuses on **interacting with chain-level temporal data** rather than node-level data. This approach makes **plotting and analyzing lineages faster and more efficient**.

## Core Features

The main capabilities of this component include:

- **Explore temporal data efficiently** using the **Lineage Viewer**.
- **Relabel** any chain in a **LineageTree** dataset.
- **Combination** of the **Lineage Viewer** with the **Napari Viewer** for easy exploration of both temporal and spatial data.
- **Iterate though all lineages** existing in a dataset using a slider.

---

## Controls


<div class="split-container">
  <div >

<ol>
  <li>
    <strong>Lineage Viewer configuration button</strong>: Press to open the configuration window
      <li>
        <strong>Lineage Viewer configuration window</strong>: Using this window, the user may change the Lineage Viewer's properties.
      </li>
      <li>
        <strong>The Lineage Viewer</strong>: Using this viewer, the user may inspect all the lineages in the dataset.
        <p><em>Controlling the Lineage Viewer:</em></p>
        <ul>
          <li><strong>Left click</strong>: Using the left click, the user can select a sublineage spawned from node on both viewers.</li>
          <li><strong>Double Left click</strong>: Clicking twice on a node on the Lineage Viewer will show the first timepoint the clicked cell spawned on the <a href="../viewer/viewer.md">Napari Viewer</a>.</li>
          <li><strong>Mouse wheel</strong>: Using the mouse wheel, the user can zoom in on the Lineage viewer to observe specific details. If zoomed in enough, the labels of each node will be shown on screen.</li>
          <li><strong>Right click and drag</strong>: Pan to see different segments of the lineage if the plot is zoomed in.</li>
          <li><strong>Z</strong>: Reset the view regardless of panning or zoom.</li>
        </ul>
      </li>
      <li><strong>The Lineage Viewer slider</strong>: Use the slider to inspect different lineages that exist in the dataset.</li>
      <li><strong>Label manipulation</strong>: Change the label of any node, remove an existing label from a node, or show all labels.</li>
      <li>
        <strong>Select Lineage/Sublineage</strong>: After the user has selected a point on the Napari Viewer, they may decide to select the whole lineage this node belongs to or its sublineage by pressing the corresponding button. This will also update the plot. The user may also decide to change the colors of all nodes selected using panel 1 of layer controls.
      </li>
      <li>
        <strong>Show/Hide Lineages</strong>: The user can hide/show selected lineages or even all lineages. Lineages that are hidden may be selected using the Lineage Viewer.
      </li>
      <li>
        <strong>General helping buttons</strong>:
        <ul>
          <li><strong>Top</strong>: Change the size of all the Points on a selected layer or all layers. The same value will be applied across all points modified.</li>
          <li><strong>Middle Left</strong>: Toggle the visibility of other layers; the same result may be achieved by <strong>Alt+Click</strong> on a layer in the layer control panel.</li>
          <li><strong>Middle Right</strong>: Add a tracks layer to the Points layer for visualization purposes.</li>
          <li><strong>Bottom</strong>: Save the LineageTree.</li>
        </ul>
      </li>
  </li>
</ol>


  </div>
  <div class="fixed-right">
    <img src="../exploration.png" alt="My Image"> 
  </div>
</div>

---
## The tracks layer of a dataset.

This layer was produced by pressing on ```Add Tracks``` while a viable layer (contains a LineageTree) was selected

![tracks](./tracks.png){: style="width:400px;"}

---

Go to [Starting page](../index.md)                                           
Go to [Tutorials](../guides/guides.md)