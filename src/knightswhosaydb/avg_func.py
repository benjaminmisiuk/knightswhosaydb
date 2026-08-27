import sys
import numpy as np
from scipy.stats import binned_statistic_2d
import warnings


def compute_avg(
    bs_line,
    filter_across = False,
    filter_along = False,
    save_raw = False,
    save_bathy = False,
    q_along = 0.01,
    q_across = 0.01,
    res = 1.0,
    w = 300,
    angle_intv = 5,
    ref = 40,
    frequency = None,
    back_filter = [-80, 20],
    method = 'dual',
    apply_avg = True
):
    #filtering
    mask = (bs_line['back'] > back_filter[0]) & (bs_line['back'] < back_filter[1])

    if frequency is not None:
        if bs_line['frequency'].max() > 1000:
            print("Converting frequency from Hz to kHz")
            bs_line['frequency'] = bs_line['frequency'] / 1000
        mask = mask & (bs_line['frequency'].isin([frequency]))

    bs_line = bs_line[mask].copy()
    
    if apply_avg:
        #angle binning and aggregation
        angles = np.arange(-70, 75, angle_intv)  # angle intervals
        bs_line['angle_bin'] = np.floor(bs_line['angle'] / angle_intv) * angle_intv
        bs_line_filtered = bs_line[(bs_line['angle_bin'] >= angles.min()) & (bs_line['angle_bin'] <= angles.max())]

        df_wide = bs_line_filtered.groupby(['ping_no', 'angle_bin'])['back'].mean().unstack()
        df_wide.reset_index()
        df_wide = df_wide.reindex(columns=angles)

        #moving averages
        df_avg = df_wide.rolling(window=w, min_periods=1, center=True).median()
        df_avg.columns = [f"a_{int(col)}" for col in df_avg.columns]

        #apply AVG correction to original line data
        avg = bs_line.merge(df_avg, left_on='ping_no', right_index=True, how='left')

        if filter_along:
            df_q_low = df_wide.rolling(window=w, min_periods=1, center=True).quantile(q_along)
            df_q_high = df_wide.rolling(window=w, min_periods=1, center=True).quantile(1 - q_along)
            df_q_low.columns = [f"q_low_{int(col)}" for col in df_q_low.columns]
            df_q_high.columns = [f"q_high_{int(col)}" for col in df_q_high.columns]
            avg = avg.merge(df_q_low, left_on='ping_no', right_index=True, how='left')
            avg = avg.merge(df_q_high, left_on='ping_no', right_index=True, how='left')

        avg['back_avg'] = np.nan

        for i in angles:
            #boolean mask for angles within the bin
            B = (avg['angle'] >= i) & (avg['angle'] <= i + angle_intv)
            if not B.any():
                continue

            idx = avg.loc[B].index
            col_current = f"a_{int(i)}"

            if filter_along:
                col_q_low = f"q_low_{int(i)}"
                col_q_high = f"q_high_{int(i)}"
                is_outlier = (avg.loc[idx, 'back'] < avg.loc[idx, col_q_low]) | (
                            avg.loc[idx, 'back'] > avg.loc[idx, col_q_high])
                idx = idx[~is_outlier]

            if method == 'single':
                col_ref = f"a_{-ref}" if i < 0 else f"a_{ref}"
                avg.loc[idx, 'back_avg'] = (
                        avg.loc[idx, 'back']
                        - avg.loc[idx, col_current]
                        + avg.loc[idx, col_ref]
                )
            elif method == 'dual':
                col_neg_ref = f"a_{-ref}"
                col_pos_ref = f"a_{ref}"
                #mean of the reference columns
                ref_angle = avg.loc[idx, [col_neg_ref, col_pos_ref]].median(axis=1)
                avg.loc[idx, 'back_avg'] = (
                        avg.loc[idx, 'back']
                        - avg.loc[idx, col_current]
                        + ref_angle
                )
    #just use the raw backscatter if AVG is disabled
    else:
        avg = bs_line.copy()
        avg['back_avg'] = avg['back']

    #across-track filtering
    if filter_across:
        #quantile filter for each ping
        q_low_back = avg['back_avg'].groupby(avg['ping_no']).transform(lambda x: x.quantile(q_across))
        q_high_back = avg['back_avg'].groupby(avg['ping_no']).transform(lambda x: x.quantile(1-q_across))
        q_low_bathy = avg['depth'].groupby(avg['ping_no']).transform(lambda x: x.quantile(q_across))
        q_high_bathy = avg['depth'].groupby(avg['ping_no']).transform(lambda x: x.quantile(1-q_across))
        mask = (avg['back_avg'] >= q_low_back) & (avg['back_avg'] <= q_high_back) & (avg['depth'] >= q_low_bathy ) & (avg['depth'] <= q_high_bathy)
        avg = avg[mask].copy()
        
    return avg

def rasterize_avg(avg, template_path=None, bounds=None, res=1.0, save_raw=False, save_bathy=False):
    #read a template raster with desired extent and resolution
    if template_path is not None:
        import rasterio
        with rasterio.open(template_path) as tmp:
            tmp_meta = tmp.meta.copy()
            xmin, ymin, xmax, ymax = tmp.bounds
            width = tmp.width
            height = tmp.height
            res_x, res_y = tmp.res
    else:
        #if no template is provided, determine extent from the data
        tmp_meta = None
        if bounds is not None:
            xmin, xmax = bounds[0], bounds[1]
            ymin, ymax = bounds[2], bounds[3]
            width = int(np.ceil((xmax - xmin) / res))
            height = int(np.ceil((ymax - ymin) / res))
            res_x, res_y = res, res
        else:
            xmin, xmax = avg['east'].min(), avg['east'].max()
            ymin, ymax = avg['north'].min(), avg['north'].max()
            width = int(np.ceil((xmax - xmin) / res))
            height = int(np.ceil((ymax - ymin) / res))
            res_x, res_y = res, res

    #determine raster extent
    x_edges = np.linspace(xmin, xmax, width + 1)
    y_edges = np.linspace(ymin, ymax, height + 1)

    output = {
        'raw': None,
        'bathy': None,
        'back': None,
        'meta': tmp_meta,
        'xmin': xmin,
        'xmax': xmax,
        'ymin': ymin,
        'ymax': ymax,
        'y_edges': y_edges,
        'width': width,
        'height': height,
        'res_x': res_x,
        'res_y': res_y
    }

    if save_raw:
        if avg.empty:
            arr_raw = np.full((height, width), np.nan, dtype=np.float32)
        else:
            stat_raw, _, _, _ = binned_statistic_2d(
                x=avg['east'], y=avg['north'], values=avg['back'],
                statistic='mean', bins=[x_edges, y_edges]
            )
            arr_raw = np.flipud(stat_raw.T).astype(np.float32)
            output['raw'] = arr_raw

    if save_bathy:
        if avg.empty:
            arr_bathy = np.full((height, width), np.nan, dtype=np.float32)
        else:
            stat_bathy, _, _, _ = binned_statistic_2d(
                x=avg['east'], y=avg['north'], values=avg['depth'],
                statistic='mean', bins=[x_edges, y_edges]
            )
            arr_bathy = np.flipud(stat_bathy.T).astype(np.float32)
            output['bathy'] = arr_bathy

    if avg.empty:
        arr_avg = np.full((height, width), np.nan, dtype=np.float32)
    else:
        stat_avg, _, _, _ = binned_statistic_2d(
            x=avg['east'], y=avg['north'], values=avg['back_avg'],
            statistic='median', bins=[x_edges, y_edges]
        )
        arr_avg = np.flipud(stat_avg.T).astype(np.float32)
        output['back'] = arr_avg    

    return output

def AVG(bs_line,
        template_path = None,
        bounds = None, #[xmin, xmax, ymin, ymax]
        filter_across = False,
        filter_along = False,
        save_raw = False,
        save_bathy = False,
        q_along = 0.01,
        q_across = 0.01,
        res = 1.0,
        w = 300,
        angle_intv = 5,
        ref = 40,
        frequency = None,
        back_filter = [-80, 20],
        method = 'dual',
        apply_avg = True):

    avg = compute_avg(
        bs_line,
        filter_across = filter_across,
        filter_along = filter_along,
        q_along = q_along,
        q_across = q_across,
        w = w,
        angle_intv = angle_intv,
        ref = ref,
        frequency = frequency,
        back_filter = back_filter,
        method = method,
        apply_avg = apply_avg
    )

    #rasterize
    return rasterize_avg(
        avg,
        template_path = template_path,
        bounds = bounds,
        res = res,
        save_raw = save_raw,
        save_bathy = save_bathy
    )