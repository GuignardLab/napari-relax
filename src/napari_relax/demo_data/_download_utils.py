"""
Utilities for downloading demo data from remote repositories (Zenodo, etc.)
"""

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlretrieve

from ._datasets import DEMO_DATASETS


def get_demo_data_dir() -> Path:
    """Get the directory where demo data should be stored."""
    return Path(__file__).parent


def get_cache_info_file() -> Path:
    """Get the path to the cache info file."""
    return get_demo_data_dir() / ".download_cache.json"


def calculate_md5(filepath: Path) -> str:
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def load_cache_info() -> dict[str, Any]:
    """Load download cache information."""
    cache_file = get_cache_info_file()
    if cache_file.exists():
        try:
            with open(cache_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_cache_info(cache_info: dict[str, Any]) -> None:
    """Save download cache information."""
    cache_file = get_cache_info_file()
    try:
        with open(cache_file, "w") as f:
            json.dump(cache_info, f, indent=2)
    except OSError:
        pass  # Ignore cache save errors


def verify_file_integrity(filepath: Path, expected_md5: str) -> bool:
    """Verify file integrity using MD5 hash."""
    if not filepath.exists():
        return False

    actual_md5 = calculate_md5(filepath)
    return actual_md5 == expected_md5


def download_with_progress(url: str, filepath: Path) -> None:
    """Download a file with basic progress indication."""

    def reporthook(block_num, block_size, total_size):
        if total_size > 0:
            percent = min(100, (block_num * block_size / total_size) * 100)
            print(f"\rDownloading: {percent:.1f}%", end="", flush=True)

    try:
        urlretrieve(url, filepath, reporthook=reporthook)
        print()  # New line after progress
    except URLError as e:
        raise RuntimeError(f"Failed to download {url}: {e}") from e


def ensure_demo_data(dataset_name: str = "demo") -> Path:
    """
    Ensure demo data is available locally, downloading if necessary.

    Parameters
    ----------
    dataset_name : str
        Name of the dataset to ensure is available

    Returns
    -------
    Path
        Path to the local dataset file

    Raises
    ------
    RuntimeError
        If download fails or dataset is not configured
    ValueError
        If dataset_name is not found in configuration
    """
    if dataset_name not in DEMO_DATASETS:
        raise ValueError(
            f"Unknown dataset: {dataset_name}. Available: {list(DEMO_DATASETS.keys())}"
        )

    dataset_config = DEMO_DATASETS[dataset_name]
    demo_dir = get_demo_data_dir()
    filepath = demo_dir / dataset_config["filename"]

    # Check if file exists and is valid
    if filepath.exists():
        if dataset_config["md5"] is None:
            # No hash to verify, assume file is good
            return filepath
        elif verify_file_integrity(filepath, dataset_config["md5"]):
            return filepath
        else:
            print(
                f"File {filepath} exists but has incorrect hash. Re-downloading..."
            )
            filepath.unlink()

    # Need to download
    if dataset_config["url"] is None:
        raise RuntimeError(
            f"Dataset '{dataset_name}' is not available locally and no download URL is configured. "
            f"Please ensure the dataset is uploaded to a remote repository and the URL is set in the configuration."
        )

    print(
        f"Downloading demo dataset '{dataset_name}' ({dataset_config['size_mb']:.1f} MB)..."
    )
    print("This is a one-time download that will be cached locally.")

    # Ensure directory exists
    demo_dir.mkdir(parents=True, exist_ok=True)

    # Download the file
    try:
        download_with_progress(dataset_config["url"], filepath)
    except Exception as e:  # noqa: BLE001
        if filepath.exists():
            filepath.unlink()  # Clean up partial download
        raise RuntimeError(
            f"Failed to download dataset '{dataset_name}': {e}"
        ) from e

    # Verify integrity if hash is available
    if dataset_config["md5"] is not None and not verify_file_integrity(
        filepath, dataset_config["md5"]
    ):
        filepath.unlink()
        raise RuntimeError(
            f"Downloaded file for '{dataset_name}' has incorrect hash"
        )

    # Update cache info
    cache_info = load_cache_info()
    cache_info[dataset_name] = {
        "downloaded_at": str(filepath.stat().st_ctime),
        "size_bytes": filepath.stat().st_size,
        "md5": (
            calculate_md5(filepath)
            if dataset_config["md5"] is None
            else dataset_config["md5"]
        ),
    }
    save_cache_info(cache_info)

    print(f"Successfully downloaded and cached dataset '{dataset_name}'")
    return filepath


def get_cached_datasets() -> dict[str, dict[str, Any]]:
    """Get information about cached datasets."""
    cache_info = load_cache_info()
    result = {}

    for dataset_name in DEMO_DATASETS:
        dataset_config = DEMO_DATASETS[dataset_name]
        filepath = get_demo_data_dir() / dataset_config["filename"]

        if filepath.exists():
            result[dataset_name] = {
                "filepath": str(filepath),
                "size_bytes": filepath.stat().st_size,
                "exists": True,
                "cache_info": cache_info.get(dataset_name, {}),
            }
        else:
            result[dataset_name] = {
                "filepath": str(filepath),
                "exists": False,
                "cache_info": {},
            }

    return result


def clear_cache(dataset_name: str | None = None) -> None:
    """
    Clear cached demo data.

    Parameters
    ----------
    dataset_name : str, optional
        Specific dataset to clear. If None, clears all cached data.
    """
    demo_dir = get_demo_data_dir()
    cache_info = load_cache_info()

    if dataset_name is not None:
        if dataset_name in DEMO_DATASETS:
            filepath = demo_dir / DEMO_DATASETS[dataset_name]["filename"]
            if filepath.exists():
                filepath.unlink()
                print(f"Cleared cached dataset: {dataset_name}")
            if dataset_name in cache_info:
                del cache_info[dataset_name]
                save_cache_info(cache_info)
        else:
            print(f"Unknown dataset: {dataset_name}")
    else:
        # Clear all datasets
        for dataset_name, config in DEMO_DATASETS.items():
            filepath = demo_dir / config["filename"]
            if filepath.exists():
                filepath.unlink()
                print(f"Cleared cached dataset: {dataset_name}")

        # Clear cache info
        cache_file = get_cache_info_file()
        if cache_file.exists():
            cache_file.unlink()
        print("Cleared all cached datasets")
