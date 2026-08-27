import numpy as np
import pandas as pd
import pytest

from knightswhosaydb.rasterize_func import (
    get_grid_params,
    grid_line,
    write_raster,
    merge_lines,
)


def _line(east, north, values):
    return pd.DataFrame({
        'east': east,
        'north': north,
        'back': values,
        'back_avg': values,
        'depth': values,
    })



def test_write_raster_roundtrip(tmp_path):
    rasterio = pytest.importorskip("rasterio")
    arr = np.arange(6, dtype=np.float32).reshape(2, 3)
    path = str(tmp_path / "r.tif")
    gp = get_grid_params(bounds=[0, 3, 0, 2], res=1.0)
    write_raster(path, arr, gp, crs="EPSG:32617")
    with rasterio.open(path) as src:
        assert src.width == 3 and src.height == 2
        assert src.res == (1.0, 1.0)
        np.testing.assert_array_equal(src.read(1), arr)


def test_get_grid_params_from_template(tmp_path):
    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_bounds
    path = str(tmp_path / "template.tif")
    meta = {
        'driver': 'GTiff', 'dtype': 'float32', 'nodata': np.nan,
        'count': 1, 'width': 4, 'height': 3, 'crs': "EPSG:32617",
        'transform': from_bounds(0, 0, 8, 6, 4, 3),
    }
    with rasterio.open(path, 'w', **meta) as dst:
        dst.write(np.zeros((3, 4), dtype=np.float32), 1)
    gp = get_grid_params(template_path=path)
    assert gp['width'] == 4 and gp['height'] == 3
    assert gp['res_x'] == pytest.approx(2.0)
    assert gp['meta'] is not None


def test_merge_lines_median(tmp_path):
    pytest.importorskip("rasterio")
    gp = get_grid_params(bounds=[0, 2, 0, 2], res=1.0)
    fa = str(tmp_path / "line_back_0.tif")
    fb = str(tmp_path / "line_back_1.tif")
    write_raster(fa, np.ones((2, 2), dtype=np.float32), gp, crs="EPSG:32617")
    write_raster(fb, np.full((2, 2), 3.0, dtype=np.float32), gp, crs="EPSG:32617")
    r_mosaic, out_meta = merge_lines([fa, fb])
    assert r_mosaic.shape == (2, 2)
    assert np.allclose(r_mosaic, 2.0)
    assert out_meta['meta']['width'] == 2 and out_meta['meta']['height'] == 2
