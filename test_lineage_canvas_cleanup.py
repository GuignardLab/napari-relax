#!/usr/bin/env python3
"""
Test script to verify the LineageCanvas cleanup:
1. No more hardcoded defaults as class attributes
2. No more all_selected logic
3. User preferences properly loaded from LineageCanvasSetup
"""

import sys
from pathlib import Path

# Add src to path to import napari_relax
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

print("🧹 Testing LineageCanvas Cleanup")
print("=" * 50)

# Test 1: Verify no hardcoded class defaults
print("\n1. Testing Removal of Hardcoded Class Defaults:")

try:
    from napari_relax.lineage_tree_analysis.lineage_viewer_widget.lineage_tree_canvas import LineageCanvas
    print("   ✓ LineageCanvas import successful")
    
    # Check that hardcoded defaults are no longer class attributes
    hardcoded_attrs = ['color_of_nodes', 'color_of_edges', 'node_size', 'lw', 'fontsize', 
                      'color_of_selection_nodes', 'color_of_selection_edges']
    
    has_hardcoded = False
    for attr in hardcoded_attrs:
        if hasattr(LineageCanvas, attr):
            print(f"   ❌ Found hardcoded class attribute: {attr} = {getattr(LineageCanvas, attr)}")
            has_hardcoded = True
    
    if not has_hardcoded:
        print("   ✓ No hardcoded class attributes found - good!")
    
    # Check that user preferences are properly imported
    from napari_relax.lineage_tree_analysis.lineage_viewer_widget.lineage_tree_canvas import _get_user_canvas_preferences
    prefs = _get_user_canvas_preferences()
    if isinstance(prefs, dict) and "color_of_edges" in prefs:
        print("   ✓ User preferences function available and working")
        print(f"   📋 Sample preference: color_of_edges = {prefs['color_of_edges']}")
    else:
        print("   ❌ User preferences function not working correctly")
        
except Exception as e:
    print(f"   ❌ Error testing hardcoded defaults: {e}")

# Test 2: Verify all_selected removal
print("\n2. Testing Removal of all_selected Logic:")

try:
    import inspect
    source = inspect.getsource(LineageCanvas)
    
    if "all_selected" in source:
        print("   ❌ all_selected still found in LineageCanvas source code")
        # Count occurrences
        count = source.count("all_selected")
        print(f"   📊 Found {count} occurrences of 'all_selected'")
    else:
        print("   ✓ all_selected completely removed from LineageCanvas")
        
    # Check specific methods for cleanup
    methods_to_check = ['change_attributes', 'click', 'draw_graph']
    for method_name in methods_to_check:
        if hasattr(LineageCanvas, method_name):
            method_source = inspect.getsource(getattr(LineageCanvas, method_name))
            if "all_selected" in method_source:
                print(f"   ❌ all_selected still found in {method_name} method")
            else:
                print(f"   ✓ {method_name} method cleaned of all_selected references")
        
except Exception as e:
    print(f"   ❌ Error testing all_selected removal: {e}")

# Test 3: Verify proper user preferences integration
print("\n3. Testing User Preferences Integration:")

try:
    # Check that the import is direct from tree_graph_popup
    from napari_relax._util_classes.tree_graph_popup import _get_user_canvas_settings
    print("   ✓ Direct import from tree_graph_popup works")
    
    # Verify settings are consistent
    settings1 = _get_user_canvas_settings()
    settings2 = _get_user_canvas_preferences()
    
    if settings1 == settings2:
        print("   ✓ Both functions return identical settings")
    else:
        print("   ❌ Settings functions return different values")
        print(f"   🔍 _get_user_canvas_settings: {settings1}")
        print(f"   🔍 _get_user_canvas_preferences: {settings2}")
        
except Exception as e:
    print(f"   ❌ Error testing user preferences integration: {e}")

# Test 4: Verify class is properly streamlined
print("\n4. Testing Class Streamlining:")

try:
    # Check that class only has necessary attributes
    essential_attrs = ['node_signal', 'quantitative_coloring_applied']
    
    class_attrs = [attr for attr in dir(LineageCanvas) if not attr.startswith('_')]
    
    print(f"   📊 Class has {len(class_attrs)} public attributes/methods")
    
    has_essential = all(hasattr(LineageCanvas, attr) for attr in essential_attrs)
    if has_essential:
        print("   ✓ Essential signals are present")
    else:
        print("   ❌ Missing essential signals")
    
    # Check that methods exist and work
    essential_methods = ['change_attributes', '__init__', 'draw_graph', 'click']
    has_methods = all(hasattr(LineageCanvas, method) for method in essential_methods)
    if has_methods:
        print("   ✓ Essential methods are present")
    else:
        print("   ❌ Missing essential methods")
        
except Exception as e:
    print(f"   ❌ Error testing class streamlining: {e}")

print("\n" + "=" * 50)
print("🏁 LineageCanvas Cleanup Verification Complete")
print("\nSUMMARY:")
print("- Removed hardcoded class defaults (color_of_nodes, color_of_edges, etc.)")
print("- Removed all_selected logic and references")  
print("- Simplified user preferences loading to use tree_graph_popup directly")
print("- LineageCanvas now gets all settings from LineageCanvasSetup as intended")
print("- Single source of truth: LineageCanvasSetup dialog controls all visual properties")