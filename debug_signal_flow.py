#!/usr/bin/env python3
"""
Debug script to test the signal flow from attribute coloring to lineage explorer.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_signal_flow():
    print("=== Testing Signal Flow ===")
    
    # Test 1: Import signal hub
    print("\n1. Testing Signal Hub:")
    from napari_relax._signal_hub import PluginSignalHub
    hub = PluginSignalHub()
    print(f"✓ Signal hub created with {len(hub.get_registered_widgets())} widgets")
    
    # Test 2: Create a mock lineage explorer to see if it gets registered
    print("\n2. Testing Widget Registration:")
    try:
        # Import without creating napari viewer
        from napari_relax.lineage_tree_analysis.lineage_viewer_widget.lineage_explorer import LineageExplorationWidget
        
        # Check if it has the enhanced methods
        has_color_mapping = hasattr(LineageExplorationWidget, 'handle_color_mapping')
        has_quantitative = hasattr(LineageExplorationWidget, 'handle_quantitative_coloring')
        has_color_change = hasattr(LineageExplorationWidget, 'handle_color_change')
        
        print(f"✓ LineageExplorationWidget imported")
        print(f"  - has handle_color_mapping: {has_color_mapping}")
        print(f"  - has handle_quantitative_coloring: {has_quantitative}")
        print(f"  - has handle_color_change: {has_color_change}")
        
    except Exception as e:
        print(f"✗ Failed to import LineageExplorationWidget: {e}")
        return False
    
    # Test 3: Test signal emission
    print("\n3. Testing Signal Emission:")
    try:
        # Test color mapping update
        mapping_data = {
            'type': 'quantitative',
            'node_colors': {1: [1, 0, 0, 1], 2: [0, 1, 0, 1]},
            'face_colors': [[1, 0, 0, 1], [0, 1, 0, 1]],
            'source': 'debug_test'
        }
        hub.emit_color_mapping_update(mapping_data)
        print("✓ emit_color_mapping_update successful")
        
        # Test quantitative coloring
        quantitative_data = {
            'node_colors': {1: [1, 0, 0, 1], 2: [0, 1, 0, 1]},
            'face_colors': [[1, 0, 0, 1], [0, 1, 0, 1]],
            'selected_nodes': {1, 2},
            'colormap': 'viridis',
            'attribute': 'debug_attr'
        }
        hub.emit_quantitative_coloring(quantitative_data)
        print("✓ emit_quantitative_coloring successful")
        
    except Exception as e:
        print(f"✗ Signal emission failed: {e}")
        return False
    
    # Test 4: Test attribute coloring widget
    print("\n4. Testing Attribute Coloring Widget:")
    try:
        from napari_relax.lineage_tree_analysis.recoloring_with_attributes_widget.attribute_coloring import QuantitativeColoringWidget
        print("✓ QuantitativeColoringWidget imported successfully")
        
        # Check if it inherits from the right base class
        from napari_relax._util_classes import LineageTreeWidgetBase
        is_correct_base = issubclass(QuantitativeColoringWidget, LineageTreeWidgetBase)
        print(f"  - inherits from LineageTreeWidgetBase: {is_correct_base}")
        
    except Exception as e:
        print(f"✗ Failed to import QuantitativeColoringWidget: {e}")
        return False
    
    print("\n=== Signal Flow Test Complete ===")
    return True

if __name__ == "__main__":
    success = test_signal_flow()
    if success:
        print("\n🎉 All signal flow tests passed!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)