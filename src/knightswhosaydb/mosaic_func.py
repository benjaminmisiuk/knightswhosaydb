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
from tqdm.auto import tqdm

from .avg_func import compute_avg
from .rasterize_func import write_raster, merge_lines, grid_line

def mosaic(
    dir_path,
    format, #'fmgt' or 'kmall'
    layer = 'backscatter', #'backscatter', 'raw' or 'depth'
    out_lines = None,
    mosaic_path = 'Mosaic.tif',
    template_path = None,
    crs = None,
    save_lines = False,
    verbose = False,
    **kwargs
):
    if layer == 'backscatter':
        is_bathy = False
        var_key = 'back'
    elif layer == 'raw':
        is_bathy = False
        var_key = 'raw'
    elif layer == 'depth':
        is_bathy = True
        var_key = 'bathy'
    else:
        raise ValueError("Invalid layer. Must be 'backscatter', 'depth' or 'raw'.")

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

    match format:
        case 'kmall':
            import themachinethatgoesping as theping
            files, index = theping.echosounders.index_functions.find_files_and_index(dir_path, ['.kmall'], index_root=out_lines)
            files.sort()
        case 'all':
            import themachinethatgoesping as theping
            files, index = theping.echosounders.index_functions.find_files_and_index(dir_path, ['.all'], index_root=out_lines)
            files.sort()
        case 'fmgt':
            files = glob.glob(os.path.join(dir_path, "*.txt"))
        case _:
            raise ValueError(f"Unsupported format: {format}. Supported formats are 'kmall', 'all' and 'fmgt'.")

    prg = tqdm(files, desc="Processing files", unit="file")
    for k, file_k in enumerate(prg):
        prg.set_postfix(file=os.path.basename(file_k))
        match format:
            case 'kmall':
                from .kmall_func import read_kmall
                f = read_kmall(file_k, index, **kwargs)
            case 'all':
                from .kongsbergall_func import read_kongsbergall
                f = read_kongsbergall(file_k, index, **kwargs)
            case 'fmgt':
                from .fmgt_func import read_fmgt
                f = read_fmgt(file_k, **kwargs)

        if is_bathy:
            avg = compute_avg(bs_line=f, apply_avg=False, verbose=verbose, **kwargs)
            if len(avg['depth']) == 0 or avg['depth'].isna().all() or avg['east'].isna().all() or avg['north'].isna().all():
                if verbose:
                    print(f"  No valid bathymetry data in file {k+1} after filtering (check frequency, back_filter, or other parameters)")
                continue
            a = grid_line(avg, template_path=template_path, save_bathy=True, **kwargs)
        elif var_key == 'raw':
            avg = compute_avg(bs_line=f, apply_avg=False, verbose=verbose, **kwargs)
            if avg.empty or avg['back'].size == 0 or np.all(np.isnan(avg['back'])) or avg['east'].isna().all() or avg['north'].isna().all():
                if verbose:
                    print(f"  No valid backscatter data in file {k+1} after filtering (check frequency, back_filter, or other parameters)")
                continue
            a = grid_line(avg, template_path=template_path, save_raw=True, **kwargs)
        else:
            avg = compute_avg(bs_line=f, apply_avg=True, verbose=verbose, **kwargs)
            if avg.empty or len(avg['back_avg']) == 0 or avg['east'].isna().all() or avg['north'].isna().all():
                if verbose:
                    print(f"  No valid backscatter data in file {k+1} after filtering (check frequency, back_filter, or other parameters)")
                continue
            a = grid_line(avg, template_path=template_path, save_bathy=False, **kwargs)

        #line_arr chooses the bathy or back output from AVG()
        line_arr = a[var_key]

        #skip remainder of this file if empty
        if line_arr is None:
            if verbose:
                print(f"  No valid data in file {k+1} after filtering (check frequency, back_filter, or other parameters)")
            continue

        write_raster(os.path.join(out_lines, f'{prefix}_{k}.tif'), line_arr, a, crs=crs)

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

    if verbose:
        print(f"Found {len(r_files)} raster files to mosaic")
    
    #load all rasters as a list
    r_mosaic, grid_param = merge_lines(r_files, template_path=template_path, method='median')
    write_raster(mosaic_path, r_mosaic, grid_param, crs=crs)

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
