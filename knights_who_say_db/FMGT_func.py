def read_fmgt(file, col_map = None, **kwargs):
    import pandas as pd
    import re

    if col_map is None:
        col_map = {
                "Ping Time": "time",
                "Ping Number": "ping_no",
                "Beam Number": "beam_no",
                "Easting": "east",
                "Northing": "north",
                "Depth": "depth",
                "Longitude": "long",
                "Latitude": "lat",
                "Backscatter Value": "back_raw",
                "Corrected Backscatter Value": "back",
                "True Angle": "angle",
                "Frequency": "frequency",
                "Saturation flag": "sat_flag"
            }

    raw_columns = []
    skiprows = 0

    with open(file, 'r') as f:
        for line in f:
            line_str = line.strip()

            #stop scanning at a line that starts with a number
            if line_str and (line_str[0].isdigit() or line_str.startswith('-')):
                break

            skiprows += 1

            #extract column names
            if ':' in line_str and not any(header_tag in line_str for header_tag in ["Filename", "Ping Count", "Columns"]):
                col_name = line_str.split(':', 1)[1].strip()
                if col_name:
                    raw_columns.append(col_name)

    clean_cols = [
            col_map.get(col, re.sub(r'\s+', '_', col.lower()))
            for col in raw_columns
        ]

    return(
        pd.read_csv(
            file,
            sep=r'\s+',
            skiprows=skiprows,
            names=clean_cols,
            engine='c'
        )
    )