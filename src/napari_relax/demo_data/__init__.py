from ._load_demo import load_demo, load_c_elegans
from ._download_utils import (
    ensure_demo_data,
    get_cached_datasets,
    clear_cache,
)
from ._datasets import DEMO_DATASETS

__all__ = [
    "load_demo",
    "load_c_elegans",
    "ensure_demo_data", 
    "get_cached_datasets",
    "clear_cache",
    "DEMO_DATASETS"
]
