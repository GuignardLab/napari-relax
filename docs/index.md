# Welcome to ReLAX

<p style="text-align: justify;">

This napari plugin extends the functionality of the <a href="https://guignardlab.github.io/LineageTree/" target="_blank">LineageTree</a> project by providing a comprehensive Graphical User Interface (GUI). Leveraging napari’s interactive visualization capabilities and Qt’s flexible framework, it enables users to import and explore tracking datasets, called <b>lineagetrees</b> from now on, directly into the napari viewer. With this plugin, users can intuitively navigate spatial and temporal tracking data. Beyond data exploration, it also offers features such as:
</p>

- **Node Recoloring**: Customize node colors based on lineage attributes for better insights into the embryo.

- **Tree Distance Calculation**: Compute distances between different lineage trees to assess their similarity or dissimilarity, using **Unordered Tree Edit Distance (UTED)**.

- **Morphology Inspection**: Visually compare tree structures to analyze morphological differences.

This integration enhances lineage analysis by combining the powerful visualization of Napari with quantitative comparison tools in an interactive environment.

## What does this combination of LineageTree and Napari offer

- **Viewer**: The 3-D positional data are loaded into the napari viewer and can be interacted with.
- **Interaction with huge datasets**: Huge datasets contain hundreds of annotations/nodes per chain/branch, the plugin offers the capability to explore lineages on an interactive lineage viewer
- **No need for programming knowledge**: This plugin does not require programming capabilities, thus comparing lineagetrees is possible even for the untrained user.

This plugin consists of 4 components:

- [Explore and Relabel](./explore_relabel.md): Explore the lineages with its interactive **Lineage Viewer**, relabel lineages of interest.
- [Attribute recoloring](./attribute.md): Recolor nodes on both the **Lineage Viewer** and the **Napari standard Viewer**, using the distance or precomputed attributes.
- [Distance Calculation](./distance.md): Calculate the unordered tree edit distance, inspect the distances on  the **Napari Standard Viewer** and create histograms to compare lineages through their sublineages.
