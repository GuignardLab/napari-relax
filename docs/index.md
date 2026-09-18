# Welcome to ReLAX

<p style="text-align: justify;">

This <a href="https://napari.org/dev/index.html" target="_blank">napari</a> plugin extends the functionality of the <a href="https://guignardlab.github.io/LineageTree/" target="_blank">LineageTree</a> project by providing a comprehensive Graphical User Interface (GUI). Leveraging napari’s interactive visualization capabilities and Qt’s flexible framework, it enables users to import and explore tracking datasets, called <b>LineageTrees</b> directly into the Napari viewer. This project as well as LineageTree lie at the interface between graph theory and biology, thus a useful <a href="https://guignardlab.github.io/LineageTree/glossary/" target="_blank">glossary</a> was created to accomodate users who are not familiar with either of the fields

</p>

--- 

 With this plugin the user has access to features like:

- **Spatial and Temporal data exploration**: The user can interact with the **[Napari viewer](./viewer/viewer.md)** and the **[Lineage Viewer](./explore_relabel/explore_relabel.md)** simultaneously.

- **Node Recoloring**: Recolor node colors based on lineage attributes for better insights into any dataset.

- **Unordered Tree Edit Distance Calculation**: Compute pairwise distances of lineages and sublineages in datasets, to assess their similarity or dissimilarity, using **[Unordered Tree Edit Distance (UTED)](https://gitlab.ub.uni-bielefeld.de/bpaassen/python-edit-distances/-/tree/master)**.


---

[Here are guides](./guides/guides.md) available for tutorials on specific aspects of workflows available in the plugin.

---

This integration enhances lineage analysis by combining the powerful visualization of Napari with quantitative comparison tools in an interactive environment.

## What does this combination of LineageTree and Napari offer

- **The Viewer**: The spatial data are loaded into the napari viewer and can be interacted with.
- **Interaction with big datasets**: Big datasets contain hundreds of annotations/nodes per chain/branch, the plugin offers the capability to explore large lineages on the interactive Lineage Viewer
- **No need for programming knowledge**: This plugin does not require programming knowledge, thus comparing LineageTrees is accessible even for the untrained user.

This plugin consists of 2 components, one tailored for single dataset analysis and inspection and one for multiple dataset analysis:

- Single dataset analysis: 
    - [Lineage Viewer - Explore and Relabel](./explore_relabel/explore_relabel.md): Explore the lineages with its interactive **Lineage Viewer**, relabel lineages of interest.
    - [Attribute recoloring](./attribute/attribute.md): Recolor nodes on both the **Lineage Viewer** and the **Napari standard Viewer**, using the distance or precomputed attributes.
    - [Distance Calculation](./distance/distance.md): Calculate the unordered tree edit distance, inspect the distances on the **Napari Standard Viewer** and in an interactive clustermap to compare lineages through their sublineages.

- Multiple dataset analysis:
    - [Manager](./cross+comparison/manager.md): A manager to handle and save multiple embryos.
    - [Cross Dataset Comparison](./cross+comparison/distance_cross.md): Easily calculate the unordered tree edit distance of lineages or sublineages across datasets.

---
