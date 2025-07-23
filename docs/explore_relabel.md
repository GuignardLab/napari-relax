This component serves as the starting screen and is mainly focused on data exploration and inspection. The user may also make changes to the labels of the dataset or inspect which sublineages create which structures using the lineage viewer and napari viewer simultaneously. Apart from that, the user may also make changes to the aesthetics of the application.

This plugin component contains features for navigating the lineages with the Lineage Viewer, renaming lineages, and interacting with the viewer.


The Lineage Viewer is the plugin's first component, enabling lineage exploration, relabeling, and navigation through the viewer's time data.
Lineage Viewer configuration button: Press to open the configuration window
Configuration window: Using this window, the user may change the node size, node color, edge size, label fontsize, and the color of the selected cells (maybe add background??)
The lineage viewer. Using this viewer, the user may inspect all the lineages that exist in a dataset. It is zoomable and pannable; if zoomed in enough, the user may also see the label for each node that exists on the start or end of a chain. Clicking on the viewer, the user can select the nodes of subtrees by clicking on the graph in both viewers. Also, when clicking, the user may use component 5 to change the label of any subtree.
Left click: Using the left click, the user will select a subtree on the plot and the corresponding Points on the napari viewer.
Mouse wheel: Using the mouse wheel, the user can zoom in on the graph to observe specific details. If the user zooms in enough, the labels of each node will be shown on screen.
Left click and drag: Edge pan to see different segments of the lineage if the plot is zoomed in.
Z: Reset the view regardless of panning or zoom.
The lineage viewer slider: Using this slider, the user may inspect different lineages that exist in the dataset
Label component: Change a label by entering a name, show all labels, or remove an existing label.
Select Lineage/Sublineage: After the user has selected a point on the napari viewer, they may decide to select the whole lineage this node belongs to or the subtree by pressing the corresponding button. This will also update the plot. The user may also decide to change the colors of all nodes selected. Using panel 1 of. layer controls
Change the size of all the Points on a selected layer or all layers (add a gif?). The same value will be applied across all points modified.
Left: Toggle the visibility of other layers; this button may serve as a shortcut.
Right: Add a tracks layer to the Points layer for visualization purposes.


The tracks layer alone (left) and combined with the points layer (right).
