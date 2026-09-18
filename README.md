# napari-relax

[![License BSD-3](https://img.shields.io/pypi/l/napari-relax.svg?color=green)](https://github.com/guignardlab/napari-relax/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/napari-relax.svg?color=green)](https://pypi.org/project/napari-relax)
[![Python Version](https://img.shields.io/pypi/pyversions/napari-relax.svg?color=green)](https://python.org)
[![tests](https://github.com/guignardlab/napari-relax/workflows/tests/badge.svg)](https://github.com/guignardlab/napari-relax/actions)
[![codecov](https://codecov.io/gh/guignardlab/napari-relax/branch/main/graph/badge.svg)](https://codecov.io/gh/guignardlab/napari-relax)
[![napari hub](https://img.shields.io/endpoint?url=https://api.napari-hub.org/shields/napari-relax)](https://napari-hub.org/plugins/napari-relax)
[![npe2](https://img.shields.io/badge/plugin-npe2-blue?link=https://napari.org/stable/plugins/index.html)](https://napari.org/stable/plugins/index.html)
[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-purple.json)](https://github.com/copier-org/copier)

**ReLAX** (Reconstructed Lineage Analysis & eXploration) is a [napari] plugin to visualise and compare cell lineage trees. It gives [LineageTree] datasets a graphical interface, so no programming is needed.

**Documentation: [guignardlab.github.io/napari-relax](https://guignardlab.github.io/napari-relax/)**

## Features

- **Explore** tracking datasets in the napari viewer and in an interactive Lineage Viewer, side by side.
- **Relabel** lineages and save them as `.lT` files.
- **Recolor** cells by clone or by any numeric attribute of the dataset.
- **Compare** lineages and sublineages with unordered tree edit distances, shown as an interactive clustermap.
- **Compare across datasets**, even with different time resolutions.

ReLAX opens `.lT`, MaMuT and ASTEC `.xml`, Mastodon and `.bmf` files, and comes with two demo datasets under **File > Open Sample > ReLAX**.

## Installation

ReLAX requires Python 3.10 or newer and napari 0.9 or newer. You can install `napari-relax` via [pip]:

```
pip install napari-relax
```

If napari is not already installed, you can install `napari-relax` with napari and Qt via:

```
pip install "napari-relax[all]"
```

To install the latest development version:

```
pip install git+https://github.com/guignardlab/napari-relax.git
```

Then open **Plugins > Lineage tree analysis** or **Plugins > Cross Lineagetree comparison** in napari. The [Quick Start](https://guignardlab.github.io/napari-relax/quick_start/q_start/) walks through a first session.

## Contributing

Contributions are very welcome. Tests can be run with [tox], please ensure
the coverage at least stays the same before you submit a pull request.

The documentation is built with [MkDocs] from the `docs/` folder and published automatically when `main` changes. To preview it locally:

```
pip install -e ".[docs]"
mkdocs serve
```

See the [developer documentation](https://guignardlab.github.io/napari-relax/developer/architecture/) for an overview of the code.

## License

Distributed under the terms of the [BSD-3] license,
"napari-relax" is free and open source software

## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

----------------------------------

This [napari] plugin was generated with [copier] using the [napari-plugin-template].

[napari]: https://github.com/napari/napari
[LineageTree]: https://guignardlab.github.io/LineageTree/
[copier]: https://copier.readthedocs.io/en/stable/
[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[napari-plugin-template]: https://github.com/napari/napari-plugin-template
[MkDocs]: https://www.mkdocs.org/
[file an issue]: https://github.com/guignardlab/napari-relax/issues
[tox]: https://tox.readthedocs.io/en/latest/
[pip]: https://pypi.org/project/pip/
