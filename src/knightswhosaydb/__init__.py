"""knightswhosaydb — Multibeam backscatter reading and processing

"""

from importlib.metadata import version as _version
from .mosaic_func import mosaic
from .fmgt_func import read_fmgt
from .kmall_func import read_kmall
from .kongsbergall_func import read_kongsbergall
from .avg_func import AVG
from .rasterize_func import get_grid_params, grid_line, write_raster, merge_lines

__version__ = _version("knightswhosaydb")

__all__ = [
    "mosaic",
    "read_fmgt",
    "read_kmall",
    "read_kongsbergall",
    "AVG",
    "get_grid_params",
    "grid_line",
    "write_raster",
    "merge_lines",
]
