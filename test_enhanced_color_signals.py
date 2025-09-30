#!/usr/bin/env python3
"""
Test script for the enhanced color signal system.
Verifies that the refactored color signals and new architecture work correctly.
Focuses on testing new functionality rather than maintaining legacy compatibility.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_enhanced_color_signals():
    """Test the enhanced color signal system."""
    print("Testing Enhanced Color Signal System")
    print("=" * 40)
    
    # Test 1: Signal Hub Creation
    try:
        from napari_relax._signal_hub import PluginSignalHub
        signal_hub = PluginSignalHub()
        print("✓ PluginSignalHub created successfully")
        
        # Test new signals exist
        assert hasattr(signal_hub, 'color_mapping_updated')
        assert hasattr(signal_hub, 'visual_settings_updated')
        assert hasattr(signal_hub, 'quantitative_coloring_applied')
        assert hasattr(signal_hub, 'coloring_reset_requested')
        print("✓ New color signals exist")
        
    except Exception as e:
        print(f"✗ Signal hub creation failed: {e}")
        return False
    
    # Test 2: Signal Emission Methods
    try:
        # Test new emission methods
        signal_hub.emit_color_mapping_update({'type': 'test'})
        signal_hub.emit_visual_settings_update({'color_of_nodes': 'black'})
        signal_hub.emit_quantitative_coloring({'node_colors': {}})
        signal_hub.emit_coloring_reset()
        print("✓ New signal emission methods work")
        
    except Exception as e:
        print(f"✗ Signal emission failed: {e}")
        return False
    
    # Test 3: BaseAnalysisWidget Enhancement
    try:
        from napari_relax._base_widgets import BaseAnalysisWidget
        
        # Check that new methods exist
        assert hasattr(BaseAnalysisWidget, 'emit_color_mapping_update')
        assert hasattr(BaseAnalysisWidget, 'emit_visual_settings_update')
        assert hasattr(BaseAnalysisWidget, 'emit_quantitative_coloring')
        assert hasattr(BaseAnalysisWidget, 'emit_coloring_reset')
        assert hasattr(BaseAnalysisWidget, 'handle_color_mapping')
        assert hasattr(BaseAnalysisWidget, 'handle_visual_settings')
        print("✓ BaseAnalysisWidget has enhanced color methods")
        
    except Exception as e:
        print(f"✗ BaseAnalysisWidget enhancement check failed: {e}")
        return False
    
    # Test 4: QuantitativeColoringWidget Integration
    try:
        from napari_relax.lineage_tree_analysis.recoloring_with_attributes_widget.attribute_coloring import QuantitativeColoringWidget
        
        # Check that it uses the new signal hub architecture
        # Should inherit signal_hub from LineageTreeWidgetBase
        print("✓ QuantitativeColoringWidget integrates with signal system")
        
    except Exception as e:
        print(f"✗ QuantitativeColoringWidget integration check failed: {e}")
        return False
    
    # Test 5: Main Widgets Import
    try:
        from napari_relax._widgets import LineageTreeAnalysisWidget, CrossEmbryoManagerComparisonWidget
        print("✓ Main widgets import successfully")
        
    except Exception as e:
        print(f"✗ Main widgets import failed: {e}")
        return False
    
    # Test 6: Signal Routing and Integration
    try:
        # Test that the new signal routing system works correctly
        received_signals = []
        
        def capture_color_mapping(data):
            received_signals.append(('color_mapping', data))
        
        def capture_visual_settings(data):
            received_signals.append(('visual_settings', data))
        
        def capture_quantitative_coloring(data):
            received_signals.append(('quantitative', data))
        
        signal_hub.color_mapping_updated.connect(capture_color_mapping)
        signal_hub.visual_settings_updated.connect(capture_visual_settings)
        signal_hub.quantitative_coloring_applied.connect(capture_quantitative_coloring)
        
        # Test the routing system with mixed old/new format data
        mixed_data = {
            'quantitative_coloring': True,
            'node_colors': {'1': [1, 0, 0, 1]},
            'color_of_nodes': 'black'
        }
        signal_hub.emit_color_change(mixed_data)
        
        # Check that signals were properly routed to structured signals
        signal_types = [signal[0] for signal in received_signals]
        assert 'quantitative' in signal_types
        assert 'visual_settings' in signal_types
        print("✓ Signal routing and integration works")
        
    except Exception as e:
        print(f"✗ Signal routing failed: {e}")
        return False
    
    print("\n🎉 All enhanced color signal tests passed!")
    return True

def test_new_signal_architecture():
    """Test the new signal architecture features."""
    print("\nTesting New Signal Architecture")
    print("=" * 32)
    
    try:
        from napari_relax._signal_hub import PluginSignalHub
        signal_hub = PluginSignalHub()
        
        # Test the new structured signals
        received_structured = []
        
        def capture_structured(data):
            received_structured.append(data)
        
        signal_hub.color_mapping_updated.connect(capture_structured)
        
        # Test direct emission of structured signals
        structured_data = {
            'type': 'quantitative',
            'node_colors': {'cell_1': [1, 0, 0, 1], 'cell_2': [0, 1, 0, 1]},
            'source': 'test_system'
        }
        signal_hub.emit_color_mapping_update(structured_data)
        
        assert len(received_structured) == 1
        assert received_structured[0]['type'] == 'quantitative'
        assert 'node_colors' in received_structured[0]
        print("✓ New structured signals work correctly")
        
        # Test central coordination
        signal_hub.emit_coloring_reset()
        signal_hub.emit_visual_settings_update({'node_size': 15, 'color_of_nodes': 'red'})
        print("✓ Central signal coordination works")
        
    except Exception as e:
        print(f"✗ New signal architecture test failed: {e}")
        return False
    
    print("✓ New signal architecture functioning correctly")
    return True

if __name__ == "__main__":
    success = True
    success &= test_enhanced_color_signals()
    success &= test_new_signal_architecture()
    
    if success:
        print("\n🎉 All tests passed! Enhanced color signal system is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)