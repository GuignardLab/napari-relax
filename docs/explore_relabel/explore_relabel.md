# Explore and Relabel

This component focuses on **interacting with chain-level temporal data** rather than node-level data. This approach makes **plotting and analyzing lineages faster and more efficient**. It is the first tab of the **Lineage tree analysis** widget (***Plugins>Lineage tree analysis***).

## Core Features

The main capabilities of this component include:

- **Explore temporal data efficiently** using the **Lineage Viewer**.
- **Relabel** any chain in a **LineageTree** dataset.
- **Combination** of the **Lineage Viewer** with the **Napari Viewer** for easy exploration of both temporal and spatial data.
- **Iterate through all lineages** existing in a dataset using a slider, or **jump to any cell** using its ID.

---

## Controls

<div class="split-container">
  <div >

<ol>
  <li value = "0">
    <strong>Lineage Viewer settings:</strong> The node size, edge size and font size of the Lineage Viewer are set in napari's <strong>File>Preferences</strong>, on the <strong>ReLAX</strong> page (napari 0.9 or newer).
  </li>
  <li value="1">
    <strong>The Lineage Viewer</strong>: Using this viewer, the user may inspect all the lineages in the dataset. The current timepoint of the <a href="../viewer/viewer.md">Napari Viewer</a> is drawn on it.
    <p><em>Controlling the Lineage Viewer:</em></p>
    <ul>
      <li><strong>Left click</strong>: Select the sublineage spawned from the clicked node on both viewers. Clicking an empty area clears the selection and shows hidden nodes again.</li>
      <li><strong>Double Left click</strong>: Move the <a href="../viewer/viewer.md">Napari Viewer</a> to the first timepoint of the clicked cell.</li>
      <li><strong>Mouse wheel</strong>: Using the mouse wheel, the user can zoom in on the Lineage Viewer to observe specific details. If zoomed in enough, the labels of each node will be shown on screen.</li>
      <li><strong>Right click and drag</strong>: Pan to see different segments of the lineage if the plot is zoomed in.</li>
      <li><strong>Z</strong>: Reset the view regardless of panning or zoom.</li>
    </ul>
  </li>
  <li>
    <strong>Lineage slider</strong>: Use the slider to inspect the different lineages that exist in the dataset. Its tooltip shows how many lineages are available; small lineages may be hidden by the <em>Filter Dataset</em> option used when <a href="../guides/loading_data.md">opening the dataset</a>.

  <li><strong>Cell ID selector</strong> (under the slider): type a cell ID and press <strong>Enter</strong> or <strong>Go</strong>. The Lineage Viewer shows the lineage containing this cell and circles it, the cell is selected in the Napari Viewer, and the time slider moves to its first timepoint. If the ID does not exist, the closest existing ID is used.</li>
  </li>
  <li>
    <strong>Label manipulation</strong>: The text field shows the ID and label of the current node (<em>ID of root: … - Label: …</em>). Type a new label and press <strong>Enter</strong> to rename it, press <strong>Remove this label</strong> to delete it, or <strong>Show Labels</strong> to list all labels. Labels are used by <a href="../distance/distance.md">Distance Calculation</a> and saved with the LineageTree.
  </li>
  <li>
    <strong>Select Lineage/Sub-Lineage</strong>: After the user has selected a point on the Napari Viewer with <strong>Shift + Right click</strong>, they may select the lineage that spawns this node (<strong>Select Lineage</strong>) or the sublineage spawned by this node (<strong>Select Sub-Lineage</strong>). This will also update the plot. The user may also decide to change the colors of all nodes selected using the layer controls.
  </li>
  <li>
    <strong>Show/Hide Lineages</strong>: <strong>Hide Lineage</strong> hides the selected lineage, <strong>Show Lineage</strong> shows only the selected lineage, and <strong>Hide all</strong> / <strong>Show all</strong> apply to every lineage. Linked mesh layers follow. Lineages that are hidden may still be selected using the Lineage Viewer.
  </li>
  <li>
    <strong>Shared tools</strong>, at the bottom of the <strong>Lineage tree analysis</strong> widget and visible in every tab:
    <ul>
      <li><strong>Size of spheres</strong>: Change the size of the Points of the selected layer, or of all layers when <strong>All layers</strong> is ticked. <strong>Reset slider</strong> restores the size estimated from the distances between neighboring cells.</li>
      <li><strong>Toggle visibility of other layers</strong>: When ticked, selecting a layer hides all the other layers; the same result may be achieved by <strong>Alt+Click</strong> on a layer in the layer list.</li>
      <li><strong>Add Tracks</strong>: Add a tracks layer to the selected Points layer for visualization purposes.</li>
      <li><strong>Save LineageTree</strong>: Choose a file with <strong>Select file</strong>, then press <strong>Save LineageTree</strong> to save the dataset, with its labels and comparisons, as a <code>.lT</code> file.</li>
    </ul>
  </li>
</ol>


  </div>
  <div class="fixed-right">
    <img src="./exploration.png" alt="Explore and Relabel panel"
     width="600"
    height="1000">
  </div>
</div>

---
## The tracks layer of a dataset.

This layer was produced by pressing on ```Add Tracks``` while a viable layer (contains a LineageTree) was selected

![tracks](./tracks.png){: style="width:400px;"}

---

Go to [Starting page](../index.md)  
Go to [Tutorials](../guides/guides.md)
