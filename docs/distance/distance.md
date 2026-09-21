*Distance Calculation* focuses on systematic calculation of unordered tree edit distances of lineages and their sublineages across multiple timepoints, using various [approximation methods](https://guignardlab.github.io/LineageTree/uted/).

This systematic comparison enables users to calculate the pairwise distance of clones/sublineages that spawn from a specific timepoint, across multiple timepoints.

The results of these comparisons will be shown on a clustermap, which the user can download. However, a clustermap by itself is lacking in information, or at least is difficult to interpret the results in means of morphology, for this reason we allow for users to click on this clustermap to inspect which sublineages are being compared in each specific cell!


---

## Configuration Tab

<div class="split-container3">
  <div class="scrollable-left1">
<p>
    This Tab is responsible for setting up the systematic pairwise distance parameters.</p>

<ol>
  <li>
    <strong>Timepoints Selection</strong>: The user has two options to set the timepoints for the comparison:
    <ul>
      <li><strong>Top</strong>: The user may set a range with <em>start</em>, <em>stop</em> and <em>step</em>. The <em>stop</em> timepoint is not included; with a step of 0, only <em>start</em> is used.</li>
      <li><strong>Bottom</strong>: The user may set a list of specific timepoints they want to compare, separated by commas (for example <code>10, 25, 40</code>).</li>
    </ul>
    Timepoints with a single cell are skipped.
  </li>

  <li>
    <strong>Time crop</strong>: The last timepoint to be included in the analysis. Type it and press <strong>Enter</strong>; the field then shows <em>Final Timepoint</em>. If the tree has nodes at later timepoints, they will be excluded (cut) from the analysis. Leave it empty to use the whole dataset.
  </li>

  <li>
    <strong>Approximation / Style selection</strong>: The approximation to be used in the analysis. Hover over the list for a short description of each style:
    <ul>
      <li><code>mini</code>: only the division pattern, ignoring how long each cell lives.</li>
      <li><code>simple</code>: each cell becomes one node weighted by its lifetime.</li>
      <li><code>normalized_simple</code>: like <code>simple</code>, but small timing differences between long-lived cells cost less.</li>
      <li><code>downsampled</code>: the tree is resampled every <em>n</em> timepoints, with <em>n</em> chosen in the box that appears next to the list. Accurate and fast, recommended for use in napari.</li>
      <li><code>full</code>: compares the complete trees. The most accurate, but extremely slow.</li>
    </ul>
    <strong>CAUTION:</strong> Different algorithms have different uses. For more information, visit
    <a href="https://guignardlab.github.io/LineageTree/uted/#different-tree-approximations" target="_blank" rel="noopener">
      LineageTree Tree approximations
    </a>.
    The full tree mode is <em>not recommended</em> for large LineageTrees.
  </li>

  <li>
    <strong>Subtree selection</strong>: The list shows the labelled lineages as <em>label - ID starts from t timepoint</em> (see <a href="../explore_relabel/explore_relabel.md">Explore and Relabel</a> to add labels).
    Specific lineages may be selected to calculate their pairwise distances; if none is selected, all lineages that start at the first timepoint of the dataset are compared.
    Some lineages may spawn later than the first selected timepoint due to tracking or imaging issues;
    they can still be included if they exist at any of the selected timepoints.
  </li>

  <li>
    <strong>Start / Stop Comparisons</strong>: The user can start calculating the comparisons with <code>Run Comparisons</code>.
    While the comparisons are being processed, the rest of the plugin and Napari remain responsive.
    At any point, the user may stop processing by clicking <code>Stop Processing</code>.
    A progress bar indicates the calculation progress.
  </li>
</ol>



  </div>
  <div class="fixed-right3">
    <img src="./config_uted.png" alt="Configuration Panel">
  </div>
</div>
---

## Clustermap Tab

!!! note "Screenshot from an earlier version"
    The tabs are now called **Configuration Panel** and **Clustermap**, and the former **Histograms** tab was removed. The **Clustermap** tab contains all the controls shown here.

<div class="split-container">
  <div class="scrollable-left4">
<p>
    The results of the comparisons are shown as an interactive clustermap: one row and one column per sublineage, colored by their distance. Rows and columns are ordered by hierarchical clustering (Ward linkage), so similar sublineages end up next to each other.</p>
<ol>
  <li>
    <strong>Tree plots</strong>: Displays the trees that are currently being interacted with through the clustermap,
    with the compared sublineages in magenta and cyan.
  </li>

  <li>
    <strong>Clustermap Configuration</strong>:
    <ul>
      <li><strong>Reset Colors</strong> restores the original colors of the dataset.</li>
      <li><strong>Move in time</strong>: when ticked, clicking on the clustermap also moves the Napari Viewer to the timepoint where the first compared sublineage starts.</li>
      <li>The left combobox selects the normalization: <code>max</code> divides the distance by the size of the larger tree, <code>sum</code> by the sizes of both trees (results always between 0 and 1), and <code>None</code> shows the raw edit distance.</li>
      <li>The right combobox selects the colormap of the clustermap.</li>
    </ul>
  </li>

  <li>
    <strong>Clustermap</strong>: There is one clustermap for each timepoint selected in the configuration tab; use the slider under it to switch between them.
    <ul>
    <li><strong>Hover</strong> over a cell to see the two compared lineages and their score.</li>
    <li><strong>Left Click</strong> on any cell to draw the corresponding tree plots and recolor the dataset: the two compared sublineages in magenta and cyan, everything else in white.</li>
    </ul>
    Press <strong>Select file</strong> and then <strong>Save Comparisons</strong> to save the results as a <code>.pkl</code> file (timepoints, distances, normalizations, sublineage names, crop time and labels). The comparisons are also kept in the LineageTree, so saving the dataset as <code>.lT</code> keeps them too.
  </li>
  </ol>



  </div>
  <div class="fixed-right4">
    <img src="./clustermap_analysis_celegans.png" alt="Clustermap tab">
  </div>
</div>

---

Go to [Starting page](../index.md)  
Go to [Tutorials](../guides/guides.md)
