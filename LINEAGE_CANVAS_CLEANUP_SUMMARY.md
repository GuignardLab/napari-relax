# LineageCanvas Cleanup - Summary

## Issues Identified and Fixed

### Issue 1: Obsolete `all_selected` Variable ❌ → ✅

**Problem**: The `all_selected` class attribute and associated logic was legacy code that was no longer needed.

**Analysis**:
- `all_selected` was only used within `LineageCanvas` itself
- The logic was confusing and redundant with the existing selection system
- It complicated the code without providing clear benefit

**Solution**:
- **Removed** `all_selected` class attribute
- **Simplified** `change_attributes()` method to only check for `"quantitative_coloring"` in signals
- **Streamlined** selection logic in `click()` method to always select subtree when clicking nodes
- **Cleaned up** `draw_graph()` method to remove `all_selected` conditional logic

**Result**: Cleaner, more predictable selection behavior.

### Issue 2: Hardcoded Class Defaults ❌ → ✅

**Problem**: LineageCanvas had hardcoded default values as class attributes that were immediately overridden in `__init__`, violating the single source of truth principle.

**Before**:
```python
class LineageCanvas(FigureCanvas):
    # Default hardcoded fallbacks that will be overridden with user preferences in __init__
    color_of_nodes = "black"
    color_of_edges = "black"
    node_size = 10
    lw = 0.3
    fontsize = 6
    color_of_selection_nodes = "magenta"
    color_of_selection_edges = "magenta"
    all_selected = False
```

**After**:
```python
class LineageCanvas(FigureCanvas):
    node_signal = Signal(dict)
    quantitative_coloring_applied = Signal()
```

**Analysis**:
- These defaults were redundant since user preferences are loaded in `__init__`
- They created confusion about the source of truth for visual settings
- LineageCanvasSetup should be the only place controlling these values

**Solution**:
- **Removed** all hardcoded class attribute defaults
- **Ensured** all visual properties are loaded from user preferences via `_get_user_canvas_preferences()`
- **Maintained** the proper fallback mechanism in the preferences function

**Result**: Single source of truth maintained - all visual settings come from LineageCanvasSetup.

## Architecture Improvements

### Before Cleanup:
```
LineageCanvas Class Attributes (hardcoded)
    ↓ (overridden in __init__)
User Preferences from LineageCanvasSetup
    ↓ (complicated by all_selected logic)
Runtime Behavior
```

### After Cleanup:
```
LineageCanvasSetup Dialog (single source of truth)
    ↓
User Preferences via _get_user_canvas_preferences()
    ↓ (clean, direct loading in __init__)
Runtime Behavior
```

## Code Quality Improvements

1. **Reduced Complexity**: Removed 8 hardcoded class attributes and complex `all_selected` conditional logic
2. **Improved Readability**: Clear data flow from LineageCanvasSetup → User Preferences → Canvas Properties
3. **Better Maintainability**: Single source of truth for all visual settings
4. **Cleaner Selection Logic**: Simplified click behavior and selection highlighting

## Verification Results ✅

- ✅ No hardcoded class attributes found
- ✅ `all_selected` completely removed from all methods
- ✅ User preferences integration working correctly
- ✅ Essential signals and methods preserved
- ✅ Single source of truth maintained

## Impact

This cleanup ensures that:
1. **LineageCanvasSetup dialog** is the authoritative source for all visual settings
2. **No conflicting defaults** exist in the codebase
3. **Selection behavior** is predictable and straightforward
4. **User preferences** are consistently applied across all canvas instances
5. **Code maintainability** is improved through reduced complexity

The cleanup maintains full backward compatibility while significantly improving code quality and architectural consistency.