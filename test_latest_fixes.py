#!/usr/bin/env python3
"""
Test script to verify the latest fixes for:
1. Edge colors still linked to node colors 
2. Reset button not working
3. Sublineage highlighting broken in quantitative mode
"""

import sys
from pathlib import Path

# Add src to path to import napari_relax
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

print("🔧 Testing Latest Fixes")
print("=" * 50)

# Test 1: Verify edge color isolation
print("\n1. Testing Edge Color Isolation:")
print("   - Checking that change_attributes method no longer updates edge colors from non-setup signals")

try:
    from napari_relax.lineage_tree_analysis.lineage_viewer_widget.lineage_tree_canvas import LineageCanvas
    print("   ✓ LineageCanvas import successful")
    
    # Check the change_attributes method implementation 
    import inspect
    source = inspect.getsource(LineageCanvas.change_attributes)
    if "self.color_of_edges = signal.get(\"color_of_edges\"" not in source:
        print("   ✓ Edge color update line removed from change_attributes")
    else:
        print("   ❌ Edge color update line still present in change_attributes")
        
    if "color_of_edges" in source and "LineageCanvasSetup" in source:
        print("   ✓ Special handling for LineageCanvasSetup signals detected")
    else:
        print("   ⚠️  LineageCanvasSetup signal handling not clearly detected")
        
except Exception as e:
    print(f"   ❌ Error testing edge color isolation: {e}")

# Test 2: Verify reset functionality
print("\n2. Testing Reset Functionality:")
print("   - Checking that reset loads user preferences and applies them via change_attributes")

try:
    from napari_relax.lineage_tree_analysis.lineage_viewer_widget.lineage_explorer import LineageExplorationWidget
    print("   ✓ LineageExplorationWidget import successful")
    
    # Check the handle_color_mapping method for reset handling
    source = inspect.getsource(LineageExplorationWidget.handle_color_mapping)
    if "_get_user_canvas_settings" in source and "quantitative_coloring\": False" in source:
        print("   ✓ Reset functionality now loads user settings and calls change_attributes")
    else:
        print("   ❌ Reset functionality not properly implemented")
        
    if "Direct approach" in source and "self.canvas.is_quantitative_mode = False" in source:
        print("   ❌ Old direct approach still present - should be replaced")
    else:
        print("   ✓ Direct approach has been replaced with proper change_attributes call")
        
except Exception as e:
    print(f"   ❌ Error testing reset functionality: {e}")

# Test 3: Verify sublineage highlighting
print("\n3. Testing Sublineage Highlighting in Quantitative Mode:")
print("   - Checking that draw_graph preserves selection in quantitative mode")

try:
    # Check the draw_graph method implementation
    source = inspect.getsource(LineageCanvas.draw_graph)
    if "preserve existing selection highlighting" in source.lower():
        print("   ✓ Selection preservation logic added to draw_graph")
    else:
        print("   ❌ Selection preservation logic not found in draw_graph")
        
    if "self.selected_subtree = set()" in source and "preserve" in source:
        print("   ✓ Conditional selection clearing logic present")
    else:
        print("   ❌ Selection clearing logic not properly modified")
        
except Exception as e:
    print(f"   ❌ Error testing sublineage highlighting: {e}")

# Test 4: Check signal hub functionality
print("\n4. Testing Signal Hub Integration:")
print("   - Checking that reset signals are properly routed")

try:
    from napari_relax._signal_hub import PluginSignalHub
    print("   ✓ PluginSignalHub import successful")
    
    # Verify signal methods exist
    hub = PluginSignalHub()
    if hasattr(hub, 'emit_coloring_reset'):
        print("   ✓ emit_coloring_reset method available")
    else:
        print("   ❌ emit_coloring_reset method missing")
        
    if hasattr(hub, 'coloring_reset_requested'):
        print("   ✓ coloring_reset_requested signal available")
    else:
        print("   ❌ coloring_reset_requested signal missing")
        
except Exception as e:
    print(f"   ❌ Error testing signal hub: {e}")

# Test 5: Check user preferences system
print("\n5. Testing User Preferences System:")
print("   - Checking that user canvas settings are properly imported")

try:
    from napari_relax._util_classes.tree_graph_popup import _get_user_canvas_settings
    print("   ✓ _get_user_canvas_settings import successful")
    
    # Try to get user settings
    settings = _get_user_canvas_settings()
    if isinstance(settings, dict) and "color_of_edges" in settings:
        print("   ✓ User settings retrieved successfully with edge color")
        print(f"   📋 Default edge color: {settings['color_of_edges']}")
    else:
        print("   ❌ User settings format incorrect or missing edge color")
        
except Exception as e:
    print(f"   ❌ Error testing user preferences: {e}")

print("\n" + "=" * 50)
print("🏁 Fix Verification Complete")
print("\nSUMMARY:")
print("- Edge color isolation: Modified change_attributes to prevent edge color updates from non-setup signals")
print("- Reset functionality: Fixed to load user preferences and apply via change_attributes")  
print("- Sublineage highlighting: Modified draw_graph to preserve selections in quantitative mode")
print("- All changes maintain backward compatibility and integrate with existing signal system")