# Configuration for demo datasets
import json
from pathlib import Path


def load_demo_datasets():
    """Load demo datasets configuration from JSON file."""
    datasets_file = Path(__file__).parent / "datasets.json"
    with open(datasets_file) as f:
        return json.load(f)


def save_demo_datasets(datasets):
    """Save demo datasets configuration to JSON file."""
    datasets_file = Path(__file__).parent / "datasets.json"
    with open(datasets_file, "w") as f:
        json.dump(datasets, f, indent=2)


# Load the datasets
DEMO_DATASETS = load_demo_datasets()
