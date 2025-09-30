#!/usr/bin/env python3
"""
Test the actual widget creation and signal flow.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_widget_signal_flow():
    print("=== Testing Widget Signal Flow ===")
    
    # Test 1: Create signal hub like the plugin does
    print("\n1. Creating Signal Hub:")
    from napari_relax._signal_hub import PluginSignalHub
    signal_hub = PluginSignalHub()
    print(f"✓ Signal hub created")
    
    # Test 2: Create a mock widget and register it
    print("\n2. Testing Widget Registration:")
    
    class MockLineageExplorer:
        def __init__(self):
            self.name = "Mock Explore and Relabel"
            self.color_mapping_calls = []
            self.quantitative_calls = []
            self.color_change_calls = []
            
        def update_lineage_tree(self, lineage_tree):
            pass
            
        def handle_selection_change(self, selected_ids):
            pass
            
        def handle_color_change(self, color_mapping):
            self.color_change_calls.append(color_mapping)
            print(f"  → handle_color_change called with: {list(color_mapping.keys())}")
            
        def handle_label_update(self, label_text):
            pass
            
        def handle_color_mapping(self, mapping_data):
            self.color_mapping_calls.append(mapping_data)
            print(f"  → handle_color_mapping called with type: {mapping_data.get('type')}")
            
        def handle_quantitative_coloring(self, coloring_data):
            self.quantitative_calls.append(coloring_data)
            print(f"  → handle_quantitative_coloring called")
    
    # Register the mock widget
    mock_widget = MockLineageExplorer()
    signal_hub.register_widget("Mock Explore and Relabel", mock_widget)
    
    registered_widgets = signal_hub.get_registered_widgets()
    print(f"✓ Widget registered. Total widgets: {len(registered_widgets)}")
    print(f"  Registered widgets: {registered_widgets}")
    
    # Test 3: Emit signals and see what gets called
    print("\n3. Testing Signal Emission:")
    
    # Test color mapping update (new structured signal)
    mapping_data = {
        'type': 'quantitative',
        'node_colors': {1: [1, 0, 0, 1], 2: [0, 1, 0, 1]},
        'face_colors': [[1, 0, 0, 1], [0, 1, 0, 1]],
        'source': 'test'
    }
    
    print("  Emitting color_mapping_update...")
    signal_hub.emit_color_mapping_update(mapping_data)
    
    # Test quantitative coloring (new structured signal)
    quantitative_data = {
        'node_colors': {1: [1, 0, 0, 1], 2: [0, 1, 0, 1]},
        'face_colors': [[1, 0, 0, 1], [0, 1, 0, 1]],
        'selected_nodes': {1, 2},
        'colormap': 'viridis',
        'attribute': 'test_attr'
    }
    
    print("  Emitting quantitative_coloring...")
    signal_hub.emit_quantitative_coloring(quantitative_data)
    
    # Test old-style color change (widget-compatible signal)
    legacy_data = {
        'quantitative_coloring': True,
        'node_colors': {1: [1, 0, 0, 1], 2: [0, 1, 0, 1]},
        'face_colors': [[1, 0, 0, 1], [0, 1, 0, 1]]
    }
    
    print("  Emitting colors_changed...")
    signal_hub.colors_changed.emit(legacy_data)
    
    # Test 4: Check what was received
    print("\n4. Checking Results:")
    print(f"  handle_color_mapping calls: {len(mock_widget.color_mapping_calls)}")
    print(f"  handle_quantitative_coloring calls: {len(mock_widget.quantitative_calls)}")
    print(f"  handle_color_change calls: {len(mock_widget.color_change_calls)}")
    
    success = (
        len(mock_widget.color_mapping_calls) > 0 and
        len(mock_widget.quantitative_calls) > 0 and
        len(mock_widget.color_change_calls) > 0
    )
    
    if success:
        print("✓ All signal types received by widget")
    else:
        print("✗ Some signals not received")
        
    return success

if __name__ == "__main__":
    success = test_widget_signal_flow()
    if success:
        print("\n🎉 Widget signal flow test passed!")
    else:
        print("\n❌ Widget signal flow test failed!")
        sys.exit(1)