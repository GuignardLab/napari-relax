# Napari-ReLAX Refactoring Guide

## Overview

This document describes the architectural refactoring of the napari-relax plugin from a complex inheritance-based system to a cleaner composition-based architecture while **maintaining separate plugin entries** for different analysis types.

## Key Principles

1. **Preserve Separate Plugin Entries**: `lineage_tree_analysis` and `cross_embryo_comparison` remain as separate napari widgets
2. **Maintain Backward Compatibility**: Existing widgets continue to work unchanged
3. **Introduce Composition**: Use data managers and signal hubs instead of complex inheritance
4. **Enable Gradual Migration**: New architecture available alongside existing code

## Key Changes

### 1. **Separation of Data and UI Logic**

**Before**: `LineageTreeWidgetBase` mixed data operations with Qt widget inheritance
**After**: `LineageTreeDataManager` handles pure data operations without Qt dependencies

```python
# Old approach (mixed concerns)
class MyWidget(LineageTreeWidgetBase):
    def __init__(self, viewer):
        super().__init__(viewer)  # Inherits data + UI
    
    def my_analysis(self):
        lT = self.get_lT()  # Data operation mixed with UI

# New approach (separated concerns)
class MyWidget(ModernLineageWidget):
    def __init__(self, viewer, signal_hub):
        super().__init__(viewer, signal_hub)
    
    def my_analysis(self):
        lT = self.data_manager.get_lineage_tree()  # Pure data operation
```

### 2. **Centralized Signal Management**

**Before**: Direct widget-to-widget signal connections scattered throughout code
**After**: `PluginSignalHub` coordinates communication between both plugin types

```python
# Old approach (tight coupling)
self.widget_a.signal.connect(self.widget_b.method)

# New approach (loose coupling via signal hub)
# In LineageTreeAnalysisWidget
self.signal_hub.label_update_requested.connect(distance_widget.label_update)
```

### 3. **Updated Base Classes**

**Before**: Complex inheritance from `LineageTreeWidgetBase`
**After**: Multiple inheritance options:

1. **`LineageTreeWidgetBase`** (updated to use composition internally)
2. **`ModernLineageWidget`** (new clean alternative)
3. **`BaseAnalysisWidget`** (for completely new widgets)

### 4. **Simplified Layout Management**

**Before**: Custom `Containerize` class
**After**: `SimpleContainer` and utility functions using standard Qt layouts

```python
# Old approach
container = Containerize([widget1, widget2], horizontal=True)

# New approach
container = SimpleContainer([widget1, widget2], horizontal=True)
```

## Plugin Structure (Unchanged)

The plugin maintains its original structure with two separate entries:

1. **Lineage tree analysis** (`napari_relax._widgets:LineageTreeAnalysisWidget`)
   - Cell Size Analysis (always visible)
   - Explore and Relabel
   - Distance Calculation  
   - Attribute Based Recoloring

2. **Cross Lineagetree comparison** (`napari_relax._widgets:CrossEmbryoManagerComparisonWidget`)
   - Manager Manipulation
   - Embryo comparisons

Both widgets now use:
- Shared `PluginSignalHub` for signal coordination
- Individual `LineageTreeDataManager` instances for data operations

## New Architecture Components

### Core Classes

1. **`LineageTreeDataManager`** (`_data_management.py`)
   - Pure data operations for lineage trees
   - No Qt inheritance
   - Handles selection, painting, metadata operations

2. **`PluginSignalHub`** (`_signal_hub.py`)
   - Central event coordination between both plugin types
   - Reduces widget coupling
   - Auto-connects standard widget methods

3. **`ModernLineageWidget`** (`_modern_base.py`)
   - Clean alternative to `LineageTreeWidgetBase`
   - Uses composition with data manager
   - Maintains compatibility interface

### Signal Flow

```
LineageTreeAnalysisWidget:
  Explore and Relabel → signal_hub → Distance Calculation
  Attribute Recoloring → signal_hub → Explore and Relabel

CrossEmbryoManagerComparisonWidget:
  Manager → signal_hub → Embryo Comparison
```

## Migration Strategies

### For Existing Widgets (No Changes Required)

Existing widgets continue to work exactly as before:
- `LineageTreeWidgetBase` updated internally to use composition
- All existing method signatures preserved
- No breaking changes

### For New Widgets (Recommended)

Use the modern architecture:

```python
from napari_relax._modern_base import ModernLineageWidget

class MyNewWidget(ModernLineageWidget):
    def __init__(self, napari_viewer, signal_hub=None):
        super().__init__(napari_viewer, signal_hub)
        self.name = "My New Analysis"
        
        # Access data operations
        lineage_tree = self.data_manager.get_lineage_tree()
        
        # Emit signals
        self.emit_selection_change(selected_cells)
```

### For Gradual Modernization

Replace inheritance with composition gradually:

```python
# Step 1: Add signal hub to existing widget
class ExistingWidget(LineageTreeWidgetBase):
    def __init__(self, napari_viewer):
        super().__init__(napari_viewer)
        self.signal_hub = PluginSignalHub()  # Add this
        
    # Keep existing methods unchanged

# Step 2: Replace direct signal connections
# Old: self.widget_a.signal.connect(self.widget_b.method)
# New: self.signal_hub.label_update_requested.connect(widget_b.handle_label_update)
```

## Benefits Achieved

1. **Backward Compatibility**: All existing code continues to work
2. **Separate Plugin Entries**: Original napari menu structure preserved
3. **Cleaner Architecture**: Data/UI separation where desired
4. **Signal Coordination**: Better communication between plugin types
5. **Gradual Migration**: Can adopt new patterns incrementally

## File Structure

### New Files
- `_data_management.py` - Pure data operations
- `_signal_hub.py` - Signal coordination
- `_modern_base.py` - Alternative base class
- `_layout_utils.py` - Layout utilities

### Updated Files
- `_widgets.py` - Uses signal hub for widget coordination
- `_util_classes/layer_corrector.py` - Uses composition internally
- `napari.yaml` - Keeps original plugin entries

### Removed Files
- None (maintains full backward compatibility)

## Usage Examples

### Creating the Plugin Widgets

```python
# In napari - both entries remain available
viewer = napari.Viewer()

# Original separate entries still work
lineage_widget = LineageTreeAnalysisWidget(viewer)
embryo_widget = CrossEmbryoManagerComparisonWidget(viewer)

viewer.window.add_dock_widget(lineage_widget, name="Lineage Analysis")
viewer.window.add_dock_widget(embryo_widget, name="Cross-Embryo Analysis")
```

### Signal Coordination Example

```python
# Signals now coordinated through signal hub
# LineageTreeAnalysisWidget automatically connects:
# "Explore and Relabel" line edit → signal_hub → "Distance Calculation"
# "Attribute Recoloring" colors → signal_hub → "Explore and Relabel"

# CrossEmbryoManagerComparisonWidget automatically connects:
# "Manager" ready → signal_hub → "Embryo comparisons"
```

## Testing

Run the example to verify the refactored architecture:

```bash
python example_new_architecture.py
```

This demonstrates:
- Signal hub coordination
- Data manager operations  
- Backward compatibility
- Layout utilities
- Modern widget alternatives

## Future Enhancements

1. **Widget-specific signal hubs**: Each plugin type could have its own hub
2. **Configuration management**: Centralized settings across plugin types
3. **Plugin registration system**: Easier addition of new analysis widgets
4. **Performance optimization**: Shared caching between plugin types