# Knights Who Say dB

Multibeam backscatter reading and processing in Python

This package is used to read and process raw multibeam backscatter data with Python. At the very simplest, it can be used to produce a backscatter mosaic from raw. It also allows for extracting sounding information for developing bespoke processing pipelines. Reading raw datagrams is enabled by [themachinethatgoesping](https://github.com/themachinethatgoesping).

Current functionality includes:
- creating a backscatter mosaic from raw multibeam data
- quickly processing and exporting single multibeam data lines (files)
- processing multifrequency multibeam data
- extracting soundings (not mosaics) from raw multibeam files
- **free** and **open source**!

Use-cases for these processes include:
- automatically processing large amounts of data as one or many separate mosaics
- programatically mosaicking one or multiple backscatter frequencies from multifrequency systems
- extracting raw soundings to create your own backscatter mosaicking methods
- extracting soundings to perform angular backscatter analyses
- building automated processing pipelines, for example, enabling preliminary viewing and exporting of backscatter while at sea 🚢


## Status
| Format | Support | Status |
| -------- | -------- | -------- |
| FMGT ASCII | ✅ | Implemented |
| KMALL | ✅ | In development... |
| ALL | ✅ | In development... |
| GSF | ❌ | Planned |
| R2S | ❌ | Planned |
| S7K | ❌ | Planned |

## Installation
To install the package download the code or clone the repository then install on your machine using pip by pointing to the directory.
```
pip install /path/to/knightswhosaydb
```
Or install directly from the git repository.
```
pip install git+https://github.com/benjaminmisiuk/knightswhosaydb
```
Alternatively, install via [pixi](https://pixi.sh) instead, which sets up a project-local environment matching `pixi.lock`. Run the following command from within the downloaded/cloned directory.
```
pixi install
```

## Functionality
At it's most basic, the package can be used to extract soundings from raw data using [themachinethatgoesping](https://github.com/themachinethatgoesping), and grid the backscatter. 

```
from knightswhosaydb import mosaic

mosaic(
    'C:/data/MBES',
    format='kmall',
    mosaic_path='scratch/Mosaic.tif',
    crs='EPSG:32755'
)
```

Check out our [tutorials](https://github.com/benjaminmisiuk/knightswhosaydb/tree/main/tutorials) on how to fully use the package.
