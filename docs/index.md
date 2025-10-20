# Welcome to ReLAX

<p style="text-align: justify;">

This napari plugin extends the functionality of the <a href="https://guignardlab.github.io/LineageTree/" target="_blank">LineageTree</a> project by providing a comprehensive Graphical User Interface (GUI). Leveraging napari’s interactive visualization capabilities and Qt’s flexible framework, it enables users to import and explore tracking datasets, called <b>LineageTrees</b> directly into the napari viewer. With this plugin, users can intuitively navigate spatial and temporal tracking data. Beyond data exploraxtion, it also offers features such as:
</p>

- **Node Recoloring**: Customize node colors based on lineage attributes for better insights into datasets.

- **Tree Distance Calculation**: Compute pairwise distances of lineages inside the LineageTrees, to assess their similarity or dissimilarity, using <a href="https://gitlab.ub.uni-bielefeld.de/bpaassen/python-edit-distances/-/tree/master" target="_blank">**Unordered Tree Edit Distance (UTED)**</a>
.

- **Morphology Inspection**: The core feature of this plugin is its capability to connect analysis of tracked data with the morphology of the dataset.

This integration enhances lineage analysis by combining the powerful visualization of Napari with quantitative comparison tools in an interactive environment.

## What does this combination of LineageTree and Napari offer

- **Viewer**: The positional data are loaded into the napari viewer and can be interacted with.
- **Interaction with huge datasets**: Big datasets contain hundreds of annotations/nodes per chain/branch, the plugin offers the capability to explore large lineages on an interactive lineage viewer
- **No need for programming knowledge**: This plugin does not require programming knowledge, thus comparing LineageTrees is possible even for the untrained user.

This plugin consists of 4 components:

- [Explore and Relabel](./explore_relabel/explore_relabel.md): Explore the lineages with its interactive **Lineage Viewer**, relabel lineages of interest.
- [Attribute recoloring](./attribute/attribute.md): Recolor nodes on both the **Lineage Viewer** and the **Napari standard Viewer**, using the distance or precomputed attributes.
- [Distance Calculation](./distance/distance.md): Calculate the unordered tree edit distance, inspect the distances on  the **Napari Standard Viewer** and create histograms to compare lineages through their sublineages.
