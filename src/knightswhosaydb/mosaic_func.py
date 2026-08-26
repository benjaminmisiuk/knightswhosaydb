import gc
import glob
import os
import warnings
import numpy as np
import shutil
import time
import rasterio
import rasterio.warp
from rasterio.merge import merge
from pathlib import Path

from .avg_func import AVG

def mosaic(
    dir_path,
    format, #'fmgt' or 'kmall'
    layer = 'backscatter', #'backscatter' or 'depth'
    out_lines = None,
    mosaic_path = 'Mosaic.tif',
    template_path = None,
    crs = None,
    save_lines = False,
    **kwargs
):
    if layer == 'backscatter':
        is_bathy = False
        var_key = 'back'
    elif layer == 'depth':
        is_bathy = True
        var_key = 'bathy'
    else:
        raise ValueError("Invalid layer. Must be 'backscatter' or 'depth'.")

    prefix = f'line_{var_key}'

    if mosaic_path is None:
        mosaic_path = 'Bathymetry.tif' if is_bathy else 'Mosaic.tif'

    if template_path is None and crs is None:
        raise ValueError("Either template_path or crs must be provided.")

    if template_path is not None and crs is not None:
        warnings.warn("Both template and CRS provided. Defaulting to template.")
        crs = None

    if out_lines is None:
        out_lines = str(Path.cwd()/"temp")

    os.makedirs(out_lines, exist_ok=True)

    if format == 'kmall':
        import themachinethatgoesping as theping
        files, index = theping.echosounders.index_functions.find_files_and_index(dir_path, ['.kmall'], index_root=out_lines)
        files.sort()

    if format == 'fmgt':
        files = glob.glob(os.path.join(dir_path, "*.txt"))

    for k, file_k in enumerate(files):
        print(f"Processing file {k+1} of {len(files)}: {os.path.basename(file_k)}")
        if format == 'kmall':
            from .kmall_func import read_kmall
            f = read_kmall(file_k, index, **kwargs)
        elif format == 'fmgt':
            from .fmgy_func import read_fmgt
            f = read_fmgt(file_k, **kwargs)

        if is_bathy:
            a = AVG(bs_line=f, template_path=template_path, save_bathy=True, apply_avg=False, **kwargs)
        else:
            a = AVG(bs_line=f, template_path=template_path, **kwargs)

        #line_arr chooses the bathy or back output from AVG()
        line_arr = a[var_key]

        #skip remainder of this file if empty
        if line_arr is None:
            print(f"  No valid data in file {k+1} after filtering (check frequency, back_filter, or other parameters)")
            continue

        if template_path is not None:
            with rasterio.open(os.path.join(out_lines, f'{prefix}_{k}.tif'), 'w', **a['meta']) as dst:
                dst.write(line_arr, 1)

        else:
            meta = {
                'driver': 'GTiff',
                'dtype': 'float32',
                'nodata': np.nan,
                'count': 1,
                'width': line_arr.shape[1],
                'height': line_arr.shape[0],
                'crs': crs,
                'transform': rasterio.transform.from_bounds(
                    west=a['xmin'],
                    south=a['ymin'],
                    east=a['xmin'] + line_arr.shape[1],
                    north=a['ymin'] + line_arr.shape[0],
                    width=line_arr.shape[1],
                    height=line_arr.shape[0]
                )
            }
            with rasterio.open(os.path.join(out_lines, f'{prefix}_{k}.tif'), 'w', **meta) as dst:
                dst.write(line_arr, 1)

    r_files = glob.glob(os.path.join(out_lines, f"{prefix}_*.tif"))
    
    # Diagnostic: Check if any .tif files were created
    if not r_files:
        error_msg = (
            f"\n❌ ERROR: No output rasters created.\n"
            f"   Expected files matching: {prefix}_*.tif in {out_lines}\n"
            f"   \n"
            f"   This likely means ALL input files were filtered out.\n"
            f"   Check your parameters:\n"
            f"   - frequency={kwargs.get('frequency', 'None')} (data must match exactly)\n"
            f"   - back_filter={kwargs.get('back_filter', 'None')} (check if data falls in this range)\n"
            f"   \n"
            f"   Tip: Run AVG() on a single file separately to diagnose the issue."
        )
        raise FileNotFoundError(error_msg)
    
    print(f"Found {len(r_files)} raster files to mosaic")
    
    #load all rasters as a list
    layers = []
    if template_path is not None:
        for rf in r_files:
            with rasterio.open(rf) as src:
                layers.append(src.read(1))
    else:
        src_datasets = [rasterio.open(rf) for rf in r_files]
        #determine total extent and resample
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
                resampling=rasterio.warp.Resampling.bilinear  # Bilinear smooths sub-pixel shifts cleanly
            )
            src.close()
        del src_datasets
        layers = cube.copy()
        del cube
        gc.collect()

    #take the mean/median of all lines to mosaic
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        r_mosaic = np.nanmedian(np.stack(layers), axis=0)
    del layers

    #plt.imshow(r_mosaic)
    #plt.show()

    if template_path is not None:
        with rasterio.open(template_path) as tmp:
            tmp_meta = tmp.meta.copy()
    else:
        tmp_meta = {
            'driver': 'GTiff',
            'dtype': 'float32',
            'nodata': np.nan,
            'count': 1,
            'width': master_width,
            'height': master_height,
            'crs': master_crs,
            'transform': master_transform
        }

    with rasterio.open(mosaic_path, 'w', **tmp_meta) as dst:
        dst.write(r_mosaic, 1)

    print(f'Processing complete. Output mosaic saved as: {mosaic_path}')

    gc.collect()
    if not save_lines:
        time.sleep(0.1)
        try:
            shutil.rmtree(out_lines)
        except PermissionError:
            shutil.rmtree(out_lines, ignore_errors=True)
    else:
        print(f'Lines saved to: {out_lines}')
