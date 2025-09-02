#!/usr/bin/env python3
"""
Setup script for configuring demo data downloads.

This script helps you:
1. Calculate MD5 hashes and file sizes for demo files in the directory
2. Check which files are already configured in _datasets.py
3. Propose configuration for new .lT files found in the directory

Usage:
    python setup_demo_config.py
"""

from pathlib import Path

# Import the actual configuration
from ._datasets import DEMO_DATASETS
from ._download_utils import calculate_md5


def scan_demo_files():
    """Scan for .lT files in the demo directory and check their configuration status."""
    demo_dir = Path(__file__).parent
    lt_files = list(demo_dir.glob("*.lT"))

    # Get list of already configured filenames
    configured_files = {
        config["filename"] for config in DEMO_DATASETS.values()
    }

    print("Found .lT files in demo directory:")
    print("-" * 40)

    configured_found = []
    unconfigured_found = []

    for filepath in lt_files:
        if filepath.name in configured_files:
            configured_found.append(filepath)
            print(f"✅ {filepath.name} (already configured)")
        else:
            unconfigured_found.append(filepath)
            print(f"❓ {filepath.name} (not configured)")

    return configured_found, unconfigured_found


def calculate_file_info(filepath: Path):
    """Calculate file information for a given file."""
    md5_hash = calculate_md5(filepath)
    size_mb = filepath.stat().st_size / (1024 * 1024)
    return {
        "filename": filepath.name,
        "md5": md5_hash,
        "size_mb": round(size_mb, 2),
        "size_bytes": filepath.stat().st_size,
    }


def show_configured_files(configured_files):
    """Show information about files that are already configured."""
    if not configured_files:
        return

    print("\n" + "=" * 60)
    print("CONFIGURED FILES - File Information")
    print("=" * 60)

    for filepath in configured_files:
        # Find the dataset name for this file
        dataset_name = None
        for name, config in DEMO_DATASETS.items():
            if config["filename"] == filepath.name:
                dataset_name = name
                break

        info = calculate_file_info(filepath)
        config = DEMO_DATASETS[dataset_name]

        print(f"\nDataset: '{dataset_name}'")
        print(f"  File: {info['filename']}")
        print(f"  Actual MD5: {info['md5']}")
        print(f"  Configured MD5: {config['md5']}")
        print(f"  Actual size: {info['size_mb']} MB")
        print(f"  Configured size: {config['size_mb']} MB")

        # Check for mismatches
        if config["md5"] and config["md5"] != info["md5"]:
            print("  ⚠️  MD5 mismatch! Update configuration.")
        if (
            config["size_mb"]
            and abs(config["size_mb"] - info["size_mb"]) > 0.01
        ):
            print("  ⚠️  Size mismatch! Update configuration.")


def propose_configurations(unconfigured_files):
    """Propose configurations for unconfigured files."""
    if not unconfigured_files:
        return

    print("\n" + "=" * 60)
    print("UNCONFIGURED FILES - Proposed Configuration")
    print("=" * 60)

    for filepath in unconfigured_files:
        info = calculate_file_info(filepath)

        # Suggest a dataset name based on filename
        suggested_name = (
            filepath.stem.replace("_demo", "").replace("-", "_").lower()
        )

        print(f"\nFile: {info['filename']}")
        print(f"Suggested dataset name: '{suggested_name}'")
        print("Proposed configuration to add to _datasets.py:")
        print(f'    "{suggested_name}": {{')
        print(f'        "filename": "{info["filename"]}",')
        print(
            '        "url": None,  # Set after uploading to hosting platform'
        )
        print(f'        "md5": "{info["md5"]}",')
        print(
            '        "description": "Demo dataset",  # Update with proper description'
        )
        print(f'        "size_mb": {info["size_mb"]}')
        print("    }},")


def setup_demo_config():
    print("napari-relax Demo Data Configuration Helper")
    print("=" * 50)
    print()

    # Scan for files
    configured_files, unconfigured_files = scan_demo_files()

    if not configured_files and not unconfigured_files:
        print("No .lT files found in the demo directory.")
        return

    # Show configured files info
    show_configured_files(configured_files)

    # Propose configurations for unconfigured files
    propose_configurations(unconfigured_files)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Configured files: {len(configured_files)}")
    print(f"Unconfigured files: {len(unconfigured_files)}")

    if unconfigured_files:
        print("\nTo add unconfigured files:")
        print("1. Copy the proposed configuration above")
        print("2. Add it to the DEMO_DATASETS dictionary in _datasets.py")
        print("3. Update the description field with meaningful text")
        print("4. Create a loading function in _load_demo.py")
        print("5. Register with napari in napari.yaml")

    if configured_files:
        print("\nConfigured files are ready for upload to hosting platforms.")
        print(
            "Remember to update the 'url' field in _datasets.py after upload."
        )


if __name__ == "__main__":
    main()
