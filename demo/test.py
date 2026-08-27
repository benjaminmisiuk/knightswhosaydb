import knightswhosaydb as kdb

kdb.mosaic(
    dir_path = "/home/data/test_data/Egmont_Key/kmall/",
    format = 'kmall',
    out_lines = 'lines',
    mosaic_path = 'egmont025.tif',
    crs = "EPSG:32617",
    save_lines=True,
    res=0.25
)