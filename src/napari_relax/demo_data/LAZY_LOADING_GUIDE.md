# Lazy Demo Data Implementation Guide

This implementation provides a comprehensive lazy loading system for napari-relax demo data that automatically downloads datasets on-demand from remote repositories like Zenodo. 

The system features automatic downloads with progress indicators when users request demo data, ensuring datasets are only downloaded when needed and cached locally to prevent re-downloading. File integrity is verified through MD5 hash validation, with corrupted files automatically re-downloaded, while network issues are handled gracefully with clear error messages and fallback mechanisms when possible. The architecture supports multiple datasets with individual configuration for sources and metadata, seamlessly integrating with napari's "Open Sample" menu without requiring changes to existing user workflows.

## Quick Start

```python
from napari_relax.demo_data import load_demo

# Load demo dataset (downloads automatically if needed)
data = load_demo()
```

## Configuration

Datasets are configured in `_datasets.py`:

```python
DEMO_DATASETS = {
    "demo": {
        "filename": "demo.lT",
        "url": "https://zenodo.org/records/XXXXX/files/demo.lT",  # Set after uploading to Zenodo
        "md5": "d601b8b9e0ebf92e2bb3f9a81915bc5f", 
        "description": "Demo lineage tree dataset",
        "size_mb": 1.09
    }
    # ... other datasets ...
}
```

### 📁 **Core Components**

1. **`_datasets.py`** - Dataset configuration registry
   - Central configuration for all available datasets
   - Includes URLs, MD5 hashes, descriptions, and metadata

2. **`_download_utils.py`** - Core download and caching system
   - Downloads data from remote repositories on-demand
   - Verifies file integrity with MD5 hashes
   - Implements local caching with automatic cleanup
   - Handles network errors gracefully

3. **`_load_demo.py`** - Demo loading functions
   - Provides dataset loading functions (e.g., `load_demo()`)
   - Uses lazy loading with automatic download
   - Integrates seamlessly with napari's sample data interface

4. **`.gitignore`** - Version control exclusions
   - Excludes downloaded files from git tracking
   - Keeps repository size minimal

### 🛠️ **Utility Scripts**

5. **`setup_demo_config.py`** - Configuration helper
   - Calculates MD5 hashes for dataset files
   - Helps prepare configuration for new datasets

6. **`test_multi_datasets.py`** - Test suite
   - Verifies system functionality
   - Tests download mechanisms and error handling

## Cache Management

```python
from napari_relax.demo_data import get_cached_datasets, clear_cache

# Check cache status
cached = get_cached_datasets()

# Clear cache for specific dataset
clear_cache("demo")

# Clear all cached data
clear_cache()
```

## 📋 **Managing Datasets**

### **Adding a New Dataset**

1. **Prepare the dataset file** and upload to a hosting service (Zenodo, etc.)

2. **Calculate file information**:
   ```bash
   # Scan demo directory and show configuration status
   python setup_demo_config.py
   ```
   This will:
   - Show information about files already configured in `_datasets.py`
   - Detect any .lT files not yet configured 
   - Propose configuration entries for new files
   - Check for mismatches between actual and configured MD5/size values

3. **Add dataset configuration** to `_datasets.py`:
   ```python
   DEMO_DATASETS = {
       # ... existing datasets ...
       "my_new_dataset": {
           "filename": "[CHOSE A NAME].lT",
           "url": "https://zenodo.org/records/XXXXX/files/my_data.lT",
           "md5": "[CALCULATED MD5 HASH]", # can be set to None
           "description": "Description of my dataset",
           "size_mb": [SIZE IN MB] # can be set to None
       }
   }
   ```

4. **Create a loading function** in `_load_demo.py`:
   ```python
   def load_my_new_dataset():
       """Load my new dataset."""
       demo_file_path = ensure_demo_data("my_new_dataset")
       demo_data = LineageTree.load(str(demo_file_path))
       demo_data.time_resolution = 1
       data = layer_preparation(demo_data, "My Dataset")
       return data
   ```

5. **Register with napari** in `napari.yaml`:
   ```yaml
   commands:
     - id: napari-relax.load_my_new_dataset
       python_name: napari_relax.demo_data:load_my_new_dataset
       title: Load My New Dataset
   
   sample_data:
     - command: napari-relax.load_my_new_dataset
       display_name: My New Dataset
       key: unique_id.X
   ```

6. **Export the function** in `__init__.py`:
   ```python
   __all__ = [
       # ... existing exports ...
       "load_my_new_dataset"
   ]
   ```

### **Removing a Dataset**

1. **Remove from `_datasets.py`**: Delete the dataset entry from `DEMO_DATASETS`

2. **Remove loading function**: Delete the corresponding function from `_load_demo.py`

3. **Remove napari registration**: Delete entries from `napari.yaml`

4. **Update exports**: Remove from `__init__.py`

5. **Clear cached files** (optional):
   ```python
   from napari_relax.demo_data import clear_cache
   clear_cache("dataset_name")
   ```

### **Updating Dataset URLs or Metadata**

Simply edit the corresponding entry in `_datasets.py`. The system will automatically use the new configuration for future downloads.

## � **How It Works**

1. User selects a sample dataset in napari ("Open Sample" menu)
2. System checks if the dataset file exists locally
3. If missing, downloads automatically from the configured URL
4. Verifies file integrity using MD5 hash
5. Caches the file for future use
6. Loads data into napari viewer

The system is backward compatible - existing users with cached data won't notice any difference, while new users get automatic downloads.

## 🎯 **Use Cases**

### **Package Maintainers**
- Reduce package size by removing bundled data
- Update datasets without releasing new package versions
- Add/remove datasets easily through configuration

### **Users**
- Automatic download of demo data when needed
- No manual download steps required
- Reliable data integrity verification

### **Researchers**
- Host datasets on professional platforms (Zenodo) with DOIs
- Version control for datasets
- Citation-ready data hosting

## �️ **Development Tools**

### **Testing**
```bash
# Test the multi-dataset system
python src/napari_relax/demo_data/test_multi_datasets.py

# Check dataset status
python -c "from napari_relax.demo_data import get_cached_datasets; print(get_cached_datasets())"
```

### **Configuration Helper**
```bash
# Scan demo directory for files and check configuration status
python src/napari_relax/demo_data/setup_demo_config.py
```

This helper script will:
- Scan for .lT files in the demo directory
- Show information about already configured files
- Propose configuration entries for unconfigured files
- Detect mismatches between actual and configured file properties

## 🌐 **Available Hosting Platforms Ideas**

The system works with any platform that provides direct download URLs:
- **[Zenodo](https://zenodo.org/)** (recommended for research data)
- **[Figshare](https://figshare.com/)** 
- **[GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)**