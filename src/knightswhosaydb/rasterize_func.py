import gc
import warnings

import numpy as np
from scipy.stats import binned_statistic_2d


def get_grid_params(data=None, template_path=None, bounds=None, res=1.0):
    #read a template raster with desired extent and resolution
    if template_path is not None:
        import rasterio
        with rasterio.open(template_path) as tmp:
            meta = tmp.meta.copy()
            xmin, ymin, xmax, ymax = tmp.bounds
            width = tmp.width
            height = tmp.height
            res_x, res_y = tmp.res
        x_edges = np.linspace(xmin, xmax, width + 1)
        y_edges = np.linspace(ymin, ymax, height + 1)
    else:
        meta = None
        res_x = res_y = res
        if bounds is not None:
            xmin, xmax, ymin, ymax = bounds[0], bounds[1], bounds[2], bounds[3]
        else:
            xmin, xmax = data['east'].min(), data['east'].max()
            ymin, ymax = data['north'].min(), data['north'].max()
        if np.isnan(xmin) or np.isnan(xmax) or np.isnan(ymin) or np.isnan(ymax):
            raise ValueError(
                f"Cannot compute grid parameters: data contains no valid coordinates. xmin={xmin}, xmax={xmax}, ymin={ymin}, ymax={ymax}. Check that your frequency and filtering parameters result in valid data.")
        width = int(np.ceil((xmax - xmin) / res))
        height = int(np.ceil((ymax - ymin) / res))
        #snap edges to an exact pixel size so every line shares the same resolution
        x_edges = xmin + np.arange(width + 1) * res
        y_edges = ymin + np.arange(height + 1) * res
        xmax = xmin + width * res
        ymax = ymin + height * res

    return {
        'meta': meta,
        'xmin': xmin,
        'xmax': xmax,
        'ymin': ymin,
        'ymax': ymax,
        'x_edges': x_edges,
        'y_edges': y_edges,
        'width': width,
        'height': height,
        'res_x': res_x,
        'res_y': res_y,
    }


def grid_line(data, template_path=None, bounds=None, res=1.0, save_raw=False, save_bathy=False, **kwargs):
    grid_params = get_grid_params(data, template_path=template_path, bounds=bounds, res=res)

    x_edges = grid_params['x_edges']
    y_edges = grid_params['y_edges']
    shape = (grid_params['height'], grid_params['width'])

    def _grid(values, statistic):
        if data.empty:
            return np.full(shape, np.nan, dtype=np.float32)
        stat, _, _, _ = binned_statistic_2d(
            x=data['east'], y=data['north'], values=values,
            statistic=statistic, bins=[x_edges, y_edges]
        )
        return np.flipud(stat.T).astype(np.float32)

    output = dict(grid_params)
    output['raw'] = _grid(data['back'], 'mean') if save_raw else None
    output['bathy'] = _grid(data['depth'], 'mean') if save_bathy else None
    output['back'] = _grid(data['back_avg'], 'median')
    return output


def write_raster(path, array, grid_params, crs=None):
    import rasterio

    def build_meta(grid_params, crs=None):
        #reuse the template metadata when gridding onto a template
        if grid_params['meta'] is not None:
            return grid_params['meta']

        return {
            'driver': 'GTiff',
            'dtype': 'float32',
            'nodata': np.nan,
            'count': 1,
            'width': grid_params['width'],
            'height': grid_params['height'],
            'crs': crs,
            'transform': rasterio.transform.from_bounds(
                west=grid_params['xmin'],
                south=grid_params['ymin'],
                east=grid_params['xmax'],
                north=grid_params['ymax'],
                width=grid_params['width'],
                height=grid_params['height'],
            ),
        }
    meta = build_meta(grid_params, crs=crs)
    
    with rasterio.open(path, 'w', **meta) as dst:
        dst.write(array, 1)


def merge_lines(r_files, template_path=None, method='median'):
    import rasterio
    import rasterio.warp
    from rasterio.merge import merge

    if template_path is not None:
        #every line already shares the template grid, so stack them directly
        with rasterio.open(template_path) as tmp:
            out_meta = tmp.meta.copy()
        layers = []
        for rf in r_files:
            with rasterio.open(rf) as src:
                layers.append(src.read(1))
        cube = np.stack(layers)
    else:
        src_datasets = [rasterio.open(rf) for rf in r_files]
        #determine total extent and resample every line onto it
        temp_arr, master_transform = merge(src_datasets, method='count')
        master_height, master_width = temp_arr.shape[1], temp_arr.shape[2]
        master_crs = src_datasets[0].crs
        del temp_arr
        cube = np.full((len(src_datasets), master_height, master_width), np.nan, dtype=np.float32)
        for i, src in enumerate(src_datasets):
            rasterio.warp.reproject(
                source=rasterio.band(src, 1),
                destination=cube[i, :, :],
                src_transform=src.transform,
                src_crs=src.crs,
                src_nodata=np.nan,
                dst_transform=master_transform,
                dst_crs=master_crs,
                dst_nodata=np.nan,
                resampling=rasterio.warp.Resampling.bilinear
            )
            src.close()
        del src_datasets
        out_meta = {
            'driver': 'GTiff',
            'dtype': 'float32',
            'nodata': np.nan,
            'count': 1,
            'width': master_width,
            'height': master_height,
            'crs': master_crs,
            'transform': master_transform,
        }

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        if method == 'mean':
            r_mosaic = np.nanmean(cube, axis=0)
        else:
            r_mosaic = np.nanmedian(cube, axis=0)
    del cube
    gc.collect()
    out_meta={
        'meta' : out_meta
    }

    return r_mosaic, out_meta
