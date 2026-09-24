When comparing multiple datasets, users must account for various parameters, one of the most critical being temporal resolution. Recent advances in imaging and acquisition techniques have enabled significantly improved time resolution, leading to increased adoption of these modern tools. Consequently, integrating or comparing legacy datasets with newer, high-resolution data has become challenging. This component is designed specifically to address this issue by managing differences in temporal resolution, thereby allowing users to concentrate on the analysis and interpretation of the data rather than on preprocessing or alignment tasks.

It is the **Manager Manipulation** entry of the **Cross Lineagetree comparison** widget (***Plugins>Cross Lineagetree comparison***).

---

## Manager
<div class="split-container">
  <div class="scrollable-left1">

<ol>
  <li>
    <strong>Create a Manager from existing layers</strong>: 
    Pressing this button will create a new manager that consists of all the layers of napari that contain a LineageTree.
  </li>

  <li>
    <strong>Load an existing Manager</strong>: Press <strong>Select file</strong> to choose a manager file, then <strong>Load a Manager</strong>.
  </li>

  <li>
    <strong>The LineageTree list</strong>: 
    This list contains all the LineageTrees the current manager contains. Users may interact with this list with right-click: <strong>Change Time Resolution</strong> sets the time between two timepoints (in minutes) of a dataset, and <strong>Remove Embryo</strong> removes it from the manager.
  </li>

  <li>
    <strong>Add a LineageTree from the manager to the viewer</strong>: 
    Add the LineageTrees selected in the list to the viewer <em>if</em> they do not already exist in the layer list.
  </li>

  <li>
    <strong>Add an embryo from file</strong>: 
    Press <strong>Select files</strong> to choose one or more <code>.lT</code> files, then <strong>Add LineageTrees</strong> to add them to the manager.
  </li>

  <li>
    <strong>Save the Manager</strong>: 
    Press <strong>Select file</strong> to choose where to save, then <strong>Save Manager</strong>. The manager file keeps all its LineageTrees and their time resolutions.
  </li>
</ol>


  </div>
  <div class="fixed-right">
    <img src="../manager.png" alt="My Image"> 
  </div>
</div>

---

Go to [Starting page](../index.md)                                           
Go to [Tutorials](../guides/guides.md)