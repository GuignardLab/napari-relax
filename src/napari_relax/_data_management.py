"""
Data management layer for lineage tree operations.
Separates data logic from UI components.
"""
from typing import Optional, Set, Dict, Any
from lineagetree import LineageTree
from ._utils import _select_active_lt_layer

# Default selection color - can be overridden by canvas settings
DEFAULT_SELECTION_COLOR_RGBA = [1, 0, 1, 1]  # magenta


class LineageTreeDataManager:
    """
    Pure data management for lineage tree operations.
    No Qt inheritance - focuses only on data operations.
    """
    
    def __init__(self, napari_viewer):
        self.viewer = napari_viewer
    
    def get_lineage_tree(self) -> Optional[LineageTree]:
        """
        Get the LineageTree structure from the active layer.
        
        Returns:
            LineageTree object or None if no active layer found
        """
        active_layer = _select_active_lt_layer(self.viewer)
        if active_layer is None:
            return None
        return active_layer.metadata.get("LineageTree", None)
    
    def select_subtree(self, cell_id: Optional[int] = None) -> int:
        """
        Add all descendants of a cell to selected_data.
        Reads the selected data from napari layer and selects all descendants.
        
        Args:
            cell_id: Optional specific cell ID to select. If None, uses current selection.
            
        Returns:
            Number of cells selected (0 if no selection)
        """
        active_layer = _select_active_lt_layer(self.viewer)
        if not active_layer.selected_data:
            return 0
            
        lT = active_layer.metadata["LineageTree"]
        
        if cell_id is None:
            cell = active_layer.selected_data.pop()
        else:
            cell = cell_id
            
        active_layer.selected_data = {cell}
        descendant_nodes = lT.get_subtree_nodes(active_layer.metadata["napari2lT"][cell])
        
        for node in descendant_nodes:
            active_layer.selected_data.add(
                active_layer.metadata["lT2napari"][node]
            )
        
        active_layer.refresh()
        return len(descendant_nodes)
    
    def paint_tree_nodes(self, graph_index: int, color_from_trees: bool = False) -> None:
        """
        Change the color of the subtree or the whole tree.
        
        Args:
            graph_index: Index of the graph in the graphs list
            color_from_trees: If True, color only the subtree; if False, color whole tree
        """
        active_layer = _select_active_lt_layer(self.viewer)
        active_layer.face_color = active_layer.metadata["clone2"]
        
        if color_from_trees:
            # Find root node for the selected graph
            root_nodes = [
                i
                for i, degree in active_layer.metadata["graphs"][0][graph_index].in_degree()
                if degree == 0
            ]
            
            if root_nodes:
                root = root_nodes[0]
                active_layer.selected_data.add(
                    active_layer.metadata["lT2napari"][root]
                )
                self.select_subtree()
                selection = list(active_layer.selected_data)
                active_layer.face_color[selection] = DEFAULT_SELECTION_COLOR_RGBA
                active_layer.selected_data.clear()
                active_layer.refresh()
    
    def find_graph_index(self, cell_id: int, lineage_tree: LineageTree, graphs: Dict) -> Optional[int]:
        """
        Find the correct index in the list of graphs for a given cell.
        
        Args:
            cell_id: ID of the node
            lineage_tree: The LineageTree object
            graphs: Dictionary of graphs
            
        Returns:
            Graph index or None if not found
        """
        for index, graph in graphs.items():
            if lineage_tree.get_ancestor_at_t(cell_id) == graph["root"]:
                return index
        return None
    
    def get_active_layer(self):
        """Get the currently active lineage tree layer."""
        return _select_active_lt_layer(self.viewer)
    
    def get_layer_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get metadata from the active layer.
        
        Args:
            key: Metadata key to retrieve
            default: Default value if key not found
            
        Returns:
            Metadata value or default
        """
        active_layer = self.get_active_layer()
        if active_layer is None:
            return default
        return active_layer.metadata.get(key, default)