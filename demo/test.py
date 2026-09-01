import knightswhosaydb as kdb

kdb.mosaic(
    dir_path = "/home/data/test_data/m143/",
    format = 'all',
    out_lines = 'lines',
    mosaic_path = 'egmont025_b.tif',
    crs = "EPSG:32635",
    layer='depth',
    save_lines=True,
    res=10
)
# kdb.mosaic(
#     dir_path = "/home/data/test_data/Egmont_Key/kmall/",
#     format = 'kmall',
#     out_lines = 'lines',
#     mosaic_path = 'egmont025_r.tif',
#     crs = "EPSG:32617",
#     layer='raw',
#     save_lines=True,
#     res=0.25
# )
# kdb.mosaic(
#     dir_path = "/home/data/test_data/Egmont_Key/kmall/",
#     format = 'kmall',
#     out_lines = 'lines',
#     mosaic_path = 'egmont025_avg.tif',
#     crs = "EPSG:32617",
#     layer='backscatter',
#     save_lines=True,
#     res=0.25
# )
