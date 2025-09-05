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
from ._datasets import DEMO_DATASETS, load_demo_datasets, save_demo_datasets
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
        print("Proposed configuration:")
        print(f'    "{suggested_name}": {{')
        print(f'        "filename": "{info["filename"]}",')
        print(
            '        "url": null,  # Set after uploading to hosting platform'
        )
        print(f'        "md5": "{info["md5"]}",')
        print(
            '        "description": "Demo dataset",  # Update with proper description'
        )
        print(f'        "size_mb": {info["size_mb"]}')
        print("    }},")

    return [
        {
            "name": filepath.stem.replace("_demo", "").replace("-", "_").lower(),
            "config": {
                "filename": calculate_file_info(filepath)["filename"],
                "url": None,
                "md5": calculate_file_info(filepath)["md5"],
                "description": "Demo dataset",
                "size_mb": calculate_file_info(filepath)["size_mb"]
            }
        }
        for filepath in unconfigured_files
    ]


def add_datasets_interactively(proposed_datasets):
    """Interactively add new datasets to configuration."""
    if not proposed_datasets:
        return

    print(f"\n{'='*60}")
    print("INTERACTIVE DATASET ADDITION")
    print(f"{'='*60}")

    datasets = load_demo_datasets()
    added_count = 0

    for proposal in proposed_datasets:
        print(f"\nDataset: '{proposal['name']}'")
        print(f"File: {proposal['config']['filename']}")
        print(f"MD5: {proposal['config']['md5']}")
        print(f"Size: {proposal['config']['size_mb']} MB")

        while True:
            choice = input("\nAdd this dataset? (y/n/e=edit name): ").lower().strip()

            if choice == 'y':
                datasets[proposal['name']] = proposal['config']
                print(f"✅ Added dataset '{proposal['name']}'")
                added_count += 1
                break
            elif choice == 'n':
                print(f"⏭️  Skipped dataset '{proposal['name']}'")
                break
            elif choice == 'e':
                new_name = input(f"Enter new name (current: {proposal['name']}): ").strip()
                if new_name and new_name not in datasets:
                    proposal['name'] = new_name
                    print(f"📝 Name updated to '{new_name}'")
                elif new_name in datasets:
                    print(f"❌ Name '{new_name}' already exists. Try again.")
                else:
                    print("❌ Invalid name. Try again.")
            else:
                print("Please enter 'y', 'n', or 'e'")

    if added_count > 0:
        save_demo_datasets(datasets)
        print(f"\n🎉 Successfully added {added_count} dataset(s) to configuration!")
        print("💡 Remember to:")
        print("   1. Update descriptions in datasets.json")
        print("   2. Upload files to hosting platforms")
        print("   3. Update URLs in datasets.json")
        print("   4. Create loading functions in _load_demo.py")
        print("   5. Register with napari in napari.yaml")
    else:
        print("\n📝 No datasets were added.")


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
    proposed_datasets = propose_configurations(unconfigured_files)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Configured files: {len(configured_files)}")
    print(f"Unconfigured files: {len(unconfigured_files)}")

    if unconfigured_files:
        print(f"\nFound {len(unconfigured_files)} unconfigured file(s).")

        choice = input("Would you like to add them interactively? (y/n): ").lower().strip()
        if choice == 'y':
            add_datasets_interactively(proposed_datasets)
        else:
            print("\nTo add unconfigured files manually:")
            print("1. Copy the proposed configuration above")
            print("2. Add it to datasets.json")
            print("3. Update the description field with meaningful text")
            print("4. Create a loading function in _load_demo.py")
            print("5. Register with napari in napari.yaml")

    if configured_files:
        print("\nConfigured files are ready for upload to hosting platforms.")
        print(
            "Remember to update the 'url' field in datasets.json after upload."
        )


if __name__ == "__main__":
    setup_demo_config()
