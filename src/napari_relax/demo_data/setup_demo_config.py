#!/usr/bin/env python3
"""
Setup script for configuring demo data downloads.

This script helps you:
1. Calculate MD5 hashes for your current demo files
2. Generate the configuration needed for Zenodo uploads
3. Update the download configuration

Usage:
    python setup_demo_config.py
"""

import json
from pathlib import Path
import sys
import os
import hashlib

# Configuration for demo datasets (copied from _download_utils.py)
DEMO_DATASETS = {
    "demo": {
        "filename": "demo.lT",
        "url": None,  # To be set when you upload to Zenodo
        "md5": None,  # To be calculated from your file
        "description": "Demo lineage tree dataset",
        "size_mb": 1.1  # Approximate size
    },
    "c_elegans": {
        "filename": "c_elegans_demo.lT",
        "url": None,  # To be set when you upload to Zenodo
        "md5": None,  # To be calculated from your file
        "description": "C. elegans demo lineage tree dataset",
        "size_mb": None  # To be calculated when file is available
    }
}

def calculate_md5(filepath: Path) -> str:
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def calculate_current_hashes():
    """Calculate MD5 hashes for existing demo files."""
    demo_dir = Path(__file__).parent
    results = {}
    
    for dataset_name, config in DEMO_DATASETS.items():
        filepath = demo_dir / config["filename"]
        if filepath.exists():
            md5_hash = calculate_md5(filepath)
            size_mb = filepath.stat().st_size / (1024 * 1024)
            results[dataset_name] = {
                "filename": config["filename"],
                "md5": md5_hash,
                "size_mb": round(size_mb, 2),
                "size_bytes": filepath.stat().st_size
            }
            print(f"Dataset '{dataset_name}':")
            print(f"  File: {config['filename']}")
            print(f"  MD5: {md5_hash}")
            print(f"  Size: {size_mb:.2f} MB")
            print()
        else:
            print(f"Warning: {filepath} not found")
    
    return results

def update_configuration():
    """Interactive configuration update."""
    print("=" * 60)
    print("UPDATE CONFIGURATION")
    print("=" * 60)
    print()
    print("After uploading to Zenodo, update the configuration with the download URLs:")
    print()
    
    config_file = Path(__file__).parent / "_datasets.py"
    
    for dataset_name in DEMO_DATASETS:
        print(f"For dataset '{dataset_name}':")
        url = input(f"  Enter Zenodo download URL (or press Enter to skip): ").strip()
        if url:
            print(f"  URL: {url}")
            # Here you could automatically update the file, but for safety we'll just show instructions
    
    print()
    print("To update the configuration:")
    print(f"1. Open {config_file}")
    print("2. Update the DEMO_DATASETS dictionary with:")
    print("   - 'url': The Zenodo download URL")
    print("   - 'md5': The MD5 hash calculated above")
    print("   - 'size_mb': The file size calculated above")

def main():
    print("napari-relax Demo Data Configuration Setup")
    print("=" * 50)
    print()
    
    # Calculate hashes for current files
    print("Calculating file information...")
    file_info = calculate_current_hashes()
    
    if not file_info:
        print("No demo files found. Please ensure demo.lT exists in the demo_data directory.")
        return
    
    # Offer to update configuration
    if input("Would you like to update the configuration now? (y/n): ").lower().startswith('y'):
        update_configuration()
    
    print()
    print("Configuration complete!")
    print()
    print("Next steps:")
    print("1. See IMPLEMENTATION_SUMMARY.md for detailed Zenodo upload instructions")
    print("2. Update _datasets.py with the Zenodo URLs and file hashes")
    print("3. Test the download functionality")
    print("4. Remove the original demo.lT file from git")

if __name__ == "__main__":
    main()
