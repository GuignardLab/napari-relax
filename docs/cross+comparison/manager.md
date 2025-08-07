If a user want to compare multiple embryos, there are multiple parameters they have to take into account like time resolution. Thus, we developed this manager to handle such calculations on the background,such as the users can perform their analysis hassle free.

![manager](./manager.png)

1. **Create a Manager from existing layers**: Pressing this button will create a new manager that consists of all the layers of napari that contain a LineageTree.

- **Load an existing Manager**
- **The LineageTree list**: This list contains all the LineageTrees the curent manager contains. Users may interact with this list with right+Click to change the time resolutions of any dataset or remove it.
- **Add a LineageTree from the manager to the viewer**: Add a LineageTree from the manager to the viewer *if* it does not already exist in the layer list.
- **Add an embryo from file**: Imports an embryo from a file directly to the viewer.
- **Save the Manager**: Save the manager.
