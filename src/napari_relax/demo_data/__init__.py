"""Demo datasets available under File > Open Sample > ReLAX.

Datasets are described in ``datasets.json`` and downloaded on
first use when they do not ship with the plugin.
"""

from ._datasets import DEMO_DATASETS, load_demo_datasets, save_demo_datasets
from ._download_utils import (
    clear_cache,
    ensure_demo_data,
    get_cached_datasets,
)
from ._load_demo import load_celegans, load_demo
from ._setup_demo_config import setup_demo_config

__all__ = [
    "load_demo",
    "ensure_demo_data",
    "get_cached_datasets",
    "clear_cache",
    "setup_demo_config",
    "DEMO_DATASETS",
    "save_demo_datasets",
    "load_demo_datasets",
    "load_celegans",
]
