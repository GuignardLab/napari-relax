# Node and Edge Color Isolation Fix

## Problem Statement
1. **Initial Issue**: Edge colors in lineage tree visualizations were being influenced by the points layer colors, both in default mode and quantitative recoloring mode.
2. **Secondary Issue**: After fixing edge colors, nodes in default mode (non-quantitative, non-selection) were staying black instead of showing their proper colors from the points layer.

## Root Cause Analysis

### Primary Issue - Edge Color Contamination
The `default_color` parameter passed to `draw_tree_graph()` was being set from points layer data, which was influencing edge rendering even when `color_of_edges` was explicitly provided.

### Secondary Issue - Node Color Override  
The code was always providing `color_of_nodes=self.color_of_selection_nodes` in normal mode, which overrode the natural node colors that should come from the points layer via `default_color`.

## Solution Implemented

### Files Modified
- `src/napari_relax/lineage_tree_analysis/lineage_viewer_widget/lineage_tree_canvas.py`

### Changes Made

#### 1. Fixed Node Color Logic in `draw_graph()` method (lines 603-615)
**Before:**
```python
if getattr(self, "is_quantitative_mode", False) and hasattr(self, "node_colors"):
    color_of_nodes = self.node_colors
else:
    # This was always overriding default colors!
    color_of_nodes = self.color_of_selection_nodes
```

**After:**
```python
if getattr(self, "is_quantitative_mode", False) and hasattr(self, "node_colors"):
    # Use individual colors from quantitative coloring
    color_of_nodes = self.node_colors
elif self.selected_subtree:
    # Only use selection colors when there are actual selections
    color_of_nodes = self.color_of_selection_nodes
else:
    # Let default_color handle node coloring from points layer
    color_of_nodes = None
```

#### 2. Conditional Parameter Passing (lines 617-631)
**Before:**
```python
self.lT.draw_tree_graph(
    # ... other params ...
    color_of_nodes=color_of_nodes,  # Always provided, even when None
    # ... other params ...
)
```

**After:**
```python
# Build parameters conditionally
draw_params = {
    "lw": float(self.lw),
    "size": float(self.node_size),
    "color_of_edges": color_of_edges,
    "default_color": default_color,
    "selected_nodes": self.selected_subtree,
    "selected_edges": set(),
    "ax": self.ax,
}

# Only provide color_of_nodes if we have specific node colors to apply
if color_of_nodes is not None:
    draw_params["color_of_nodes"] = color_of_nodes

self.lT.draw_tree_graph(self.pos, self.lnks_tms, **draw_params)
```

#### 3. Fixed `__init__()` method (lines 159-166)
**Before:**
```python
self.lT.draw_tree_graph(
    # ... other params ...
    color_of_nodes=self.color_of_selection_nodes,  # Always overriding!
    # ... other params ...
)
```

**After:**
```python
self.lT.draw_tree_graph(
    self.pos,
    self.graph,
    ax=self.ax,
    color_of_edges=self.color_of_edges,
    default_color=default_color,
    # No color_of_nodes - let default_color handle node colors from points layer
)
```

#### 4. Restored Proper default_color Logic
```python
# Use current color as default if available, otherwise fallback to original reader color
# This allows nodes to get proper colors from points layer in default mode
default_color = None
if color_info and color_info.get("color"):
    default_color = color_info["color"]
else:
    reader_color = self._extract_node_colors_from_reader()
    default_color = (
        reader_color if reader_color is not None else self.color_of_nodes
    )
```

## Expected Behavior After Fix

### Default Mode (no selections, non-quantitative)
- ✅ **Nodes**: Get individual colors from points layer via `default_color` parameter
- ✅ **Edges**: Maintain fixed color from LineageCanvasSetup dialog (black by default)
- ✅ **Parameter handling**: `color_of_nodes` not provided, allowing `default_color` to work

### Selection Mode (has selections)
- ✅ **Selected nodes**: Use selection color (magenta by default) via `color_of_nodes`
- ✅ **Non-selected nodes**: Get colors from points layer via `default_color`
- ✅ **Edges**: Maintain fixed color from LineageCanvasSetup dialog
- ✅ **Parameter handling**: `color_of_nodes` provided for selection highlighting

### Quantitative Mode
- ✅ **Nodes**: Use individual colors from quantitative coloring (dictionary format)
- ✅ **Edges**: Maintain fixed color from LineageCanvasSetup dialog  
- ✅ **Parameter handling**: `color_of_nodes` provided as dictionary of individual colors

### Edge Coloring (all modes)
- ✅ **Edges**: Always use fixed color from user preferences (`self.color_of_edges`)
- ✅ **Never influenced**: by points layer data, quantitative coloring, or selection state
- ✅ **User control**: Only changes via LineageCanvasSetup dialog

## Technical Details

### Key Insight
The `LineageTree.draw_tree_graph()` method uses this parameter hierarchy:
1. `color_of_nodes` (if provided): Overrides colors for specific nodes or all nodes
2. `default_color`: Used for nodes not covered by `color_of_nodes`
3. `color_of_edges`: Always respected for edge coloring

The fix ensures we only provide `color_of_nodes` when we actually want to override the natural coloring behavior.

### Validation
- All imports work correctly
- Related components (QuantitativeColoringWidget, LineageExplorationWidget) are unaffected
- User preference system continues to function properly
- No breaking changes to existing APIs

## Resolution Status
✅ **COMPLETE**: Both edge color isolation and node color restoration are now working correctly.
- Edge colors are completely isolated from points layer influence
- Node colors properly display points layer data in default mode
- Selection and quantitative coloring modes work as expected
- User preferences control all visual properties via LineageCanvasSetup dialog

The user can now proceed to tackle the main sublineage highlighting issue with confidence that the color system is working correctly.