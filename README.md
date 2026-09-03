# Knights Who Say dB

Multibeam backscatter reading and processing

This package is used to read and process raw multibeam backscatter data with Python. At the very simplest, it can be used to produce a backscatter mosaic from raw. It also allows for extracting sounding information for developing bespoke processing pipelines. Reading raw datagrams is enabled by [themachinethatgoesping](https://github.com/themachinethatgoesping).

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
pip install D:\knightswhosaydb
```
Or install directly from the git repository.
```
pip install git+https://github.com/benjaminmisiuk/knightswhosaydb
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

