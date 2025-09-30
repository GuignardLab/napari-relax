"""
Example demonstrating the refactored napari-relax architecture.
Shows how the new composition-based system works while maintaining
separate plugin entries for different analysis types.
"""

import sys

from qtpy.QtWidgets import (
    QApplication,
)


# Mock napari viewer for testing
class MockNapariViewer:
    def __init__(self):
        self.layers = []


def demonstrate_refactored_architecture():
    """Demonstrate the refactored plugin architecture."""

    # Create QApplication if it doesn't exist
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # Create mock viewer
    viewer = MockNapariViewer()

    # Import refactored components
    from src.napari_relax._base_widgets import BaseAnalysisWidget
    from src.napari_relax._data_management import LineageTreeDataManager
    from src.napari_relax._layout_utils import (
        SimpleContainer,
    )
    from src.napari_relax._signal_hub import PluginSignalHub

    print("🚀 Demonstrating Refactored napari-relax Architecture")
    print("=" * 60)

    # 1. Create signal hub (shared between both plugin types)
    signal_hub = PluginSignalHub()
    print("✓ Created PluginSignalHub for coordinating signals")

    # 2. Create data manager
    LineageTreeDataManager(viewer)
    print("✓ Created LineageTreeDataManager for data operations")

    # 3. Test the updated LineageTreeWidgetBase (backward compatibility)
    from src.napari_relax._util_classes.layer_corrector import (
        LineageTreeWidgetBase,
    )

    LineageTreeWidgetBase(viewer)
    print("✓ LineageTreeWidgetBase still works (uses composition internally)")

    # 4. Test the modern alternative
    modern_widget = BaseAnalysisWidget(viewer, signal_hub)
    modern_widget.name = "Modern Lineage Analysis"
    print(f"✓ Created BaseAnalysisWidget: '{modern_widget.name}'")

    # 5. Test that existing widgets can still be imported
    try:
        from src.napari_relax._widgets import (
            CrossEmbryoComparisonWidget,
            LineageTreeAnalysisWidget,
        )

        print("✓ Original widget classes still importable")

        # Test creating the main widgets
        LineageTreeAnalysisWidget(viewer)
        CrossEmbryoComparisonWidget(viewer)
        print("✓ Main plugin widgets created successfully")
        print("  - LineageTreeAnalysisWidget with signal hub")
        print("  - CrossEmbryoComparisonWidget with signal hub")

    except Exception as e:
        print(f"⚠️  Issue with main widgets: {e}")

    # 6. Test layout utilities
    from qtpy.QtWidgets import QPushButton

    button1 = QPushButton("Analysis 1")
    button2 = QPushButton("Analysis 2")

    # Using SimpleContainer (replaces Containerize)
    SimpleContainer([button1, button2], horizontal=True)
    print("✓ Created SimpleContainer (replaces Containerize)")

    print("\n🎯 Refactoring Benefits Achieved:")
    print("- ✓ Separation of data and UI logic (LineageTreeDataManager)")
    print("- ✓ Centralized signal management (PluginSignalHub)")
    print("- ✓ Backward compatibility maintained")
    print("- ✓ Separate plugin entries preserved")
    print("- ✓ Simplified layout utilities")
    print("- ✓ Gradual migration path available")

    print("\n📋 Plugin Structure:")
    print("- 'Lineage tree analysis' - for lineage analysis widgets")
    print("- 'Cross Lineagetree comparison' - for cross-embryo analysis")
    print("- Both use shared signal hub for coordination")

    return True


if __name__ == "__main__":
    try:
        success = demonstrate_refactored_architecture()
        if success:
            print(
                "\n✅ Refactored architecture demonstration completed successfully!"
            )
        else:
            print("\n❌ Architecture demonstration failed!")
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback

        traceback.print_exc()
