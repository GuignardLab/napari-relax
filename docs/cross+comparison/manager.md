When comparing multiple datasets, users must account for various parameters, one of the most critical being temporal resolution. Recent advances in imaging and acquisition techniques have enabled significantly improved time resolution, leading to increased adoption of these modern tools. Consequently, integrating or comparing legacy datasets with newer, high-resolution data has become challenging. This component is designed specifically to address this issue by managing differences in temporal resolution, thereby allowing users to concentrate on the analysis and interpretation of the data rather than on preprocessing or alignment tasks.

---

## Manager
<div class="split-container">
  <div >

<ol>
  <li>
    <strong>Create a Manager from existing layers</strong>: 
    Pressing this button will create a new manager that consists of all the layers of napari that contain a LineageTree.
  </li>

  <li>
    <strong>Load an existing Manager</strong>
  </li>

  <li>
    <strong>The LineageTree list</strong>: 
    This list contains all the LineageTrees the current manager contains. Users may interact with this list with right-click to change the time resolutions of any dataset or remove it.
  </li>

  <li>
    <strong>Add a LineageTree from the manager to the viewer</strong>: 
    Add a LineageTree from the manager to the viewer <em>if</em> it does not already exist in the layer list.
  </li>

  <li>
    <strong>Add an embryo from file</strong>: 
    Imports an embryo from a file directly to the viewer.
  </li>

  <li>
    <strong>Save the Manager</strong>: 
    Save the manager.
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